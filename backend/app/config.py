"""Application configuration loaded from environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # LLM
    ANTHROPIC_API_KEY: str = ""

    # Databases
    POSTGRES_URL: str = "postgresql+asyncpg://dichvucong:dichvucong@localhost:5432/dichvucong"
    REDIS_URL: str = "redis://localhost:6379/0"
    QDRANT_URL: str = "http://localhost:6333"

    # Storage
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "dichvucong"

    # Embeddings
    EMBEDDING_BACKEND: str = "bge-m3"
    OPENAI_API_KEY: str = ""

    # Observability
    LANGSMITH_API_KEY: str = ""
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_PROJECT: str = "dichvucong"

    # App
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"


settings = Settings()
