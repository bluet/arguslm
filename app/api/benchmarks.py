"""Benchmark API endpoints for running and managing benchmarks."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas.benchmark import (
    BenchmarkCreate,
    BenchmarkDetailResponse,
    BenchmarkListResponse,
    BenchmarkResultListResponse,
    BenchmarkResultResponse,
    BenchmarkRunResponse,
    BenchmarkStartResponse,
    StatisticsResponse,
)
from app.core.benchmark_engine import BenchmarkConfig, calculate_statistics, run_benchmark
from app.db.init import get_db
from app.models.benchmark import BenchmarkResult, BenchmarkRun
from app.models.model import Model

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

router = APIRouter(prefix="/api/v1/benchmarks", tags=["benchmarks"])

# Store for active WebSocket connections per run_id
_active_connections: dict[uuid.UUID, list[WebSocket]] = {}
# Store for benchmark progress tracking
_benchmark_progress: dict[uuid.UUID, dict] = {}


async def _broadcast_to_run(run_id: uuid.UUID, message: dict) -> None:
    """Broadcast a message to all WebSocket connections for a run."""
    connections = _active_connections.get(run_id, [])
    disconnected = []
    for ws in connections:
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.append(ws)
    # Clean up disconnected
    for ws in disconnected:
        if ws in _active_connections.get(run_id, []):
            _active_connections[run_id].remove(ws)


async def _run_benchmark_task(
    run_id: uuid.UUID,
    config: BenchmarkConfig,
    db_factory: type,
) -> None:
    """Background task to run benchmarks and save results."""
    from app.db.init import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            # Update status to running
            result = await db.execute(select(BenchmarkRun).where(BenchmarkRun.id == run_id))
            run = result.scalar_one_or_none()
            if not run:
                return

            run.status = "running"
            await db.commit()
            await _broadcast_to_run(run_id, {"type": "progress", "status": "running"})

            # Initialize progress tracking
            total_benchmarks = len(config.models) * config.num_runs
            _benchmark_progress[run_id] = {"completed": 0, "total": total_benchmarks}

            # Run benchmarks
            results = await run_benchmark(config)

            # Save results to database
            for benchmark_result in results:
                # Update run_id to match our run
                db_result = BenchmarkResult(
                    run_id=run_id,
                    model_id=benchmark_result.model_id,
                    ttft_ms=benchmark_result.ttft_ms,
                    tps=benchmark_result.tps,
                    tps_excluding_ttft=benchmark_result.tps_excluding_ttft,
                    total_latency_ms=benchmark_result.total_latency_ms,
                    input_tokens=benchmark_result.input_tokens,
                    output_tokens=benchmark_result.output_tokens,
                    estimated_cost=benchmark_result.estimated_cost,
                    error=benchmark_result.error,
                )
                db.add(db_result)

                # Broadcast result
                await _broadcast_to_run(
                    run_id,
                    {
                        "type": "result",
                        "model_id": str(benchmark_result.model_id),
                        "ttft_ms": benchmark_result.ttft_ms,
                        "tps": benchmark_result.tps,
                    },
                )

            # Update run status to completed
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            await db.commit()

            # Broadcast completion
            await _broadcast_to_run(run_id, {"type": "complete", "status": "completed"})

        except Exception as e:
            # Update run status to failed
            try:
                result = await db.execute(select(BenchmarkRun).where(BenchmarkRun.id == run_id))
                run = result.scalar_one_or_none()
                if run:
                    run.status = "failed"
                    run.completed_at = datetime.now(timezone.utc)
                    await db.commit()
            except Exception:
                pass

            # Broadcast error
            await _broadcast_to_run(run_id, {"type": "error", "error": str(e), "status": "failed"})

        finally:
            # Clean up progress tracking
            _benchmark_progress.pop(run_id, None)


def _build_run_response(run: BenchmarkRun) -> BenchmarkRunResponse:
    """Build a BenchmarkRunResponse from a BenchmarkRun model."""
    return BenchmarkRunResponse(
        id=run.id,
        name=run.name,
        status=run.status,
        model_ids=run.model_ids,
        prompt_pack=run.prompt_pack,
        triggered_by=run.triggered_by,
        started_at=run.started_at,
        completed_at=run.completed_at,
        result_count=len(run.results) if run.results else 0,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def _build_result_response(
    result: BenchmarkResult, model_name: str | None = None
) -> BenchmarkResultResponse:
    """Build a BenchmarkResultResponse from a BenchmarkResult model."""
    return BenchmarkResultResponse(
        id=result.id,
        model_id=result.model_id,
        model_name=model_name,
        ttft_ms=result.ttft_ms,
        tps=result.tps,
        tps_excluding_ttft=result.tps_excluding_ttft,
        total_latency_ms=result.total_latency_ms,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        estimated_cost=result.estimated_cost,
        error=result.error,
    )


@router.post("", response_model=BenchmarkStartResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_benchmark(
    benchmark: BenchmarkCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> BenchmarkStartResponse:
    """Start a new benchmark run.

    Creates a benchmark run record and starts execution in background.
    Returns immediately with the run ID and pending status.
    """
    # Validate model_ids exist
    model_result = await db.execute(select(Model).where(Model.id.in_(benchmark.model_ids)))
    models = model_result.scalars().all()

    if len(models) != len(benchmark.model_ids):
        found_ids = {m.id for m in models}
        missing = [str(mid) for mid in benchmark.model_ids if mid not in found_ids]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model IDs not found: {', '.join(missing)}",
        )

    # Create benchmark run record
    run_name = (
        benchmark.name or f"Benchmark {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
    )
    run = BenchmarkRun(
        name=run_name,
        model_ids=[str(mid) for mid in benchmark.model_ids],
        prompt_pack=benchmark.prompt_pack,
        status="pending",
        triggered_by="user",
        started_at=datetime.now(timezone.utc),
        completed_at=None,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # Create benchmark config
    config = BenchmarkConfig(
        models=list(models),
        prompt_pack=benchmark.prompt_pack,
        max_tokens=benchmark.max_tokens,
        num_runs=benchmark.num_runs,
    )

    # Start background task
    background_tasks.add_task(
        _run_benchmark_task,
        run.id,
        config,
        type(db),
    )

    return BenchmarkStartResponse(
        id=run.id,
        status="pending",
        message="Benchmark run started",
    )


@router.get("", response_model=BenchmarkListResponse)
async def list_benchmarks(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: str | None = Query(
        None,
        alias="status",
        description="Filter by status (pending, running, completed, failed)",
    ),
    db: AsyncSession = Depends(get_db),
) -> BenchmarkListResponse:
    """List all benchmark runs with pagination and optional status filter."""
    # Build query
    query = select(BenchmarkRun).options(selectinload(BenchmarkRun.results))

    if status_filter:
        query = query.where(BenchmarkRun.status == status_filter)

    # Count total
    count_query = select(func.count(BenchmarkRun.id))
    if status_filter:
        count_query = count_query.where(BenchmarkRun.status == status_filter)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and ordering
    query = query.order_by(BenchmarkRun.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    runs = result.scalars().all()

    return BenchmarkListResponse(
        runs=[_build_run_response(run) for run in runs],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{run_id}", response_model=BenchmarkDetailResponse)
async def get_benchmark(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> BenchmarkDetailResponse:
    """Get detailed benchmark run with results and statistics."""
    result = await db.execute(
        select(BenchmarkRun)
        .where(BenchmarkRun.id == run_id)
        .options(selectinload(BenchmarkRun.results))
    )
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Benchmark run {run_id} not found",
        )

    # Build result responses with model names
    result_responses = []
    model_ids = [r.model_id for r in run.results]
    models_result = await db.execute(select(Model).where(Model.id.in_(model_ids)))
    models_map = {m.id: m.custom_name or m.model_id for m in models_result.scalars().all()}

    for r in run.results:
        model_name = models_map.get(r.model_id)
        result_responses.append(_build_result_response(r, model_name))

    # Calculate statistics
    ttft_values = [r.ttft_ms for r in run.results if r.error is None]
    tps_values = [r.tps for r in run.results if r.error is None]

    ttft_stats = calculate_statistics(ttft_values)
    tps_stats = calculate_statistics(tps_values)

    stats = StatisticsResponse(
        ttft_p50=ttft_stats["p50"],
        ttft_p95=ttft_stats["p95"],
        ttft_p99=ttft_stats["p99"],
        tps_p50=tps_stats["p50"],
        tps_p95=tps_stats["p95"],
        tps_p99=tps_stats["p99"],
    )

    return BenchmarkDetailResponse(
        id=run.id,
        name=run.name,
        status=run.status,
        model_ids=run.model_ids,
        prompt_pack=run.prompt_pack,
        triggered_by=run.triggered_by,
        started_at=run.started_at,
        completed_at=run.completed_at,
        result_count=len(run.results),
        created_at=run.created_at,
        updated_at=run.updated_at,
        results=result_responses,
        statistics=stats,
    )


@router.get("/{run_id}/results", response_model=BenchmarkResultListResponse)
async def get_benchmark_results(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> BenchmarkResultListResponse:
    """Get detailed results for a benchmark run."""
    # Check run exists
    run_result = await db.execute(select(BenchmarkRun).where(BenchmarkRun.id == run_id))
    run = run_result.scalar_one_or_none()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Benchmark run {run_id} not found",
        )

    # Get results with model info
    results_query = await db.execute(
        select(BenchmarkResult).where(BenchmarkResult.run_id == run_id)
    )
    results = results_query.scalars().all()

    # Get model names
    model_ids = [r.model_id for r in results]
    models_result = await db.execute(select(Model).where(Model.id.in_(model_ids)))
    models_map = {m.id: m.custom_name or m.model_id for m in models_result.scalars().all()}

    result_responses = [_build_result_response(r, models_map.get(r.model_id)) for r in results]

    return BenchmarkResultListResponse(
        results=result_responses,
        total=len(result_responses),
    )


@router.get("/{run_id}/export")
async def export_benchmark(
    run_id: uuid.UUID,
    format: str = Query("json", pattern="^(json|csv)$"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Export benchmark results in JSON or CSV format.

    Args:
        run_id: Benchmark run ID
        format: Export format (json or csv)
        db: Database session

    Returns:
        File download response with appropriate content type
    """
    # Get benchmark run with results
    result = await db.execute(
        select(BenchmarkRun)
        .where(BenchmarkRun.id == run_id)
        .options(selectinload(BenchmarkRun.results))
    )
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Benchmark run {run_id} not found",
        )

    # Get model names and providers
    model_ids = [r.model_id for r in run.results]
    models_result = await db.execute(
        select(Model).where(Model.id.in_(model_ids)).options(selectinload(Model.provider_account))
    )
    models = models_result.scalars().all()
    models_map = {
        m.id: (m.custom_name or m.model_id, m.provider_account.provider_type) for m in models
    }

    if format == "json":
        # Build JSON export
        export_data = {
            "run_id": str(run.id),
            "run_name": run.name,
            "prompt_pack": run.prompt_pack,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "results": [],
        }

        for r in run.results:
            model_name, provider = models_map.get(r.model_id, ("Unknown", "Unknown"))
            export_data["results"].append(
                {
                    "model_name": model_name,
                    "provider": provider,
                    "ttft_ms": r.ttft_ms,
                    "tps": r.tps,
                    "tps_excluding_ttft": r.tps_excluding_ttft,
                    "total_latency_ms": r.total_latency_ms,
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "error": r.error,
                    "timestamp": r.created_at.isoformat() if r.created_at else None,
                }
            )

        import json

        content = json.dumps(export_data, indent=2)
        media_type = "application/json"
        filename = f"benchmark_{run_id}.json"
    else:  # CSV format
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "model_name",
                "provider",
                "ttft_ms",
                "tps",
                "tps_excluding_ttft",
                "total_latency_ms",
                "input_tokens",
                "output_tokens",
                "error",
                "timestamp",
            ],
        )
        writer.writeheader()

        for r in run.results:
            model_name, provider = models_map.get(r.model_id, ("Unknown", "Unknown"))
            writer.writerow(
                {
                    "model_name": model_name,
                    "provider": provider,
                    "ttft_ms": r.ttft_ms,
                    "tps": r.tps,
                    "tps_excluding_ttft": r.tps_excluding_ttft,
                    "total_latency_ms": r.total_latency_ms,
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "error": r.error or "",
                    "timestamp": r.created_at.isoformat() if r.created_at else "",
                }
            )

        content = output.getvalue()
        media_type = "text/csv; charset=utf-8"
        filename = f"benchmark_{run_id}.csv"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.websocket("/{run_id}/stream")
async def stream_benchmark(
    websocket: WebSocket,
    run_id: uuid.UUID,
) -> None:
    """WebSocket endpoint for live benchmark progress updates.

    Messages sent:
    - {"type": "progress", "completed": N, "total": M, "current_model": "..."}
    - {"type": "result", "model_id": "...", "ttft_ms": ..., "tps": ...}
    - {"type": "complete", "status": "completed"}
    - {"type": "error", "error": "...", "status": "failed"}
    """
    await websocket.accept()

    # Register connection
    if run_id not in _active_connections:
        _active_connections[run_id] = []
    _active_connections[run_id].append(websocket)

    try:
        # Send initial progress if available
        if run_id in _benchmark_progress:
            progress = _benchmark_progress[run_id]
            await websocket.send_json(
                {
                    "type": "progress",
                    "completed": progress.get("completed", 0),
                    "total": progress.get("total", 0),
                    "current_model": progress.get("current_model"),
                }
            )

        # Keep connection open until client disconnects or run completes
        while True:
            try:
                # Wait for messages from client (ping/pong) with timeout
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Echo pings as pongs
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send keep-alive ping
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
            except WebSocketDisconnect:
                break

    finally:
        # Unregister connection
        if run_id in _active_connections:
            if websocket in _active_connections[run_id]:
                _active_connections[run_id].remove(websocket)
            if not _active_connections[run_id]:
                del _active_connections[run_id]
