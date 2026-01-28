import os
import hashlib
import zlib
from typing import Union, Optional, List, Dict, Any
import shutil

class GitObject:
    """
    Base class for Git objects (blob, tree, commit).
    Implements object serialization and deserialization.
    """

    def __init__(self, obj_type: str, data: bytes):
        """
        Initializes a Git object.

        Args:
            obj_type: The type of the Git object (e.g., "blob", "tree", "commit").
            data: The raw data of the Git object.
        """
        self.type: str = obj_type
        self.data: bytes = data

    def serialize(self) -> bytes:
        """
        Serializes the Git object into a byte stream suitable for storage.

        Returns:
            The serialized byte stream.
        """
        header: bytes = f"{self.type} {len(self.data)}\0".encode("utf-8")
        return header + self.data

    def deserialize(self, data: bytes) -> None:
        """
        Deserializes a byte stream into a Git object.

        Args:
            data: The byte stream to deserialize.
        """
        header, self.data = data.split(b"\0", 1)
        self.type = header.split(b" ")[0].decode("utf-8")

    def calculate_hash(self) -> str:
        """
        Calculates the SHA-1 hash of the serialized object.

        Returns:
            The SHA-1 hash as a hexadecimal string.
        """
        serialized_data: bytes = self.serialize()
        return hashlib.sha1(serialized_data).hexdigest()


class Blob(GitObject):
    """
    Represents a Git blob object, which stores file data.
    """

    def __init__(self, data: bytes):
        """
        Initializes a Blob object.

        Args:
            data: The content of the file as bytes.
        """
        super().__init__("blob", data)


class Tree(GitObject):
    """
    Represents a Git tree object, which stores directory structure.
    """

    def __init__(self, entries: List[Dict[str, str]]):
        """
        Initializes a Tree object.

        Args:
            entries: A list of dictionaries, where each dictionary represents
                     a tree entry with keys "mode", "type", "name", and "hash".
        """
        self.entries: List[Dict[str, str]] = entries
        data: bytes = b"".join(
            f"{entry['mode']} {entry['name']}\0{bytes.fromhex(entry['hash'])}"
            .encode("utf-8")
            for entry in entries
        )
        super().__init__("tree", data)


class Commit(GitObject):
    """
    Represents a Git commit object, which stores commit metadata.
    """

    def __init__(self, tree: str, parents: List[str], author: str, committer: str, message: str):
        """
        Initializes a Commit object.

        Args:
            tree: The hash of the tree object this commit points to.
            parents: A list of parent commit hashes.
            author: The author of the commit.
            committer: The committer of the commit.
            message: The commit message.
        """
        self.tree: str = tree
        self.parents: List[str] = parents
        self.author: str = author
        self.committer: str = committer
        self.message: str = message

        data: bytes = (
            f"tree {tree}\n"
            + "".join(f"parent {parent}\n" for parent in parents)
            + f"author {author}\n"
            + f"committer {committer}\n"
            + f"\n{message}"
        ).encode("utf-8")
        super().__init__("commit", data)


class GitRepository:
    """
    Represents a Git repository.
    Manages object storage and retrieval.
    """

    def __init__(self, git_dir: str):
        """
        Initializes a Git repository.

        Args:
            git_dir: The path to the .git directory.
        """
        self.git_dir: str = git_dir

    def object_path(self, object_hash: str) -> str:
        """
        Constructs the path to a Git object file.

        Args:
            object_hash: The SHA-1 hash of the object.

        Returns:
            The path to the object file.
        """
        return os.path.join(self.git_dir, "objects", object_hash[:2], object_hash[2:])

    def store_object(self, obj: GitObject) -> str:
        """
        Stores a Git object in the object database.

        Args:
            obj: The Git object to store.

        Returns:
            The SHA-1 hash of the stored object.
        """
        object_hash: str = obj.calculate_hash()
        object_path: str = self.object_path(object_hash)

        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(object_path), exist_ok=True)

        try:
            with open(object_path, "wb") as f:
                compressed_data: bytes = zlib.compress(obj.serialize())
                f.write(compressed_data)
        except OSError as e:
            print(f"Error writing to object file: {e}")
            raise

        return object_hash

    def load_object(self, object_hash: str) -> Optional[GitObject]:
        """
        Loads a Git object from the object database.

        Args:
            object_hash: The SHA-1 hash of the object to load.

        Returns:
            The Git object, or None if the object is not found.
        """
        object_path: str = self.object_path(object_hash)

        try:
            with open(object_path, "rb") as f:
                compressed_data: bytes = f.read()
                serialized_data: bytes = zlib.decompress(compressed_data)
        except FileNotFoundError:
            print(f"Object not found: {object_hash}")
            return None
        except OSError as e:
            print(f"Error reading object file: {e}")
            return None
        except zlib.error as e:
            print(f"Error decompressing object: {e}")
            return None

        # Determine object type from serialized data
        try:
            obj_type: str = serialized_data.split(b' ')[0].decode('utf-8')

            if obj_type == "blob":
                obj: GitObject = Blob(b'')  # Create a dummy Blob object
            elif obj_type == "tree":
                obj = Tree([]) # Create a dummy Tree Object
            elif obj_type == "commit":
                obj = Commit("", [], "", "", "") # Create a dummy Commit object
            else:
                print(f"Unknown object type: {obj_type}")
                return None

            obj.deserialize(serialized_data)
            return obj

        except Exception as e:
            print(f"Error deserializing object: {e}")
            return None

    def create_initial_commit(self, author: str, committer: str, message: str) -> str:
        """
        Creates the initial commit in the repository.

        Args:
            author: The author of the commit.
            committer: The committer of the commit.
            message: The commit message.

        Returns:
            The hash of the initial commit.
        """

        # Create an empty tree
        empty_tree = Tree([])
        tree_hash = self.store_object(empty_tree)

        # Create the commit object
        commit = Commit(tree_hash, [], author, committer, message)
        commit_hash = self.store_object(commit)

        # Update the HEAD reference
        self.update_ref("HEAD", commit_hash)

        return commit_hash

    def update_ref(self, ref_name: str, object_hash: str) -> None:
        """
        Updates a reference (e.g., HEAD, branch) to point to a specific object.

        Args:
            ref_name: The name of the reference.
            object_hash: The SHA-1 hash of the object to point to.
        """
        ref_path: str = os.path