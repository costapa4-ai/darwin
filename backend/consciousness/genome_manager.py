"""
Genome Manager — Darwin's evolvable parameter system.

All behavioral parameters live in data/genome/*.json files.
Code reads from genome with hardcoded fallback.
Darwin can evolve 1 parameter per 10 complete cycles.

Safety:
- _bounds.json defines min/max for every parameter (PROTECTED)
- _version.json tracks mutations and cooldown (PROTECTED)
- Max ±20% change per mutation for numeric values
- Single self-rollback, then manual only
"""

import copy
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from utils.logger import get_logger

logger = get_logger(__name__)

GENOME_DIR = Path("/app/data/genome")
SNAPSHOTS_DIR = GENOME_DIR / "_snapshots"
IDENTITY_DIR = Path("/app/data/identity")

DOMAINS = ["personality", "emotions", "cognition", "actions",
           "rhythms", "social", "creativity"]

MUTATION_COOLDOWN_CYCLES = 10
MAX_SNAPSHOTS = 5
MAX_CHANGE_PERCENT = 0.20  # ±20% per mutation

# Singleton
_instance: Optional["GenomeManager"] = None


def get_genome() -> "GenomeManager":
    """Get the singleton GenomeManager instance."""
    global _instance
    if _instance is None:
        _instance = GenomeManager()
    return _instance


class GenomeManager:
    """Manages Darwin's evolvable genome parameters."""

    def __init__(self, genome_dir: Path = None):
        self._dir = genome_dir or GENOME_DIR
        self._snapshots_dir = self._dir / "_snapshots"
        self._data: Dict[str, dict] = {}
        self._bounds: dict = {}
        self._version: dict = {}
        self._core_values_hash: Optional[str] = None

        self._load_all()

    # ==================== Loading ====================

    def _load_all(self):
        """Load all genome files from disk."""
        self._snapshots_dir.mkdir(parents=True, exist_ok=True)

        for domain in DOMAINS:
            path = self._dir / f"{domain}.json"
            if path.exists():
                try:
                    self._data[domain] = json.loads(path.read_text())
                except Exception as e:
                    logger.error(f"Failed to load genome/{domain}.json: {e}")
                    self._data[domain] = {}
            else:
                logger.warning(f"Genome file missing: {domain}.json — using empty")
                self._data[domain] = {}

        # Load bounds (protected)
        bounds_path = self._dir / "_bounds.json"
        if bounds_path.exists():
            try:
                self._bounds = json.loads(bounds_path.read_text())
            except Exception as e:
                logger.error(f"Failed to load _bounds.json: {e}")

        # Load version tracking
        version_path = self._dir / "_version.json"
        if version_path.exists():
            try:
                self._version = json.loads(version_path.read_text())
            except Exception as e:
                logger.error(f"Failed to load _version.json: {e}")
                self._version = self._default_version()
        else:
            self._version = self._default_version()

        # Cache core values hash for change detection
        self._core_values_hash = self._compute_core_values_hash()

        loaded = [d for d in DOMAINS if self._data.get(d)]
        logger.info(f"Genome loaded: {len(loaded)} domains ({', '.join(loaded)})")

    def _default_version(self) -> dict:
        return {
            "version": 1,
            "created_at": datetime.utcnow().isoformat(),
            "last_mutation_at": None,
            "cycles_since_last_mutation": 0,
            "mutation_cooldown_cycles": MUTATION_COOLDOWN_CYCLES,
            "rollback_available": True,
            "changelog": [],
            "stats": {
                "total_mutations": 0,
                "kept_mutations": 0,
                "rolledback_mutations": 0,
                "rejected_mutations": 0,
                "per_domain": {d: {"mutations": 0, "kept": 0, "rolledback": 0} for d in DOMAINS}
            }
        }

    # ==================== Read ====================

    def get(self, key: str, default=None) -> Any:
        """
        Get a value by dotted key path.

        Examples:
            get("emotions.moods.curious.duration_min") → 10
            get("rhythms.cycles.wake_duration_minutes") → 120
        """
        parts = key.split(".")
        if not parts:
            return default

        domain = parts[0]
        data = self._data.get(domain)
        if data is None:
            return default

        current = data
        for part in parts[1:]:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    current = current[int(part)]
                except (ValueError, IndexError):
                    return default
            else:
                return default
            if current is None:
                return default

        return current

    def get_domain(self, domain: str) -> dict:
        """Get all data for a domain."""
        return copy.deepcopy(self._data.get(domain, {}))

    def get_all(self) -> Dict[str, dict]:
        """Get all genome data (deep copy)."""
        return copy.deepcopy(self._data)

    # ==================== Write (bounds-checked) ====================

    def set(self, key: str, value: Any) -> Tuple[bool, str]:
        """
        Set a value with bounds checking. Does NOT log as mutation.
        Used for manual/Paulo changes.
        """
        parts = key.split(".")
        if len(parts) < 2:
            return False, "Key must be domain.path (e.g. emotions.moods.curious.duration_min)"

        domain = parts[0]
        if domain not in DOMAINS:
            return False, f"Unknown domain: {domain}"

        # Bounds check
        ok, msg = self._check_bounds(key, value)
        if not ok:
            return False, msg

        # Navigate to parent and set
        data = self._data.setdefault(domain, {})
        for part in parts[1:-1]:
            if isinstance(data, dict):
                data = data.setdefault(part, {})
            else:
                return False, f"Cannot navigate path: {key}"

        leaf = parts[-1]
        if isinstance(data, dict):
            data[leaf] = value
        else:
            return False, f"Cannot set on non-dict at: {key}"

        # Save domain file
        self._save_domain(domain)
        return True, "ok"

    # ==================== Evolve (mutation with full logging) ====================

    def can_evolve(self) -> bool:
        """Check if Darwin can evolve (cooldown met)."""
        cooldown = self._version.get("mutation_cooldown_cycles", MUTATION_COOLDOWN_CYCLES)
        cycles = self._version.get("cycles_since_last_mutation", 0)
        return cycles >= cooldown

    def evolve(self, key: str, value: Any, reason: str) -> dict:
        """
        Apply a mutation with full logging and safety checks.

        Returns dict with success, message, and mutation details.
        """
        if not self.can_evolve():
            cooldown = self._version.get("mutation_cooldown_cycles", MUTATION_COOLDOWN_CYCLES)
            cycles = self._version.get("cycles_since_last_mutation", 0)
            return {
                "success": False,
                "error": f"Cooldown: {cycles}/{cooldown} cycles since last mutation"
            }

        parts = key.split(".")
        if len(parts) < 2:
            return {"success": False, "error": "Invalid key path"}

        domain = parts[0]
        if domain not in DOMAINS:
            return {"success": False, "error": f"Unknown domain: {domain}"}

        # Get current value
        old_value = self.get(key)

        # Enforce ±20% change for numeric values
        if isinstance(old_value, (int, float)) and isinstance(value, (int, float)):
            if old_value != 0:
                change_pct = abs(value - old_value) / abs(old_value)
                if change_pct > MAX_CHANGE_PERCENT:
                    return {
                        "success": False,
                        "error": f"Change too large: {change_pct:.1%} (max ±{MAX_CHANGE_PERCENT:.0%}). "
                                 f"Old: {old_value}, New: {value}"
                    }

        # Bounds check
        ok, msg = self._check_bounds(key, value)
        if not ok:
            self._version["stats"]["rejected_mutations"] = \
                self._version["stats"].get("rejected_mutations", 0) + 1
            self._save_version()
            return {"success": False, "error": msg}

        # Snapshot before mutation
        snapshot_id = self.snapshot()

        # Apply the change
        ok, msg = self.set(key, value)
        if not ok:
            return {"success": False, "error": msg}

        # Log the mutation
        mutation = {
            "version": self._version.get("version", 0) + 1,
            "timestamp": datetime.utcnow().isoformat(),
            "domain": domain,
            "key": key,
            "old_value": old_value,
            "new_value": value,
            "reason": reason,
            "snapshot_before": snapshot_id,
            "status": "applied"
        }

        self._version["version"] = mutation["version"]
        self._version["last_mutation_at"] = mutation["timestamp"]
        self._version["cycles_since_last_mutation"] = 0
        self._version["changelog"].append(mutation)
        # Keep last 50 changelog entries
        if len(self._version["changelog"]) > 50:
            self._version["changelog"] = self._version["changelog"][-50:]

        # Update stats
        stats = self._version["stats"]
        stats["total_mutations"] = stats.get("total_mutations", 0) + 1
        stats["kept_mutations"] = stats.get("kept_mutations", 0) + 1

        domain_stats = stats.setdefault("per_domain", {}).setdefault(
            domain, {"mutations": 0, "kept": 0, "rolledback": 0}
        )
        domain_stats["mutations"] = domain_stats.get("mutations", 0) + 1
        domain_stats["kept"] = domain_stats.get("kept", 0) + 1

        self._save_version()

        # Log to safety logger
        try:
            from consciousness.safety_logger import get_safety_logger
            get_safety_logger().log_event(
                event_type="genome_mutation",
                details={
                    "key": key,
                    "old_value": str(old_value),
                    "new_value": str(value),
                    "reason": reason,
                    "version": mutation["version"]
                },
                severity="info"
            )
        except Exception:
            pass

        logger.info(f"Genome mutation v{mutation['version']}: {key} = {old_value} → {value} ({reason})")

        return {
            "success": True,
            "mutation": mutation
        }

    # ==================== Cycle Tracking ====================

    def record_cycle(self):
        """Record a complete wake+sleep cycle. Call at each transition."""
        self._version["cycles_since_last_mutation"] = \
            self._version.get("cycles_since_last_mutation", 0) + 1
        self._save_version()
        logger.debug(
            f"Genome cycle recorded: {self._version['cycles_since_last_mutation']}/"
            f"{self._version.get('mutation_cooldown_cycles', MUTATION_COOLDOWN_CYCLES)}"
        )

    # ==================== Snapshots & Rollback ====================

    def snapshot(self) -> str:
        """Save current genome state as a snapshot. Returns snapshot ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        snapshot_id = f"snap_{timestamp}"
        snap_dir = self._snapshots_dir / snapshot_id

        snap_dir.mkdir(parents=True, exist_ok=True)

        # Save all domain files
        for domain in DOMAINS:
            data = self._data.get(domain, {})
            (snap_dir / f"{domain}.json").write_text(
                json.dumps(data, indent=2, ensure_ascii=False)
            )

        # Save version
        (snap_dir / "_version.json").write_text(
            json.dumps(self._version, indent=2, ensure_ascii=False)
        )

        # Prune old snapshots
        self._prune_snapshots()

        logger.info(f"Genome snapshot: {snapshot_id}")
        return snapshot_id

    def rollback(self) -> Tuple[bool, str]:
        """
        Self-rollback to the most recent snapshot.
        Can only be done ONCE — after this, rollback_available = False.
        """
        if not self._version.get("rollback_available", True):
            return False, "Rollback already used. Only Paulo can rollback further (manual_rollback)."

        # Find most recent snapshot
        snapshots = sorted(self._snapshots_dir.iterdir()) if self._snapshots_dir.exists() else []
        snapshots = [s for s in snapshots if s.is_dir() and s.name.startswith("snap_")]

        if not snapshots:
            return False, "No snapshots available for rollback"

        latest = snapshots[-1]

        # Restore domain files
        for domain in DOMAINS:
            snap_file = latest / f"{domain}.json"
            if snap_file.exists():
                try:
                    self._data[domain] = json.loads(snap_file.read_text())
                    self._save_domain(domain)
                except Exception as e:
                    logger.error(f"Rollback failed for {domain}: {e}")

        # Update version tracking
        # Find the last mutation in changelog and mark it as rolled back
        if self._version.get("changelog"):
            last_mutation = self._version["changelog"][-1]
            last_mutation["status"] = "rolledback"
            domain = last_mutation.get("domain")
            if domain:
                domain_stats = self._version["stats"].get("per_domain", {}).get(domain, {})
                domain_stats["rolledback"] = domain_stats.get("rolledback", 0) + 1
                domain_stats["kept"] = max(0, domain_stats.get("kept", 0) - 1)
                self._version["stats"]["kept_mutations"] = max(
                    0, self._version["stats"].get("kept_mutations", 0) - 1
                )
                self._version["stats"]["rolledback_mutations"] = \
                    self._version["stats"].get("rolledback_mutations", 0) + 1

        self._version["rollback_available"] = False
        self._save_version()

        # Log to safety logger
        try:
            from consciousness.safety_logger import get_safety_logger
            get_safety_logger().log_event(
                event_type="genome_rollback",
                details={"snapshot": latest.name, "self_initiated": True},
                severity="warning"
            )
        except Exception:
            pass

        logger.warning(f"Genome rolled back to {latest.name}. Rollback now locked.")
        return True, f"Rolled back to {latest.name}. Further rollbacks require Paulo."

    def manual_rollback(self, snapshot_id: str = None) -> Tuple[bool, str]:
        """
        Paulo-only rollback. Re-enables rollback_available.
        If snapshot_id is None, uses the latest snapshot.
        """
        if snapshot_id:
            snap_dir = self._snapshots_dir / snapshot_id
        else:
            snapshots = sorted(self._snapshots_dir.iterdir()) if self._snapshots_dir.exists() else []
            snapshots = [s for s in snapshots if s.is_dir() and s.name.startswith("snap_")]
            if not snapshots:
                return False, "No snapshots available"
            snap_dir = snapshots[-1]

        if not snap_dir.exists():
            return False, f"Snapshot not found: {snapshot_id}"

        # Restore
        for domain in DOMAINS:
            snap_file = snap_dir / f"{domain}.json"
            if snap_file.exists():
                try:
                    self._data[domain] = json.loads(snap_file.read_text())
                    self._save_domain(domain)
                except Exception as e:
                    logger.error(f"Manual rollback failed for {domain}: {e}")

        # Re-enable self-rollback
        self._version["rollback_available"] = True
        self._save_version()

        logger.info(f"Manual rollback to {snap_dir.name}. Self-rollback re-enabled.")
        return True, f"Rolled back to {snap_dir.name}. Darwin can self-rollback again."

    def _prune_snapshots(self):
        """Keep only MAX_SNAPSHOTS most recent snapshots."""
        if not self._snapshots_dir.exists():
            return
        snapshots = sorted(
            [s for s in self._snapshots_dir.iterdir() if s.is_dir() and s.name.startswith("snap_")]
        )
        while len(snapshots) > MAX_SNAPSHOTS:
            oldest = snapshots.pop(0)
            shutil.rmtree(str(oldest), ignore_errors=True)
            logger.debug(f"Pruned old snapshot: {oldest.name}")

    # ==================== Core Values Detection ====================

    def _compute_core_values_hash(self) -> Optional[str]:
        """Compute hash of darwin_self.json core_values for change detection."""
        identity_file = IDENTITY_DIR / "darwin_self.json"
        if not identity_file.exists():
            return None
        try:
            data = json.loads(identity_file.read_text())
            core_values = data.get("core_values", [])
            content = json.dumps(core_values, sort_keys=True)
            return hashlib.md5(content.encode()).hexdigest()
        except Exception:
            return None

    def check_core_values_changed(self) -> Optional[str]:
        """
        Check if Paulo changed core values since last check.
        Returns description of change, or None if unchanged.
        """
        new_hash = self._compute_core_values_hash()
        if new_hash is None or self._core_values_hash is None:
            self._core_values_hash = new_hash
            return None

        if new_hash != self._core_values_hash:
            # Something changed — read and describe
            old_hash = self._core_values_hash
            self._core_values_hash = new_hash
            try:
                identity_file = IDENTITY_DIR / "darwin_self.json"
                data = json.loads(identity_file.read_text())
                values = data.get("core_values", [])
                return f"Core values updated by Paulo: {values}"
            except Exception:
                return "Core values were changed (could not read details)"

        return None

    def get_core_values(self) -> list:
        """Read current core values (read-only for Darwin)."""
        identity_file = IDENTITY_DIR / "darwin_self.json"
        if not identity_file.exists():
            return []
        try:
            data = json.loads(identity_file.read_text())
            return data.get("core_values", [])
        except Exception:
            return []

    # ==================== Bounds Checking ====================

    def _check_bounds(self, key: str, value: Any) -> Tuple[bool, str]:
        """Check if a value is within bounds."""
        if not self._bounds:
            return True, "ok"  # No bounds loaded, allow

        # Try exact key match first
        bound = self._bounds.get(key)

        # Try wildcard matching (e.g., emotions.moods.*.duration_min)
        if bound is None:
            bound = self._find_wildcard_bound(key)

        if bound is None:
            return True, "ok"  # No bounds defined for this key

        # Skip non-dict bounds (like _comment)
        if not isinstance(bound, dict):
            return True, "ok"

        expected_type = bound.get("type", "any")
        min_val = bound.get("min")
        max_val = bound.get("max")

        # Type check
        if expected_type == "int" and not isinstance(value, int):
            if isinstance(value, float) and value == int(value):
                value = int(value)  # Allow 10.0 as int
            else:
                return False, f"Expected int for {key}, got {type(value).__name__}"
        elif expected_type == "float" and not isinstance(value, (int, float)):
            return False, f"Expected float for {key}, got {type(value).__name__}"

        # Range check
        if min_val is not None and value < min_val:
            return False, f"Value {value} below minimum {min_val} for {key}"
        if max_val is not None and value > max_val:
            return False, f"Value {value} above maximum {max_val} for {key}"

        return True, "ok"

    def _find_wildcard_bound(self, key: str) -> Optional[dict]:
        """Match a key against wildcard bounds patterns."""
        parts = key.split(".")
        for pattern, bound in self._bounds.items():
            if not isinstance(bound, dict):
                continue
            pattern_parts = pattern.split(".")
            if len(pattern_parts) != len(parts):
                continue
            match = True
            for p, k in zip(pattern_parts, parts):
                if p == "*":
                    continue
                if p != k:
                    match = False
                    break
            if match:
                return bound
        return None

    # ==================== Persistence ====================

    def _save_domain(self, domain: str):
        """Save a domain file to disk."""
        path = self._dir / f"{domain}.json"
        try:
            path.write_text(json.dumps(self._data[domain], indent=2, ensure_ascii=False))
        except Exception as e:
            logger.error(f"Failed to save genome/{domain}.json: {e}")

    def _save_version(self):
        """Save version tracking to disk."""
        path = self._dir / "_version.json"
        try:
            path.write_text(json.dumps(self._version, indent=2, ensure_ascii=False))
        except Exception as e:
            logger.error(f"Failed to save _version.json: {e}")

    # ==================== Stats & Summary ====================

    def get_stats(self) -> dict:
        """Get per-domain mutation statistics."""
        return {
            "version": self._version.get("version", 1),
            "cycles_since_last_mutation": self._version.get("cycles_since_last_mutation", 0),
            "mutation_cooldown_cycles": self._version.get("mutation_cooldown_cycles", MUTATION_COOLDOWN_CYCLES),
            "can_evolve": self.can_evolve(),
            "rollback_available": self._version.get("rollback_available", True),
            "last_mutation_at": self._version.get("last_mutation_at"),
            "stats": self._version.get("stats", {}),
        }

    def get_changelog(self, limit: int = 50) -> List[dict]:
        """Get recent evolution changelog."""
        return self._version.get("changelog", [])[-limit:]

    def get_summary(self) -> str:
        """Compact genome summary for prompt injection."""
        stats = self._version.get("stats", {})
        total = stats.get("total_mutations", 0)
        kept = stats.get("kept_mutations", 0)
        rolled = stats.get("rolledback_mutations", 0)
        version = self._version.get("version", 1)
        cycles = self._version.get("cycles_since_last_mutation", 0)
        cooldown = self._version.get("mutation_cooldown_cycles", MUTATION_COOLDOWN_CYCLES)
        can_evolve = self.can_evolve()

        lines = [
            f"Genome v{version} — {total} mutations ({kept} kept, {rolled} rolled back)",
            f"Evolution: {'READY' if can_evolve else f'{cycles}/{cooldown} cycles until next'}"
        ]

        # Per-domain summary (only those with mutations)
        per_domain = stats.get("per_domain", {})
        active = [(d, s) for d, s in per_domain.items() if s.get("mutations", 0) > 0]
        if active:
            domain_parts = [f"{d}:{s['mutations']}m/{s['kept']}k" for d, s in active]
            lines.append(f"Active: {', '.join(domain_parts)}")

        return " | ".join(lines)

    # ==================== Timing Constraint ====================

    def validate_cycle_timing(self, wake_min: int, sleep_min: int) -> Tuple[bool, str]:
        """Validate that cycle timing respects constraints."""
        if wake_min < 30:
            return False, f"Wake duration {wake_min}min below minimum 30min"
        if sleep_min < 30:
            return False, f"Sleep duration {sleep_min}min below minimum 30min"
        if wake_min + sleep_min > 1440:
            return False, f"Total cycle {wake_min + sleep_min}min exceeds 24h maximum"
        return True, "ok"
