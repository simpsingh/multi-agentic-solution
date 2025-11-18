"""
Chat Interface Component

Provides chat interface for DDL/Data generation with streaming and approval workflow.
"""

import gradio as gr
import httpx
import os

FASTAPI_ENDPOINT = os.getenv("FASTAPI_ENDPOINT", "http://localhost:8000")


def create_chat_interface(mode: str):
    """
    Create chat interface for specific mode.

    Args:
        mode: "ddl", "data", or "qa"

    Returns:
        gr.Column: Chat interface components
    """
    with gr.Column():
        gr.Markdown(f"### {mode.upper()} Generation")

        # Input fields
        metadata_id = gr.Textbox(
            label="Metadata ID",
            placeholder="Enter metadata ID",
            visible=(mode in ["ddl", "data"]),
        )

        if mode == "data":
            ddl_id = gr.Number(
                label="DDL ID (optional)",
                precision=0,
                visible=True,
            )
            num_rows = gr.Slider(
                minimum=1,
                maximum=100,
                value=10,
                step=1,
                label="Number of Rows",
            )

        user_prompt = gr.Textbox(
            label="Prompt",
            placeholder=f"Enter your {mode} generation request...",
            lines=3,
        )

        # Generate button
        generate_btn = gr.Button(f"Generate {mode.upper()}", variant="primary")

        # Output area
        output = gr.Textbox(
            label="Generated Output",
            lines=20,
            max_lines=30,
            interactive=False,
        )

        # Validation scores
        validation_output = gr.JSON(label="Validation Scores")

        # Approval buttons
        with gr.Row():
            approve_btn = gr.Button("Approve", variant="primary")
            reject_btn = gr.Button("Reject", variant="secondary")

        feedback_input = gr.Textbox(
            label="Feedback (if rejecting)",
            placeholder="Provide feedback for improvements...",
            lines=2,
            visible=False,
        )

        # Status messages
        status = gr.Textbox(label="Status", interactive=False)

        # TODO: Wire up event handlers
        def generate_placeholder(*args):
            return "TODO: Implement generation", {}, "Ready to approve/reject"

        def approve_placeholder():
            return "Approved! Saved to database and S3."

        def reject_placeholder():
            return True  # Show feedback input

        generate_btn.click(
            fn=generate_placeholder,
            inputs=[metadata_id, user_prompt] if mode != "data" else [metadata_id, user_prompt, num_rows],
            outputs=[output, validation_output, status],
        )

        approve_btn.click(
            fn=approve_placeholder,
            outputs=[status],
        )

        reject_btn.click(
            fn=reject_placeholder,
            outputs=[feedback_input],
        )

    return gr.Column()
