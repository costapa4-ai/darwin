"""
File Operations Tool - Darwin's Read/Write Capabilities

Gives Darwin the ability to:
- Read files from the project and data directories
- Write/create files in safe writable directories
- List directory contents
- Check file existence and metadata
- Append to files (logs, notes, etc.)

Safety boundaries:
- READABLE: /app (backend), /project (full repo), /backup, /tmp
- WRITABLE: /backup, /app/data, /app/tools, /app/logs, /tmp
- BLOCKED: .env, credentials, secrets, SSH keys, docker configs with secrets
- MAX file size: 10MB read, 1MB write
"""

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from utils.logger import get_logger as _get_logger

logger = _get_logger(__name__)

# === SAFETY BOUNDARIES ===

# Directories Darwin can READ from (inside Docker container)
READABLE_ROOTS = [
    Path("/app"),        # Backend code
    Path("/project"),    # Full project (read-only mount)
    Path("/backup"),     # Backup drive
    Path("/tmp"),        # Temporary files
]

# Directories Darwin can WRITE to
WRITABLE_ROOTS = [
    Path("/backup"),     # USB backup drive
    Path("/app/data"),   # Runtime data (identity, memory, etc.)
    Path("/app/tools"),  # Darwin can create new tools!
    Path("/app/logs"),   # Log files
    Path("/tmp"),        # Temporary workspace
]

# File patterns that are NEVER readable or writable
BLOCKED_PATTERNS = {
    '.env', '.secret', 'credentials', 'private_key', 'id_rsa',
    'id_ed25519', '.pem', '.key', 'password', 'token',
}

# Extensions that are blocked from writing (binaries, executables)
BLOCKED_WRITE_EXTENSIONS = {
    '.exe', '.bin', '.so', '.dll', '.dylib', '.sh',
}

MAX_READ_SIZE = 10 * 1024 * 1024   # 10MB
MAX_WRITE_SIZE = 1 * 1024 * 1024   # 1MB


def _is_path_readable(path: Path) -> bool:
    """Check if a path is within readable boundaries."""
    resolved = path.resolve()
    return any(
        str(resolved).startswith(str(root))
        for root in READABLE_ROOTS
    )


def _is_path_writable(path: Path) -> bool:
    """Check if a path is within writable boundaries."""
    resolved = path.resolve()
    return any(
        str(resolved).startswith(str(root))
        for root in WRITABLE_ROOTS
    )


def _is_blocked(path: Path) -> bool:
    """Check if a file matches blocked patterns (secrets, credentials)."""
    name_lower = path.name.lower()
    for pattern in BLOCKED_PATTERNS:
        if pattern in name_lower:
            return True
    return False


def _is_write_blocked(path: Path) -> bool:
    """Check if a file extension is blocked for writing."""
    return path.suffix.lower() in BLOCKED_WRITE_EXTENSIONS


async def read_file(
    file_path: str,
    encoding: str = "utf-8",
    max_lines: int = 0
) -> Dict[str, Any]:
    """
    Read the contents of a file.

    Args:
        file_path: Absolute path to the file to read.
        encoding: File encoding (default utf-8).
        max_lines: If > 0, only return this many lines from the start.

    Returns:
        Dict with file content, size, and metadata.
    """
    path = Path(file_path)

    if not _is_path_readable(path):
        return {
            "success": False,
            "error": f"Path not readable: {file_path}. Allowed: {[str(r) for r in READABLE_ROOTS]}"
        }

    if _is_blocked(path):
        return {
            "success": False,
            "error": f"Blocked: {path.name} matches a protected pattern (secrets/credentials)"
        }

    if not path.exists():
        return {"success": False, "error": f"File not found: {file_path}"}

    if not path.is_file():
        return {"success": False, "error": f"Not a file: {file_path}"}

    size = path.stat().st_size
    if size > MAX_READ_SIZE:
        return {
            "success": False,
            "error": f"File too large: {size} bytes (max {MAX_READ_SIZE})"
        }

    try:
        with open(path, 'r', encoding=encoding) as f:
            if max_lines > 0:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    lines.append(line)
                content = "".join(lines)
                truncated = i >= max_lines  # noqa: F821
            else:
                content = f.read()
                truncated = False

        logger.info(f"Darwin read file: {file_path} ({len(content)} chars)")

        return {
            "success": True,
            "file_path": file_path,
            "content": content,
            "size_bytes": size,
            "lines": content.count('\n'),
            "truncated": truncated,
            "encoding": encoding,
        }

    except UnicodeDecodeError:
        return {
            "success": False,
            "error": f"Cannot read {file_path} as {encoding} — may be a binary file"
        }
    except Exception as e:
        logger.error(f"Failed to read {file_path}: {e}")
        return {"success": False, "error": str(e)}


async def write_file(
    file_path: str,
    content: str,
    create_dirs: bool = True,
    overwrite: bool = True
) -> Dict[str, Any]:
    """
    Write content to a file.

    Args:
        file_path: Absolute path where to write.
        content: Text content to write.
        create_dirs: Create parent directories if they don't exist.
        overwrite: If False, refuse to overwrite existing files.

    Returns:
        Dict with write result and file metadata.
    """
    path = Path(file_path)

    if not _is_path_writable(path):
        return {
            "success": False,
            "error": f"Path not writable: {file_path}. Allowed: {[str(r) for r in WRITABLE_ROOTS]}"
        }

    if _is_blocked(path):
        return {
            "success": False,
            "error": f"Blocked: {path.name} matches a protected pattern"
        }

    if _is_write_blocked(path):
        return {
            "success": False,
            "error": f"Blocked extension: {path.suffix} — cannot write binary/executable files"
        }

    content_size = len(content.encode('utf-8'))
    if content_size > MAX_WRITE_SIZE:
        return {
            "success": False,
            "error": f"Content too large: {content_size} bytes (max {MAX_WRITE_SIZE})"
        }

    if not overwrite and path.exists():
        return {
            "success": False,
            "error": f"File already exists: {file_path} (overwrite=False)"
        }

    try:
        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)

        existed = path.exists()
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Darwin wrote file: {file_path} ({content_size} bytes, {'overwritten' if existed else 'created'})")

        return {
            "success": True,
            "file_path": file_path,
            "size_bytes": content_size,
            "lines": content.count('\n'),
            "action": "overwritten" if existed else "created",
        }

    except Exception as e:
        logger.error(f"Failed to write {file_path}: {e}")
        return {"success": False, "error": str(e)}


async def append_file(
    file_path: str,
    content: str,
    create_if_missing: bool = True
) -> Dict[str, Any]:
    """
    Append content to an existing file (useful for logs, notes).

    Args:
        file_path: Absolute path to append to.
        content: Text content to append.
        create_if_missing: Create the file if it doesn't exist.

    Returns:
        Dict with append result.
    """
    path = Path(file_path)

    if not _is_path_writable(path):
        return {
            "success": False,
            "error": f"Path not writable: {file_path}"
        }

    if _is_blocked(path):
        return {"success": False, "error": f"Blocked: {path.name}"}

    if not create_if_missing and not path.exists():
        return {"success": False, "error": f"File not found: {file_path}"}

    content_size = len(content.encode('utf-8'))
    if content_size > MAX_WRITE_SIZE:
        return {"success": False, "error": f"Content too large: {content_size} bytes"}

    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'a', encoding='utf-8') as f:
            f.write(content)

        new_size = path.stat().st_size
        logger.info(f"Darwin appended to: {file_path} (+{content_size} bytes, total {new_size})")

        return {
            "success": True,
            "file_path": file_path,
            "appended_bytes": content_size,
            "total_size": new_size,
        }

    except Exception as e:
        logger.error(f"Failed to append to {file_path}: {e}")
        return {"success": False, "error": str(e)}


async def list_directory(
    dir_path: str,
    pattern: str = "*",
    recursive: bool = False,
    include_hidden: bool = False
) -> Dict[str, Any]:
    """
    List contents of a directory.

    Args:
        dir_path: Absolute path to the directory.
        pattern: Glob pattern to filter files (e.g., "*.py").
        recursive: If True, search recursively.
        include_hidden: If True, include dotfiles/dotdirs.

    Returns:
        Dict with directory listing.
    """
    path = Path(dir_path)

    if not _is_path_readable(path):
        return {
            "success": False,
            "error": f"Path not readable: {dir_path}"
        }

    if not path.exists():
        return {"success": False, "error": f"Directory not found: {dir_path}"}

    if not path.is_dir():
        return {"success": False, "error": f"Not a directory: {dir_path}"}

    try:
        entries = []
        glob_func = path.rglob if recursive else path.glob

        for item in sorted(glob_func(pattern)):
            if not include_hidden and item.name.startswith('.'):
                continue
            if _is_blocked(item):
                continue

            try:
                stat = item.stat()
                entries.append({
                    "name": item.name,
                    "path": str(item),
                    "type": "dir" if item.is_dir() else "file",
                    "size": stat.st_size if item.is_file() else None,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
            except (OSError, PermissionError):
                continue

            # Cap at 200 entries to avoid huge responses
            if len(entries) >= 200:
                break

        logger.info(f"Darwin listed: {dir_path} ({len(entries)} entries)")

        return {
            "success": True,
            "dir_path": dir_path,
            "pattern": pattern,
            "entries": entries,
            "count": len(entries),
            "truncated": len(entries) >= 200,
        }

    except Exception as e:
        logger.error(f"Failed to list {dir_path}: {e}")
        return {"success": False, "error": str(e)}


async def file_info(file_path: str) -> Dict[str, Any]:
    """
    Get metadata about a file or directory.

    Args:
        file_path: Absolute path to check.

    Returns:
        Dict with file existence, type, size, permissions, etc.
    """
    path = Path(file_path)

    if not _is_path_readable(path):
        return {"success": False, "error": f"Path not readable: {file_path}"}

    if _is_blocked(path):
        return {"success": False, "error": f"Blocked: {path.name}"}

    if not path.exists():
        return {
            "success": True,
            "exists": False,
            "file_path": file_path,
        }

    try:
        stat = path.stat()
        info = {
            "success": True,
            "exists": True,
            "file_path": file_path,
            "name": path.name,
            "type": "directory" if path.is_dir() else "file",
            "size_bytes": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "readable": os.access(path, os.R_OK),
            "writable": os.access(path, os.W_OK),
        }

        if path.is_file():
            info["extension"] = path.suffix
            # Compute checksum for small files
            if stat.st_size < 1024 * 1024:  # <1MB
                h = hashlib.md5()
                with open(path, 'rb') as f:
                    for chunk in iter(lambda: f.read(8192), b''):
                        h.update(chunk)
                info["md5"] = h.hexdigest()

        return info

    except Exception as e:
        logger.error(f"Failed to get info for {file_path}: {e}")
        return {"success": False, "error": str(e)}


async def search_files(
    dir_path: str,
    text: str,
    file_pattern: str = "*.py",
    max_results: int = 20
) -> Dict[str, Any]:
    """
    Search for text content within files.

    Args:
        dir_path: Directory to search in.
        text: Text string to search for (case-insensitive).
        file_pattern: Glob pattern for files to search (default: *.py).
        max_results: Maximum number of matches to return.

    Returns:
        Dict with matching files and line numbers.
    """
    path = Path(dir_path)

    if not _is_path_readable(path):
        return {"success": False, "error": f"Path not readable: {dir_path}"}

    if not path.exists() or not path.is_dir():
        return {"success": False, "error": f"Not a valid directory: {dir_path}"}

    try:
        matches = []
        text_lower = text.lower()

        for file_path in path.rglob(file_pattern):
            if _is_blocked(file_path):
                continue
            if not file_path.is_file():
                continue
            if file_path.stat().st_size > MAX_READ_SIZE:
                continue

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        if text_lower in line.lower():
                            matches.append({
                                "file": str(file_path),
                                "line": line_num,
                                "content": line.strip()[:200],
                            })
                            if len(matches) >= max_results:
                                break
            except (OSError, PermissionError):
                continue

            if len(matches) >= max_results:
                break

        logger.info(f"Darwin searched '{text}' in {dir_path}: {len(matches)} matches")

        return {
            "success": True,
            "query": text,
            "dir_path": dir_path,
            "file_pattern": file_pattern,
            "matches": matches,
            "count": len(matches),
            "truncated": len(matches) >= max_results,
        }

    except Exception as e:
        logger.error(f"Search failed: {e}")
        return {"success": False, "error": str(e)}
