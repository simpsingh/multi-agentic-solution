"""
Agent Interface Component

Provides natural language interface for interacting with the multi-agent system.
All requests route through the supervisor agent for intent detection and routing.
"""

import gradio as gr
import httpx
import os
import json
import time
from typing import Optional, Tuple, Dict, Any
from datetime import datetime

# FastAPI endpoint for agent interaction
FASTAPI_ENDPOINT = os.getenv("FASTAPI_ENDPOINT", "http://fastapi:8000")

# Status icons - removed all icons per user request
STATUS_ICONS = {
    "completed": "",
    "processing": "",
    "awaiting_approval": "",
    "failed": "",
    "pending": "",
}


def invoke_agent(user_prompt: str, session_id: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
    """
    Invoke the agent system through the supervisor.

    Args:
        user_prompt: Natural language prompt from user
        session_id: Optional session identifier for conversation continuity

    Returns:
        Tuple of (success, response_dict)
    """
    try:
        # Generate session ID if not provided
        if not session_id:
            session_id = f"ui_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Prepare request payload
        payload = {
            "user_prompt": user_prompt,
            "session_id": session_id,
            "metadata": {
                "source": "gradio_ui",
                "timestamp": datetime.utcnow().isoformat()
            }
        }

        # Call agent API
        url = f"{FASTAPI_ENDPOINT}/api/v1/agents/invoke"

        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code in [200, 201]:
                return True, response.json()
            else:
                return False, {"error": f"API returned {response.status_code}: {response.text}"}

    except Exception as e:
        return False, {"error": str(e)}


def submit_feedback(thread_id: str, feedback: str, approved: bool) -> Tuple[bool, Dict[str, Any]]:
    """
    Submit feedback for a paused agent execution.

    Args:
        thread_id: Thread identifier from initial agent invocation
        feedback: User feedback text
        approved: Whether the result is approved

    Returns:
        Tuple of (success, response_dict)
    """
    try:
        payload = {
            "thread_id": thread_id,
            "feedback": feedback if feedback.strip() else None,
            "approved": approved
        }

        url = f"{FASTAPI_ENDPOINT}/api/v1/agents/feedback"

        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code in [200, 201]:
                return True, response.json()
            else:
                return False, {"error": f"API returned {response.status_code}: {response.text}"}

    except Exception as e:
        return False, {"error": str(e)}


def check_thread_status(thread_id: str) -> Tuple[str, Dict[str, Any]]:
    """
    Check the status of an agent thread.

    Args:
        thread_id: Thread identifier

    Returns:
        Tuple of (status_string, full_state_dict)
    """
    try:
        url = f"{FASTAPI_ENDPOINT}/api/v1/agents/status/{thread_id}"

        with httpx.Client(timeout=30.0) as client:
            response = client.get(url)

            if response.status_code == 200:
                result = response.json()
                status = result.get("status", "unknown")
                icon = STATUS_ICONS.get(status, "?")
                return f"{icon} {status.upper()}", result
            else:
                return f"✗ Error: {response.status_code}", {}

    except Exception as e:
        return f"✗ Error: {str(e)}", {}


def format_agent_result(result: Dict[str, Any], state: Dict[str, Any] = None) -> str:
    """
    Format agent result for display.

    Args:
        result: Agent result dictionary
        state: Optional full state dictionary (contains metadata_id after approval)

    Returns:
        Formatted string for display
    """
    if not result:
        return "No result available"

    # Check for different types of results
    if "doc_parse_result" in result and result["doc_parse_result"]:
        doc_result = result["doc_parse_result"]

        # Extract metadata_json to display data dictionary
        metadata_json = doc_result.get("metadata_json", {})
        tables = metadata_json.get("tables", [])

        # Check if there's an update that was applied
        updated_column = state.get("updated_column") if state else None
        update_command = state.get("update_command") if state else None

        # Build formatted output
        output = f"""Document Processing Result:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Document Information
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status: {doc_result.get('status', 'N/A')}
Job ID: {doc_result.get('job_id', 'N/A')}
Document: {doc_result.get('document_name', 'N/A')}
S3 Location: s3://{doc_result.get('s3_bucket', 'N/A')}/{doc_result.get('s3_key', 'N/A')}
Metadata ID: {doc_result.get('metadata_id', 'N/A')}
Tables: {doc_result.get('table_count', 0)}
Columns: {doc_result.get('column_count', 0)}
"""

        # If there's an updated column, show it prominently for review
        if updated_column and update_command:
            output += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  Column Update Applied - PLEASE REVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Update Applied: Column ID {update_command['column_id']}
Field Changed: {update_command['field']} = {update_command['value']}

Updated Column (All 22 Fields):
"""
            # Show all 22 fields of the updated column
            section = "unknown"
            if updated_column.get("is_header"):
                section = "header"
            elif updated_column.get("is_body"):
                section = "body"
            elif updated_column.get("is_trailer"):
                section = "trailer"

            updated_column_display = {
                "column_id": updated_column.get('column_id'),
                "column_name": updated_column.get('column_name'),
                "description": updated_column.get('description'),
                "data_type": updated_column.get('data_type'),
                "data_length": updated_column.get('data_length'),
                "precision": updated_column.get('precision'),
                "scale": updated_column.get('scale'),
                "nullable": updated_column.get('nullable'),
                "notes": updated_column.get('notes'),
                "is_header": updated_column.get('is_header'),
                "is_body": updated_column.get('is_body'),
                "is_trailer": updated_column.get('is_trailer'),
                "allowed_values": updated_column.get('allowed_values'),
                "format_hint": updated_column.get('format_hint'),
                "default_value": updated_column.get('default_value'),
                "is_system_generated": updated_column.get('is_system_generated'),
                "data_classification": updated_column.get('data_classification'),
                "foreign_key_table": updated_column.get('foreign_key_table'),
                "foreign_key_column": updated_column.get('foreign_key_column'),
                "business_rule": updated_column.get('business_rule'),
                "sample_values": updated_column.get('sample_values'),
                "section": section
            }
            output += json.dumps(updated_column_display, indent=2)
            output += """

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  IMPORTANT: Please review the updated column above.
Click 'Approve' to save to database, or 'Submit Feedback' for more changes.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            # IMPORTANT: Return here - don't show all columns when we have an update to review
            return output

        # If metadata_id from state (after DB insertion), show it prominently
        elif state and state.get("metadata_id"):
            output += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Database Record Created
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DB Record ID: {state['metadata_id']}
Status: Successfully inserted into metadata_extract table
"""

        # Display data dictionary as JSON (ALL columns)
        if tables and len(tables) > 0:
            table = tables[0]
            all_columns = table.get("columns", [])  # Get ALL columns

            output += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Data Dictionary (All {len(all_columns)} Columns) - JSON Format
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Table: {table.get('table_name', 'N/A')}
"""

            # Count header/body/trailer fields in ALL columns
            header_count = sum(1 for c in all_columns if c.get("is_header"))
            body_count = sum(1 for c in all_columns if c.get("is_body"))
            trailer_count = sum(1 for c in all_columns if c.get("is_trailer"))

            # Create JSON structure with all 22 fields for each column
            columns_json = []
            for col in all_columns:
                # Determine section based on is_header/is_body/is_trailer
                section = "unknown"
                if col.get("is_header"):
                    section = "header"
                elif col.get("is_body"):
                    section = "body"
                elif col.get("is_trailer"):
                    section = "trailer"

                column_dict = {
                    "column_id": col.get('column_id', None),
                    "column_name": col.get('column_name', None),
                    "description": col.get('description', None),
                    "data_type": col.get('data_type', None),
                    "data_length": col.get('data_length', None),
                    "precision": col.get('precision', None),
                    "scale": col.get('scale', None),
                    "nullable": col.get('nullable', None),
                    "notes": col.get('notes', None),
                    "is_header": col.get('is_header', None),
                    "is_body": col.get('is_body', None),
                    "is_trailer": col.get('is_trailer', None),
                    "allowed_values": col.get('allowed_values', None),
                    "format_hint": col.get('format_hint', None),
                    "default_value": col.get('default_value', None),
                    "is_system_generated": col.get('is_system_generated', None),
                    "data_classification": col.get('data_classification', None),
                    "foreign_key_table": col.get('foreign_key_table', None),
                    "foreign_key_column": col.get('foreign_key_column', None),
                    "business_rule": col.get('business_rule', None),
                    "sample_values": col.get('sample_values', None),
                    "section": section  # 22nd field
                }
                columns_json.append(column_dict)

            # Format JSON with proper indentation
            json_output = json.dumps({
                "table_name": table.get('table_name', 'N/A'),
                "total_columns": len(all_columns),
                "columns": columns_json
            }, indent=2)

            output += f"""
{json_output}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Column Type Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Header Fields: {header_count}
Body Fields: {body_count}
Trailer Fields: {trailer_count}
Total Columns: {len(all_columns)}
"""

        return output

    elif "ddl_result" in result and result["ddl_result"]:
        return f"""DDL Generation Result:
{result['ddl_result']}
"""
    elif "data_result" in result and result["data_result"]:
        return f"""Data Generation Result:
{result['data_result']}
"""
    else:
        # Generic result display
        return json.dumps(result, indent=2)


def format_progress_tasks(tasks: list) -> str:
    """
    Format progress tasks for display.

    Args:
        tasks: List of task dictionaries with 'task' and 'status' keys

    Returns:
        Formatted progress string
    """
    if not tasks:
        return ""

    output = "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nProcessing Progress\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

    for task in tasks:
        task_name = task.get("task", "Unknown")
        task_status = task.get("status", "pending")

        # Format task name (remove task prefix)
        display_name = task_name.replace("task1_", "1. ").replace("task2_", "2. ").replace("task3_", "3. ").replace("task4_", "4. ").replace("task5_", "5. ")
        display_name = display_name.replace("_", " ").title()

        output += f"{task_status} {display_name}\n"

    return output


def process_with_agent(user_prompt: str, session_id: str, progress=gr.Progress()):
    """
    Process user prompt through the agent system with progress tracking.

    Args:
        user_prompt: Natural language input from user
        session_id: Session identifier for conversation
        progress: Gradio progress tracker

    Yields:
        Tuple of (status, intent, result, thread_id, needs_approval)
    """
    if not user_prompt or not user_prompt.strip():
        yield "ERROR", "", "Please provide a prompt", "", False
        return

    # Removed progress bar per user request
    yield "PROCESSING", "Processing...", "Processing your request...", "", False

    # Invoke agent
    success, response = invoke_agent(user_prompt, session_id)

    if not success:
        yield "ERROR", "", f"Failed to invoke agent: {response.get('error', 'Unknown error')}", "", False
        return

    thread_id = response.get("thread_id", "")
    intent = response.get("intent", "unknown")
    status = response.get("status", "processing")

    # Show intent detection (but don't display it to user)
    # yield "PROCESSING", f"Intent detected: {intent}", f"Routing to specialized agent: {intent.replace('_', ' ').title()} Agent", "", False

    # Initial yield - no icons
    if status == "awaiting_approval":
        status_text = "AWAITING_APPROVAL"
    elif status == "completed":
        status_text = "COMPLETED"
    elif status == "processing":
        status_text = "PROCESSING"
    else:
        status_text = status.upper()

    # If awaiting approval immediately, fetch the full state first
    if status == "awaiting_approval":
        # progress(0.5, desc="")
        status_str, state_info = check_thread_status(thread_id)

        if state_info:
            current_state = state_info.get("current_state", {})

            # Show progress tasks if available
            progress_text = ""
            if current_state.get("progress_tasks"):
                progress_text = format_progress_tasks(current_state["progress_tasks"])

            # Format result based on what's available
            if current_state.get("doc_parse_result"):
                result_text = format_agent_result({"doc_parse_result": current_state["doc_parse_result"]}, current_state)
            elif current_state.get("ddl_result"):
                result_text = format_agent_result({"ddl_result": current_state["ddl_result"]}, current_state)
            elif current_state.get("data_result"):
                result_text = format_agent_result({"data_result": current_state["data_result"]}, current_state)
            else:
                result_text = "Awaiting approval..."

            # Prepend progress if available
            if progress_text:
                result_text = progress_text + "\n" + result_text
        else:
            result_text = "Awaiting approval..."

        # progress(1.0, desc="")
        yield status_text, f"Intent: {intent}", result_text, thread_id, True
        return

    # For other statuses, use response result if available
    if "result" in response and response["result"]:
        result_text = format_agent_result(response["result"])
    else:
        result_text = "Processing your request..."

    needs_approval = False
    yield status_text, f"Intent: {intent}", result_text, thread_id, needs_approval

    # Poll for completion if still processing
    if status == "processing":
        max_polls = 30  # 30 polls = ~1 minute
        poll_count = 0

        while poll_count < max_polls:
            time.sleep(2)
            # progress(0.1, desc="Processing...")

            # Check status
            status_str, state_info = check_thread_status(thread_id)

            if state_info:
                current_status = state_info.get("status", "processing")
                current_state = state_info.get("current_state", {})

                # Show progress tasks if available
                progress_text = ""
                if current_state.get("progress_tasks"):
                    progress_text = format_progress_tasks(current_state["progress_tasks"])

                if current_status in ["completed", "failed", "awaiting_approval"]:
                    # Final state reached
                    if current_state.get("doc_parse_result"):
                        result_text = format_agent_result({"doc_parse_result": current_state["doc_parse_result"]}, current_state)
                    elif current_state.get("ddl_result"):
                        result_text = format_agent_result({"ddl_result": current_state["ddl_result"]}, current_state)
                    elif current_state.get("data_result"):
                        result_text = format_agent_result({"data_result": current_state["data_result"]}, current_state)
                    else:
                        result_text = json.dumps(current_state, indent=2)

                    # Prepend progress if available
                    if progress_text:
                        result_text = progress_text + "\n" + result_text

                    needs_approval = current_status == "awaiting_approval"
                    yield status_str, f"Intent: {intent}", result_text, thread_id, needs_approval
                    return
                else:
                    # Still processing - show progress update
                    if progress_text:
                        result_text = progress_text + "\n\nProcessing continues..."
                        yield status_str, f"Intent: {intent}", result_text, thread_id, False

            poll_count += 1

        # Timeout
        yield "TIMEOUT", f"Intent: {intent}", "Request is still processing. Use thread ID to check status.", thread_id, False


def handle_feedback(thread_id: str, feedback_text: str, approved: bool, progress=gr.Progress()):
    """
    Handle user feedback for an agent result.

    Args:
        thread_id: Thread identifier
        feedback_text: User feedback
        approved: Whether approved
        progress: Gradio progress tracker

    Yields:
        Tuple of (status, result_text)
    """
    if not thread_id:
        yield "ERROR", "No thread ID provided"
        return

    # progress(0.1, desc="Submitting feedback...")

    # Submit feedback
    success, response = submit_feedback(thread_id, feedback_text, approved)

    if not success:
        yield "ERROR", f"Failed to submit feedback: {response.get('error', 'Unknown error')}"
        return

    status = response.get("status", "processing")

    if approved:
        # Check if we have state info with metadata_id
        current_state = response.get("current_state", {})

        # Set status to COMPLETED for approved items
        status_text = "COMPLETED"

        # Try to find metadata_id in different locations (based on API response structure)
        metadata_id = None

        # Check in current_state.doc_parse_result.metadata_id (confirmed location from debug)
        if current_state.get("doc_parse_result", {}).get("metadata_id"):
            metadata_id = current_state["doc_parse_result"]["metadata_id"]
        # Check in result.metadata_id (another confirmed location)
        elif response.get("result", {}).get("metadata_id"):
            metadata_id = response["result"]["metadata_id"]
        # Check other possible locations
        elif current_state.get("metadata_id"):
            metadata_id = current_state["metadata_id"]
        elif response.get("result", {}).get("doc_parse_result", {}).get("metadata_id"):
            metadata_id = response["result"]["doc_parse_result"]["metadata_id"]

        if metadata_id:
            result_text = f"""Result approved and saved to database!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Database Record Created Successfully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Metadata ID: {metadata_id}
Table: metadata_extract
Status: Successfully inserted with all updates applied

You can verify in PostgreSQL:
SELECT * FROM metadata_extract WHERE metadata_id = '{metadata_id}';
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            result_text = "Result approved and saved!"

        yield status_text, result_text
    else:
        # Check if an update was applied
        current_state = response.get("current_state", {})

        # Continue processing with feedback
        status_text = status.upper()

        # If update was applied, format the updated result
        if current_state.get("update_applied"):
            # Show ONLY the updated column for review
            updated_column = current_state.get("updated_column")
            update_command = current_state.get("update_command")

            if updated_column and update_command:
                # Build the output showing ONLY the updated column
                result_text = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  Column Update Applied - PLEASE REVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Update Applied: Column ID {update_command['column_id']}
Field Changed: {update_command['field']} = {update_command['value']}

Updated Column (All 22 Fields):
"""
                # Show all 22 fields of the updated column
                section = "unknown"
                if updated_column.get("is_header"):
                    section = "header"
                elif updated_column.get("is_body"):
                    section = "body"
                elif updated_column.get("is_trailer"):
                    section = "trailer"

                updated_column_display = {
                    "column_id": updated_column.get('column_id'),
                    "column_name": updated_column.get('column_name'),
                    "description": updated_column.get('description'),
                    "data_type": updated_column.get('data_type'),
                    "data_length": updated_column.get('data_length'),
                    "precision": updated_column.get('precision'),
                    "scale": updated_column.get('scale'),
                    "nullable": updated_column.get('nullable'),
                    "notes": updated_column.get('notes'),
                    "is_header": updated_column.get('is_header'),
                    "is_body": updated_column.get('is_body'),
                    "is_trailer": updated_column.get('is_trailer'),
                    "allowed_values": updated_column.get('allowed_values'),
                    "format_hint": updated_column.get('format_hint'),
                    "default_value": updated_column.get('default_value'),
                    "is_system_generated": updated_column.get('is_system_generated'),
                    "data_classification": updated_column.get('data_classification'),
                    "foreign_key_table": updated_column.get('foreign_key_table'),
                    "foreign_key_column": updated_column.get('foreign_key_column'),
                    "business_rule": updated_column.get('business_rule'),
                    "sample_values": updated_column.get('sample_values'),
                    "section": section
                }
                result_text += json.dumps(updated_column_display, indent=2)
                result_text += """

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  IMPORTANT: Please review the updated column above.
Click 'Approve' to save to database, or 'Submit Feedback' for more changes.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                status_text = "AWAITING_APPROVAL"
            else:
                result_text = "Update applied. Please review and approve."
                status_text = "AWAITING_APPROVAL"
        else:
            # Don't show full result if we're processing an update
            # Just show processing message
            result_text = "Processing your feedback..."

        yield status_text, result_text

        # Poll for completion if still processing
        if status == "processing":
            max_polls = 30
            poll_count = 0

            while poll_count < max_polls:
                time.sleep(2)
                # progress(0.5, desc="Reprocessing...")

                status_str, state_info = check_thread_status(thread_id)

                if state_info:
                    current_status = state_info.get("status", "processing")
                    current_state = state_info.get("current_state", {})

                    # Show progress tasks if available
                    progress_text = ""
                    if current_state.get("progress_tasks"):
                        progress_text = format_progress_tasks(current_state["progress_tasks"])

                    if current_status in ["completed", "failed", "awaiting_approval"]:
                        if current_state.get("doc_parse_result"):
                            result_text = format_agent_result({"doc_parse_result": current_state["doc_parse_result"]}, current_state)
                        elif current_state.get("ddl_result"):
                            result_text = format_agent_result({"ddl_result": current_state["ddl_result"]}, current_state)
                        elif current_state.get("data_result"):
                            result_text = format_agent_result({"data_result": current_state["data_result"]}, current_state)
                        else:
                            result_text = json.dumps(current_state, indent=2)

                        # Prepend progress if available
                        if progress_text:
                            result_text = progress_text + "\n" + result_text

                        yield status_str, result_text
                        return

                poll_count += 1

            yield "TIMEOUT", "Reprocessing is taking longer than expected. Check status later."


def create_agent_interface():
    """
    Create the agent interface component.

    Returns:
        gr.Column: Agent interface components
    """
    with gr.Column():
        # Session management
        session_id = gr.Textbox(
            label="Session ID",
            value=f"ui_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            interactive=False
        )

        # User input
        user_prompt = gr.Textbox(
            label="Your Request",
            placeholder="e.g., Parse document Fintrac_Swift_Source_Extract_Specification_v4_plus_appendix.docx from S3 bucket ses-v1",
            lines=3
        )

        process_btn = gr.Button("Go", variant="primary", size="lg")

        # Status and results
        with gr.Row():
            status_output = gr.Textbox(
                label="Status",
                lines=1,
                interactive=False
            )
            intent_output = gr.Textbox(
                label="Detected Intent",
                lines=1,
                interactive=False
            )

        result_output = gr.Textbox(
            label="Result",
            lines=10,
            interactive=False
        )

        thread_id = gr.Textbox(
            label="Thread ID",
            interactive=False,
            visible=False
        )

        # Human approval section
        with gr.Group(visible=False) as approval_section:
            gr.Markdown("### Human Approval Required")

            feedback_text = gr.Textbox(
                label="Feedback (optional)",
                placeholder="Provide feedback if you want changes...",
                lines=3
            )

            with gr.Row():
                approve_btn = gr.Button("Approve", variant="primary")
                reject_btn = gr.Button("Submit Feedback", variant="secondary")

        # Feedback results
        feedback_status = gr.Textbox(
            label="Feedback Status",
            lines=1,
            interactive=False,
            visible=False
        )

        feedback_result = gr.Textbox(
            label="Updated Result",
            lines=10,
            interactive=False,
            visible=False
        )

        # Wire up event handlers
        def on_process(prompt, sid):
            """Process user prompt and handle approval state."""
            generator = process_with_agent(prompt, sid)
            for status, intent, result, tid, needs_approval in generator:
                # Update approval section visibility
                approval_visible = needs_approval
                thread_visible = bool(tid)

                yield {
                    status_output: status,
                    intent_output: intent,
                    result_output: result,
                    thread_id: tid,
                    approval_section: gr.update(visible=approval_visible),
                    thread_id: gr.update(value=tid, visible=thread_visible),
                    feedback_status: gr.update(visible=False),
                    feedback_result: gr.update(visible=False)
                }

        def on_approve(tid):
            """Handle approval."""
            generator = handle_feedback(tid, "", True)
            for status, result in generator:
                yield {
                    status_output: status,  # Update main status to COMPLETED
                    feedback_status: gr.update(value=status, visible=True),
                    feedback_result: gr.update(value=result, visible=True),
                    approval_section: gr.update(visible=False)
                }

        def on_reject(tid, feedback):
            """Handle rejection with feedback."""
            generator = handle_feedback(tid, feedback, False)
            for status, result in generator:
                # Check if status indicates we're awaiting approval (update was applied)
                needs_approval = status == "AWAITING_APPROVAL"

                yield {
                    status_output: status,  # Update main status
                    feedback_status: gr.update(value=status, visible=True),
                    feedback_result: gr.update(value=result, visible=True),
                    # DON'T update result_output - keep original result unchanged
                    approval_section: gr.update(visible=needs_approval)  # Keep visible if update needs approval
                }

        process_btn.click(
            fn=on_process,
            inputs=[user_prompt, session_id],
            outputs=[
                status_output, intent_output, result_output,
                thread_id, approval_section, thread_id,
                feedback_status, feedback_result
            ]
        )

        approve_btn.click(
            fn=on_approve,
            inputs=[thread_id],
            outputs=[status_output, feedback_status, feedback_result, approval_section]
        )

        reject_btn.click(
            fn=on_reject,
            inputs=[thread_id, feedback_text],
            outputs=[status_output, feedback_status, feedback_result, approval_section]
        )

    return gr.Column()