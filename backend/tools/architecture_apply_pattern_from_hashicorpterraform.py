import json
import os
from typing import Any, Dict, Optional, Tuple, Union

class StateManager:
    """
    Manages the state of the Darwin System, providing persistence and
    concurrency control. Inspired by Terraform's state management.

    This class handles reading, writing, and updating the state file,
    ensuring data integrity and preventing race conditions.
    """

    def __init__(self, state_file: str = "darwin.tfstate") -> None:
        """
        Initializes the StateManager with the specified state file path.

        Args:
            state_file: The path to the state file.  Defaults to "darwin.tfstate".
        """
        self.state_file: str = state_file
        self._lock: bool = False  # Simple in-memory lock for demonstration purposes.
                                 # In a production environment, consider using a more robust
                                 # locking mechanism like a file lock or a database lock.

    def lock(self, timeout: float = 60.0) -> bool:
        """
        Acquires a lock on the state file.

        Args:
            timeout: The maximum time to wait for the lock, in seconds.

        Returns:
            True if the lock was acquired successfully, False otherwise.
        """
        start_time: float = os.times().elapsed_sec
        while self._lock:
            if os.times().elapsed_sec - start_time > timeout:
                return False
            # In a real-world scenario, we would likely sleep for a short interval here
            # to avoid busy-waiting.
            pass  # Placeholder for sleep in a real implementation.

        self._lock = True
        return True

    def unlock(self) -> None:
        """
        Releases the lock on the state file.
        """
        self._lock = False

    def read_state(self) -> Dict[str, Any]:
        """
        Reads the state from the state file.

        Returns:
            A dictionary representing the state, or an empty dictionary if the
            file does not exist or is empty.
        """
        try:
            if not os.path.exists(self.state_file):
                return {}

            with open(self.state_file, "r") as f:
                try:
                    state: Dict[str, Any] = json.load(f)
                    return state
                except json.JSONDecodeError:
                    print(f"Warning: State file {self.state_file} is corrupted. Returning empty state.")
                    return {}
        except Exception as e:
            print(f"Error reading state file: {e}")
            return {}

    def write_state(self, state: Dict[str, Any]) -> bool:
        """
        Writes the state to the state file.

        Args:
            state: The dictionary representing the state to write.

        Returns:
            True if the state was written successfully, False otherwise.
        """
        try:
            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=4)  # Pretty-print the JSON for readability
            return True
        except Exception as e:
            print(f"Error writing state file: {e}")
            return False

    def update_state(self, key: str, value: Any) -> bool:
        """
        Updates a specific key in the state with the given value.

        Args:
            key: The key to update.
            value: The value to set for the key.

        Returns:
            True if the state was updated successfully, False otherwise.
        """
        if not self.lock():
            print("Error: Could not acquire lock to update state.")
            return False

        try:
            state: Dict[str, Any] = self.read_state()
            state[key] = value
            success: bool = self.write_state(state)
            return success
        except Exception as e:
            print(f"Error updating state: {e}")
            return False
        finally:
            self.unlock()

    def delete_state(self, key: str) -> bool:
        """
        Deletes a specific key from the state.

        Args:
            key: The key to delete.

        Returns:
            True if the key was deleted successfully, False otherwise.
        """
        if not self.lock():
            print("Error: Could not acquire lock to delete from state.")
            return False

        try:
            state: Dict[str, Any] = self.read_state()
            if key in state:
                del state[key]
            success: bool = self.write_state(state)
            return success
        except Exception as e:
            print(f"Error deleting state: {e}")
            return False
        finally:
            self.unlock()

class Resource:
    """
    Represents a resource in the Darwin System.  This is a simplified
    example and would be extended in a real-world scenario.
    """

    def __init__(self, resource_type: str, name: str, attributes: Dict[str, Any]) -> None:
        """
        Initializes a Resource object.

        Args:
            resource_type: The type of the resource (e.g., "compute_instance").
            name: The name of the resource.
            attributes: A dictionary of attributes for the resource.
        """
        self.resource_type: str = resource_type
        self.name: str = name
        self.attributes: Dict[str, Any] = attributes

    def create(self, state_manager: StateManager) -> bool:
        """
        Creates the resource.  This is a placeholder for the actual creation logic.

        Args:
            state_manager: The StateManager instance to use for persisting state.

        Returns:
            True if the resource was created successfully, False otherwise.
        """
        print(f"Creating resource: {self.resource_type}.{self.name}")
        # Simulate resource creation by adding it to the state.
        state_key: str = f"{self.resource_type}.{self.name}"
        if not state_manager.update_state(state_key, self.attributes):
            print(f"Error: Failed to update state for resource {state_key}")
            return False
        return True

    def delete(self, state_manager: StateManager) -> bool:
        """
        Deletes the resource.  This is a placeholder for the actual deletion logic.

        Args:
            state_manager: The StateManager instance to use for persisting state.

        Returns:
            True if the resource was deleted successfully, False otherwise.
        """
        print(f"Deleting resource: {self.resource_type}.{self.name}")
        # Simulate resource deletion by removing it from the state.
        state_key: str = f"{self.resource_type}.{self.name}"
        if not state_manager.delete_state(state_key):
            print(f"Error: Failed to delete state for resource {state_key}")
            return False
        return True

def main() -> None:
    """
    Main function to demonstrate the usage of the StateManager and Resource classes.
    """
    state_manager: StateManager = StateManager("darwin.tfstate")

    # Create a resource
    resource1: Resource = Resource(
        "compute_instance",
        "web_server",
        {"size": "large", "ami": "ami-12345"}
    )
    resource1.create(state_manager)

    # Create another resource
    resource2: Resource = Resource(
        "database",
        "my_database",
        {"engine": "postgres", "version": "14"}
    )
    resource2.create(state_manager)

    # Read and print the state
    current_state: Dict[str, Any] = state_manager.read_state()
    print("Current State:")
    print(json.dumps(current_state, indent=4))

    # Delete a resource
    resource1.delete(state_manager)

    # Read and print the updated state
    updated_state: Dict[str, Any] = state_manager.read_state()
    print("\nUpdated State:")
    print(json.dumps(updated_state, indent=4))

if __name__ == "__main__":
    main()