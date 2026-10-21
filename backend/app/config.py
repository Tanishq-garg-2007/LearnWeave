import logging
import os
import secrets
from typing import List, Union
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("learnweave.config")

# Values that must never be used to sign tokens or connect to a shared database.
KNOWN_INSECURE_JWT_SECRETS = {
    "",
    "learnweave-super-secret-key-change-in-production-12345",
}
MIN_JWT_SECRET_LENGTH = 32
INSECURE_DB_CREDENTIAL_MARKER = "postgres:postgres@"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Groq Settings
    GROQ_API_KEY: str = ""
    GROQ_PRIMARY_MODEL: str = "qwen/qwen3.8-27b"
    GROQ_FALLBACK_MODEL: str = "openai/gpt-oss-120b"
    GROQ_STT_MODEL: str = "whisper-large-v3-turbo"
    GROQ_REASONING_MODE: str = "hidden"
    GROQ_TIMEOUT_SECONDS: int = 60
    GROQ_MAX_RETRIES: int = 3
    GROQ_MAX_COMBINED_TOKENS: int = 6000
    GROQ_MAX_RPM: int = 28
    GROQ_MAX_TPM: int = 8000
    GROQ_TOTAL_DEADLINE_SECONDS: int = 90

    # PostgreSQL Database (local-development defaults only; non-development
    # environments refuse to start with the default credentials, see _check_security)
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "learnweave"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/learnweave"
    SYNC_DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/learnweave"

    # Security & Auth
    # No default secret: outside APP_ENV=development the app refuses to start without a
    # random value of at least 32 characters. In development a random per-process secret
    # is generated when this is unset (tokens then do not survive a restart).
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Local Embeddings & TTS
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    KOKORO_MODEL_PATH: str = "models/kokoro-v1.0.onnx"
    KOKORO_VOICES_PATH: str = "models/voices.bin"

    # Integrations
    ENABLE_MEM0: bool = False

    # Rate limiting (per process)
    RATE_LIMIT_ENABLED: bool = True
    USER_DAILY_LLM_CALLS: int = 300

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

    @model_validator(mode="after")
    def _check_security(self) -> "Settings":
        is_dev = self.APP_ENV.strip().lower() == "development"
        secret_is_weak = (
            self.JWT_SECRET in KNOWN_INSECURE_JWT_SECRETS or len(self.JWT_SECRET) < MIN_JWT_SECRET_LENGTH
        )

        if is_dev:
            if secret_is_weak:
                self.JWT_SECRET = secrets.token_urlsafe(48)
                logger.warning(
                    "JWT_SECRET is unset or weak; using a random per-process secret for development. "
                    "Tokens will be invalid after a restart. Set JWT_SECRET in .env to fix this."
                )
            return self

        if secret_is_weak:
            raise ValueError(
                f"JWT_SECRET must be set to a random value of at least {MIN_JWT_SECRET_LENGTH} characters "
                f"when APP_ENV is '{self.APP_ENV}' (generate one with: "
                "python -c \"import secrets; print(secrets.token_urlsafe(48))\")."
            )
        if INSECURE_DB_CREDENTIAL_MARKER in self.DATABASE_URL or INSECURE_DB_CREDENTIAL_MARKER in self.SYNC_DATABASE_URL:
            raise ValueError(
                "DATABASE_URL/SYNC_DATABASE_URL still use the default postgres:postgres credentials. "
                f"Set a real database password when APP_ENV is '{self.APP_ENV}'."
            )
        return self


settings = Settings()
