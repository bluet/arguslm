"""Pydantic schemas for Monitoring API endpoints."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MonitoringConfigResponse(BaseModel):
    """Schema for monitoring configuration response."""

    id: UUID = Field(..., description="Configuration ID")
    interval_minutes: int = Field(..., ge=1, description="Monitoring interval in minutes")
    prompt_pack: str = Field(..., description="Prompt pack to use for checks")
    enabled: bool = Field(..., description="Whether monitoring is enabled")
    last_run_at: Optional[datetime] = Field(None, description="Last monitoring run timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class MonitoringConfigUpdate(BaseModel):
    """Schema for updating the global monitoring configuration."""

    interval_minutes: Optional[int] = Field(
        None,
        ge=1,
        description="How often to run health checks (in minutes)",
        examples=[15],
    )
    prompt_pack: Optional[str] = Field(
        None,
        description="The prompt pack to use for health checks",
        examples=["shakespeare"],
    )
    enabled: Optional[bool] = Field(
        None,
        description="Whether automated monitoring is globally enabled",
        examples=[True],
    )


class MonitoringRunResponse(BaseModel):
    """Schema for manual monitoring run response."""

    run_id: str = Field(..., description="Run identifier")
    status: str = Field(..., description="Run status (queued, running, completed)")
    message: str = Field(..., description="Status message")


class UptimeCheckResponse(BaseModel):
    """Schema for uptime check result."""

    id: UUID = Field(..., description="Check ID")
    model_id: UUID = Field(..., description="Model ID")
    model_name: str = Field(..., description="Model display name")
    status: str = Field(..., description="Check status (up, down, degraded)")
    latency_ms: Optional[float] = Field(None, description="Response latency in milliseconds")
    error: Optional[str] = Field(None, description="Error message if check failed")
    created_at: datetime = Field(..., description="Check timestamp")

    model_config = ConfigDict(from_attributes=True)


class UptimeHistoryResponse(BaseModel):
    """Schema for paginated uptime history response."""

    items: list[UptimeCheckResponse] = Field(..., description="List of uptime checks")
    total: int = Field(..., description="Total number of checks")
    limit: int = Field(..., description="Limit used in query")
    offset: int = Field(..., description="Offset used in query")
