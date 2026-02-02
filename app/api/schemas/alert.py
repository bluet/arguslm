"""Pydantic schemas for Alert API endpoints."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AlertRuleCreate(BaseModel):
    """Schema for creating a new alert rule."""

    name: str = Field(..., min_length=1, max_length=255, description="Rule name")
    rule_type: str = Field(
        ...,
        description="Rule type: any_model_down, specific_model_down, model_unavailable_everywhere, performance_degradation",
    )
    target_model_id: Optional[UUID] = Field(
        None, description="Target model ID (required for specific_model_down)"
    )
    target_model_name: Optional[str] = Field(
        None, description="Target model name (required for model_unavailable_everywhere)"
    )
    enabled: bool = Field(default=True, description="Enable/disable rule")
    notify_in_app: bool = Field(default=True, description="Send in-app notifications")


class AlertRuleUpdate(BaseModel):
    """Schema for updating an alert rule."""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Rule name")
    enabled: Optional[bool] = Field(None, description="Enable/disable rule")
    notify_in_app: Optional[bool] = Field(None, description="Send in-app notifications")


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
