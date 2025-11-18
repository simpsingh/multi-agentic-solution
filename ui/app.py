"""
Gradio UI Application

Provides interface for document processing and intelligent search.
"""

import gradio as gr
import os
import sys
from pathlib import Path

# Add ui directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from components.agent_interface import create_agent_interface
from components.document_processor import create_document_processor_interface
from components.ddl_generator import create_ddl_generator_interface
from components.synthetic_data_generator import create_synthetic_data_generator_interface
from components.search import create_search_interface

# Environment variables
FASTAPI_ENDPOINT = os.getenv("FASTAPI_ENDPOINT", "http://localhost:8000")


def create_app():
    """
    Create Gradio application with tabbed interface.

    Returns:
        gr.Blocks: Gradio application
    """
    with gr.Blocks(title="Datatron - Multi Agentic AI Solution") as app:
        gr.Markdown("# Datatron - Multi Agentic AI Solution")

        with gr.Tabs():
            with gr.Tab("Multi Agentic Interface"):
                create_agent_interface()

            with gr.Tab("Document Processor"):
                create_document_processor_interface()

            with gr.Tab("Generate DDL"):
                create_ddl_generator_interface()

            with gr.Tab("Generate Synthetic Data"):
                create_synthetic_data_generator_interface()

            with gr.Tab("Search"):
                create_search_interface()

    return app


if __name__ == "__main__":
    app = create_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_api=False,
    )
