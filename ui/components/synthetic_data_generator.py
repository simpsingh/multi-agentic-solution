"""
Synthetic Data Generator Component

Interface for generating synthetic test data.
"""

import gradio as gr
import httpx
import os
import json

FASTAPI_ENDPOINT = os.getenv("FASTAPI_ENDPOINT", "http://fastapi:8000")


def create_synthetic_data_generator_interface():
    """
    Create synthetic data generation interface.

    Returns:
        gr.Column: Synthetic data generator interface components
    """
    with gr.Column():
        gr.Markdown("## Generate Synthetic Data")
        gr.Markdown("Generate realistic synthetic test data based on metadata specifications.")

        # Metadata ID input
        metadata_id = gr.Textbox(
            label="Metadata ID",
            placeholder="META_TEST_JOB_UI_014",
            lines=1,
        )

        # Number of rows
        num_rows = gr.Slider(
            label="Number of Rows",
            minimum=1,
            maximum=1000,
            value=10,
            step=1,
        )

        generate_btn = gr.Button("Generate Synthetic Data", variant="primary", size="lg")

        # Output display
        data_output = gr.Code(
            label="Generated Data (JSON)",
            language="json",
            lines=20,
            interactive=False,
        )

        status_output = gr.Textbox(
            label="Status",
            lines=2,
            interactive=False,
        )

        def generate_synthetic_data(metadata_id: str, num_rows: int):
            """Generate synthetic data from metadata ID"""
            if not metadata_id or not metadata_id.strip():
                return "", "Please provide a metadata ID"

            try:
                url = f"{FASTAPI_ENDPOINT}/api/v1/synthetic/generate"

                with httpx.Client(timeout=120.0) as client:
                    response = client.post(
                        url,
                        json={
                            "metadata_id": metadata_id.strip(),
                            "num_rows": int(num_rows)
                        }
                    )

                    if response.status_code == 200:
                        result = response.json()
                        data = result.get("data", [])
                        formatted_data = json.dumps(data, indent=2)
                        return formatted_data, f"✅ Generated {len(data)} rows of synthetic data for {metadata_id}"
                    else:
                        return "", f"❌ Failed to generate data: {response.status_code} - {response.text}"

            except Exception as e:
                return "", f"❌ Error: {str(e)}"

        # Wire up event handler
        generate_btn.click(
            fn=generate_synthetic_data,
            inputs=[metadata_id, num_rows],
            outputs=[data_output, status_output],
        )

    return gr.Column()
