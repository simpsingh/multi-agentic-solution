"""
Document Parser Agent

Triggers Airflow DAG, polls for completion, retrieves results from XCom.
Shows progress to user, presents data dictionary for approval BEFORE DB insertion.
"""

import httpx
import time
import json
from typing import Dict, Any
from src.agents.state import AgentState
from src.utils.logger import get_logger
from src.config import settings

logger = get_logger(__name__)

AIRFLOW_URL = settings.AIRFLOW_URL
AIRFLOW_USER = settings.AIRFLOW_ADMIN_USER
AIRFLOW_PASSWORD = settings.AIRFLOW_ADMIN_PASSWORD


async def doc_parser_agent_node(state: AgentState) -> AgentState:
    """
    Document parser agent: Triggers Airflow, polls for completion, retrieves data dictionary.

    Flow:
    1. Extract doc info from prompt
    2. Trigger Airflow DAG
    3. Poll task states with progress tracking
    4. Retrieve metadata_json from XCom
    5. Return for human approval (NO DB insertion yet)
    """
    user_prompt = state.get("user_prompt", "")
    iteration = state.get("iteration_count", 0)
    feedback = state.get("feedback")

    logger.info(f"Document Parser Agent activated (iteration {iteration})")

    # Extract document info
    doc_info = _extract_document_info(user_prompt)

    if not doc_info.get("document_name"):
        state["doc_parse_result"] = {"error": "No document specified"}
        state["awaiting_human_approval"] = True
        return state

    try:
        # Prepare DAG config
        dag_config = _prepare_dag_config(doc_info)
        job_id = dag_config["job_id"]

        logger.info(f"Triggering Airflow DAG: {job_id}")

        # Trigger DAG
        run_id = await _trigger_airflow_dag(dag_config)

        if not run_id:
            raise Exception("Failed to trigger Airflow DAG")

        logger.info(f"Airflow DAG triggered: {run_id}")

        # Poll for completion with progress tracking
        task_states, final_status = await _poll_dag_completion(run_id, dag_config)

        # Update progress in state
        state["progress_tasks"] = task_states

        if final_status != "success":
            raise Exception(f"Airflow DAG failed with status: {final_status}")

        # Retrieve metadata from XCom
        metadata_result = await _retrieve_xcom_data(run_id, "task5_parse_document", "document_parse")

        if not metadata_result:
            raise Exception("Failed to retrieve metadata from Airflow XCom")

        logger.info(f"Retrieved metadata: {metadata_result.get('table_count')} tables, {metadata_result.get('column_count')} columns")

        # Store in state for human approval
        state["doc_parse_result"] = metadata_result
        state["awaiting_human_approval"] = True
        state["iteration_count"] = iteration + 1

        return state

    except Exception as e:
        logger.error(f"Document parser error: {e}")
        state["doc_parse_result"] = {"error": str(e), "status": "failed"}
        state["awaiting_human_approval"] = True
        return state


def _extract_document_info(prompt: str) -> Dict[str, Any]:
    """Extract document name and S3 info from prompt."""
    prompt_lower = prompt.lower()

    doc_info = {
        "document_name": None,
        "s3_bucket": "ses-v1",
        "command": "parse_document"
    }

    # Extract document name
    if "fintrac" in prompt_lower:
        doc_info["document_name"] = "Fintrac_Swift_Source_Extract_Specification_v4_plus_appendix.docx"
        doc_info["s3_key"] = "input/Fintrac_Swift_Source_Extract_Specification_v4_plus_appendix.docx"

    # Extract bucket if specified
    if "bucket" in prompt_lower:
        import re
        bucket_match = re.search(r'bucket\s+(\S+)', prompt_lower)
        if bucket_match:
            doc_info["s3_bucket"] = bucket_match.group(1)

    return doc_info


def _prepare_dag_config(doc_info: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare Airflow DAG configuration."""
    import uuid
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_id = f"DOC_PARSE_{timestamp}_{uuid.uuid4().hex[:6].upper()}"

    return {
        "job_id": job_id,
        "document_name": doc_info["document_name"],
        "s3_bucket": doc_info["s3_bucket"],
        "s3_key": doc_info["s3_key"],
        "command": doc_info["command"]
    }


async def _trigger_airflow_dag(dag_config: Dict[str, Any]) -> str:
    """Trigger Airflow DAG and return run_id."""
    url = f"{AIRFLOW_URL}/api/v1/dags/doc_processor/dagRuns"

    payload = {"conf": dag_config}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            json=payload,
            auth=(AIRFLOW_USER, AIRFLOW_PASSWORD)
        )

        if response.status_code in [200, 201]:
            data = response.json()
            return data.get("dag_run_id")
        else:
            logger.error(f"Airflow trigger failed: {response.status_code} - {response.text}")
            return None


async def _poll_dag_completion(run_id: str, dag_config: Dict[str, Any], max_polls: int = 120, poll_interval: int = 3) -> tuple:
    """
    Poll Airflow DAG until completion, track task progress.

    Returns:
        (task_states, final_status)
    """
    task_names = [
        "task1_verify_endpoints",
        "task2_verify_s3_access",
        "task3_verify_containers",
        "task4_fetch_document",
        "task5_parse_document"
    ]

    task_states = [{"task": name, "status": "pending"} for name in task_names]

    for poll_count in range(max_polls):
        await asyncio.sleep(poll_interval)

        # Get task states
        url = f"{AIRFLOW_URL}/api/v1/dags/doc_processor/dagRuns/{run_id}/taskInstances"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, auth=(AIRFLOW_USER, AIRFLOW_PASSWORD))

            if response.status_code == 200:
                task_instances = response.json().get("task_instances", [])

                # Update task states
                for i, task_name in enumerate(task_names):
                    task_instance = next((t for t in task_instances if t["task_id"] == task_name), None)
                    if task_instance:
                        task_state = task_instance.get("state", "pending")
                        if task_state == "success":
                            task_states[i]["status"] = "✓ completed"
                        elif task_state == "failed":
                            task_states[i]["status"] = "✗ failed"
                            return task_states, "failed"
                        elif task_state in ["running", "queued"]:
                            task_states[i]["status"] = "⟳ running"

                # Check if all tasks completed
                all_done = all(t["status"] == "✓ completed" for t in task_states)
                if all_done:
                    return task_states, "success"

    return task_states, "timeout"


async def _retrieve_xcom_data(run_id: str, task_id: str, xcom_key: str) -> Dict[str, Any]:
    """Retrieve data from Airflow XCom."""
    import asyncio
    import ast

    url = f"{AIRFLOW_URL}/api/v1/dags/doc_processor/dagRuns/{run_id}/taskInstances/{task_id}/xcomEntries/{xcom_key}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, auth=(AIRFLOW_USER, AIRFLOW_PASSWORD))

        if response.status_code == 200:
            data = response.json()
            value = data.get("value", {})

            # XCom may return value as string, need to parse it
            if isinstance(value, str):
                try:
                    value = ast.literal_eval(value)
                except (ValueError, SyntaxError) as e:
                    logger.error(f"Failed to parse XCom value as dict: {e}")
                    return None

            return value
        else:
            logger.error(f"XCom retrieval failed: {response.status_code}")
            return None


# Import asyncio at module level
import asyncio
