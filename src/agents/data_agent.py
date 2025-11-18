"""
Synthetic Data Generation Agent

Generates synthetic test data in HDR/BDY/TLR format.
"""

from src.agents.state import AgentState
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def data_agent_node(state: AgentState) -> AgentState:
    """
    Data agent node that generates synthetic test data.

    Args:
        state: Current agent state

    Returns:
        AgentState: Updated state with data result
    """
    metadata_id = state.get("metadata_id")
    metadata_json = state.get("metadata_json")

    logger.info(f"Data agent generating synthetic data for metadata_id: {metadata_id}")

    # TODO: Implement synthetic data generation logic
    # 1. Fetch metadata if not in state
    # 2. Generate data using LLM in HDR/BDY/TLR format
    # 3. Validate data format and constraints
    # 4. Update state with results and validation scores

    state["data_result"] = "HDR|...\nBDY|...\nTLR|..."
    state["validation_scores"] = {}
    state["awaiting_human_approval"] = True

    return state
