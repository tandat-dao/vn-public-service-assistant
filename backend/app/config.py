"""Application configuration loaded from environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=["../.env", ".env"],   # project root first, then backend/
        case_sensitive=False,
    )

    # LLM
    ANTHROPIC_API_KEY: str = ""
    LLM_MODEL: str = "claude-haiku-4-5-20251001"
    LLM_BACKEND: str = "anthropic"  # "anthropic" | "gemini"
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"
    CLAUDE_MODEL: str = ""  # reserved for future Claude-direct integration

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
    SENTENCE_TRANSFORMERS_HOME: str = ".cache/"

    # Qdrant / RAG
    QDRANT_COLLECTION: str = "legal_documents"
    QDRANT_VECTOR_SIZE: int = 1024
    RAG_TOP_K: int = 24
    RAG_TOKEN_BUDGET: int = 6000
    RAG_MIN_SCORE_THRESHOLD: float = 0.01  # RRF scores with k=60 top out at ~0.033; 0.3 was unreachable

    # Observability
    LANGSMITH_API_KEY: str = ""
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_PROJECT: str = "dichvucong"

    # Security
    CORS_ALLOW_ORIGINS: str = "http://localhost:3000"
    CORS_EXTRA_ORIGINS: str = ""  # comma-separated; append Ngrok URLs here without code changes
    REDIS_PASSWORD: str = ""
    CHAT_RATE_LIMIT: str = "10/minute"
    UPLOAD_RATE_LIMIT: str = "5/minute"
    REDIS_ENCRYPTION_KEY: str = ""  # 32-byte base64 Fernet key; raise RuntimeError if empty
    MINIO_SECURE: bool = False

    # OCR
    PADDLEOCR_USE_GPU: bool = False
    PADDLEOCR_LANG: str = "vi"
    OCR_QR_MAX_ATTEMPTS: int = 5
    OCR_CONFIDENCE_THRESHOLD: float = 0.7
    OCR_MIN_TEXT_LENGTH: int = 2
    OCR_RAW_TOKEN_CAP: int = 8000
    OCR_CLAHE_CLIP_LIMIT: float = 2.0
    OCR_DESKEW_MAX_DEGREES: float = 15.0
    OCR_DENOISE_H: int = 10
    CCCD_PROVINCE_CODE_MAX: int = 96

    # App
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"


settings = Settings()
