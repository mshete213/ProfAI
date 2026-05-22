from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # Database
    database_url: str = "postgresql+psycopg2://edtech:edtech_dev@localhost:5432/edtech"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"

    # Anthropic
    anthropic_api_key: str = "your-anthropic-api-key"
    anthropic_model: str = "claude-sonnet-4-6"

    # OpenAI (embeddings)
    openai_api_key: str = "your-openai-api-key"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # Pinecone
    pinecone_api_key: str = "your-pinecone-api-key"
    pinecone_index_name: str = "edtech-prod"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"

    # JWT auth
    jwt_secret: str = "change-me-in-production-please"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # URLs
    backend_public_url: str = "http://localhost:8000"
    frontend_public_url: str = "http://localhost:3000"

    # RAG tuning
    rag_top_k: int = 8
    rag_score_threshold: float = 0.72
    history_token_budget: int = 4000

    # Credential encryption (Fernet key, base64-encoded 32 bytes)
    credentials_encryption_key: str = "your-fernet-key-here"

    # Canvas webhook receiver public URL
    canvas_webhook_public_url: str = "https://your-public-domain.com/webhooks/canvas"

    # Uploads
    upload_dir: str = "/app/uploads"
    watch_dir: str = "/watched"


@lru_cache
def get_settings() -> Settings:
    return Settings()
