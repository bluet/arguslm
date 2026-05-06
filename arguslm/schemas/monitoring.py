"""Pydantic schemas for Monitoring API endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MonitoringConfigResponse(BaseModel):
    """Schema for monitoring configuration response."""

    id: UUID = Field(..., description="Configuration ID")
    interval_minutes: int = Field(..., ge=1, description="Monitoring interval in minutes")
    prompt_pack: str = Field(..., description="Prompt pack to use for checks")
    enabled: bool = Field(..., description="Whether monitoring is enabled")
    last_run_at: datetime | None = Field(None, description="Last monitoring run timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class MonitoringConfigUpdate(BaseModel):
    """Schema for updating the global monitoring configuration."""

    interval_minutes: int | None = Field(
        None,
        ge=1,
        description="How often to run health checks (in minutes)",
        examples=[15],
    )
    prompt_pack: str | None = Field(
        None,
        description="The prompt pack to use for health checks",
        examples=["shakespeare"],
    )
    enabled: bool | None = Field(
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
    provider_type: str | None = Field(None, description="Provider type (e.g. openai, lmstudio)")
    status: str = Field(..., description="Check status (up, down, degraded)")
    latency_ms: float | None = Field(None, description="Response latency in milliseconds")
    ttft_ms: float | None = Field(None, description="Time to first token in milliseconds")
    tps: float | None = Field(None, description="Tokens per second throughput")
    output_tokens: int | None = Field(None, description="Number of tokens generated")
    error: str | None = Field(None, description="Error message if check failed")
    created_at: datetime = Field(..., description="Check timestamp")

    model_config = ConfigDict(from_attributes=True)


class UptimeHistoryResponse(BaseModel):
    """Schema for paginated uptime history response."""

    items: list[UptimeCheckResponse] = Field(..., description="List of uptime checks")
    total: int = Field(..., description="Total number of checks")
    limit: int = Field(..., description="Limit used in query")
    offset: int = Field(..., description="Offset used in query")


class PromptPackResponse(BaseModel):
    """Schema for a single prompt pack."""

    id: str = Field(..., description="Prompt pack identifier")
    name: str = Field(..., description="Human-readable name")
    prompt: str = Field(..., description="The prompt text")
    expected_tokens: int = Field(..., description="Expected output token count")
