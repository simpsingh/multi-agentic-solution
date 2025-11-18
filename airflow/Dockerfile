# =============================================================================
# Apache Airflow Dockerfile with UV
# =============================================================================

FROM apache/airflow:2.9.3-python3.11

# Install UV
USER root
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /opt/airflow

# Copy only source code (no full project install to avoid dependency conflicts)
COPY src ./src

# Install only packages NOT already in Airflow base image
# Airflow 2.9 already has: boto3, sqlalchemy, pydantic, python-dotenv
RUN uv pip install --system --no-cache \
    python-docx>=1.1.0 \
    aioboto3>=15.4.0 \
    structlog>=24.1.0 \
    pydantic-settings>=2.1.0 \
    asyncpg>=0.29.0

# Add system site-packages to PYTHONPATH so airflow user can access them
ENV PYTHONPATH="/opt/airflow/src:/usr/local/lib/python3.11/site-packages:${PYTHONPATH}"

# Switch to airflow user for runtime
USER airflow

# Copy DAGs and plugins
COPY airflow/dags ./dags
COPY airflow/plugins ./plugins

# Copy entrypoint script
COPY airflow/scripts/entrypoint.sh /opt/airflow/scripts/entrypoint.sh

# Switch to root to set permissions, then back to airflow
USER root
RUN chmod +x /opt/airflow/scripts/entrypoint.sh && \
    apt-get update && \
    apt-get install -y postgresql-client && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
USER airflow

# Set entrypoint
ENTRYPOINT ["/opt/airflow/scripts/entrypoint.sh"]

# Default command (can be overridden in docker-compose)
CMD ["airflow", "webserver"]
