"""
Database connection pooling module for Darwin System.

This module provides optimized SQLAlchemy connection pooling configuration
to reduce database overhead and improve query performance.
"""

import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional

from sqlalchemy import create_engine, event, pool
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool, NullPool

logger = logging.getLogger(__name__)


class DatabaseConnectionPool:
    """
    Manages database connection pooling with optimized settings.
    
    Provides connection pool management with configurable parameters,
    automatic reconnection, and health checks.
    """
    
    def __init__(
        self,
        database_url: str,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        pool_pre_ping: bool = True,
        echo: bool = False,
        top_k: int = None,
        **kwargs
    ) -> None:
        """
        Initialize database connection pool.
        
        Args:
            database_url: Database connection string
            pool_size: Number of connections to maintain in the pool
            max_overflow: Maximum number of connections that can be created beyond pool_size
            pool_timeout: Seconds to wait before giving up on getting a connection
            pool_recycle: Seconds after which a connection is automatically recycled
            pool_pre_ping: Enable connection health checks before checkout
            echo: Enable SQL query logging
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
        """
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.pool_pre_ping = pool_pre_ping
        self.echo = echo
        
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        
        try:
            self._initialize_engine()
            self._setup_event_listeners()
            logger.info(
                f"Database connection pool initialized: "
                f"pool_size={pool_size}, max_overflow={max_overflow}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {e}")
            raise
    
    def _initialize_engine(self) -> None:
        """Initialize SQLAlchemy engine with connection pooling."""
        try:
            poolclass = QueuePool
            
            if "sqlite" in self.database_url.lower():
                if ":memory:" in self.database_url.lower():
                    poolclass = NullPool
                else:
                    self.pool_size = 1
                    self.max_overflow = 0
            
            self._engine = create_engine(
                self.database_url,
                poolclass=poolclass,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_timeout=self.pool_timeout,
                pool_recycle=self.pool_recycle,
                pool_pre_ping=self.pool_pre_ping,
                echo=self.echo,
                connect_args={
                    "connect_timeout": 10,
                    "application_name": "darwin_system"
                } if "postgresql" in self.database_url.lower() else {}
            )
            
            self._session_factory = sessionmaker(
                bind=self._engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
            
        except SQLAlchemyError as e:
            logger.error(f"SQLAlchemy error during engine initialization: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during engine initialization: {e}")
            raise
    
    def _setup_event_listeners(self) -> None:
        """Set up SQLAlchemy event listeners for connection management."""
        if not self._engine:
            return
        
        @event.listens_for(self._engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """Handle new database connections."""
            logger.debug("New database connection established")
            connection_record.info["pid"] = os.getpid()
        
        @event.listens_for(self._engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """Handle connection checkout from pool."""
            pid = os.getpid()
            if connection_record.info.get("pid") != pid:
                logger.warning(
                    f"Connection record belongs to different process, invalidating"
                )
                connection_record.connection = connection_proxy.connection = None
                raise SQLAlchemyError(
                    "Connection record belongs to different process"
                )
        
        @event.listens_for(self._engine, "close")
        def receive_close(dbapi_conn, connection_record):
            """Handle connection closure."""
            logger.debug("Database connection closed")
    
    @contextmanager
    def get_session(
        self, 
        top_k: int = None, 
        **kwargs
    ) -> Generator[Session, None, None]:
        """
        Get a database session from the pool.
        
        Context manager that provides a database session and handles
        commit/rollback automatically.
        
        Args:
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
            
        Yields:
            Session: SQLAlchemy database session
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        if not self._session_factory:
            raise RuntimeError("Database connection pool not initialized")
        
        session = self._session_factory()
        
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error, rolling back transaction: {e}")
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Unexpected error, rolling back transaction: {e}")
            raise
        finally:
            session.close()
    
    def get_engine(self, top_k: int = None, **kwargs) -> Engine:
        """
        Get the SQLAlchemy engine.
        
        Args:
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
            
        Returns:
            Engine: SQLAlchemy engine instance
        """
        if not self._engine:
            raise RuntimeError("Database engine not initialized")
        return self._engine
    
    def get_pool_status(self, top_k: int = None, **kwargs) -> Dict[str, Any]:
        """
        Get current connection pool status.
        
        Args:
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
            
        Returns:
            Dict containing pool statistics
        """
        if not self._engine or not hasattr(self._engine.pool, "size"):
            return {"error": "Pool statistics not available"}
        
        try:
            pool_obj = self._engine.pool
            return {
                "pool_size": self.pool_size,
                "max_overflow": self.max_overflow,
                "checked_in": pool_obj.checkedin() if hasattr(pool_obj, "checkedin") else "N/A",
                "checked_out": pool_obj.checkedout() if hasattr(pool_obj, "checkedout") else "N/A",
                "overflow": pool_obj.overflow() if hasattr(pool_obj, "overflow") else "N/A",
                "pool_timeout": self.pool_timeout,
                "pool_recycle": self.pool_recycle
            }
        except Exception as e:
            logger.error(f"Error retrieving pool status: {e}")
            return {"error": str(e)}