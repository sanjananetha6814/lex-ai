import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "LexAI API"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    ENVIRONMENT: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", os.getenv("ENV", "development")))
    
    # Security
    DEFAULT_INSECURE_SECRET: str = "lexai-super-secret-jwt-key-2026-production-ready"
    SECRET_KEY: str = Field(
        default_factory=lambda: os.getenv(
            "SECRET_KEY",
            "lexai-super-secret-jwt-key-2026-production-ready"
        )
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Database configuration
    # Can be set to PostgreSQL (e.g. postgresql+psycopg2://user:pass@localhost:5432/lexai)
    # or SQLite (sqlite:///./lexai.db)
    DATABASE_URL: str = Field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "sqlite:///./lexai.db"
        )
    )
    
    # CORS: Explicitly whitelisted trusted origins without wildcard
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "https://lex-ai-rust-five.vercel.app"
    ]

    def validate_production_security(self) -> None:
        """
        Enforce strict security guardrails before application startup.
        In production, fail startup immediately if insecure default secret or wildcards are detected.
        """
        is_prod = self.ENVIRONMENT.lower() in ["production", "prod"]
        if is_prod:
            if not self.SECRET_KEY or self.SECRET_KEY == self.DEFAULT_INSECURE_SECRET or len(self.SECRET_KEY) < 32:
                raise RuntimeError(
                    "FATAL SECURITY CONFIGURATION: In production mode, SECRET_KEY must be configured "
                    "with a strong, unique secret key (minimum 32 characters) via the SECRET_KEY environment "
                    "variable. Server startup aborted."
                )
            if "*" in self.CORS_ORIGINS:
                raise RuntimeError(
                    "FATAL SECURITY CONFIGURATION: Wildcard '*' in CORS_ORIGINS is prohibited in production "
                    "when allow_credentials=True."
                )

    # AI & RAG Configuration
    OPENAI_API_KEY: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    OPENAI_MODEL: str = Field(default="gpt-4o-mini")
    OPENAI_EMBEDDING_MODEL: str = Field(default="text-embedding-3-small")

    # Document & Storage Configuration
    UPLOAD_DIR: str = Field(default="./uploads")
    MAX_UPLOAD_SIZE: int = 20 * 1024 * 1024  # 20 MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".png", ".jpg", ".jpeg"]
    ALLOWED_MIME_TYPES: List[str] = ["application/pdf", "image/png", "image/jpeg"]

    model_config = SettingsConfigDict(env_file=".env", extra="allow")

settings = Settings()
