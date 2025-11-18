"""
Database Service

Handles PostgreSQL operations with async support.
"""

from typing import AsyncGenerator, Generator, List, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine, select, update, delete
from sqlalchemy.exc import IntegrityError

from src.config import settings
from src.utils.logger import get_logger
from src.models.metadata import MetadataExtract
from src.models.ddl import DDLGeneration
from src.models.synthetic_data import SyntheticDataGeneration

logger = get_logger(__name__)


class DatabaseService:
    """Async PostgreSQL service"""

    def __init__(self):
        self.engine = create_async_engine(
            settings.DATABASE_URL,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            echo=False,
        )
        self.async_session_factory = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session.

        Yields:
            AsyncSession: Database session
        """
        async with self.async_session_factory() as session:
            yield session

    async def close(self):
        """Close database connections"""
        await self.engine.dispose()
        logger.info("Database connections closed")

    # Metadata CRUD operations
    async def create_metadata(
        self, metadata_id: str, src_doc_name: str, src_doc_path: str, metadata_json: dict, description: Optional[str] = None
    ) -> MetadataExtract:
        """Create a new metadata entry"""
        async with self.async_session_factory() as session:
            metadata = MetadataExtract(
                metadata_id=metadata_id,
                src_doc_name=src_doc_name,
                src_doc_path=src_doc_path,
                metadata_json=metadata_json,
                description=description,
            )
            session.add(metadata)
            try:
                await session.commit()
                await session.refresh(metadata)
                return metadata
            except IntegrityError as e:
                await session.rollback()
                logger.error(f"Failed to create metadata: {e}")
                raise

    async def get_metadata(self, metadata_id: str) -> Optional[MetadataExtract]:
        """Get metadata by metadata_id"""
        async with self.async_session_factory() as session:
            result = await session.execute(
                select(MetadataExtract).where(MetadataExtract.metadata_id == metadata_id)
            )
            return result.scalar_one_or_none()

    async def get_metadata_by_id(self, id: int) -> Optional[MetadataExtract]:
        """Get metadata by primary key id"""
        async with self.async_session_factory() as session:
            result = await session.execute(
                select(MetadataExtract).where(MetadataExtract.id == id)
            )
            return result.scalar_one_or_none()

    async def list_metadata(self, skip: int = 0, limit: int = 10) -> List[MetadataExtract]:
        """List all metadata with pagination"""
        async with self.async_session_factory() as session:
            result = await session.execute(
                select(MetadataExtract).offset(skip).limit(limit).order_by(MetadataExtract.created_at.desc())
            )
            return list(result.scalars().all())

    # DDL CRUD operations
    async def create_ddl(
        self,
        metadata_id: int,
        thread_id: str,
        ddl_statement: str,
        ddl_file_path: Optional[str] = None,
        validation_score: Optional[float] = None,
        accuracy_score: Optional[float] = None,
    ) -> DDLGeneration:
        """Create a new DDL generation entry"""
        async with self.async_session_factory() as session:
            ddl = DDLGeneration(
                metadata_id=metadata_id,
                thread_id=thread_id,
                ddl_statement=ddl_statement,
                ddl_file_path=ddl_file_path,
                validation_score=validation_score,
                accuracy_score=accuracy_score,
            )
            session.add(ddl)
            await session.commit()
            await session.refresh(ddl)
            return ddl

    async def get_ddl_by_thread(self, thread_id: str) -> Optional[DDLGeneration]:
        """Get DDL by thread_id"""
        async with self.async_session_factory() as session:
            result = await session.execute(
                select(DDLGeneration).where(DDLGeneration.thread_id == thread_id).order_by(DDLGeneration.created_at.desc())
            )
            return result.scalar_one_or_none()

    async def update_ddl_status(self, ddl_id: int, status: str, feedback: Optional[str] = None) -> bool:
        """Update DDL status and feedback"""
        async with self.async_session_factory() as session:
            await session.execute(
                update(DDLGeneration)
                .where(DDLGeneration.id == ddl_id)
                .values(status=status, user_feedback=feedback)
            )
            await session.commit()
            return True

    async def list_ddl(self, metadata_id: Optional[int] = None, skip: int = 0, limit: int = 10) -> List[DDLGeneration]:
        """List DDL generations with optional filtering"""
        async with self.async_session_factory() as session:
            query = select(DDLGeneration)
            if metadata_id:
                query = query.where(DDLGeneration.metadata_id == metadata_id)
            query = query.offset(skip).limit(limit).order_by(DDLGeneration.created_at.desc())
            result = await session.execute(query)
            return list(result.scalars().all())

    # Synthetic Data CRUD operations
    async def create_synthetic_data(
        self,
        metadata_id: int,
        thread_id: str,
        synthetic_json: dict,
        ddl_id: Optional[int] = None,
        file_path: Optional[str] = None,
        row_count: Optional[int] = None,
        data_type: Optional[str] = None,
    ) -> SyntheticDataGeneration:
        """Create a new synthetic data entry"""
        async with self.async_session_factory() as session:
            data = SyntheticDataGeneration(
                metadata_id=metadata_id,
                ddl_id=ddl_id,
                thread_id=thread_id,
                file_path=file_path,
                synthetic_json=synthetic_json,
                row_count=row_count,
                data_type=data_type,
            )
            session.add(data)
            await session.commit()
            await session.refresh(data)
            return data

    async def get_synthetic_data_by_thread(self, thread_id: str) -> Optional[SyntheticDataGeneration]:
        """Get synthetic data by thread_id"""
        async with self.async_session_factory() as session:
            result = await session.execute(
                select(SyntheticDataGeneration)
                .where(SyntheticDataGeneration.thread_id == thread_id)
                .order_by(SyntheticDataGeneration.created_at.desc())
            )
            return result.scalar_one_or_none()

    async def update_synthetic_data_status(self, data_id: int, status: str, feedback: Optional[str] = None) -> bool:
        """Update synthetic data status and feedback"""
        async with self.async_session_factory() as session:
            await session.execute(
                update(SyntheticDataGeneration)
                .where(SyntheticDataGeneration.id == data_id)
                .values(status=status, user_feedback=feedback)
            )
            await session.commit()
            return True

    async def list_synthetic_data(
        self, metadata_id: Optional[int] = None, skip: int = 0, limit: int = 10
    ) -> List[SyntheticDataGeneration]:
        """List synthetic data generations with optional filtering"""
        async with self.async_session_factory() as session:
            query = select(SyntheticDataGeneration)
            if metadata_id:
                query = query.where(SyntheticDataGeneration.metadata_id == metadata_id)
            query = query.offset(skip).limit(limit).order_by(SyntheticDataGeneration.created_at.desc())
            result = await session.execute(query)
            return list(result.scalars().all())


# Global instance
db_service = DatabaseService()


# Dependency for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions"""
    async for session in db_service.get_session():
        yield session


# Synchronous session for Airflow DAGs
# Convert postgresql+asyncpg:// to postgresql+psycopg2:// for sync operations
_sync_database_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
_sync_engine = create_engine(
    _sync_database_url,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=False,
)
_sync_session_factory = sessionmaker(_sync_engine, class_=Session, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    """
    Synchronous database session generator for Airflow DAGs.

    Usage:
        session = next(get_session())
        try:
            # Use session
            session.commit()
        finally:
            session.close()

    Yields:
        Session: Synchronous database session
    """
    session = _sync_session_factory()
    try:
        yield session
    finally:
        session.close()
