"""Provider account model with encrypted credentials."""

from typing import Any, Literal

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.security import decrypt_credentials, encrypt_credentials
from app.models.base import BaseModel

ProviderType = Literal[
    "openai",
    "anthropic",
    "google_vertex",
    "google_gemini",
    "aws_bedrock",
    "azure_openai",
    "ollama",
    "lm_studio",
    "openrouter",
    "together_ai",
    "groq",
    "mistral",
    "custom_openai_compatible",
]


class ProviderAccount(BaseModel):
    """Provider account with encrypted credentials.

    Stores API credentials for LLM providers with encryption at rest.
    Supports multiple accounts per provider type.
    """

    __tablename__ = "provider_accounts"

    provider_type: Mapped[str] = mapped_column(String(50), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    credentials_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    models: Mapped[list["Model"]] = relationship(
        "Model", back_populates="provider_account", cascade="all, delete-orphan"
    )

    @property
    def credentials(self) -> dict[str, Any]:
        """Decrypt and return credentials dictionary."""
        return decrypt_credentials(self.credentials_encrypted)

    @credentials.setter
    def credentials(self, value: dict[str, Any]) -> None:
        """Encrypt and store credentials dictionary."""
        self.credentials_encrypted = encrypt_credentials(value)

    @property
    def base_url(self) -> str | None:
        """Extract base_url from credentials for display (non-sensitive)."""
        return self.credentials.get("base_url")

    @property
    def region(self) -> str | None:
        """Extract region from credentials for display (non-sensitive)."""
        return self.credentials.get("region")

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<ProviderAccount(id={self.id}, provider_type={self.provider_type}, "
            f"display_name={self.display_name}, enabled={self.enabled})>"
        )
