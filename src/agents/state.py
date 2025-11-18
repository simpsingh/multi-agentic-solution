"""
Agent State Definition

Defines the AgentState schema used by LangGraph for state management.
"""

from typing import TypedDict, Sequence, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    State schema for LangGraph agents.

    This state is persisted via AsyncPostgresSaver checkpoints.
    """

    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_prompt: str
    metadata_id: int | None
    metadata_json: dict | None
    session_id: str
    intent: str  # "ddl" | "data" | "both" | "qa"
    ddl_result: str | None
    data_result: str | None
    qa_result: str | None
    validation_scores: dict
    accuracy_scores: dict
    feedback: str | None
    iteration_count: int
    approved: bool
    awaiting_human_approval: bool
    ddl_file_path: str | None
    data_file_path: str | None
    tool_calls: list
    retrieved_context: list[dict] | None

    # Document parsing fields
    doc_parse_result: dict | None  # Full result from doc parser including metadata_json
    progress_tasks: list[dict] | None  # Task progress with status for UI display

    # Additional fields
    thread_id: str  # Thread ID for LangGraph checkpointing
    user_id: str  # User identifier
    created_at: str  # Timestamp when request was created
    should_end: bool  # Flag to end workflow
    error: str | None  # Error message if any
