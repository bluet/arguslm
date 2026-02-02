"""Monitoring configuration and uptime check models."""

import uuid
from typing import Literal

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

UptimeStatus = Literal["up", "down", "degraded"]


class MonitoringConfig(BaseModel):
    """Global monitoring configuration.

    Controls automated uptime monitoring settings.
    """

    __tablename__ = "monitoring_configs"

    interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_pack: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_run_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<MonitoringConfig(id={self.id}, interval={self.interval_minutes}min, "
            f"prompt_pack={self.prompt_pack}, enabled={self.enabled})>"
        )


class UptimeCheck(BaseModel):
    """Uptime check result for a model.

    Records health check results for monitoring model availability.
    """

    __tablename__ = "uptime_checks"

    model_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("models.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    model: Mapped["Model"] = relationship("Model", back_populates="uptime_checks")

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<UptimeCheck(id={self.id}, model_id={self.model_id}, "
            f"status={self.status}, latency={self.latency_ms}ms)>"
        )
