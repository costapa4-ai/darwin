"""
Health Tracker: Monitors system health and enables auto-recovery from crashes

This system:
1. Records heartbeat on every successful startup
2. Detects crashes by checking for missing shutdown signal
3. Triggers automatic rollback on startup if previous session crashed
4. Tracks which changes were applied before crash
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict


@dataclass
class HealthSnapshot:
    """Snapshot of system health at a point in time"""
    timestamp: str
    status: str  # 'starting', 'running', 'shutdown', 'crashed'
    last_change_id: Optional[str] = None
    last_change_applied_at: Optional[str] = None
    uptime_seconds: float = 0
    total_changes_applied: int = 0


class HealthTracker:
    """
    Tracks system health and enables crash detection + auto-recovery

    How it works:
    1. On startup: Check if previous session crashed
    2. If crashed: Identify last applied change and rollback
    3. During runtime: Update heartbeat regularly
    4. On shutdown: Mark clean shutdown
    """

    def __init__(self, health_file: str = "/app/data/health.json"):
        """
        Initialize health tracker

        Args:
            health_file: Path to health tracking JSON file
        """
        self.health_file = Path(health_file)
        self.health_file.parent.mkdir(parents=True, exist_ok=True)

        self.startup_time = datetime.utcnow()
        self.current_snapshot: Optional[HealthSnapshot] = None

    def check_previous_crash(self) -> Dict[str, Any]:
        """
        Check if previous session crashed (no clean shutdown)

        Returns:
            dict with:
                - crashed: bool
                - last_change_id: str (change applied before crash)
                - timestamp: str (when crash occurred)
                - should_rollback: bool
        """
        if not self.health_file.exists():
            return {
                'crashed': False,
                'first_run': True,
                'message': 'No previous health data found'
            }

        try:
            with open(self.health_file, 'r') as f:
                data = json.load(f)

            last_status = data.get('status', 'unknown')

            # If last status was NOT 'shutdown', system crashed
            if last_status in ['starting', 'running']:
                return {
                    'crashed': True,
                    'last_change_id': data.get('last_change_id'),
                    'last_change_applied_at': data.get('last_change_applied_at'),
                    'timestamp': data.get('timestamp'),
                    'uptime_seconds': data.get('uptime_seconds', 0),
                    'should_rollback': data.get('last_change_id') is not None,
                    'message': f"System crashed after applying change {data.get('last_change_id', 'unknown')}"
                }

            return {
                'crashed': False,
                'clean_shutdown': True,
                'message': 'Previous session ended cleanly'
            }

        except Exception as e:
            return {
                'crashed': False,
                'error': str(e),
                'message': f'Failed to read health data: {e}'
            }

    def record_startup(self):
        """Record that system is starting up"""
        self.current_snapshot = HealthSnapshot(
            timestamp=datetime.utcnow().isoformat(),
            status='starting',
            uptime_seconds=0
        )
        self._save_snapshot()
        print(f"💓 Health tracker: System starting at {self.current_snapshot.timestamp}")

    def record_running(self):
        """Record that system is now fully running"""
        if self.current_snapshot:
            self.current_snapshot.status = 'running'
            self.current_snapshot.uptime_seconds = (datetime.utcnow() - self.startup_time).total_seconds()
            self._save_snapshot()
            print(f"💓 Health tracker: System running (uptime: {self.current_snapshot.uptime_seconds:.1f}s)")

    def record_change_applied(self, change_id: str):
        """
        Record that a code change was just applied

        Args:
            change_id: ID of the change that was applied
        """
        if self.current_snapshot:
            self.current_snapshot.last_change_id = change_id
            self.current_snapshot.last_change_applied_at = datetime.utcnow().isoformat()
            self.current_snapshot.total_changes_applied += 1
            self.current_snapshot.uptime_seconds = (datetime.utcnow() - self.startup_time).total_seconds()
            self._save_snapshot()
            print(f"💓 Health tracker: Recorded change {change_id} applied")

    def update_heartbeat(self):
        """Update heartbeat to show system is still alive"""
        if self.current_snapshot and self.current_snapshot.status == 'running':
            self.current_snapshot.uptime_seconds = (datetime.utcnow() - self.startup_time).total_seconds()
            self._save_snapshot()

    def record_shutdown(self):
        """Record clean shutdown"""
        if self.current_snapshot:
            self.current_snapshot.status = 'shutdown'
            self.current_snapshot.uptime_seconds = (datetime.utcnow() - self.startup_time).total_seconds()
            self._save_snapshot()
            print(f"💓 Health tracker: Clean shutdown (uptime: {self.current_snapshot.uptime_seconds:.1f}s)")

    def _save_snapshot(self):
        """Save current snapshot to file"""
        if self.current_snapshot:
            try:
                with open(self.health_file, 'w') as f:
                    json.dump(asdict(self.current_snapshot), f, indent=2)
            except Exception as e:
                print(f"⚠️ Failed to save health snapshot: {e}")

    def get_current_health(self) -> Dict[str, Any]:
        """Get current health status"""
        if self.current_snapshot:
            return {
                'status': self.current_snapshot.status,
                'uptime_seconds': (datetime.utcnow() - self.startup_time).total_seconds(),
                'last_change_id': self.current_snapshot.last_change_id,
                'total_changes_applied': self.current_snapshot.total_changes_applied
            }
        return {'status': 'unknown'}


class AutoRecovery:
    """
    Handles automatic recovery from crashes

    Works with AutoApplier to rollback changes that caused crashes
    """

    def __init__(self, health_tracker: HealthTracker, auto_applier=None):
        """
        Initialize auto-recovery system

        Args:
            health_tracker: HealthTracker instance
            auto_applier: AutoApplier instance (for rollback)
        """
        self.health_tracker = health_tracker
        self.auto_applier = auto_applier

    async def check_and_recover(self) -> Dict[str, Any]:
        """
        Check for crash and recover if needed

        Returns:
            dict with recovery status
        """
        crash_info = self.health_tracker.check_previous_crash()

        if not crash_info.get('crashed'):
            print("✅ No crash detected. Previous session ended cleanly.")
            return {
                'recovery_needed': False,
                'message': crash_info.get('message', 'System healthy')
            }

        print(f"🚨 CRASH DETECTED! {crash_info.get('message')}")

        # If no change was applied before crash, nothing to rollback
        if not crash_info.get('should_rollback'):
            print("⚠️ No code changes were applied before crash. Skipping rollback.")
            return {
                'recovery_needed': False,
                'crash_detected': True,
                'rollback_performed': False,
                'message': 'Crash detected but no changes to rollback'
            }

        # Perform rollback
        last_change_id = crash_info.get('last_change_id')
        print(f"🔄 Attempting to rollback change: {last_change_id}")

        if not self.auto_applier:
            print("❌ AutoApplier not available. Cannot perform automatic rollback.")
            return {
                'recovery_needed': True,
                'crash_detected': True,
                'rollback_performed': False,
                'error': 'AutoApplier not available',
                'last_change_id': last_change_id
            }

        try:
            # Find the rollback for this change
            rollback_result = await self._perform_rollback(last_change_id)

            if rollback_result.get('success'):
                print(f"✅ Successfully rolled back change {last_change_id}")
                return {
                    'recovery_needed': True,
                    'crash_detected': True,
                    'rollback_performed': True,
                    'last_change_id': last_change_id,
                    'rollback_result': rollback_result,
                    'message': f'Successfully recovered from crash by rolling back {last_change_id}'
                }
            else:
                print(f"❌ Failed to rollback change {last_change_id}: {rollback_result.get('error')}")
                return {
                    'recovery_needed': True,
                    'crash_detected': True,
                    'rollback_performed': False,
                    'last_change_id': last_change_id,
                    'error': rollback_result.get('error'),
                    'message': 'Failed to perform automatic rollback'
                }

        except Exception as e:
            print(f"❌ Exception during rollback: {e}")
            return {
                'recovery_needed': True,
                'crash_detected': True,
                'rollback_performed': False,
                'error': str(e),
                'message': f'Exception during rollback: {e}'
            }

    async def _perform_rollback(self, change_id: str) -> Dict[str, Any]:
        """
        Perform actual rollback of a change

        Args:
            change_id: ID of change to rollback

        Returns:
            dict with rollback result
        """
        # Get rollback ID from applied changes
        applied_changes = self.auto_applier._load_applied_changes()

        rollback_id = None
        for change in applied_changes:
            if change.get('change_id') == change_id:
                rollback_id = change.get('rollback_id')
                break

        if not rollback_id:
            return {
                'success': False,
                'error': f'No rollback found for change {change_id}'
            }

        # Perform rollback
        return self.auto_applier.rollback(rollback_id)
