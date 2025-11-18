"""
Generation Endpoints

Handles DDL and synthetic data generation with SSE streaming.
"""

import uuid
import json
import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from src.schemas.ddl import DDLGenerationRequest, DDLGenerationResponse
from src.schemas.synthetic_data import SyntheticDataRequest, SyntheticDataResponse, ApprovalRequest
from src.services.database import db_service
from src.services.llm import llm_service
from src.services.s3 import s3_service
from src.config import settings
from src.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


async def generate_ddl_stream(metadata_id: str, user_prompt: str, thread_id: str):
    """Stream DDL generation with SSE"""
    try:
        # Get metadata
        metadata = await db_service.get_metadata(metadata_id)
        if not metadata:
            yield {
                "event": "error",
                "data": json.dumps({"error": f"Metadata {metadata_id} not found"}),
            }
            return

        # Send start event
        yield {"event": "start", "data": json.dumps({"thread_id": thread_id, "status": "generating"})}

        # Mock DDL generation (replace with LangGraph later)
        ddl_parts = [
            f"-- DDL Generation for {metadata_id}\n",
            "CREATE TABLE sample_table (\n",
            "    id INTEGER PRIMARY KEY,\n",
            "    name VARCHAR(255) NOT NULL,\n",
            "    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n",
            ");\n",
        ]

        full_ddl = ""
        for part in ddl_parts:
            full_ddl += part
            await asyncio.sleep(0.1)
            yield {"event": "chunk", "data": json.dumps({"content": part})}

        # Save to database
        ddl_record = await db_service.create_ddl(
            metadata_id=metadata.id,
            thread_id=thread_id,
            ddl_statement=full_ddl,
            validation_score=0.95,
            accuracy_score=0.92,
        )

        # Upload to S3
        s3_key = f"{settings.S3_DDL_OUTPUT_PREFIX}{thread_id}.sql"
        await s3_service.upload_file(full_ddl, s3_key, content_type="text/plain")

        # Update with S3 path
        await db_service.update_ddl_status(ddl_record.id, "pending", None)

        # Send completion event
        yield {
            "event": "complete",
            "data": json.dumps(
                {
                    "thread_id": thread_id,
                    "ddl_id": ddl_record.id,
                    "status": "pending",
                    "s3_path": s3_key,
                    "validation_score": 0.95,
                }
            ),
        }

    except Exception as e:
        logger.error(f"Error in DDL generation: {e}")
        yield {"event": "error", "data": json.dumps({"error": str(e)})}


async def generate_data_stream(
    metadata_id: str, user_prompt: str, thread_id: str, num_rows: int, data_type: str
):
    """Stream synthetic data generation with SSE"""
    try:
        # Get metadata
        metadata = await db_service.get_metadata(metadata_id)
        if not metadata:
            yield {
                "event": "error",
                "data": json.dumps({"error": f"Metadata {metadata_id} not found"}),
            }
            return

        # Send start event
        yield {"event": "start", "data": json.dumps({"thread_id": thread_id, "status": "generating"})}

        # Mock synthetic data generation (replace with LangGraph later)
        synthetic_data = {
            "header": {"record_count": num_rows, "file_date": "2025-01-01"},
            "body": [
                {"id": i, "name": f"Test User {i}", "email": f"user{i}@test.com"}
                for i in range(1, num_rows + 1)
            ],
            "trailer": {"total_records": num_rows, "checksum": "ABC123"},
        }

        # Stream data in chunks
        data_str = json.dumps(synthetic_data, indent=2)
        chunk_size = 100
        for i in range(0, len(data_str), chunk_size):
            chunk = data_str[i : i + chunk_size]
            await asyncio.sleep(0.05)
            yield {"event": "chunk", "data": json.dumps({"content": chunk})}

        # Save to database
        data_record = await db_service.create_synthetic_data(
            metadata_id=metadata.id,
            thread_id=thread_id,
            synthetic_json=synthetic_data,
            row_count=num_rows,
            data_type=data_type,
        )

        # Upload to S3
        s3_key = f"{settings.S3_DATA_OUTPUT_PREFIX}{thread_id}.json"
        await s3_service.upload_file(data_str, s3_key, content_type="application/json")

        # Send completion event
        yield {
            "event": "complete",
            "data": json.dumps(
                {
                    "thread_id": thread_id,
                    "data_id": data_record.id,
                    "status": "pending",
                    "s3_path": s3_key,
                    "row_count": num_rows,
                }
            ),
        }

    except Exception as e:
        logger.error(f"Error in synthetic data generation: {e}")
        yield {"event": "error", "data": json.dumps({"error": str(e)})}


@router.post("/ddl")
async def generate_ddl(request: DDLGenerationRequest):
    """
    Generate DDL with SSE streaming.

    Args:
        request: DDL generation request

    Returns:
        StreamingResponse: SSE stream of generated DDL
    """
    thread_id = request.thread_id or str(uuid.uuid4())

    return EventSourceResponse(
        generate_ddl_stream(request.metadata_id, request.user_prompt, thread_id),
        media_type="text/event-stream",
    )


@router.post("/data")
async def generate_synthetic_data(request: SyntheticDataRequest):
    """
    Generate synthetic test data with SSE streaming.

    Args:
        request: Data generation request

    Returns:
        StreamingResponse: SSE stream of generated data
    """
    thread_id = request.thread_id or str(uuid.uuid4())

    return EventSourceResponse(
        generate_data_stream(
            request.metadata_id,
            request.user_prompt,
            thread_id,
            request.num_rows,
            request.data_type or "happy_path",
        ),
        media_type="text/event-stream",
    )


@router.post("/approve")
async def approve_generation(request: ApprovalRequest):
    """
    Approve or reject generated content.

    Args:
        request: Approval request

    Returns:
        dict: Approval status
    """
    try:
        status_value = "approved" if request.approved else "rejected"

        if request.generation_type == "ddl":
            # Update DDL status
            success = await db_service.update_ddl_status(
                request.generation_id, status_value, request.feedback
            )
        elif request.generation_type == "synthetic_data":
            # Update synthetic data status
            success = await db_service.update_synthetic_data_status(
                request.generation_id, status_value, request.feedback
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid generation_type. Must be 'ddl' or 'synthetic_data'",
            )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Generation not found"
            )

        return {
            "generation_id": request.generation_id,
            "generation_type": request.generation_type,
            "status": status_value,
            "message": f"Generation {status_value} successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update generation status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update status: {str(e)}",
        )
