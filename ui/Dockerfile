# =============================================================================
# Gradio UI Dockerfile with UV
# =============================================================================

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock README.md ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy UI code
COPY ui ./ui

# Expose Gradio port
EXPOSE 7860

# Run Gradio app
CMD ["uv", "run", "python", "ui/app.py"]
