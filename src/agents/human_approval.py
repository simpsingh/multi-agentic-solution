"""
Human-in-the-loop approval node for LangGraph.

Pauses graph execution for user feedback on DDL/data generation results.
"""
from src.agents.state import AgentState
from src.agents.db_helpers import insert_document_metadata
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def human_approval_node(state: AgentState) -> AgentState:
    """
    Human approval node - pauses graph execution for user feedback.

    This node is called via interrupt_before() mechanism.
    Graph execution pauses here until app.aupdate_state() is called.

    The user can:
    - Approve (approved=True, feedback=None) → End workflow, save to DB/S3
    - Reject with feedback (approved=False, feedback="...") → Retry with feedback
    - Reject without feedback (approved=False, feedback=None) → Retry same prompt

    Args:
        state: Current agent state

    Returns:
        AgentState: State (potentially modified if approval includes DB insertion)

    Note:
        If approved=True AND doc_parse_result exists, this function will:
        1. Insert metadata into PostgreSQL
        2. Update state with metadata_id (primary key)
        3. Mark workflow as complete
    """
    iteration = state.get("iteration_count", 0)
    approved = state.get("approved", False)
    logger.info(f"Awaiting human approval (iteration: {iteration}, approved: {approved})")

    # Log what we're waiting approval for
    if state.get("ddl_result"):
        logger.info(f"Awaiting approval for DDL generation")
        logger.debug(f"DDL preview: {state['ddl_result'][:200]}...")

    if state.get("data_result"):
        logger.info(f"Awaiting approval for synthetic data generation")
        logger.debug(f"Data preview: {state['data_result'][:200]}...")

    if state.get("qa_result"):
        logger.info(f"Awaiting approval for Q&A response")
        logger.debug(f"Q&A preview: {state['qa_result'][:200]}...")

    # Log validation scores if available
    if state.get("validation_scores"):
        logger.info(f"Validation scores: {state['validation_scores']}")

    if state.get("accuracy_scores"):
        logger.info(f"Accuracy scores: {state['accuracy_scores']}")

    # CRITICAL: If approved AND doc_parse_result exists, insert into DB
    # This should happen both for initial approval and after update approval
    if approved and state.get("doc_parse_result"):
        doc_result = state["doc_parse_result"]

        # Check if we have all required fields
        if all(key in doc_result for key in ["metadata_id", "document_name", "s3_bucket", "s3_key", "metadata_json"]):
            try:
                logger.info("User approved document parse result - inserting into database")

                # Insert metadata into PostgreSQL
                db_id = await insert_document_metadata(
                    metadata_id=doc_result["metadata_id"],
                    document_name=doc_result["document_name"],
                    s3_bucket=doc_result["s3_bucket"],
                    s3_key=doc_result["s3_key"],
                    metadata_json=doc_result["metadata_json"]
                )

                # Update state with database ID
                state["metadata_id"] = db_id
                state["metadata_json"] = doc_result["metadata_json"]

                logger.info(f"✅ Metadata inserted successfully with DB ID: {db_id}")

            except Exception as e:
                logger.error(f"❌ Failed to insert metadata into database: {e}")
                # Update state with error
                state["error"] = f"Database insertion failed: {str(e)}"
        else:
            logger.warning("⚠️  Approved but missing required fields in doc_parse_result")
            state["error"] = "Missing required fields for database insertion"

    # State will be updated externally via app.aupdate_state()
    # No changes needed here - just return state as-is
    return state
