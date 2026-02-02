"""Model entity representing LLM models from providers."""

import re
import uuid
from typing import Any, Literal, TYPE_CHECKING

from sqlalchemy import JSON, Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.benchmark import BenchmarkResult
    from app.models.monitoring import UptimeCheck
    from app.models.provider import ProviderAccount

ModelSource = Literal["discovered", "manual"]


class Model(BaseModel):
    """LLM model from a provider account.

    Represents a specific model (e.g., gpt-4o) from a provider account.
    Can be discovered automatically or added manually.
    """

    __tablename__ = "models"

    provider_account_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("provider_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    custom_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    enabled_for_monitoring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enabled_for_benchmark: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    model_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    # Relationships
    provider_account: Mapped["ProviderAccount"] = relationship(
        "ProviderAccount", back_populates="models"
    )
    benchmark_results: Mapped[list["BenchmarkResult"]] = relationship(
        "BenchmarkResult", back_populates="model", cascade="all, delete-orphan"
    )
    uptime_checks: Mapped[list["UptimeCheck"]] = relationship(
        "UptimeCheck", back_populates="model", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation."""
        display = self.custom_name or self.model_id
        return (
            f"<Model(id={self.id}, model_id={self.model_id}, "
            f"display={display}, source={self.source})>"
        )


async def create_manual_model(
    db_session: AsyncSession,
    provider_account_id: uuid.UUID,
    model_id: str,
    custom_name: str | None,
    metadata: dict[str, Any],
) -> Model:
    """Create a manually added model.

    Args:
        db_session: Database session
        provider_account_id: ID of the provider account
        model_id: Model identifier (e.g., "custom-model-v1")
        custom_name: Optional custom display name
        metadata: Additional model metadata

    Returns:
        Created Model instance
    """
    model = Model(
        provider_account_id=provider_account_id,
        model_id=model_id,
        custom_name=custom_name,
        source="manual",
        enabled_for_benchmark=True,
        model_metadata=metadata,
    )
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)
    return model


async def update_custom_name(db_session: AsyncSession, model: Model, new_name: str | None) -> Model:
    """Update the custom name of a model.

    Args:
        db_session: Database session
        model: Model instance to update
        new_name: New custom name (or None to clear)

    Returns:
        Updated Model instance
    """
    model.custom_name = new_name
    await db_session.commit()
    await db_session.refresh(model)
    return model


def validate_model_id(model_id: str) -> bool:
    """Validate model ID format.

    Model IDs must be non-empty, non-whitespace strings containing only
    alphanumeric characters, hyphens, and underscores.

    Args:
        model_id: Model ID to validate

    Returns:
        True if valid, False otherwise
    """
    if not model_id or not model_id.strip():
        return False
    # Allow alphanumeric, hyphens, and underscores
    pattern = r"^[a-zA-Z0-9_-]+$"
    return bool(re.match(pattern, model_id))
