"""
LangGraph Workflow Definition

Builds the complete LangGraph workflow with all agents and routing.
"""

import asyncio
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from src.agents.state import AgentState
from src.agents.supervisor import supervisor_node, should_continue
from src.agents.ddl_agent import ddl_agent_node
from src.agents.data_agent import data_agent_node
from src.agents.doc_parser_agent import doc_parser_agent_node
from src.agents.human_approval import human_approval_node
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Global checkpointer instance (singleton)
_checkpointer_instance = None
_checkpointer_context = None


def create_workflow() -> StateGraph:
    """
    Create the LangGraph workflow with all nodes and edges.

    Workflow Architecture:
        1. ALL inputs (UI/API) → supervisor (entry point)
        2. supervisor analyzes intent → routes to specialized agents
        3. Agents generate output → human_approval (with interrupt_before)
        4. User provides feedback → supervisor (retry) or END (approved)

    Returns:
        StateGraph: Compiled LangGraph workflow

    Notes:
        - Human approval uses interrupt_before() mechanism
        - Feedback loop max iterations: MAX_FEEDBACK_ITERATIONS (config)
        - Document parsing will also use this pathway (future)
    """
    workflow = StateGraph(AgentState)

    # Add all nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("ddl_agent", ddl_agent_node)
    workflow.add_node("data_agent", data_agent_node)
    workflow.add_node("doc_parser_agent", doc_parser_agent_node)  # Document parser agent
    workflow.add_node("human_approval", human_approval_node)
    # workflow.add_node("qa_agent", qa_agent_node)  # TODO: Implement
    # workflow.add_node("lineage_agent", lineage_agent_node)  # TODO: Implement

    # Set entry point - ALL inputs go through supervisor first
    workflow.set_entry_point("supervisor")

    # Add conditional edges from supervisor (routes based on intent)
    workflow.add_conditional_edges(
        "supervisor",
        should_continue,
        {
            "ddl_agent": "ddl_agent",
            "data_agent": "data_agent",
            "doc_parser_agent": "doc_parser_agent",  # Document parser routing
            # "qa_agent": "qa_agent",  # TODO: Uncomment when implemented
            # "lineage_agent": "lineage_agent",  # TODO: Uncomment when implemented
            "human_approval": "human_approval",
            "supervisor": "supervisor",  # Retry loop for feedback
            "end": END
        }
    )

    # Agent outputs → human_approval for review
    workflow.add_edge("ddl_agent", "human_approval")
    workflow.add_edge("data_agent", "human_approval")
    workflow.add_edge("doc_parser_agent", "human_approval")  # Doc parser → human approval
    # workflow.add_edge("qa_agent", "human_approval")  # TODO: Uncomment when implemented
    # workflow.add_edge("lineage_agent", "human_approval")  # TODO: Uncomment when implemented

    # Human approval → conditional routing (approve → END, reject → supervisor)
    workflow.add_conditional_edges(
        "human_approval",
        should_continue,
        {
            "supervisor": "supervisor",  # User rejected, retry with feedback
            "end": END  # User approved, end workflow
        }
    )

    return workflow


async def get_postgres_checkpointer():
    """
    Create and return an AsyncPostgresSaver checkpointer with proper connection management.

    Returns:
        AsyncPostgresSaver: Configured checkpointer for state persistence
    """
    global _checkpointer_instance, _checkpointer_context

    # Return existing instance if already initialized
    if _checkpointer_instance is not None:
        return _checkpointer_instance

    # Create checkpointer with connection string (AsyncPostgresSaver manages its own pool)
    connection_string = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

    # Enter async context manager and keep it alive
    _checkpointer_context = AsyncPostgresSaver.from_conn_string(connection_string)
    _checkpointer_instance = await _checkpointer_context.__aenter__()

    # Setup the checkpointer tables if they don't exist
    await _checkpointer_instance.setup()

    logger.info("PostgreSQL checkpointer initialized successfully")
    return _checkpointer_instance


async def get_compiled_graph():
    """
    Get compiled LangGraph with checkpointer and human-in-the-loop.

    Returns:
        Compiled graph with AsyncPostgresSaver and interrupt_before enabled

    Notes:
        - interrupt_before=["human_approval"] pauses execution before human_approval node
        - Graph resumes when app.aupdate_state() is called with user feedback
        - Checkpointer persists state across interruptions
    """
    workflow = create_workflow()

    try:
        # Get the PostgreSQL checkpointer
        checkpointer = await get_postgres_checkpointer()

        # Compile with checkpointer and human-in-the-loop
        app = workflow.compile(
            checkpointer=checkpointer,
            interrupt_before=["human_approval"]  # Pause before human approval
        )

        logger.info("LangGraph compiled with checkpointer and human-in-the-loop enabled")

    except Exception as e:
        logger.warning(f"Failed to setup checkpointer: {e}. Falling back to non-persistent mode.")
        # Fallback to non-checkpointed version if there's an issue
        app = workflow.compile()

    return app
