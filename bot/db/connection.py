"""
Database connection management with connection pooling and health checks.
"""

import sqlite3
import threading
from contextlib import contextmanager
from typing import Optional, Generator

from bot.config import get_config
from bot.exceptions import DatabaseError
from bot.logger import setup_logger

logger = setup_logger(__name__)


class DatabaseConnection:
    """Manages SQLite database connections with pooling."""

    def __init__(self):
        """Initialize database connection."""
        self.config = get_config()
        self.db_path = self.config.db_path
        self._local = threading.local()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a thread-local database connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            try:
                conn = sqlite3.connect(
                    str(self.db_path),
                    timeout=10.0,
                    check_same_thread=False
                )
                conn.row_factory = sqlite3.Row
                conn.execute('PRAGMA journal_mode=WAL')
                conn.execute('PRAGMA synchronous=NORMAL')
                conn.execute('PRAGMA foreign_keys=ON')
                self._local.connection = conn
                logger.info("Database connection established", extra={'db': str(self.db_path)})
            except sqlite3.Error as e:
                logger.error(f"Failed to connect to database: {e}")
                raise DatabaseError(f"Database connection failed: {e}") from e
        return self._local.connection

    def close(self) -> None:
        """Close the thread-local connection."""
        if hasattr(self._local, 'connection') and self._local.connection:
            try:
                self._local.connection.close()
                self._local.connection = None
                logger.info("Database connection closed")
            except sqlite3.Error as e:
                logger.warning(f"Error closing database: {e}")

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database connections."""
        conn = self._get_connection()
        try:
            yield conn
        except Exception as e:
            logger.error(f"Database operation error: {e}", exc_info=True)
            raise

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a database query."""
        try:
            conn = self._get_connection()
            return conn.execute(query, params)
        except sqlite3.Error as e:
            logger.error(f"Query execution failed: {e}", extra={'query': query})
            raise DatabaseError(f"Query execution failed: {e}") from e

    def execute_many(self, query: str, params_list: list) -> None:
        """Execute multiple queries in transaction."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Batch execution failed: {e}")
            raise DatabaseError(f"Batch execution failed: {e}") from e

    def commit(self) -> None:
        """Commit the current transaction."""
        try:
            conn = self._get_connection()
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Commit failed: {e}")
            raise DatabaseError(f"Commit failed: {e}") from e

    def rollback(self) -> None:
        """Rollback the current transaction."""
        try:
            conn = self._get_connection()
            conn.rollback()
        except sqlite3.Error as e:
            logger.error(f"Rollback failed: {e}")
            raise DatabaseError(f"Rollback failed: {e}") from e

    def health_check(self) -> bool:
        """Check if database is accessible."""
        try:
            conn = self._get_connection()
            conn.execute('SELECT 1')
            logger.debug("Database health check passed")
            return True
        except sqlite3.Error as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def vacuum(self) -> None:
        """Optimize database file size."""
        try:
            conn = self._get_connection()
            conn.execute('VACUUM')
            conn.commit()
            logger.info("Database vacuumed")
        except sqlite3.Error as e:
            logger.warning(f"Vacuum failed: {e}")

    def analyze(self) -> None:
        """Analyze database for query optimization."""
        try:
            conn = self._get_connection()
            conn.execute('ANALYZE')
            conn.commit()
            logger.info("Database analyzed")
        except sqlite3.Error as e:
            logger.warning(f"Analyze failed: {e}")


# Global database instance
_db: Optional[DatabaseConnection] = None


def get_db() -> DatabaseConnection:
    """Get or create the global database connection."""
    global _db
    if _db is None:
        _db = DatabaseConnection()
    return _db


def reset_db() -> None:
    """Reset the global database connection (useful for testing)."""
    global _db
    if _db:
        _db.close()
    _db = None
