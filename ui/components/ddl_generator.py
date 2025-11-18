"""
DDL Generator Component

Interface for generating DDL from parsed metadata.
"""

import gradio as gr
import httpx
import os

FASTAPI_ENDPOINT = os.getenv("FASTAPI_ENDPOINT", "http://fastapi:8000")


def create_ddl_generator_interface():
    """
    Create DDL generation interface.

    Returns:
        gr.Column: DDL generator interface components
    """
    with gr.Column():
        gr.Markdown("## Generate DDL")
        gr.Markdown("Generate Data Definition Language (DDL) statements from parsed metadata.")

        # Metadata ID input
        metadata_id = gr.Textbox(
            label="Metadata ID",
            placeholder="META_TEST_JOB_UI_014",
            lines=1,
        )

        generate_btn = gr.Button("Generate DDL", variant="primary", size="lg")

        # Output display
        ddl_output = gr.Code(
            label="Generated DDL",
            language="sql",
            lines=20,
            interactive=False,
        )

        status_output = gr.Textbox(
            label="Status",
            lines=2,
            interactive=False,
        )

        def generate_ddl(metadata_id: str):
            """Generate DDL from metadata ID"""
            if not metadata_id or not metadata_id.strip():
                return "", "Please provide a metadata ID"

            try:
                url = f"{FASTAPI_ENDPOINT}/api/v1/ddl/generate"

                with httpx.Client(timeout=60.0) as client:
                    response = client.post(
                        url,
                        json={"metadata_id": metadata_id.strip()}
                    )

                    if response.status_code == 200:
                        result = response.json()
                        ddl = result.get("ddl", "")
                        return ddl, f"✅ DDL generated successfully for {metadata_id}"
                    else:
                        return "", f"❌ Failed to generate DDL: {response.status_code} - {response.text}"

            except Exception as e:
                return "", f"❌ Error: {str(e)}"

        # Wire up event handler
        generate_btn.click(
            fn=generate_ddl,
            inputs=[metadata_id],
            outputs=[ddl_output, status_output],
        )

    return gr.Column()
