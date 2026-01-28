"""
Auto-Applier: Applies approved changes to code with backup and rollback
Handles file modifications, backups, and rollback mechanism
"""
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import json


@dataclass
class AppliedChange:
    """Record of an applied change"""
    rollback_id: str
    change_id: str
    file_path: str
    backup_path: str
    applied_at: str
    success: bool
    error: Optional[str] = None


class AutoApplier:
    """
    Applies approved code changes with backup and rollback capability
    """

    def __init__(
        self,
        backup_dir: str = "/app/backups",
        project_root: str = "/app",
        health_tracker=None
    ):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.project_root = Path(project_root)
        self.health_tracker = health_tracker  # NEW: For crash tracking

        self.applied_changes: Dict[str, AppliedChange] = {}
        self._load_applied_changes()

    def apply_change(self, change: Dict) -> Dict[str, Any]:
        """
        Apply an approved change to the codebase

        Args:
            change: ChangeRequest dictionary with generated_code

        Returns:
            {
                'success': bool,
                'rollback_id': str,
                'backup_path': str,
                'applied_at': str,
                'error': Optional[str]
            }
        """
        generated_code = change['generated_code']
        file_path = generated_code['file_path']

        print(f"📝 Applying change to {file_path}...")

        try:
            # 1. Resolve full file path
            full_path = self._resolve_path(file_path)

            # NEW: Create directory and file if they don't exist
            file_exists = full_path.exists()

            if not file_exists:
                # Create parent directories if needed
                full_path.parent.mkdir(parents=True, exist_ok=True)
                print(f"📁 Created directory: {full_path.parent}")

                # Create empty file
                full_path.touch()
                print(f"📄 Created new file: {file_path}")

            # 2. Create backup (only if file existed before)
            if file_exists:
                backup_path = self._create_backup(full_path)
                print(f"💾 Backup created: {backup_path}")
            else:
                backup_path = None
                print(f"ℹ️ No backup needed (new file)")

            # 3. Apply changes
            try:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(generated_code['new_code'])

                print(f"✅ Changes applied to {file_path}")

                # 4. Record change
                rollback_id = self._generate_rollback_id()
                applied_change = AppliedChange(
                    rollback_id=rollback_id,
                    change_id=change['id'],
                    file_path=str(full_path),
                    backup_path=str(backup_path) if backup_path else "",
                    applied_at=datetime.now().isoformat(),
                    success=True
                )

                self.applied_changes[rollback_id] = applied_change
                self._save_applied_changes()

                # NEW: Notify health tracker that change was applied
                if self.health_tracker:
                    self.health_tracker.record_change_applied(change['id'])

                return {
                    'success': True,
                    'rollback_id': rollback_id,
                    'backup_path': str(backup_path),
                    'applied_at': applied_change.applied_at,
                    'message': f'✅ Successfully applied change to {file_path}'
                }

            except Exception as write_error:
                # Restore from backup if write fails (only if backup exists)
                if backup_path:
                    print(f"❌ Write failed, restoring from backup...")
                    shutil.copy(backup_path, full_path)
                else:
                    print(f"❌ Write failed, removing newly created file...")
                    if full_path.exists():
                        full_path.unlink()

                return {
                    'success': False,
                    'error': f'Failed to write changes: {str(write_error)}'
                }

        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to apply change: {str(e)}'
            }

    def rollback(self, rollback_id: str) -> Dict[str, Any]:
        """
        Rollback a previously applied change

        Args:
            rollback_id: ID returned when change was applied

        Returns:
            {
                'success': bool,
                'message': str,
                'file_restored': str
            }
        """
        if rollback_id not in self.applied_changes:
            return {
                'success': False,
                'message': f'❌ Rollback ID not found: {rollback_id}'
            }

        applied_change = self.applied_changes[rollback_id]

        print(f"⏪ Rolling back change {rollback_id}...")

        try:
            backup_path = Path(applied_change.backup_path)
            file_path = Path(applied_change.file_path)

            if not backup_path.exists():
                return {
                    'success': False,
                    'message': f'❌ Backup file not found: {backup_path}'
                }

            # Restore from backup
            shutil.copy(backup_path, file_path)

            print(f"✅ Rolled back {file_path}")

            return {
                'success': True,
                'message': f'✅ Successfully rolled back change to {file_path}',
                'file_restored': str(file_path)
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'❌ Rollback failed: {str(e)}'
            }

    def get_rollback_info(self, rollback_id: str) -> Optional[Dict]:
        """Get information about a rollback"""
        if rollback_id in self.applied_changes:
            return asdict(self.applied_changes[rollback_id])
        return None

    def list_applied_changes(self, limit: int = 50) -> List[Dict]:
        """List all applied changes"""
        changes = list(self.applied_changes.values())
        changes.sort(key=lambda x: x.applied_at, reverse=True)
        return [asdict(c) for c in changes[:limit]]

    def cleanup_old_backups(self, days: int = 7) -> int:
        """
        Delete backups older than specified days

        Args:
            days: Delete backups older than this many days

        Returns:
            Number of backups deleted
        """
        deleted = 0
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)

        try:
            for backup_file in self.backup_dir.glob("*.backup"):
                if backup_file.stat().st_mtime < cutoff:
                    backup_file.unlink()
                    deleted += 1

            print(f"🗑️ Cleaned up {deleted} old backups")
            return deleted

        except Exception as e:
            print(f"⚠️ Backup cleanup error: {e}")
            return deleted

    def _create_backup(self, file_path: Path) -> Path:
        """
        Create backup of file before modifying

        Args:
            file_path: Path to file to backup

        Returns:
            Path to backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.name}.{timestamp}.backup"
        backup_path = self.backup_dir / backup_name

        shutil.copy(file_path, backup_path)

        return backup_path

    def _resolve_path(self, file_path: str) -> Path:
        """
        Resolve file path relative to project root

        Args:
            file_path: Relative or absolute file path

        Returns:
            Absolute Path object
        """
        path = Path(file_path)

        if path.is_absolute():
            return path

        # Try relative to project root
        resolved = self.project_root / path
        if resolved.exists():
            return resolved

        # Try as-is
        if path.exists():
            return path

        # Return relative to project root anyway (might be new file)
        return self.project_root / path

    def _generate_rollback_id(self) -> str:
        """Generate unique rollback ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return f"rollback_{timestamp}"

    def _save_applied_changes(self):
        """Save applied changes to disk"""
        try:
            save_file = self.backup_dir / "applied_changes.json"

            data = {
                rollback_id: asdict(change)
                for rollback_id, change in self.applied_changes.items()
            }

            with open(save_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print(f"⚠️ Failed to save applied changes: {e}")

    def _load_applied_changes(self):
        """Load applied changes from disk"""
        try:
            save_file = self.backup_dir / "applied_changes.json"

            if save_file.exists():
                with open(save_file, 'r') as f:
                    data = json.load(f)

                self.applied_changes = {
                    rollback_id: AppliedChange(**change_data)
                    for rollback_id, change_data in data.items()
                }

                print(f"📥 Loaded {len(self.applied_changes)} applied changes")

        except Exception as e:
            print(f"⚠️ Failed to load applied changes: {e}")
            self.applied_changes = {}
