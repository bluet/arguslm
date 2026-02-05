"""Monitoring configuration and uptime check API endpoints."""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas.monitoring import (
    MonitoringConfigResponse,
    MonitoringConfigUpdate,
    MonitoringRunResponse,
    PromptPackResponse,
    UptimeCheckResponse,
    UptimeHistoryResponse,
)
from app.core.alert_evaluator import evaluate_alerts
from app.core.prompt_packs import VALID_PROMPT_PACK_IDS, list_prompt_packs
from app.core.scheduler import configure_scheduler
from app.core.uptime import check_uptime
from app.db.init import get_db
from app.models.model import Model
from app.models.monitoring import MonitoringConfig, UptimeCheck

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])


async def get_or_create_default_config(db: AsyncSession) -> MonitoringConfig:
    """Get existing monitoring config or create default if none exists."""
    stmt = select(MonitoringConfig).limit(1)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if config is None:
        config = MonitoringConfig(
            interval_minutes=15,
            prompt_pack="health_check",
            enabled=True,
        )
        db.add(config)
        await db.commit()
        await db.refresh(config)

    return config


@router.get("/config", response_model=MonitoringConfigResponse)
async def get_monitoring_config(db: AsyncSession = Depends(get_db)) -> MonitoringConfigResponse:
    """Get current monitoring configuration.

    Creates default configuration if none exists.
    """
    config = await get_or_create_default_config(db)
    return MonitoringConfigResponse.model_validate(config)


@router.patch("/config", response_model=MonitoringConfigResponse)
async def update_monitoring_config(
    update: MonitoringConfigUpdate,
    db: AsyncSession = Depends(get_db),
) -> MonitoringConfigResponse:
    """Update monitoring configuration.

    Validates:
    - interval_minutes must be >= 1
    - prompt_pack must be valid
    """
    config = await get_or_create_default_config(db)

    # Validate interval_minutes
    if update.interval_minutes is not None:
        if update.interval_minutes < 1:
            raise HTTPException(
                status_code=400,
                detail="interval_minutes must be >= 1",
            )
        config.interval_minutes = update.interval_minutes

    # Validate prompt_pack
    if update.prompt_pack is not None:
        if update.prompt_pack not in VALID_PROMPT_PACK_IDS:
            raise HTTPException(
                status_code=400,
                detail=f"prompt_pack must be one of: {', '.join(sorted(VALID_PROMPT_PACK_IDS))}",
            )
        config.prompt_pack = update.prompt_pack

    # Update enabled flag
    if update.enabled is not None:
        config.enabled = update.enabled

    await db.commit()
    await db.refresh(config)

    await configure_scheduler(config.interval_minutes, config.enabled)

    return MonitoringConfigResponse.model_validate(config)


async def run_uptime_checks_task() -> None:
    """Background task to run uptime checks for all enabled models."""
    from app.db.init import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            config = await get_or_create_default_config(db)
            prompt_pack = config.prompt_pack or "health_check"

            stmt = (
                select(Model)
                .where(Model.enabled_for_monitoring == True)
                .options(selectinload(Model.provider_account))
            )
            result = await db.execute(stmt)
            models = result.scalars().all()

            uptime_checks: list[UptimeCheck] = []
            for model in models:
                uptime_check = await check_uptime(model, prompt_pack=prompt_pack)
                db.add(uptime_check)
                uptime_checks.append(uptime_check)

            await evaluate_alerts(db, uptime_checks)

            config.last_run_at = datetime.now(datetime.now().astimezone().tzinfo)
            await db.commit()
        except Exception as e:
            import logging

            logging.error(f"Uptime check failed: {e}")


@router.post("/run", response_model=MonitoringRunResponse)
async def trigger_monitoring_run(
    background_tasks: BackgroundTasks,
) -> MonitoringRunResponse:
    """Trigger manual monitoring run.

    Runs uptime checks for all models with enabled_for_monitoring=True.
    Returns immediately; checks run in background.
    """
    run_id = str(uuid.uuid4())
    background_tasks.add_task(run_uptime_checks_task)

    return MonitoringRunResponse(
        run_id=run_id,
        status="queued",
        message="Monitoring run queued for execution",
    )


@router.get("/uptime", response_model=UptimeHistoryResponse)
async def get_uptime_history(
    model_id: Optional[uuid.UUID] = Query(None, description="Filter by model ID"),
    status: Optional[str] = Query(None, description="Filter by status (up, down, degraded)"),
    since: Optional[datetime] = Query(None, description="Filter by created_at >= since"),
    enabled_only: bool = Query(
        False, description="Only show checks for models with monitoring enabled"
    ),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_db),
) -> UptimeHistoryResponse:
    """Get uptime check history with optional filters.

    Filters:
    - model_id: Filter by specific model
    - status: Filter by status (up, down, degraded)
    - since: Filter by created_at >= since
    - enabled_only: Only return checks for models with monitoring enabled (default True)
    - limit: Maximum results (default 100, max 1000)
    - offset: Pagination offset (default 0)
    """
    # Build query with filters
    filters = []

    if model_id is not None:
        filters.append(UptimeCheck.model_id == model_id)

    if status is not None:
        filters.append(UptimeCheck.status == status)

    if since is not None:
        filters.append(UptimeCheck.created_at >= since)

    if enabled_only:
        filters.append(Model.enabled_for_monitoring == True)

    count_stmt = select(func.count(UptimeCheck.id))
    if enabled_only:
        count_stmt = count_stmt.join(Model, UptimeCheck.model_id == Model.id)
    if filters:
        count_stmt = count_stmt.where(and_(*filters))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    stmt = select(UptimeCheck).options(selectinload(UptimeCheck.model))
    if enabled_only:
        stmt = stmt.join(Model, UptimeCheck.model_id == Model.id)
    stmt = stmt.order_by(desc(UptimeCheck.created_at)).limit(limit).offset(offset)

    if filters:
        stmt = stmt.where(and_(*filters))

    result = await db.execute(stmt)
    checks = result.scalars().all()

    # Convert to response schema with model names
    items = []
    for check in checks:
        model_name = check.model.custom_name or check.model.model_id if check.model else "Unknown"
        items.append(
            UptimeCheckResponse(
                id=check.id,
                model_id=check.model_id,
                model_name=model_name,
                status=check.status,
                latency_ms=check.latency_ms,
                ttft_ms=check.ttft_ms,
                tps=check.tps,
                output_tokens=check.output_tokens,
                error=check.error,
                created_at=check.created_at,
            )
        )

    return UptimeHistoryResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/uptime/export")
async def export_uptime_history(
    format: str = Query("json", pattern="^(json|csv)$"),
    model_id: Optional[uuid.UUID] = Query(None, description="Filter by model ID"),
    start_date: Optional[datetime] = Query(None, description="Filter by created_at >= start_date"),
    end_date: Optional[datetime] = Query(None, description="Filter by created_at <= end_date"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Export uptime check history in JSON or CSV format.

    Args:
        format: Export format (json or csv)
        model_id: Optional filter by model ID
        start_date: Optional filter by start date
        end_date: Optional filter by end date
        db: Database session

    Returns:
        File download response with appropriate content type
    """
    # Build query with filters
    filters = []

    if model_id is not None:
        filters.append(UptimeCheck.model_id == model_id)

    if start_date is not None:
        filters.append(UptimeCheck.created_at >= start_date)

    if end_date is not None:
        filters.append(UptimeCheck.created_at <= end_date)

    # Get uptime checks with model info
    stmt = (
        select(UptimeCheck)
        .options(selectinload(UptimeCheck.model).selectinload(Model.provider_account))
        .order_by(desc(UptimeCheck.created_at))
    )

    if filters:
        stmt = stmt.where(and_(*filters))

    result = await db.execute(stmt)
    checks = result.scalars().all()

    if format == "json":
        # Build JSON export
        export_data = {"checks": []}

        for check in checks:
            model_name = (
                check.model.custom_name or check.model.model_id if check.model else "Unknown"
            )
            provider = (
                check.model.provider_account.provider_type
                if check.model and check.model.provider_account
                else "Unknown"
            )
            export_data["checks"].append(
                {
                    "model_name": model_name,
                    "provider": provider,
                    "status": check.status,
                    "latency_ms": check.latency_ms,
                    "error": check.error,
                    "timestamp": check.created_at.isoformat() if check.created_at else None,
                }
            )

        import json

        content = json.dumps(export_data, indent=2)
        media_type = "application/json"
        filename = "uptime_history.json"
    else:  # CSV format
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "model_name",
                "provider",
                "status",
                "latency_ms",
                "error",
                "timestamp",
            ],
        )
        writer.writeheader()

        for check in checks:
            model_name = (
                check.model.custom_name or check.model.model_id if check.model else "Unknown"
            )
            provider = (
                check.model.provider_account.provider_type
                if check.model and check.model.provider_account
                else "Unknown"
            )
            writer.writerow(
                {
                    "model_name": model_name,
                    "provider": provider,
                    "status": check.status,
                    "latency_ms": check.latency_ms or "",
                    "error": check.error or "",
                    "timestamp": check.created_at.isoformat() if check.created_at else "",
                }
            )

        content = output.getvalue()
        media_type = "text/csv; charset=utf-8"
        filename = "uptime_history.csv"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/prompt-packs", response_model=list[PromptPackResponse])
async def get_prompt_packs() -> list[PromptPackResponse]:
    """List available prompt packs for monitoring configuration."""
    return [
        PromptPackResponse(
            id=pack.id,
            name=pack.name,
            prompt=pack.prompt,
            expected_tokens=pack.expected_tokens,
        )
        for pack in list_prompt_packs()
    ]
