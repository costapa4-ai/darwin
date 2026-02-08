"""
Materialized View Manager for Darwin System

This module provides functionality to manage materialized views in database systems,
enabling efficient data caching and query optimization through automated view creation,
refresh, and management.
"""

import sqlite3
import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path


logger = logging.getLogger(__name__)


class MaterializedViewManager:
    """
    Manages materialized views for optimizing database queries.
    
    Provides functionality to create, refresh, drop, and monitor materialized views
    with automatic dependency tracking and refresh scheduling.
    """
    
    def __init__(self, db_path: str = "darwin_views.db"):
        """
        Initialize the Materialized View Manager.
        
        Args:
            db_path: Path to the database file for storing view metadata
        """
        self.db_path = db_path
        self._initialize_metadata_db()
        
    def _initialize_metadata_db(self) -> None:
        """Initialize the metadata database for tracking materialized views."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS materialized_views (
                    view_name TEXT PRIMARY KEY,
                    source_query TEXT NOT NULL,
                    query_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_refreshed TEXT,
                    refresh_count INTEGER DEFAULT 0,
                    auto_refresh BOOLEAN DEFAULT 0,
                    refresh_interval_seconds INTEGER,
                    dependencies TEXT,
                    row_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active'
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS view_refresh_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    view_name TEXT NOT NULL,
                    refresh_time TEXT NOT NULL,
                    duration_ms INTEGER,
                    rows_affected INTEGER,
                    status TEXT,
                    error_message TEXT,
                    FOREIGN KEY (view_name) REFERENCES materialized_views(view_name)
                )
            """)
            
            conn.commit()
            conn.close()
            logger.info(f"Initialized materialized view metadata database at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize metadata database: {e}")
            raise
    
    def create_view(
        self,
        view_name: str,
        source_query: str,
        target_db_path: str,
        auto_refresh: bool = False,
        refresh_interval_seconds: Optional[int] = None,
        dependencies: Optional[List[str]] = None,
        top_k: int = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new materialized view.
        
        Args:
            view_name: Name for the materialized view
            source_query: SQL query to materialize
            target_db_path: Path to the target database where view will be created
            auto_refresh: Whether to automatically refresh the view
            refresh_interval_seconds: Seconds between automatic refreshes
            dependencies: List of table/view names this view depends on
            top_k: For compatibility with tool registry
            **kwargs: For compatibility with tool registry
            
        Returns:
            Dictionary with creation status and view information
        """
        try:
            query_hash = hashlib.sha256(source_query.encode()).hexdigest()
            created_at = datetime.utcnow().isoformat()
            
            target_conn = sqlite3.connect(target_db_path)
            target_cursor = target_conn.cursor()
            
            target_cursor.execute(f"DROP TABLE IF EXISTS {view_name}")
            target_cursor.execute(f"CREATE TABLE {view_name} AS {source_query}")
            
            row_count = target_cursor.execute(f"SELECT COUNT(*) FROM {view_name}").fetchone()[0]
            
            target_conn.commit()
            target_conn.close()
            
            meta_conn = sqlite3.connect(self.db_path)
            meta_cursor = meta_conn.cursor()
            
            deps_str = ",".join(dependencies) if dependencies else ""
            
            meta_cursor.execute("""
                INSERT OR REPLACE INTO materialized_views
                (view_name, source_query, query_hash, created_at, last_refreshed,
                 refresh_count, auto_refresh, refresh_interval_seconds, dependencies,
                 row_count, status)
                VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?, 'active')
            """, (view_name, source_query, query_hash, created_at, created_at,
                  auto_refresh, refresh_interval_seconds, deps_str, row_count))
            
            meta_conn.commit()
            meta_conn.close()
            
            logger.info(f"Created materialized view '{view_name}' with {row_count} rows")
            
            return {
                "status": "success",
                "view_name": view_name,
                "row_count": row_count,
                "created_at": created_at,
                "query_hash": query_hash
            }
            
        except Exception as e:
            logger.error(f"Failed to create materialized view '{view_name}': {e}")
            return {
                "status": "error",
                "view_name": view_name,
                "error": str(e)
            }
    
    def refresh_view(
        self,
        view_name: str,
        target_db_path: str,
        top_k: int = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Refresh an existing materialized view.
        
        Args:
            view_name: Name of the view to refresh
            target_db_path: Path to the target database
            top_k: For compatibility with tool registry
            **kwargs: For compatibility with tool registry
            
        Returns:
            Dictionary with refresh status and metrics
        """
        start_time = datetime.utcnow()
        
        try:
            meta_conn = sqlite3.connect(self.db_path)
            meta_cursor = meta_conn.cursor()
            
            view_info = meta_cursor.execute("""
                SELECT source_query FROM materialized_views WHERE view_name = ?
            """, (view_name,)).fetchone()
            
            if not view_info:
                meta_conn.close()
                return {
                    "status": "error",
                    "view_name": view_name,
                    "error": "View not found"
                }
            
            source_query = view_info[0]
            
            target_conn = sqlite3.connect(target_db_path)
            target_cursor = target_conn.cursor()
            
            target_cursor.execute(f"DROP TABLE IF EXISTS {view_name}")
            target_cursor.execute(f"CREATE TABLE {view_name} AS {source_query}")
            
            row_count = target_cursor.execute(f"SELECT COUNT(*) FROM {view_name}").fetchone()[0]
            
            target_conn.commit()
            target_conn.close()
            
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            meta_cursor.execute("""
                UPDATE materialized_views
                SET last_refreshed = ?, refresh_count = refresh_count + 1, row_count = ?
                WHERE view_name = ?
            """, (end_time.isoformat(), row_count, view_name))
            
            meta_cursor.execute("""
                INSERT INTO view_refresh_log
                (view_name, refresh_time, duration_ms, rows_affected, status)
                VALUES (?, ?, ?, ?, 'success')
            """, (view_name, end_time.isoformat(), duration_ms, row_count))

            meta_conn.commit()
            meta_conn.close()

            logger.info(
                f"Refreshed materialized view '{view_name}': "
                f"{row_count} rows in {duration_ms}ms"
            )

            return {
                "status": "success",
                "view_name": view_name,
                "row_count": row_count,
                "duration_ms": duration_ms,
                "refreshed_at": end_time.isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to refresh materialized view '{view_name}': {e}")

            # Log the failure
            try:
                meta_conn = sqlite3.connect(self.db_path)
                meta_cursor = meta_conn.cursor()
                meta_cursor.execute("""
                    INSERT INTO view_refresh_log
                    (view_name, refresh_time, duration_ms, rows_affected, status, error_message)
                    VALUES (?, ?, ?, 0, 'error', ?)
                """, (view_name, datetime.utcnow().isoformat(), 0, str(e)))
                meta_conn.commit()
                meta_conn.close()
            except Exception:
                pass

            return {
                "status": "error",
                "view_name": view_name,
                "error": str(e)
            }

    def drop_view(
        self,
        view_name: str,
        target_db_path: str,
        top_k: int = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Drop a materialized view.

        Args:
            view_name: Name of the view to drop
            target_db_path: Path to the target database
            top_k: For compatibility with tool registry
            **kwargs: For compatibility with tool registry

        Returns:
            Dictionary with drop status
        """
        try:
            target_conn = sqlite3.connect(target_db_path)
            target_cursor = target_conn.cursor()
            target_cursor.execute(f"DROP TABLE IF EXISTS {view_name}")
            target_conn.commit()
            target_conn.close()

            meta_conn = sqlite3.connect(self.db_path)
            meta_cursor = meta_conn.cursor()
            meta_cursor.execute("""
                UPDATE materialized_views SET status = 'dropped' WHERE view_name = ?
            """, (view_name,))
            meta_conn.commit()
            meta_conn.close()

            logger.info(f"Dropped materialized view '{view_name}'")

            return {
                "status": "success",
                "view_name": view_name,
                "action": "dropped"
            }

        except Exception as e:
            logger.error(f"Failed to drop materialized view '{view_name}': {e}")
            return {
                "status": "error",
                "view_name": view_name,
                "error": str(e)
            }

    def list_views(
        self,
        status_filter: Optional[str] = None,
        top_k: int = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        List all materialized views.

        Args:
            status_filter: Optional status filter ('active', 'dropped')
            top_k: For compatibility with tool registry
            **kwargs: For compatibility with tool registry

        Returns:
            Dictionary with list of views
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if status_filter:
                rows = cursor.execute("""
                    SELECT view_name, source_query, created_at, last_refreshed,
                           refresh_count, auto_refresh, row_count, status
                    FROM materialized_views WHERE status = ?
                """, (status_filter,)).fetchall()
            else:
                rows = cursor.execute("""
                    SELECT view_name, source_query, created_at, last_refreshed,
                           refresh_count, auto_refresh, row_count, status
                    FROM materialized_views
                """).fetchall()

            conn.close()

            views = [
                {
                    "view_name": row[0],
                    "source_query": row[1],
                    "created_at": row[2],
                    "last_refreshed": row[3],
                    "refresh_count": row[4],
                    "auto_refresh": bool(row[5]),
                    "row_count": row[6],
                    "status": row[7]
                }
                for row in rows
            ]

            return {
                "status": "success",
                "views": views,
                "count": len(views)
            }

        except Exception as e:
            logger.error(f"Failed to list materialized views: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def get_view_info(
        self,
        view_name: str,
        top_k: int = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get detailed information about a specific materialized view.

        Args:
            view_name: Name of the view
            top_k: For compatibility with tool registry
            **kwargs: For compatibility with tool registry

        Returns:
            Dictionary with view details and refresh history
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            view_row = cursor.execute("""
                SELECT view_name, source_query, query_hash, created_at, last_refreshed,
                       refresh_count, auto_refresh, refresh_interval_seconds,
                       dependencies, row_count, status
                FROM materialized_views WHERE view_name = ?
            """, (view_name,)).fetchone()

            if not view_row:
                conn.close()
                return {
                    "status": "error",
                    "error": f"View '{view_name}' not found"
                }

            refresh_history = cursor.execute("""
                SELECT refresh_time, duration_ms, rows_affected, status, error_message
                FROM view_refresh_log WHERE view_name = ?
                ORDER BY refresh_time DESC LIMIT 10
            """, (view_name,)).fetchall()

            conn.close()

            return {
                "status": "success",
                "view_name": view_row[0],
                "source_query": view_row[1],
                "query_hash": view_row[2],
                "created_at": view_row[3],
                "last_refreshed": view_row[4],
                "refresh_count": view_row[5],
                "auto_refresh": bool(view_row[6]),
                "refresh_interval_seconds": view_row[7],
                "dependencies": view_row[8].split(",") if view_row[8] else [],
                "row_count": view_row[9],
                "view_status": view_row[10],
                "refresh_history": [
                    {
                        "refresh_time": r[0],
                        "duration_ms": r[1],
                        "rows_affected": r[2],
                        "status": r[3],
                        "error_message": r[4]
                    }
                    for r in refresh_history
                ]
            }

        except Exception as e:
            logger.error(f"Failed to get view info for '{view_name}': {e}")
            return {
                "status": "error",
                "error": str(e)
            }