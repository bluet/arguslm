"""Pydantic schemas for Model API endpoints."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelCreate(BaseModel):
    """Schema for creating a new model."""

    provider_account_id: UUID = Field(
        ...,
        description="ID of the provider account this model belongs to",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    model_id: str = Field(
        ...,
        min_length=1,
        description="Model identifier as used by the provider (e.g., 'gpt-4o', 'claude-3-opus-20240229')",
        examples=["gpt-4o"],
    )
    custom_name: Optional[str] = Field(
        None,
        description="Optional human-readable display name for the model",
        examples=["My Production GPT-4o"],
    )
    metadata: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional model metadata such as context window size or pricing",
        examples=[{"context_window": 128000, "input_price_per_1m": 5.0}],
    )


class ModelUpdate(BaseModel):
    """Schema for updating a model's configuration."""

    custom_name: Optional[str] = Field(
        None,
        description="New human-readable display name",
        examples=["Updated Model Name"],
    )
    enabled_for_monitoring: Optional[bool] = Field(
        None,
        description="Whether this model should be included in automated uptime monitoring",
        examples=[True],
    )
    enabled_for_benchmark: Optional[bool] = Field(
        None,
        description="Whether this model should be available for manual benchmarking",
        examples=[True],
    )


class ModelResponse(BaseModel):
    """Schema for model response."""

    id: UUID = Field(..., description="Model ID")
    provider_account_id: UUID = Field(..., description="Provider account ID")
    provider_name: Optional[str] = Field(None, description="Provider display name")
    model_id: str = Field(..., description="Model identifier")
    custom_name: Optional[str] = Field(None, description="Custom display name")
    source: str = Field(..., description="Source of the model (discovered or manual)")
    enabled_for_monitoring: bool = Field(..., description="Monitoring enabled")
    enabled_for_benchmark: bool = Field(..., description="Benchmarking enabled")
    model_metadata: dict[str, Any] = Field(default_factory=dict, description="Model metadata")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class ModelListResponse(BaseModel):
    """Schema for paginated model list response."""

    items: list[ModelResponse] = Field(..., description="List of models")
    total: int = Field(..., description="Total number of models")
    limit: int = Field(..., description="Limit used in query")
    offset: int = Field(..., description="Offset used in query")
