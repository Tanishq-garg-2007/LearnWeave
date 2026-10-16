import os
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Groq Settings
    GROQ_API_KEY: str = ""
    GROQ_PRIMARY_MODEL: str = "qwen/qwen3.8-27b"
    GROQ_FALLBACK_MODEL: str = "openai/gpt-oss-20b"
    GROQ_STT_MODEL: str = "whisper-large-v3-turbo"
    GROQ_REASONING_MODE: str = "hidden"
    GROQ_TIMEOUT_SECONDS: int = 60
    GROQ_MAX_RETRIES: int = 3
    GROQ_MAX_COMBINED_TOKENS: int = 6000

    # PostgreSQL Database
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "learnweave"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/learnweave"
    SYNC_DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/learnweave"

    # Security & Auth
    JWT_SECRET: str = "learnweave-super-secret-key-change-in-production-12345"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Local Embeddings & TTS
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    KOKORO_MODEL_PATH: str = "models/kokoro-v1.0.onnx"
    KOKORO_VOICES_PATH: str = "models/voices.bin"

    # Integrations
    ENABLE_MEM0: bool = False

    # App Settings
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:5173,http://127.0.0.1:5173"

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v


settings = Settings()
