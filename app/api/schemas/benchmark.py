"""Pydantic schemas for Benchmark API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BenchmarkCreate(BaseModel):
    """Schema for creating a benchmark run."""

    model_ids: list[UUID] = Field(
        ...,
        description="List of model UUIDs to benchmark",
        min_length=1,
    )
    prompt_pack: str = Field(
        ...,
        description="Prompt pack to use (shakespeare, synthetic_short, synthetic_medium, synthetic_long)",
        examples=["shakespeare"],
    )
    name: str | None = Field(
        None,
        description="Optional name for the benchmark run",
        examples=["Nightly benchmark"],
    )
    max_tokens: int = Field(
        200,
        description="Maximum tokens to generate per request",
        ge=1,
        le=4096,
    )
    num_runs: int = Field(
        3,
        description="Number of runs per model",
        ge=1,
        le=10,
    )


class BenchmarkResultResponse(BaseModel):
    """Schema for individual benchmark result."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Result UUID")
    model_id: UUID = Field(..., description="Model UUID")
    model_name: str | None = Field(None, description="Model display name")
    ttft_ms: float = Field(..., description="Time to first token in milliseconds")
    tps: float = Field(..., description="Tokens per second")
    tps_excluding_ttft: float = Field(..., description="Tokens per second excluding TTFT")
    total_latency_ms: float = Field(..., description="Total latency in milliseconds")
    input_tokens: int = Field(..., description="Number of input tokens")
    output_tokens: int = Field(..., description="Number of output tokens")
    estimated_cost: float | None = Field(None, description="Estimated cost in USD")
    error: str | None = Field(None, description="Error message if failed")


class BenchmarkRunResponse(BaseModel):
    """Schema for benchmark run response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Benchmark run UUID")
    name: str = Field(..., description="Run name")
    status: str = Field(..., description="Run status (pending, running, completed, failed)")
    model_ids: list[str] = Field(..., description="List of model IDs being benchmarked")
    prompt_pack: str = Field(..., description="Prompt pack used")
    triggered_by: str = Field(..., description="Who triggered the run (user, scheduled)")
    started_at: datetime = Field(..., description="Start timestamp")
    completed_at: datetime | None = Field(None, description="Completion timestamp")
    result_count: int = Field(0, description="Number of results available")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class StatisticsResponse(BaseModel):
    """Schema for benchmark statistics."""

    ttft_p50: float = Field(0.0, description="TTFT 50th percentile")
    ttft_p95: float = Field(0.0, description="TTFT 95th percentile")
    ttft_p99: float = Field(0.0, description="TTFT 99th percentile")
    tps_p50: float = Field(0.0, description="TPS 50th percentile")
    tps_p95: float = Field(0.0, description="TPS 95th percentile")
    tps_p99: float = Field(0.0, description="TPS 99th percentile")


class BenchmarkDetailResponse(BenchmarkRunResponse):
    """Schema for detailed benchmark run response with results and stats."""

    results: list[BenchmarkResultResponse] = Field(
        default_factory=list,
        description="List of benchmark results",
    )
    statistics: StatisticsResponse = Field(
        default_factory=StatisticsResponse,
        description="Aggregate statistics",
    )


class BenchmarkListResponse(BaseModel):
    """Schema for list of benchmark runs."""

    runs: list[BenchmarkRunResponse] = Field(
        default_factory=list,
        description="List of benchmark runs",
    )
    total: int = Field(..., description="Total number of runs")
    page: int = Field(1, description="Current page")
    per_page: int = Field(20, description="Items per page")


class BenchmarkResultListResponse(BaseModel):
    """Schema for list of benchmark results."""

    results: list[BenchmarkResultResponse] = Field(
        default_factory=list,
        description="List of benchmark results",
    )
    total: int = Field(..., description="Total number of results")


class BenchmarkStartResponse(BaseModel):
    """Schema for benchmark start response."""

    id: UUID = Field(..., description="Benchmark run UUID")
    status: str = Field(..., description="Run status")
    message: str = Field(..., description="Status message")


class WebSocketMessage(BaseModel):
    """Schema for WebSocket messages."""

    type: str = Field(..., description="Message type (progress, result, complete, error)")
    completed: int | None = Field(None, description="Number of completed benchmarks")
    total: int | None = Field(None, description="Total number of benchmarks")
    current_model: str | None = Field(None, description="Currently benchmarking model")
    model_id: str | None = Field(None, description="Model ID for result")
    ttft_ms: float | None = Field(None, description="TTFT for result")
    tps: float | None = Field(None, description="TPS for result")
    status: str | None = Field(None, description="Final status")
    error: str | None = Field(None, description="Error message")
