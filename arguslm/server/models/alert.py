"""Alert rule and alert models."""

import uuid
from typing import Any, Literal

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from arguslm.server.models.base import BaseModel

AlertRuleType = Literal[
    "any_model_down",
    "specific_model_down",
    "model_unavailable_everywhere",
    "performance_degradation",
]


class AlertRule(BaseModel):
    """Alert rule configuration.

    Defines conditions that trigger alerts for monitoring.
    """

    __tablename__ = "alert_rules"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    target_model_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("models.id", ondelete="CASCADE"),
        nullable=True,
    )
    target_model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    threshold_config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    notify_in_app: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_email: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notify_webhook: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert", back_populates="rule", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<AlertRule(id={self.id}, name={self.name}, "
            f"type={self.rule_type}, enabled={self.enabled})>"
        )


class Alert(BaseModel):
    """Alert instance triggered by a rule.

    Records individual alert occurrences.
    """

    __tablename__ = "alerts"

    rule_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("alert_rules.id", ondelete="CASCADE"),
        nullable=False,
    )
    model_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("models.id", ondelete="SET NULL"),
        nullable=True,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    rule: Mapped["AlertRule"] = relationship("AlertRule", back_populates="alerts")

    def __repr__(self) -> str:
        """String representation."""
        return f"<Alert(id={self.id}, rule_id={self.rule_id}, acknowledged={self.acknowledged})>"
