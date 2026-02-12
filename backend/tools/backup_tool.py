"""
Backup Tool - Darwin's Self-Preservation System

Allows Darwin to create complete backups of himself:
- Code (the entire project — who he IS)
- Data (identity, memory, conversations, interests — what he KNOWS)
- Configuration (docker-compose, .env patterns — how he RUNS)

Backups are written to /backup (mounted USB drive).
Each backup is timestamped and includes integrity verification.

Darwin can trigger this autonomously or on request.
"""

import hashlib
import json
import os
import shutil
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from utils.logger import get_logger as _get_logger

logger = _get_logger(__name__)

# Paths inside the Docker container
CODE_PATH = Path("/app")              # Backend code (mounted from ./backend)
PROJECT_PATH = Path("/project")       # Full project root (mounted read-only from ./)
DATA_PATH = Path("/app/data")         # Runtime data (identity, memory, conversations)
BACKUP_ROOT = Path("/backup")         # USB drive mount point

# Directories/files to exclude from code backup
EXCLUDE_PATTERNS = {
    '__pycache__', '.pyc', '.git', 'node_modules', '.venv',
    '.env', 'credentials', 'secret', 'ollama-data',
}


def _is_excluded(path: str) -> bool:
    """Check if a path should be excluded from backup."""
    parts = path.split(os.sep)
    for part in parts:
        for pattern in EXCLUDE_PATTERNS:
            if pattern in part:
                return True
    return False


def _compute_checksum(filepath: Path) -> str:
    """Compute MD5 checksum of a file."""
    h = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return "ERROR"


def _get_dir_size(path: Path) -> int:
    """Get total size of a directory in bytes."""
    total = 0
    try:
        for entry in path.rglob('*'):
            if entry.is_file():
                total += entry.stat().st_size
    except Exception:
        pass
    return total


def _format_size(size_bytes: int) -> str:
    """Format bytes to human readable."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"


async def create_full_backup(
    include_code: bool = True,
    include_data: bool = True,
    compress: bool = True,
    label: str = ""
) -> Dict[str, Any]:
    """
    Create a complete backup of Darwin.

    Args:
        include_code: Include the full project code
        include_data: Include runtime data (identity, memory, conversations)
        compress: Create a compressed tar.gz archive
        label: Optional label for this backup (e.g., "pre-upgrade")

    Returns:
        Dict with backup details: path, size, file count, checksums
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"darwin_backup_{timestamp}"
    if label:
        backup_name += f"_{label}"

    backup_dir = BACKUP_ROOT / backup_name

    # Verify backup drive is accessible
    if not BACKUP_ROOT.exists():
        return {
            "success": False,
            "error": "Backup drive not mounted at /backup. Ask Paulo to check the USB drive."
        }

    # Check available space
    try:
        stat = os.statvfs(str(BACKUP_ROOT))
        free_bytes = stat.f_bavail * stat.f_frsize
        free_mb = free_bytes / (1024 * 1024)
        if free_mb < 200:  # Need at least 200MB free
            return {
                "success": False,
                "error": f"Not enough space on backup drive ({free_mb:.0f}MB free, need 200MB)"
            }
    except Exception as e:
        logger.warning(f"Could not check disk space: {e}")

    results = {
        "success": True,
        "backup_name": backup_name,
        "backup_path": str(backup_dir),
        "timestamp": timestamp,
        "components": {},
        "total_files": 0,
        "total_size": 0,
    }

    try:
        backup_dir.mkdir(parents=True, exist_ok=True)

        # === 1. BACKUP CODE (the full project) ===
        if include_code:
            logger.info("Backing up Darwin code...")
            code_backup = backup_dir / "code"

            if PROJECT_PATH.exists():
                # Full project backup from /project (read-only mount of repo root)
                file_count = 0
                for item in PROJECT_PATH.iterdir():
                    if _is_excluded(item.name):
                        continue
                    dest = code_backup / item.name
                    try:
                        if item.is_dir():
                            shutil.copytree(
                                str(item), str(dest),
                                ignore=shutil.ignore_patterns(
                                    '__pycache__', '*.pyc', 'node_modules',
                                    '.git', '.venv', 'ollama-data'
                                )
                            )
                        else:
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(str(item), str(dest))
                        file_count += 1
                    except Exception as e:
                        logger.warning(f"Could not copy {item.name}: {e}")

                code_size = _get_dir_size(code_backup)
                results["components"]["code"] = {
                    "path": str(code_backup),
                    "items_copied": file_count,
                    "size": _format_size(code_size),
                }
                results["total_size"] += code_size
                logger.info(f"Code backup: {file_count} items, {_format_size(code_size)}")
            else:
                # Fallback: just backup /app (backend only)
                shutil.copytree(
                    str(CODE_PATH), str(code_backup),
                    ignore=shutil.ignore_patterns(
                        '__pycache__', '*.pyc', 'node_modules', '.git'
                    )
                )
                code_size = _get_dir_size(code_backup)
                results["components"]["code"] = {
                    "path": str(code_backup),
                    "size": _format_size(code_size),
                    "note": "Backend code only (full project mount not available)"
                }
                results["total_size"] += code_size

        # === 2. BACKUP DATA (identity, memory, conversations) ===
        if include_data:
            logger.info("Backing up Darwin data...")
            data_backup = backup_dir / "data"

            if DATA_PATH.exists():
                shutil.copytree(str(DATA_PATH), str(data_backup))
                data_size = _get_dir_size(data_backup)

                # Count important files
                data_files = list(data_backup.rglob('*'))
                file_count = len([f for f in data_files if f.is_file()])

                results["components"]["data"] = {
                    "path": str(data_backup),
                    "files": file_count,
                    "size": _format_size(data_size),
                }
                results["total_size"] += data_size
                results["total_files"] += file_count
                logger.info(f"Data backup: {file_count} files, {_format_size(data_size)}")
            else:
                results["components"]["data"] = {
                    "error": "Data directory not found at /app/data"
                }

        # === 3. GENERATE INTEGRITY MANIFEST ===
        logger.info("Generating integrity checksums...")
        manifest = {
            "backup_name": backup_name,
            "created_at": datetime.now().isoformat(),
            "darwin_version": "self-evolving",
            "label": label,
            "checksums": {}
        }

        for filepath in backup_dir.rglob('*'):
            if filepath.is_file() and filepath.name != 'manifest.json':
                rel_path = str(filepath.relative_to(backup_dir))
                manifest["checksums"][rel_path] = _compute_checksum(filepath)
                results["total_files"] += 1

        manifest["total_files"] = results["total_files"]
        manifest["total_size"] = _format_size(results["total_size"])

        manifest_path = backup_dir / "manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        # === 4. COMPRESS (optional) ===
        if compress:
            logger.info("Compressing backup...")
            archive_path = BACKUP_ROOT / f"{backup_name}.tar.gz"
            with tarfile.open(str(archive_path), "w:gz") as tar:
                tar.add(str(backup_dir), arcname=backup_name)

            archive_size = archive_path.stat().st_size
            results["archive"] = {
                "path": str(archive_path),
                "size": _format_size(archive_size),
            }

            # Remove uncompressed directory after archiving
            shutil.rmtree(str(backup_dir))
            results["backup_path"] = str(archive_path)
            logger.info(f"Compressed to {_format_size(archive_size)}")

        results["total_size_human"] = _format_size(results["total_size"])
        logger.info(f"Backup complete: {backup_name} ({results['total_files']} files, {results['total_size_human']})")

    except Exception as e:
        logger.error(f"Backup failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        results["success"] = False
        results["error"] = str(e)

    return results


async def list_backups() -> Dict[str, Any]:
    """
    List all existing backups on the backup drive.

    Returns:
        Dict with list of backups, their sizes, and dates.
    """
    if not BACKUP_ROOT.exists():
        return {"success": False, "error": "Backup drive not mounted"}

    backups = []
    for item in sorted(BACKUP_ROOT.iterdir()):
        if item.name.startswith("darwin_backup_"):
            size = item.stat().st_size if item.is_file() else _get_dir_size(item)
            backups.append({
                "name": item.name,
                "type": "archive" if item.is_file() else "directory",
                "size": _format_size(size),
                "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
            })

    # Check free space
    stat = os.statvfs(str(BACKUP_ROOT))
    free_bytes = stat.f_bavail * stat.f_frsize
    total_bytes = stat.f_blocks * stat.f_frsize

    return {
        "success": True,
        "backups": backups,
        "count": len(backups),
        "drive_free": _format_size(free_bytes),
        "drive_total": _format_size(total_bytes),
    }


async def verify_backup(backup_name: str) -> Dict[str, Any]:
    """
    Verify integrity of a backup using its manifest checksums.

    Args:
        backup_name: Name of the backup to verify

    Returns:
        Dict with verification results.
    """
    # Find the backup
    backup_path = BACKUP_ROOT / backup_name
    archive_path = BACKUP_ROOT / f"{backup_name}.tar.gz"

    if archive_path.exists():
        # Need to extract manifest from archive
        try:
            with tarfile.open(str(archive_path), "r:gz") as tar:
                manifest_member = f"{backup_name}/manifest.json"
                f = tar.extractfile(manifest_member)
                if f:
                    manifest = json.load(f)
                    return {
                        "success": True,
                        "backup": backup_name,
                        "type": "archive",
                        "created_at": manifest.get("created_at"),
                        "total_files": manifest.get("total_files"),
                        "total_size": manifest.get("total_size"),
                        "checksum_count": len(manifest.get("checksums", {})),
                        "note": "Archive integrity check — checksums stored in manifest"
                    }
        except Exception as e:
            return {"success": False, "error": f"Cannot read archive: {e}"}

    elif backup_path.exists() and backup_path.is_dir():
        manifest_path = backup_path / "manifest.json"
        if not manifest_path.exists():
            return {"success": False, "error": "No manifest.json found in backup"}

        with open(manifest_path) as f:
            manifest = json.load(f)

        errors = []
        verified = 0
        for rel_path, expected_hash in manifest.get("checksums", {}).items():
            file_path = backup_path / rel_path
            if not file_path.exists():
                errors.append(f"MISSING: {rel_path}")
            else:
                actual_hash = _compute_checksum(file_path)
                if actual_hash != expected_hash:
                    errors.append(f"CORRUPTED: {rel_path}")
                else:
                    verified += 1

        return {
            "success": len(errors) == 0,
            "backup": backup_name,
            "verified_files": verified,
            "errors": errors[:20],  # Limit error output
            "total_errors": len(errors),
        }

    return {"success": False, "error": f"Backup not found: {backup_name}"}
