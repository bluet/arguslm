"""Pydantic schemas for Model API endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _blank_to_none(v: str | None) -> str | None:
    """Normalize empty/whitespace-only strings to None.

    HTML forms POST cleared inputs as ``""`` by default. Storing ``""`` in
    ``custom_name`` would silently break the ``custom_name or model_id``
    fallback used at every display site (model would render as ``model_id``
    while the DB has ``""`` — silent UX corruption). Normalizing here makes
    the contract explicit: empty/whitespace → None → fallback to ``model_id``.
    """
    if v is None or (isinstance(v, str) and v.strip() == ""):
        return None
    return v


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
        description=(
            "Model identifier as used by the provider (e.g., 'gpt-4o', 'claude-3-opus-20240229')"
        ),
        examples=["gpt-4o"],
    )
    custom_name: str | None = Field(
        None,
        description="Optional human-readable display name for the model",
        examples=["My Production GPT-4o"],
    )

    _normalize_custom_name = field_validator("custom_name", mode="before")(_blank_to_none)

    metadata: dict[str, Any] | None = Field(
        default_factory=dict,
        description="Additional model metadata such as context window size or pricing",
        examples=[{"context_window": 128000, "input_price_per_1m": 5.0}],
    )


class ModelUpdate(BaseModel):
    """Schema for updating a model's configuration."""

    custom_name: str | None = Field(
        None,
        description="New human-readable display name (empty string clears the override)",
        examples=["Updated Model Name"],
    )

    _normalize_custom_name = field_validator("custom_name", mode="before")(_blank_to_none)

    enabled_for_monitoring: bool | None = Field(
        None,
        description="Whether this model should be included in automated uptime monitoring",
        examples=[True],
    )
    enabled_for_benchmark: bool | None = Field(
        None,
        description="Whether this model should be available for manual benchmarking",
        examples=[True],
    )


class ModelResponse(BaseModel):
    """Schema for model response."""

    id: UUID = Field(..., description="Model ID")
    provider_account_id: UUID = Field(..., description="Provider account ID")
    provider_name: str | None = Field(None, description="Provider display name")
    model_id: str = Field(..., description="Model identifier")
    custom_name: str | None = Field(None, description="Custom display name")
    source: str = Field(..., description="Source of the model (discovered or manual)")
    enabled_for_monitoring: bool = Field(..., description="Monitoring enabled")
    enabled_for_benchmark: bool = Field(..., description="Benchmarking enabled")
    model_metadata: dict[str, Any] = Field(default_factory=dict, description="Model metadata")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class ModelListResponse(BaseModel):
    """Schema for paginated model list response."""

    items: list[ModelResponse] = Field(..., description="List of models in this page")
    total: int = Field(..., description="Total number of matching models in database")
    has_more: bool = Field(..., description="Whether more items exist beyond this page")
    limit: int = Field(..., description="Page size used in query")
    offset: int = Field(..., description="Offset used in query")
