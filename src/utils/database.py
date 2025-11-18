"""
Database connection utilities.

Provides async database connections for PostgreSQL.
"""

import asyncpg
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def get_db_connection():
    """
    Async context manager for database connections.

    Yields:
        asyncpg.Connection: Database connection

    Example:
        async with get_db_connection() as conn:
            result = await conn.fetchrow("SELECT * FROM metadata_extract WHERE metadata_id = $1", metadata_id)
    """
    conn = None
    try:
        # Create connection
        conn = await asyncpg.connect(settings.DATABASE_URL)
        logger.debug("Database connection established")
        yield conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise
    finally:
        if conn:
            await conn.close()
            logger.debug("Database connection closed")


async def fetch_metadata_by_id(metadata_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch metadata from PostgreSQL by ID.

    Args:
        metadata_id: Metadata identifier

    Returns:
        dict: Metadata JSON or None if not found
    """
    async with get_db_connection() as conn:
        query = """
            SELECT
                metadata_id,
                metadata_json,
                created_at,
                updated_at
            FROM metadata_extract
            WHERE metadata_id = $1
        """

        result = await conn.fetchrow(query, metadata_id)

        if result:
            logger.info(f"Found metadata for ID: {metadata_id}")
            return {
                "metadata_id": result["metadata_id"],
                "metadata_json": result["metadata_json"],
                "created_at": result["created_at"].isoformat() if result["created_at"] else None,
                "updated_at": result["updated_at"].isoformat() if result["updated_at"] else None
            }
        else:
            logger.warning(f"No metadata found for ID: {metadata_id}")
            return None


async def test_connection() -> bool:
    """
    Test database connectivity.

    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        async with get_db_connection() as conn:
            result = await conn.fetchval("SELECT 1")
            return result == 1
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False