"""Benchmark run and result models."""

import uuid
from typing import Literal

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from arguslm.server.models.base import BaseModel

BenchmarkStatus = Literal["pending", "running", "completed", "failed"]
BenchmarkTrigger = Literal["user", "scheduled"]


class BenchmarkRun(BaseModel):
    """Benchmark run containing multiple model tests.

    Groups benchmark results for multiple models tested together.
    """

    __tablename__ = "benchmark_runs"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    prompt_pack: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    triggered_by: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    results: Mapped[list["BenchmarkResult"]] = relationship(
        "BenchmarkResult", back_populates="run", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<BenchmarkRun(id={self.id}, name={self.name}, "
            f"status={self.status}, models={len(self.model_ids)})>"
        )


class BenchmarkResult(BaseModel):
    """Individual benchmark result for a model.

    Records performance metrics for a single model in a benchmark run.
    """

    __tablename__ = "benchmark_results"

    run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("benchmark_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    model_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("models.id", ondelete="CASCADE"),
        nullable=False,
    )
    ttft_ms: Mapped[float] = mapped_column(Float, nullable=False)
    tps: Mapped[float] = mapped_column(Float, nullable=False)
    tps_excluding_ttft: Mapped[float] = mapped_column(Float, nullable=False)
    total_latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    run: Mapped["BenchmarkRun"] = relationship("BenchmarkRun", back_populates="results")
    model: Mapped["Model"] = relationship("Model", back_populates="benchmark_results")

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<BenchmarkResult(id={self.id}, model_id={self.model_id}, "
            f"ttft={self.ttft_ms}ms, tps={self.tps})>"
        )
