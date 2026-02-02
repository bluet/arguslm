"""Monitoring configuration and uptime check API endpoints."""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.monitoring import (
    MonitoringConfigResponse,
    MonitoringConfigUpdate,
    MonitoringRunResponse,
    UptimeCheckResponse,
    UptimeHistoryResponse,
)
from app.core.uptime import check_uptime
from app.db.init import get_db
from app.models.model import Model
from app.models.monitoring import MonitoringConfig, UptimeCheck

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])

# Valid prompt packs
VALID_PROMPT_PACKS = {"shakespeare", "synthetic_short", "synthetic_medium", "synthetic_long"}


async def get_or_create_default_config(db: AsyncSession) -> MonitoringConfig:
    """Get existing monitoring config or create default if none exists."""
    stmt = select(MonitoringConfig).limit(1)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if config is None:
        config = MonitoringConfig(
            interval_minutes=15,
            prompt_pack="shakespeare",
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
        if update.prompt_pack not in VALID_PROMPT_PACKS:
            raise HTTPException(
                status_code=400,
                detail=f"prompt_pack must be one of: {', '.join(VALID_PROMPT_PACKS)}",
            )
        config.prompt_pack = update.prompt_pack

    # Update enabled flag
    if update.enabled is not None:
        config.enabled = update.enabled

    await db.commit()
    await db.refresh(config)
    return MonitoringConfigResponse.model_validate(config)


async def run_uptime_checks(db: AsyncSession) -> None:
    """Background task to run uptime checks for all enabled models."""
    # Get all models with monitoring enabled
    stmt = select(Model).where(Model.enabled_for_monitoring == True)
    result = await db.execute(stmt)
    models = result.scalars().all()

    # Run checks for each model
    for model in models:
        uptime_check = await check_uptime(model)
        db.add(uptime_check)

    # Update last_run_at
    config = await get_or_create_default_config(db)
    config.last_run_at = datetime.now(datetime.now().astimezone().tzinfo)
    await db.commit()


@router.post("/run", response_model=MonitoringRunResponse)
async def trigger_monitoring_run(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> MonitoringRunResponse:
    """Trigger manual monitoring run.

    Runs uptime checks for all models with enabled_for_monitoring=True.
    Returns immediately; checks run in background.
    """
    run_id = str(uuid.uuid4())
    background_tasks.add_task(run_uptime_checks, db)

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
    limit: int = Query(100, ge=1, le=1000, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_db),
) -> UptimeHistoryResponse:
    """Get uptime check history with optional filters.

    Filters:
    - model_id: Filter by specific model
    - status: Filter by status (up, down, degraded)
    - since: Filter by created_at >= since
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

    # Get total count
    count_stmt = select(func.count(UptimeCheck.id))
    if filters:
        count_stmt = count_stmt.where(and_(*filters))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    # Get paginated results with model info
    stmt = (
        select(UptimeCheck)
        .outerjoin(Model)
        .order_by(desc(UptimeCheck.created_at))
        .limit(limit)
        .offset(offset)
    )

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
