"""
Application Configuration

Loads environment variables and provides configuration settings
for all services in the application.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    APP_NAME: str = "multi-agentic-solution"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Database (PostgreSQL)
    DATABASE_URL: str
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40

    # PostgreSQL settings for LangGraph checkpointer
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "agentic_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 10

    # OpenSearch
    OPENSEARCH_URL: str = "http://localhost:9200"
    OPENSEARCH_DDL_INDEX: str = "ddl_index"
    OPENSEARCH_SYNTHETIC_INDEX: str = "testdata_index"
    OPENSEARCH_SPEC_INDEX: str = "spec_document_chunks"
    OPENSEARCH_MAX_RETRIES: int = 5

    # AWS
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "us-east-1"

    # S3
    S3_BUCKET_NAME: str
    S3_INPUT_PREFIX: str = "input/"
    S3_OUTPUT_PREFIX: str = "output/"
    S3_DDL_OUTPUT_PREFIX: str = "output/ddl_generated/"
    S3_DATA_OUTPUT_PREFIX: str = "output/testdata_generated/"

    # Bedrock
    BEDROCK_MODEL_ID: str = "anthropic.claude-sonnet-4-5-v2:0"
    BEDROCK_REGION: str = "us-east-1"
    BEDROCK_STREAMING_ENABLED: bool = True
    BEDROCK_MAX_CONCURRENT_REQUESTS: int = 3
    BEDROCK_TIMEOUT: int = 60

    # Bedrock Embeddings
    BEDROCK_EMBEDDING_MODEL_ID: str = "amazon.titan-embed-text-v1"
    BEDROCK_EMBEDDING_DIMENSION: int = 1536

    # Airflow
    AIRFLOW_URL: str = "http://localhost:8080"
    AIRFLOW_ADMIN_USER: str = "admin"
    AIRFLOW_ADMIN_PASSWORD: str = "admin"

    # JWT Authentication
    JWT_SECRET_KEY: str = "change-this-secret-key-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # Agent Settings
    MAX_FEEDBACK_ITERATIONS: int = 10

    # Search Settings
    SEARCH_DEFAULT_DAYS_BACK: int = 7
    SEARCH_DEFAULT_LIMIT: int = 5

    # Feature Flags
    ENABLE_BACKGROUND_EMBEDDING: bool = True
    ENABLE_OPENSEARCH_SYNC: bool = True
    ENABLE_REDIS_CACHE: bool = True

    # Guardrails
    MAX_PROMPT_LENGTH: int = 5000
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DDL_PER_HOUR: int = 20
    RATE_LIMIT_DATA_PER_HOUR: int = 20
    RATE_LIMIT_SEARCH_PER_MINUTE: int = 20

    # Cache TTL (seconds)
    CACHE_TTL_SEARCH: int = 3600
    CACHE_TTL_METADATA: int = 86400
    CACHE_TTL_DDL: int = 604800
    CACHE_TTL_FEEDBACK: int = 3600

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Allow extra fields in .env without raising validation errors


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings: Application settings
    """
    return Settings()


settings = get_settings()
