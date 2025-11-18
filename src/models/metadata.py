"""
Metadata Database Model

Stores metadata extracted from Excel files uploaded to S3.
"""

from sqlalchemy import Column, String, JSON, Integer, Text
from sqlalchemy.orm import relationship
from src.models.base import Base, TimestampMixin


class MetadataExtract(Base, TimestampMixin):
    """
    Metadata extraction table.

    Stores metadata about table structures extracted from Excel files.
    Each record represents a metadata document that can be used to generate DDL.
    """

    __tablename__ = "metadata_extract"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Metadata identifier (e.g., table name or unique identifier)
    metadata_id = Column(String(64), unique=True, nullable=False, index=True)

    # Source document information
    src_doc_name = Column(String(512), nullable=False)
    src_doc_path = Column(String(512), nullable=False)  # S3 path

    # Metadata JSON containing column definitions, data types, constraints, etc.
    metadata_json = Column(JSON, nullable=False)

    # Optional: Description or notes about this metadata
    description = Column(Text, nullable=True)

    # Status: 'uploaded', 'processed', 'indexed'
    status = Column(String(32), default='uploaded', nullable=False, index=True)

    # Relationships
    ddl_generations = relationship("DDLGeneration", back_populates="metadata_extract", cascade="all, delete-orphan")
    synthetic_data_generations = relationship("SyntheticDataGeneration", back_populates="metadata_extract", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MetadataExtract(id={self.id}, metadata_id='{self.metadata_id}', status='{self.status}')>"
