"""Alert Rules API endpoints."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.alert import (
    AlertListResponse,
    AlertResponse,
    AlertRuleCreate,
    AlertRuleResponse,
    AlertRuleUpdate,
    RecentAlertsResponse,
    UnreadCountResponse,
)
from app.db.init import get_db
from app.models.alert import Alert, AlertRule

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.get("/rules", response_model=list[AlertRuleResponse])
async def list_alert_rules(db: AsyncSession = Depends(get_db)) -> list[AlertRuleResponse]:
    """List all alert rules.

    Returns:
        List of alert rules.
    """
    stmt = select(AlertRule).order_by(AlertRule.created_at.desc())
    result = await db.execute(stmt)
    rules = result.scalars().all()
    return [AlertRuleResponse.model_validate(rule) for rule in rules]


@router.post("/rules", response_model=AlertRuleResponse, status_code=201)
async def create_alert_rule(
    rule_data: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
) -> AlertRuleResponse:
    """Create a new alert rule.

    Validates rule type requirements:
    - specific_model_down: requires target_model_id
    - model_unavailable_everywhere: requires target_model_name

    Args:
        rule_data: Alert rule creation data.
        db: Database session.

    Returns:
        Created alert rule.

    Raises:
        HTTPException: 400 if validation fails.
    """
    # Validate rule type requirements
    if rule_data.rule_type == "specific_model_down" and not rule_data.target_model_id:
        raise HTTPException(
            status_code=400,
            detail="specific_model_down rule requires target_model_id",
        )

    if rule_data.rule_type == "model_unavailable_everywhere" and not rule_data.target_model_name:
        raise HTTPException(
            status_code=400,
            detail="model_unavailable_everywhere rule requires target_model_name",
        )

    # Create new rule
    new_rule = AlertRule(
        name=rule_data.name,
        rule_type=rule_data.rule_type,
        target_model_id=rule_data.target_model_id,
        target_model_name=rule_data.target_model_name,
        enabled=rule_data.enabled,
        notify_in_app=rule_data.notify_in_app,
    )

    db.add(new_rule)
    await db.flush()
    await db.refresh(new_rule)

    return AlertRuleResponse.model_validate(new_rule)


@router.patch("/rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: UUID,
    rule_data: AlertRuleUpdate,
    db: AsyncSession = Depends(get_db),
) -> AlertRuleResponse:
    """Update an alert rule.

    Args:
        rule_id: ID of the rule to update.
        rule_data: Update data.
        db: Database session.

    Returns:
        Updated alert rule.

    Raises:
        HTTPException: 404 if rule not found.
    """
    stmt = select(AlertRule).where(AlertRule.id == rule_id)
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")

    # Update fields if provided
    if rule_data.name is not None:
        rule.name = rule_data.name
    if rule_data.enabled is not None:
        rule.enabled = rule_data.enabled
    if rule_data.notify_in_app is not None:
        rule.notify_in_app = rule_data.notify_in_app

    await db.flush()
    await db.refresh(rule)

    return AlertRuleResponse.model_validate(rule)


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_alert_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an alert rule.

    Args:
        rule_id: ID of the rule to delete.
        db: Database session.

    Raises:
        HTTPException: 404 if rule not found.
    """
    stmt = select(AlertRule).where(AlertRule.id == rule_id)
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")

    await db.delete(rule)


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    rule_id: Optional[UUID] = Query(None, description="Filter by rule ID"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledgment status"),
    since: Optional[datetime] = Query(None, description="Filter alerts since this datetime"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_db),
) -> AlertListResponse:
    """List triggered alerts with optional filters.

    Args:
        rule_id: Filter by rule ID.
        acknowledged: Filter by acknowledgment status.
        since: Filter alerts created since this datetime.
        limit: Maximum number of results (default 50, max 500).
        offset: Number of results to skip (default 0).
        db: Database session.

    Returns:
        Paginated list of alerts with unacknowledged count.
    """
    # Build filter conditions
    conditions = []

    if rule_id is not None:
        conditions.append(Alert.rule_id == rule_id)

    if acknowledged is not None:
        conditions.append(Alert.acknowledged == acknowledged)

    if since is not None:
        conditions.append(Alert.created_at >= since)

    # Get total unacknowledged count
    unack_stmt = select(Alert).where(Alert.acknowledged == False)
    unack_result = await db.execute(unack_stmt)
    unacknowledged_count = len(unack_result.scalars().all())

    # Get paginated results
    stmt = select(Alert)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(desc(Alert.created_at)).limit(limit).offset(offset)

    result = await db.execute(stmt)
    alerts = result.scalars().all()

    return AlertListResponse(
        items=[AlertResponse.model_validate(alert) for alert in alerts],
        unacknowledged_count=unacknowledged_count,
        limit=limit,
        offset=offset,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(db: AsyncSession = Depends(get_db)) -> UnreadCountResponse:
    """Get count of unacknowledged alerts.

    For notification badge display in the UI.

    Args:
        db: Database session.

    Returns:
        Count of unacknowledged alerts.
    """
    stmt = select(Alert).where(Alert.acknowledged == False)
    result = await db.execute(stmt)
    count = len(result.scalars().all())
    return UnreadCountResponse(count=count)


@router.get("/recent", response_model=RecentAlertsResponse)
async def get_recent_alerts(
    limit: int = Query(10, ge=1, le=50, description="Maximum alerts to return"),
    db: AsyncSession = Depends(get_db),
) -> RecentAlertsResponse:
    """Get recent alerts for notification dropdown.

    Returns the most recent alerts (both acknowledged and not) for display
    in the notification dropdown, plus total unread count for badge.

    Args:
        limit: Maximum number of alerts to return (default 10, max 50).
        db: Database session.

    Returns:
        Recent alerts list and total unread count.
    """
    # Get recent alerts
    stmt = select(Alert).order_by(desc(Alert.created_at)).limit(limit)
    result = await db.execute(stmt)
    alerts = result.scalars().all()

    # Get total unread count
    unread_stmt = select(Alert).where(Alert.acknowledged == False)
    unread_result = await db.execute(unread_stmt)
    total_unread = len(unread_result.scalars().all())

    return RecentAlertsResponse(
        items=[AlertResponse.model_validate(alert) for alert in alerts],
        total_unread=total_unread,
    )


@router.patch("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AlertResponse:
    """Acknowledge an alert.

    Args:
        alert_id: ID of the alert to acknowledge.
        db: Database session.

    Returns:
        Updated alert.

    Raises:
        HTTPException: 404 if alert not found.
    """
    stmt = select(Alert).where(Alert.id == alert_id)
    result = await db.execute(stmt)
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.acknowledged = True
    await db.flush()
    await db.refresh(alert)

    return AlertResponse.model_validate(alert)
