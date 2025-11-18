"""
Document Parser Service

Uses Docling to parse PDF/DOCX documents and extract structured metadata.
"""

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ParserService:
    """Document parsing service using Docling"""

    def __init__(self):
        # TODO: Initialize Docling
        pass

    async def parse_document(self, file_path: str) -> dict:
        """
        Parse document and extract metadata.

        Args:
            file_path: Path to document file

        Returns:
            dict: Parsed metadata in standard format
        """
        # TODO: Implement Docling parsing
        logger.info(f"Parsing document: {file_path}")
        return {
            "spec_name": "",
            "spec_version": "",
            "spec_date": "",
            "file_delimiter": "|",
            "fields": [],
        }

    async def normalize_metadata(self, raw_metadata: dict) -> dict:
        """
        Normalize parsed metadata to standard format.

        Args:
            raw_metadata: Raw parsed metadata

        Returns:
            dict: Normalized metadata
        """
        # TODO: Implement normalization
        logger.info("Normalizing metadata")
        return raw_metadata
