"""Model entity representing LLM models from providers."""

import uuid
from typing import Any, Literal

from sqlalchemy import JSON, Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

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
