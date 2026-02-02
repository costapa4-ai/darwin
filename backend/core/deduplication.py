"""
Database-backed deduplication store for Darwin.

Provides persistent tracking of submitted insights to prevent duplicates.
Uses SQLite with transaction-based marking for reliability.
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Set
from contextlib import contextmanager

from utils.logger import setup_logger

logger = setup_logger(__name__)


class DeduplicationStore:
    """
    Persistent deduplication tracking using SQLite.

    Tracks submitted insights with:
    - Atomic check-and-mark operations
    - Automatic cleanup of old entries
    - Statistics and monitoring

    Usage:
        store = DeduplicationStore()

        # Atomic check and mark (returns True if new, False if duplicate)
        if store.check_and_mark("optimization:my_insight"):
            # Process the insight - it's new
            pass
        else:
            # Skip - already submitted
            pass
    """

    def __init__(self, db_path: str = None):
        """
        Initialize the deduplication store.

        Args:
            db_path: Path to SQLite database. Defaults to data/deduplication.db
        """
        if db_path is None:
            db_path = "./data/deduplication.db"

        self.db_path = db_path
        self._init_database()
        logger.info(f"DeduplicationStore initialized: {db_path}")

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_database(self):
        """Initialize the database schema."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Main deduplication table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS submitted_insights (
                    key TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source TEXT,
                    metadata TEXT
                )
            """)

            # Index for cleanup queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at
                ON submitted_insights(created_at)
            """)

            # Index for category-based queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_category
                ON submitted_insights(category)
            """)

            conn.commit()
            logger.debug("Deduplication database schema initialized")

    def check_and_mark(
        self,
        key: str,
        category: str = None,
        source: str = None,
        metadata: str = None
    ) -> bool:
        """
        Atomically check if key exists and mark it if not.

        This is the primary method for deduplication - it ensures
        that only one caller can "claim" a key, even with concurrent access.

        Args:
            key: Unique identifier (e.g., "optimization:my_insight_title")
            category: Optional category (extracted from key if not provided)
            source: Optional source identifier
            metadata: Optional JSON metadata

        Returns:
            True if key was new and has been marked
            False if key already existed (duplicate)
        """
        if category is None:
            # Extract category from key (e.g., "optimization:title" -> "optimization")
            category = key.split(":")[0] if ":" in key else "unknown"

        with self._get_connection() as conn:
            cursor = conn.cursor()

            try:
                # Use INSERT OR IGNORE for atomic check-and-insert
                cursor.execute("""
                    INSERT OR IGNORE INTO submitted_insights (key, category, source, metadata)
                    VALUES (?, ?, ?, ?)
                """, (key, category, source, metadata))

                conn.commit()

                # If rowcount > 0, the insert succeeded (key was new)
                is_new = cursor.rowcount > 0

                if is_new:
                    logger.debug(f"Dedup: Marked new key: {key[:50]}...")
                else:
                    logger.debug(f"Dedup: Duplicate key: {key[:50]}...")

                return is_new

            except sqlite3.Error as e:
                logger.error(f"Deduplication error: {e}")
                conn.rollback()
                # On error, assume it's a duplicate to be safe
                return False

    def is_submitted(self, key: str) -> bool:
        """
        Check if a key has already been submitted.

        Args:
            key: The key to check

        Returns:
            True if key exists (already submitted)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM submitted_insights WHERE key = ?",
                (key,)
            )
            return cursor.fetchone() is not None

    def mark_submitted(
        self,
        key: str,
        category: str = None,
        source: str = None,
        metadata: str = None
    ) -> bool:
        """
        Mark a key as submitted (without checking first).

        Use check_and_mark() for atomic operations.
        This method is for migration or explicit marking.

        Args:
            key: The key to mark
            category: Optional category
            source: Optional source
            metadata: Optional metadata

        Returns:
            True if marked successfully
        """
        if category is None:
            category = key.split(":")[0] if ":" in key else "unknown"

        with self._get_connection() as conn:
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO submitted_insights (key, category, source, metadata)
                    VALUES (?, ?, ?, ?)
                """, (key, category, source, metadata))
                conn.commit()
                return True
            except sqlite3.Error as e:
                logger.error(f"Failed to mark submitted: {e}")
                return False

    def remove(self, key: str) -> bool:
        """
        Remove a key from the deduplication store.

        Useful for allowing re-submission of a specific insight.

        Args:
            key: The key to remove

        Returns:
            True if key was removed, False if it didn't exist
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM submitted_insights WHERE key = ?", (key,))
            conn.commit()
            return cursor.rowcount > 0

    def clear(self, category: str = None) -> int:
        """
        Clear entries from the store.

        Args:
            category: If provided, only clear entries in this category.
                     If None, clear ALL entries.

        Returns:
            Number of entries removed
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if category:
                cursor.execute(
                    "DELETE FROM submitted_insights WHERE category = ?",
                    (category,)
                )
            else:
                cursor.execute("DELETE FROM submitted_insights")

            conn.commit()
            count = cursor.rowcount
            logger.info(f"Dedup: Cleared {count} entries" + (f" (category: {category})" if category else ""))
            return count

    def cleanup_old(self, days: int = 30) -> int:
        """
        Remove entries older than specified days.

        Args:
            days: Remove entries older than this many days

        Returns:
            Number of entries removed
        """
        cutoff = datetime.now() - timedelta(days=days)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM submitted_insights WHERE created_at < ?",
                (cutoff.isoformat(),)
            )
            conn.commit()
            count = cursor.rowcount

            if count > 0:
                logger.info(f"Dedup: Cleaned up {count} entries older than {days} days")

            return count

    def get_all_keys(self, category: str = None) -> Set[str]:
        """
        Get all submitted keys.

        Args:
            category: Optional category filter

        Returns:
            Set of all keys
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if category:
                cursor.execute(
                    "SELECT key FROM submitted_insights WHERE category = ?",
                    (category,)
                )
            else:
                cursor.execute("SELECT key FROM submitted_insights")

            return {row[0] for row in cursor.fetchall()}

    def get_stats(self) -> Dict:
        """
        Get statistics about the deduplication store.

        Returns:
            Dictionary with statistics
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Total count
            cursor.execute("SELECT COUNT(*) FROM submitted_insights")
            total = cursor.fetchone()[0]

            # Count by category
            cursor.execute("""
                SELECT category, COUNT(*) as count
                FROM submitted_insights
                GROUP BY category
                ORDER BY count DESC
            """)
            by_category = {row[0]: row[1] for row in cursor.fetchall()}

            # Recent entries (last 24 hours)
            yesterday = (datetime.now() - timedelta(days=1)).isoformat()
            cursor.execute(
                "SELECT COUNT(*) FROM submitted_insights WHERE created_at > ?",
                (yesterday,)
            )
            recent_24h = cursor.fetchone()[0]

            # Oldest entry
            cursor.execute("SELECT MIN(created_at) FROM submitted_insights")
            oldest = cursor.fetchone()[0]

            return {
                "total_entries": total,
                "by_category": by_category,
                "entries_last_24h": recent_24h,
                "oldest_entry": oldest,
                "database_path": self.db_path
            }

    def migrate_from_set(self, insight_set: Set[str], source: str = "migration") -> int:
        """
        Migrate entries from an in-memory set to the database.

        Args:
            insight_set: Set of insight keys to migrate
            source: Source identifier for the migration

        Returns:
            Number of entries migrated
        """
        count = 0
        for key in insight_set:
            if self.mark_submitted(key, source=source):
                count += 1

        logger.info(f"Dedup: Migrated {count} entries from in-memory set")
        return count


# Singleton instance
_dedup_store: Optional[DeduplicationStore] = None


def get_deduplication_store(db_path: str = None) -> DeduplicationStore:
    """Get or create the global deduplication store instance."""
    global _dedup_store
    if _dedup_store is None:
        _dedup_store = DeduplicationStore(db_path)
    return _dedup_store


def init_deduplication_store(db_path: str = None) -> DeduplicationStore:
    """Initialize a new deduplication store instance."""
    global _dedup_store
    _dedup_store = DeduplicationStore(db_path)
    return _dedup_store
