"""
Database Helper Functions for Agents

Provides database insertion utilities for agent workflows,
specifically for inserting parsed document metadata into PostgreSQL.
"""

from typing import Dict, Any
from src.services.database import db_service
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def insert_document_metadata(
    metadata_id: str,
    document_name: str,
    s3_bucket: str,
    s3_key: str,
    metadata_json: dict
) -> int:
    """
    Insert document metadata into PostgreSQL.

    This function is called after human approval to persist the parsed
    document metadata into the metadata_extract table.

    Args:
        metadata_id: Unique metadata identifier (e.g., META_DOC_PARSE_20250112_ABC123)
        document_name: Source document name (e.g., Fintrac_Swift_Source_Extract_Specification_v4_plus_appendix.docx)
        s3_bucket: S3 bucket name (e.g., ses-v1)
        s3_key: S3 object key (e.g., input/Fintrac_Swift_Source_Extract_Specification_v4_plus_appendix.docx)
        metadata_json: Parsed metadata dictionary containing tables and columns

    Returns:
        int: Primary key ID of the inserted metadata record

    Raises:
        Exception: If database insertion fails
    """
    try:
        logger.info(f"Inserting metadata into database: {metadata_id}")
        logger.info(f"  Document: {document_name}")
        logger.info(f"  S3 Path: s3://{s3_bucket}/{s3_key}")
        logger.info(f"  Tables: {len(metadata_json.get('tables', []))}")

        # Calculate column count
        table_count = len(metadata_json.get("tables", []))
        column_count = sum(len(table.get("columns", [])) for table in metadata_json.get("tables", []))

        logger.info(f"  Columns: {column_count}")

        # Insert into database using db_service
        metadata_record = await db_service.create_metadata(
            metadata_id=metadata_id,
            src_doc_name=document_name,
            src_doc_path=f"s3://{s3_bucket}/{s3_key}",
            metadata_json=metadata_json,
            description=f"Parsed from {document_name} - {table_count} table(s), {column_count} column(s)"
        )

        logger.info(f"✅ Metadata inserted successfully")
        logger.info(f"  Database ID: {metadata_record.id}")
        logger.info(f"  Metadata ID: {metadata_record.metadata_id}")

        return metadata_record.id

    except Exception as e:
        logger.error(f"❌ Failed to insert metadata: {e}")
        raise Exception(f"Database insertion failed: {str(e)}")
