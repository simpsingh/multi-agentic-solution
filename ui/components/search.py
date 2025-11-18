"""
Search Interface Component

Chat-based interface with hybrid search (BM25 + Vector Embeddings + Re-ranking).
"""

import gradio as gr
import httpx
import os
from typing import List, Tuple

FASTAPI_ENDPOINT = os.getenv("FASTAPI_ENDPOINT", "http://localhost:8000")


def search_documents(query: str, metadata_id: str = None, top_k: int = 5) -> str:
    """
    Perform hybrid search using BM25 + vector embeddings.

    Args:
        query: Search query
        metadata_id: Optional metadata ID filter
        top_k: Number of results to return

    Returns:
        Formatted search results
    """
    try:
        # Build search request
        params = {
            "query": query,
            "top_k": top_k,
        }

        if metadata_id and metadata_id.strip():
            params["metadata_id"] = metadata_id.strip()

        # Call FastAPI search endpoint
        url = f"{FASTAPI_ENDPOINT}/api/v1/search/hybrid"

        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params)

            if response.status_code == 200:
                results = response.json()
                return format_search_results(results)
            else:
                return f"❌ Search failed: {response.status_code} - {response.text}"

    except Exception as e:
        return f"❌ Search error: {str(e)}"


def format_search_results(results: dict) -> str:
    """
    Format search results for display.

    Args:
        results: Search results from API

    Returns:
        Formatted string
    """
    if not results or "results" not in results:
        return "No results found."

    search_results = results["results"]
    total = results.get("total_results", 0)
    search_time = results.get("search_time_ms", 0)

    output = f"**Found {total} results** (search time: {search_time}ms)\n\n"
    output += "---\n\n"

    for idx, result in enumerate(search_results, 1):
        score = result.get("score", 0.0)
        content = result.get("content", "")
        metadata_id = result.get("metadata_id", "unknown")
        chunk_id = result.get("chunk_id", "")

        output += f"### Result {idx} (Score: {score:.4f})\n\n"
        output += f"**Source:** {metadata_id}\n\n"
        output += f"{content}\n\n"
        output += "---\n\n"

    return output


def chat_with_search(message: str, history: List[Tuple[str, str]]) -> str:
    """
    Chat interface with search functionality.

    Args:
        message: User message
        history: Chat history

    Returns:
        Assistant response
    """
    # Perform search
    response = search_documents(message, top_k=5)

    return response


def create_search_interface():
    """
    Create chat-based search interface.

    Returns:
        gr.Column: Search interface components
    """
    with gr.Column():
        # Settings
        with gr.Accordion("Settings", open=False):
            metadata_filter = gr.Textbox(
                label="Filter by Metadata ID (optional)",
                placeholder="Leave empty to search all documents",
            )
            top_k_slider = gr.Slider(
                minimum=1,
                maximum=20,
                value=5,
                step=1,
                label="Number of Results",
            )

        # Chat interface
        chatbot = gr.Chatbot(
            label="Search Results",
            height=500,
            type="messages",
        )

        msg = gr.Textbox(
            label="Ask a question or search",
            placeholder="Type your question here...",
            lines=2,
        )

        with gr.Row():
            submit_btn = gr.Button("🔍 Search", variant="primary")
            clear_btn = gr.Button("Clear", variant="secondary")

        # Event handlers
        def respond(message, chat_history):
            # Perform search
            response = search_documents(message, top_k=5)

            # Add to chat history
            chat_history.append({"role": "user", "content": message})
            chat_history.append({"role": "assistant", "content": response})

            return "", chat_history

        submit_btn.click(
            fn=respond,
            inputs=[msg, chatbot],
            outputs=[msg, chatbot],
        )

        msg.submit(
            fn=respond,
            inputs=[msg, chatbot],
            outputs=[msg, chatbot],
        )

        clear_btn.click(
            fn=lambda: ([], ""),
            outputs=[chatbot, msg],
        )

    return gr.Column()
