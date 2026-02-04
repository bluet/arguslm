"""Pydantic schemas for Provider Account API."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProviderCreate(BaseModel):
    """Schema for creating a provider account."""

    provider_type: str = Field(
        ...,
        description="Provider type (openai, anthropic, etc.)",
        examples=["openai"],
    )
    display_name: str = Field(
        ...,
        description="Human-readable name for this account",
        examples=["OpenAI Production"],
    )
    credentials: dict[str, Any] = Field(
        default_factory=dict,
        description="Provider credentials (will be encrypted)",
        examples=[{"api_key": "sk-..."}],
    )


class ProviderUpdate(BaseModel):
    """Schema for updating a provider account."""

    display_name: str | None = Field(
        None,
        description="New display name",
        examples=["OpenAI Staging"],
    )
    credentials: dict[str, Any] | None = Field(
        None,
        description="Updated credentials (will be encrypted)",
        examples=[{"api_key": "sk-new..."}],
    )
    enabled: bool | None = Field(
        None,
        description="Enable or disable the account",
        examples=[True],
    )


class ProviderResponse(BaseModel):
    """Schema for provider account response (excludes sensitive credentials)."""

    id: UUID = Field(..., description="Provider account UUID")
    provider_type: str = Field(..., description="Provider type")
    display_name: str = Field(..., description="Display name")
    enabled: bool = Field(..., description="Whether account is enabled")
    base_url: str | None = Field(None, description="Base URL for the provider (non-sensitive)")
    region: str | None = Field(None, description="AWS region (for AWS Bedrock)")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class ProviderListResponse(BaseModel):
    """Schema for list of provider accounts."""

    providers: list[ProviderResponse] = Field(
        default_factory=list,
        description="List of provider accounts",
    )
    total: int = Field(..., description="Total number of providers")


class ProviderTestResponse(BaseModel):
    """Schema for provider connection test response."""

    success: bool = Field(..., description="Whether test succeeded")
    message: str = Field(..., description="Test result message")
    details: dict[str, Any] | None = Field(
        None,
        description="Additional test details",
    )


class ProviderRefreshResponse(BaseModel):
    """Schema for model refresh response."""

    success: bool = Field(..., description="Whether refresh succeeded")
    models_discovered: int = Field(..., description="Number of models discovered")
    message: str = Field(..., description="Refresh result message")
