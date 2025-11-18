"""
LangGraph Agent API Endpoints

Provides FastAPI endpoints for interacting with the multi-agent system.
All requests route through supervisor for intent detection and agent delegation.
"""

from fastapi import APIRouter, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import uuid
from datetime import datetime
import logging

from src.agents.graph import get_compiled_graph
from src.agents.state import AgentState
from src.utils.thread_helpers import generate_thread_id
from src.utils.auth import get_user_id_from_token
from src.utils.logger import get_logger
from src.config import settings

logger = get_logger(__name__)
router = APIRouter(prefix="/agents", tags=["agents"])
security = HTTPBearer(auto_error=False)


# Request/Response Models
class AgentRequest(BaseModel):
    """Request model for agent invocation"""
    user_prompt: str = Field(..., description="User's natural language prompt")
    session_id: Optional[str] = Field(None, description="Optional session identifier")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class AgentResponse(BaseModel):
    """Response model for agent invocation"""
    success: bool
    thread_id: str
    intent: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    status: str = "pending"  # pending, processing, awaiting_approval, completed, failed
    current_state: Optional[Dict[str, Any]] = None  # Full state including metadata_id


class FeedbackRequest(BaseModel):
    """Request model for human feedback"""
    thread_id: str = Field(..., description="Thread ID from initial agent request")
    feedback: Optional[str] = Field(None, description="User feedback text")
    approved: bool = Field(False, description="Whether the result is approved")


class ThreadStatusResponse(BaseModel):
    """Response model for thread status check"""
    thread_id: str
    status: str
    current_state: Dict[str, Any]
    awaiting_human_approval: bool = False


# Endpoints
@router.post("/invoke", response_model=AgentResponse)
async def invoke_agent(
    request: AgentRequest,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> AgentResponse:
    """
    Invoke the multi-agent system with a user prompt.

    ALL requests go through supervisor for intent detection and routing.
    This ensures centralized control and logging.

    Args:
        request: Agent request with user prompt
        credentials: Optional JWT credentials for user identification

    Returns:
        AgentResponse with thread_id for tracking
    """
    try:
        # Extract user ID (JWT or fallback)
        user_id = None
        if credentials:
            try:
                user_id = get_user_id_from_token(credentials)
            except Exception as e:
                logger.warning(f"Failed to extract user_id from JWT: {e}")

        # Generate thread ID
        thread_id = generate_thread_id(
            user_id=user_id,
            session_id=request.session_id
        )

        logger.info(f"Invoking agent with thread_id: {thread_id}")
        logger.info(f"User prompt: {request.user_prompt[:200]}...")

        # Initialize agent state
        initial_state = AgentState(
            user_prompt=request.user_prompt,
            thread_id=thread_id,
            user_id=user_id or "anonymous",
            session_id=request.session_id,
            metadata=request.metadata,
            iteration_count=0,
            created_at=datetime.utcnow().isoformat()
        )

        # Get compiled graph with checkpointer
        app = await get_compiled_graph()

        # Invoke graph (starts with supervisor) with thread_id configuration
        config = {"configurable": {"thread_id": thread_id}}
        result = await app.ainvoke(initial_state, config=config)

        # Extract key information from result
        response_data = {
            "success": True,
            "thread_id": thread_id,
            "intent": result.get("intent"),
            "status": "awaiting_approval" if result.get("awaiting_human_approval") else "completed"
        }

        # Include agent-specific results
        if result.get("doc_parse_result"):
            response_data["result"] = result["doc_parse_result"]
        elif result.get("ddl_result"):
            response_data["result"] = result["ddl_result"]
        elif result.get("data_result"):
            response_data["result"] = result["data_result"]

        logger.info(f"Agent invocation successful. Status: {response_data['status']}")
        return AgentResponse(**response_data)

    except Exception as e:
        logger.error(f"Error invoking agent: {e}")
        return AgentResponse(
            success=False,
            thread_id=thread_id if 'thread_id' in locals() else str(uuid.uuid4()),
            error=str(e),
            status="failed"
        )


@router.post("/feedback", response_model=AgentResponse)
async def submit_feedback(
    request: FeedbackRequest,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> AgentResponse:
    """
    Submit human feedback for a paused agent execution.

    This resumes the graph from the human_approval node with user feedback.

    Args:
        request: Feedback request with thread_id and feedback
        credentials: Optional JWT credentials

    Returns:
        AgentResponse with updated status
    """
    try:
        logger.info(f"Processing feedback for thread_id: {request.thread_id}")
        logger.info(f"Approved: {request.approved}, Feedback: {request.feedback}")

        # Get compiled graph
        app = await get_compiled_graph()

        # Get current state first
        current_state = await app.aget_state(
            config={"configurable": {"thread_id": request.thread_id}}
        )

        # Check if feedback contains update commands
        update_command = None
        if request.feedback and not request.approved:
            try:
                from src.agents.feedback_parser import feedback_parser
                update_command = feedback_parser.parse(request.feedback)
            except Exception as e:
                logger.warning(f"Failed to parse feedback as update command: {e}")
                update_command = None

            if update_command:
                logger.info(f"Detected update command: {update_command}")
                # Apply update to the doc_parse_result in current state
                if current_state.values.get("doc_parse_result"):
                    doc_result = current_state.values["doc_parse_result"]
                    metadata_json = doc_result.get("metadata_json", {})
                    tables = metadata_json.get("tables", [])

                    if tables:
                        # Find and update the specified column
                        column_id = update_command["column_id"]
                        field = update_command["field"]
                        value = update_command["value"]
                        updated_column = None

                        for table in tables:
                            columns = table.get("columns", [])
                            for col in columns:
                                if col.get("column_id") == column_id:
                                    # Update the field
                                    col[field] = value
                                    updated_column = col
                                    logger.info(f"Updated column {column_id}: {field} = {value}")
                                    break
                            if updated_column:
                                break

                        # Store the updated column for review
                        update_data = {
                            "feedback": request.feedback,
                            "approved": False,
                            "awaiting_human_approval": True,
                            "update_applied": True,
                            "updated_column": updated_column,
                            "update_command": update_command,
                            "doc_parse_result": doc_result  # Updated doc_result
                        }

                        # Don't end workflow - wait for approval of the update
                        update_data["should_end"] = False
                else:
                    # Regular feedback handling
                    update_data = {
                        "feedback": request.feedback,
                        "approved": request.approved,
                        "awaiting_human_approval": False
                    }
            else:
                # Regular feedback without update command
                update_data = {
                    "feedback": request.feedback,
                    "approved": request.approved,
                    "awaiting_human_approval": False
                }
        else:
            # Regular approval/feedback
            update_data = {
                "feedback": request.feedback,
                "approved": request.approved,
                "awaiting_human_approval": False
            }

        # If approved, we'll end the workflow AND insert to database
        if request.approved and not update_command:
            update_data["should_end"] = True

            # CRITICAL: Insert to database when approved
            # Check if we have doc_parse_result to insert
            if current_state.values.get("doc_parse_result"):
                doc_result = current_state.values["doc_parse_result"]
                if all(key in doc_result for key in ["metadata_id", "document_name", "s3_bucket", "s3_key", "metadata_json"]):
                    try:
                        from src.agents.db_helpers import insert_document_metadata
                        logger.info(f"Inserting metadata to database on approval: {doc_result['metadata_id']}")

                        # Insert metadata into PostgreSQL
                        db_id = await insert_document_metadata(
                            metadata_id=doc_result["metadata_id"],
                            document_name=doc_result["document_name"],
                            s3_bucket=doc_result["s3_bucket"],
                            s3_key=doc_result["s3_key"],
                            metadata_json=doc_result["metadata_json"]
                        )

                        logger.info(f"✅ Metadata inserted successfully with DB ID: {db_id}")
                        update_data["metadata_id"] = db_id

                    except Exception as e:
                        logger.error(f"❌ Failed to insert metadata: {e}")
        elif not request.approved and not update_command:
            # Increment iteration count for retry
            iteration_count = current_state.values.get("iteration_count", 0)
            update_data["iteration_count"] = iteration_count + 1

        # Update the state (resumes from interrupt)
        await app.aupdate_state(
            config={"configurable": {"thread_id": request.thread_id}},
            values=update_data
        )

        # ALWAYS continue execution to run human_approval node
        # The human_approval node handles DB insertion when approved=True
        try:
            result = await app.ainvoke(
                None,  # No new input, continuing from checkpoint
                config={"configurable": {"thread_id": request.thread_id}}
            )
        except Exception as e:
            # If we get an error, it might be because the workflow ended
            # Try to get the final state
            logger.warning(f"Workflow invocation issue: {e}")
            final_state = await app.aget_state(
                config={"configurable": {"thread_id": request.thread_id}}
            )
            result = final_state.values if final_state else {}

        # Build response
        response_data = {
            "success": True,
            "thread_id": request.thread_id,
            "intent": result.get("intent") if result else None,
            "status": "awaiting_approval" if update_command else ("completed" if request.approved else "processing"),
            "current_state": result  # Include full state so UI can access metadata_id
        }

        # Include results
        if result.get("doc_parse_result"):
            response_data["result"] = result["doc_parse_result"]
        elif result.get("ddl_result"):
            response_data["result"] = result["ddl_result"]
        elif result.get("data_result"):
            response_data["result"] = result["data_result"]

        # If update was applied, include the updated column in the response
        # Note: we check update_command here because result might not have update_applied after workflow
        if update_command:
            response_data["update_applied"] = True
            response_data["updated_column"] = update_data.get("updated_column")
            response_data["update_command"] = update_command
            # Make sure current_state has these flags too
            response_data["current_state"]["update_applied"] = True
            response_data["current_state"]["updated_column"] = update_data.get("updated_column")
            response_data["current_state"]["update_command"] = update_command

        logger.info(f"Feedback processed. Status: {response_data['status']}")
        return AgentResponse(**response_data)

    except Exception as e:
        logger.error(f"Error processing feedback: {e}")
        return AgentResponse(
            success=False,
            thread_id=request.thread_id,
            error=str(e),
            status="failed"
        )


@router.get("/status/{thread_id}", response_model=ThreadStatusResponse)
async def get_thread_status(
    thread_id: str,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> ThreadStatusResponse:
    """
    Get the current status of an agent thread.

    Args:
        thread_id: Thread identifier
        credentials: Optional JWT credentials

    Returns:
        ThreadStatusResponse with current state
    """
    try:
        logger.info(f"Checking status for thread_id: {thread_id}")

        # Get compiled graph
        app = await get_compiled_graph()

        # Get current state
        state = await app.aget_state(
            config={"configurable": {"thread_id": thread_id}}
        )

        if not state:
            raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found")

        # Determine status
        values = state.values
        if values.get("awaiting_human_approval"):
            status = "awaiting_approval"
        elif values.get("error"):
            status = "failed"
        elif values.get("approved") or values.get("should_end"):
            status = "completed"
        else:
            status = "processing"

        return ThreadStatusResponse(
            thread_id=thread_id,
            status=status,
            current_state=values,
            awaiting_human_approval=values.get("awaiting_human_approval", False)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting thread status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/threads", response_model=List[str])
async def list_threads(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> List[str]:
    """
    List all thread IDs for the authenticated user.

    Args:
        credentials: Optional JWT credentials

    Returns:
        List of thread IDs

    Note: This is a simplified version. In production, you'd filter by user_id.
    """
    try:
        # TODO: Implement proper thread listing with user filtering
        # For now, return empty list
        logger.info("Listing threads (not implemented)")
        return []

    except Exception as e:
        logger.error(f"Error listing threads: {e}")
        raise HTTPException(status_code=500, detail=str(e))