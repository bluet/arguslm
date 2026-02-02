"""Pydantic schemas for Model API endpoints."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelCreate(BaseModel):
    """Schema for creating a new model."""

    provider_account_id: UUID = Field(..., description="ID of the provider account")
    model_id: str = Field(..., min_length=1, description="Model identifier (e.g., 'gpt-4o')")
    custom_name: Optional[str] = Field(None, description="Optional custom display name")
    metadata: Optional[dict[str, Any]] = Field(
        default_factory=dict, description="Additional model metadata"
    )


class ModelUpdate(BaseModel):
    """Schema for updating a model."""

    custom_name: Optional[str] = Field(None, description="Custom display name")
    enabled_for_monitoring: Optional[bool] = Field(None, description="Enable/disable monitoring")
    enabled_for_benchmark: Optional[bool] = Field(None, description="Enable/disable benchmarking")


class ModelResponse(BaseModel):
    """Schema for model response."""

    id: UUID = Field(..., description="Model ID")
    provider_account_id: UUID = Field(..., description="Provider account ID")
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
