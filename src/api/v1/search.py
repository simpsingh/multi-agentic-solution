"""
Search Endpoints

Provides search functionality for DDL and synthetic data generations.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel

from src.schemas.ddl import DDLGenerationResponse
from src.schemas.synthetic_data import SyntheticDataResponse
from src.services.database import db_service
from src.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


class DDLSearchRequest(BaseModel):
    """Request model for DDL search"""

    metadata_id: Optional[str] = None
    status: Optional[str] = None
    skip: int = 0
    limit: int = 10


class DataSearchRequest(BaseModel):
    """Request model for synthetic data search"""

    metadata_id: Optional[str] = None
    status: Optional[str] = None
    data_type: Optional[str] = None
    skip: int = 0
    limit: int = 10


@router.post("/ddl", response_model=List[DDLGenerationResponse])
async def search_ddl(request: DDLSearchRequest):
    """
    Search DDL generations with filters.

    Args:
        request: DDL search request

    Returns:
        List[DDLGenerationResponse]: List of DDL generations
    """
    try:
        # Get metadata ID if provided
        metadata_db_id = None
        if request.metadata_id:
            metadata = await db_service.get_metadata(request.metadata_id)
            if not metadata:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Metadata {request.metadata_id} not found",
                )
            metadata_db_id = metadata.id

        # Search DDL generations
        ddl_list = await db_service.list_ddl(
            metadata_id=metadata_db_id, skip=request.skip, limit=request.limit
        )

        # Filter by status if provided
        if request.status:
            ddl_list = [d for d in ddl_list if d.status == request.status]

        return [DDLGenerationResponse.model_validate(d) for d in ddl_list]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search DDL generations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search DDL generations: {str(e)}",
        )


@router.post("/data", response_model=List[SyntheticDataResponse])
async def search_synthetic_data(request: DataSearchRequest):
    """
    Search synthetic data generations with filters.

    Args:
        request: Data search request

    Returns:
        List[SyntheticDataResponse]: List of synthetic data generations
    """
    try:
        # Get metadata ID if provided
        metadata_db_id = None
        if request.metadata_id:
            metadata = await db_service.get_metadata(request.metadata_id)
            if not metadata:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Metadata {request.metadata_id} not found",
                )
            metadata_db_id = metadata.id

        # Search synthetic data generations
        data_list = await db_service.list_synthetic_data(
            metadata_id=metadata_db_id, skip=request.skip, limit=request.limit
        )

        # Filter by status and data_type if provided
        if request.status:
            data_list = [d for d in data_list if d.status == request.status]
        if request.data_type:
            data_list = [d for d in data_list if d.data_type == request.data_type]

        return [SyntheticDataResponse.model_validate(d) for d in data_list]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search synthetic data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search synthetic data: {str(e)}",
        )


@router.get("/ddl/{ddl_id}", response_model=DDLGenerationResponse)
async def get_ddl_by_id(ddl_id: int):
    """
    Get a specific DDL generation by ID.

    Args:
        ddl_id: DDL generation ID

    Returns:
        DDLGenerationResponse: DDL generation details
    """
    try:
        # For now, fetch through list_ddl and filter
        # TODO: Add get_ddl_by_id method to database service
        ddl_list = await db_service.list_ddl(skip=0, limit=1000)
        ddl = next((d for d in ddl_list if d.id == ddl_id), None)

        if not ddl:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"DDL generation {ddl_id} not found"
            )

        return DDLGenerationResponse.model_validate(ddl)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get DDL generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get DDL generation: {str(e)}",
        )


@router.get("/data/{data_id}", response_model=SyntheticDataResponse)
async def get_data_by_id(data_id: int):
    """
    Get a specific synthetic data generation by ID.

    Args:
        data_id: Synthetic data generation ID

    Returns:
        SyntheticDataResponse: Synthetic data generation details
    """
    try:
        # For now, fetch through list_synthetic_data and filter
        # TODO: Add get_synthetic_data_by_id method to database service
        data_list = await db_service.list_synthetic_data(skip=0, limit=1000)
        data = next((d for d in data_list if d.id == data_id), None)

        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Synthetic data generation {data_id} not found",
            )

        return SyntheticDataResponse.model_validate(data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get synthetic data generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get synthetic data generation: {str(e)}",
        )
