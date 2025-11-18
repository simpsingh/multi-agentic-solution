"""
Supervisor Agent

Routes requests to appropriate specialized agents based on intent analysis.
All user inputs from UI/API must pass through this agent first for routing.
"""

from src.agents.state import AgentState
from src.utils.logger import get_logger
from src.config import settings

logger = get_logger(__name__)


async def supervisor_node(state: AgentState) -> AgentState:
    """
    Supervisor node that analyzes intent and routes to appropriate agent.

    ALL user inputs from UI/API must pass through this node first.
    This ensures centralized intent detection and routing.

    Args:
        state: Current agent state

    Returns:
        AgentState: Updated state with intent

    Supported Intents:
        - "ddl": DDL generation only
        - "data": Synthetic data generation only
        - "both": DDL + Data generation
        - "qa": Question answering about specs/metadata
        - "lineage": Data lineage analysis
        - "search": Search existing DDL/data/specs
    """
    user_prompt = state.get("user_prompt", "")
    feedback = state.get("feedback")
    iteration = state.get("iteration_count", 0)

    logger.info(f"Supervisor analyzing intent (iteration {iteration}): {user_prompt[:100]}...")

    # If feedback provided, log it for context
    if feedback:
        logger.info(f"Processing user feedback: {feedback[:100]}...")

    # TODO: Implement LLM-based intent detection using Bedrock
    # For now, use keyword-based heuristics
    intent = _detect_intent_heuristic(user_prompt)

    state["intent"] = intent
    logger.info(f"Detected intent: {intent}")

    return state


def _detect_intent_heuristic(prompt: str) -> str:
    """
    Heuristic-based intent detection (placeholder for LLM-based detection).

    Args:
        prompt: User prompt text

    Returns:
        str: Detected intent
    """
    prompt_lower = prompt.lower()

    # Document parsing keywords (check first as it's the user's priority)
    if any(kw in prompt_lower for kw in ["parse document", "extract from document", "process document",
                                           "parse", "extract metadata", ".docx", ".doc", "fintrac"]):
        return "doc_parse"

    # DDL generation keywords
    if any(kw in prompt_lower for kw in ["create table", "ddl", "schema", "database design"]):
        return "ddl"

    # Data generation keywords
    if any(kw in prompt_lower for kw in ["test data", "synthetic data", "generate data", "sample data"]):
        return "data"

    # Both DDL + Data
    if any(kw in prompt_lower for kw in ["ddl and data", "schema and data", "complete setup"]):
        return "both"

    # Data lineage keywords
    if any(kw in prompt_lower for kw in ["lineage", "data flow", "trace", "upstream", "downstream"]):
        return "lineage"

    # Question answering keywords
    if any(kw in prompt_lower for kw in ["what is", "explain", "how", "why", "describe", "?"]):
        return "qa"

    # Search keywords
    if any(kw in prompt_lower for kw in ["search", "find", "lookup", "retrieve", "show me"]):
        return "search"

    # Default to DDL
    return "ddl"


def should_continue(state: AgentState) -> str:
    """
    Conditional routing logic for the LangGraph workflow.

    This function determines the next node based on the current state.
    Used by LangGraph's add_conditional_edges().

    Args:
        state: Current agent state

    Returns:
        str: Next node name or "end"

    Routing Logic:
        1. If awaiting_human_approval → "human_approval"
        2. If iteration_count >= MAX_FEEDBACK_ITERATIONS → "end"
        3. If user provided feedback and not approved → "supervisor" (retry)
        4. Otherwise → route based on intent
    """
    # Check if workflow should end
    if state.get("should_end") or state.get("approved"):
        logger.info("Workflow approved or marked to end, routing to END")
        return "end"

    # Check if awaiting human approval
    if state.get("awaiting_human_approval"):
        logger.info("Routing to human_approval node")
        return "human_approval"

    # Check max iterations (prevent infinite loops)
    iteration = state.get("iteration_count", 0)
    if iteration >= settings.MAX_FEEDBACK_ITERATIONS:
        logger.warning(f"Max iterations ({settings.MAX_FEEDBACK_ITERATIONS}) reached, ending workflow")
        return "end"

    # If feedback provided and not approved, retry with supervisor
    if state.get("feedback") and not state.get("approved"):
        logger.info("User feedback provided, routing back to supervisor for retry")
        return "supervisor"

    # Route based on intent
    intent = state.get("intent", "ddl")
    logger.info(f"Routing based on intent: {intent}")

    if intent == "doc_parse":
        return "doc_parser_agent"
    elif intent == "ddl":
        return "ddl_agent"
    elif intent == "data":
        return "data_agent"
    elif intent == "qa":
        return "qa_agent"
    elif intent == "lineage":
        return "lineage_agent"
    elif intent == "both":
        # For "both", start with DDL first
        return "ddl_agent"
    elif intent == "search":
        return "qa_agent"  # QA agent handles search
    else:
        logger.warning(f"Unknown intent '{intent}', defaulting to ddl_agent")
        return "ddl_agent"
