"""Application configuration settings."""

import os
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite+aiosqlite:///./arguslm.db"
    database_echo: bool = False

    # Security
    encryption_key: str = ""
    secret_key: str = ""

    # API
    api_title: str = "ArgusLM API"
    api_version: str = "0.2.0"
    api_prefix: str = "/api/v1"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("encryption_key")
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        """Validate ENCRYPTION_KEY is set and is a valid Fernet key."""
        if not v:
            raise ValueError(
                "ENCRYPTION_KEY is required. Generate with: "
                "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        try:
            from cryptography.fernet import Fernet

            Fernet(v.encode())
        except Exception:
            raise ValueError(
                "ENCRYPTION_KEY is invalid. Must be a valid Fernet key (44 chars, base64). "
                "Generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        return v

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate SECRET_KEY is set and not the placeholder value."""
        placeholder_values = [
            "",
            "your-secret-key-here-change-in-production",
            "dev-secret-key-change-in-production",
        ]
        if v in placeholder_values:
            raise ValueError(
                "SECRET_KEY is required. Generate with: "
                "python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        return v


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Cached Settings instance.
    """
    return Settings()
