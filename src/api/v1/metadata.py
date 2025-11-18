"""
Metadata Management Endpoints

Handles metadata extraction, retrieval, and listing.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.schemas.metadata import MetadataUploadRequest, MetadataResponse
from src.services.database import db_service, get_session
from src.models.metadata import MetadataExtract
from src.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/upload", response_model=MetadataResponse, status_code=status.HTTP_201_CREATED)
async def upload_metadata(request: MetadataUploadRequest):
    """
    Upload metadata JSON directly.

    Args:
        request: Metadata upload request

    Returns:
        MetadataResponse: Created metadata details
    """
    try:
        # Set default src_doc_path if not provided
        src_doc_path = request.src_doc_path or f"input/{request.metadata_id}.json"

        # Create metadata in database
        metadata = await db_service.create_metadata(
            metadata_id=request.metadata_id,
            src_doc_name=request.src_doc_name,
            src_doc_path=src_doc_path,
            metadata_json=request.metadata_json.model_dump(),
            description=request.description,
        )

        logger.info(f"Created metadata: {metadata.metadata_id}")
        return MetadataResponse.model_validate(metadata)

    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Metadata with ID '{request.metadata_id}' already exists",
        )
    except Exception as e:
        logger.error(f"Failed to upload metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload metadata: {str(e)}",
        )


@router.get("/{metadata_id}", response_model=MetadataResponse)
async def get_metadata(metadata_id: str):
    """
    Retrieve metadata by ID.

    Args:
        metadata_id: Unique metadata identifier

    Returns:
        MetadataResponse: Metadata details
    """
    try:
        metadata = await db_service.get_metadata(metadata_id)

        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Metadata with ID '{metadata_id}' not found",
            )

        return MetadataResponse.model_validate(metadata)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve metadata: {str(e)}",
        )


@router.get("/", response_model=List[MetadataResponse])
async def list_metadata(skip: int = 0, limit: int = 10):
    """
    List all metadata entries with pagination.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List[MetadataResponse]: List of metadata entries
    """
    try:
        if limit > 100:
            limit = 100  # Cap at 100 for safety

        metadata_list = await db_service.list_metadata(skip=skip, limit=limit)
        return [MetadataResponse.model_validate(m) for m in metadata_list]

    except Exception as e:
        logger.error(f"Failed to list metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list metadata: {str(e)}",
        )


@router.get("/data-dictionary/{metadata_id}")
async def get_data_dictionary(
    metadata_id: str,
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """
    Get data dictionary for a metadata ID.

    Returns 5 sample fields including:
    - At least 1 from header section
    - At least 1 from trailer section
    - At least 2 from body section

    Args:
        metadata_id: Unique metadata identifier
        session: Database session

    Returns:
        Dict containing metadata_id, table_name, sample_fields, and section_counts
    """
    try:
        # Fetch metadata from database
        metadata_record = session.query(MetadataExtract).filter_by(
            metadata_id=metadata_id
        ).first()

        if not metadata_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Metadata ID '{metadata_id}' not found"
            )

        if not metadata_record.metadata_json:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No metadata JSON found"
            )

        # Extract metadata JSON
        metadata_json = metadata_record.metadata_json

        # Get first table
        if not metadata_json.get("tables") or len(metadata_json["tables"]) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No tables found in metadata"
            )

        table = metadata_json["tables"][0]
        columns = table.get("columns", [])

        if len(columns) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No columns found"
            )

        # Extract sample fields from different sections
        header_fields = []
        trailer_fields = []
        body_fields = []

        for column in columns:
            section_type = column.get("section_type", "").lower()

            if "header" in section_type:
                header_fields.append(column)
            elif "trailer" in section_type or "footer" in section_type:
                trailer_fields.append(column)
            else:
                body_fields.append(column)

        # Select 5 sample fields
        sample_fields = []

        # Add at least 1 header field
        if header_fields:
            sample_fields.append(header_fields[0])

        # Add at least 1 trailer field
        if trailer_fields:
            sample_fields.append(trailer_fields[0])

        # Add at least 2 body fields
        if len(body_fields) >= 2:
            sample_fields.extend(body_fields[:2])
        elif body_fields:
            sample_fields.append(body_fields[0])

        # Fill up to 5 fields if we have less
        remaining_count = 5 - len(sample_fields)
        if remaining_count > 0:
            # Add more body fields if available
            for i in range(2, min(2 + remaining_count, len(body_fields))):
                sample_fields.append(body_fields[i])

            # If still not enough, add more from any section
            if len(sample_fields) < 5:
                all_remaining = header_fields[1:] + trailer_fields[1:] + body_fields[len(sample_fields)-2:]
                for field in all_remaining:
                    if len(sample_fields) >= 5:
                        break
                    if field not in sample_fields:
                        sample_fields.append(field)

        # Limit to 5 fields
        sample_fields = sample_fields[:5]

        return {
            "metadata_id": metadata_id,
            "table_name": table.get("table_name"),
            "total_columns": len(columns),
            "sample_fields": sample_fields,
            "section_counts": {
                "header": len(header_fields),
                "body": len(body_fields),
                "trailer": len(trailer_fields)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get data dictionary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get data dictionary: {str(e)}",
        )
