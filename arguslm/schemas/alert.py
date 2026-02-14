"""Pydantic schemas for Alert API endpoints."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AlertRuleCreate(BaseModel):
    """Schema for creating a new alert rule."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Descriptive name for the alert rule",
        examples=["Critical Model Down Alert"],
    )
    rule_type: str = Field(
        ...,
        description="Type of rule to evaluate: any_model_down, specific_model_down, model_unavailable_everywhere, performance_degradation",
        examples=["any_model_down"],
    )
    target_model_id: Optional[UUID] = Field(
        None,
        description="Target model ID (required only for specific_model_down)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    target_model_name: Optional[str] = Field(
        None,
        description="Target model name (required only for model_unavailable_everywhere)",
        examples=["gpt-4o"],
    )
    enabled: bool = Field(
        default=True,
        description="Whether the rule is currently active",
        examples=[True],
    )
    notify_in_app: bool = Field(
        default=True,
        description="Whether to show notifications in the web dashboard",
        examples=[True],
    )


class AlertRuleUpdate(BaseModel):
    """Schema for updating an existing alert rule."""

    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="New name for the rule",
        examples=["Updated Alert Name"],
    )
    enabled: Optional[bool] = Field(
        None,
        description="Enable or disable the rule",
        examples=[False],
    )
    notify_in_app: Optional[bool] = Field(
        None,
        description="Enable or disable in-app notifications",
        examples=[True],
    )


class AlertRuleResponse(BaseModel):
    """Schema for alert rule response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Rule ID")
    name: str = Field(..., description="Rule name")
    rule_type: str = Field(..., description="Rule type")
    enabled: bool = Field(..., description="Rule enabled status")
    target_model_id: Optional[UUID] = Field(None, description="Target model ID")
    target_model_name: Optional[str] = Field(None, description="Target model name")
    threshold_config: Optional[dict[str, Any]] = Field(None, description="Threshold configuration")
    notify_in_app: bool = Field(..., description="In-app notification enabled")
    notify_email: bool = Field(..., description="Email notification enabled")
    notify_webhook: bool = Field(..., description="Webhook notification enabled")
    webhook_url: Optional[str] = Field(None, description="Webhook URL")
    created_at: datetime = Field(..., description="Creation timestamp")


class AlertResponse(BaseModel):
    """Schema for alert response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Alert ID")
    rule_id: UUID = Field(..., description="Rule ID")
    model_id: Optional[UUID] = Field(None, description="Model ID")
    message: str = Field(..., description="Alert message")
    acknowledged: bool = Field(..., description="Acknowledgment status")
    created_at: datetime = Field(..., description="Creation timestamp")


class AlertListResponse(BaseModel):
    """Schema for paginated alert list response."""

    items: list[AlertResponse] = Field(..., description="List of alerts")
    unacknowledged_count: int = Field(..., description="Count of unacknowledged alerts")
    limit: int = Field(..., description="Limit used in query")
    offset: int = Field(..., description="Offset used in query")


class UnreadCountResponse(BaseModel):
    """Schema for unread alert count response."""

    count: int = Field(..., description="Number of unacknowledged alerts")


class RecentAlertsResponse(BaseModel):
    """Schema for recent alerts response (for notification dropdown)."""

    items: list[AlertResponse] = Field(..., description="List of recent alerts")
    total_unread: int = Field(..., description="Total unacknowledged alerts count")
