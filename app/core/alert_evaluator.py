"""Alert evaluation service for uptime monitoring.

Evaluates alert rules against uptime check results and creates
alerts for matching conditions. Handles deduplication to avoid
creating duplicate alerts for the same ongoing incident.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertRule
from app.models.monitoring import UptimeCheck

if TYPE_CHECKING:
    from app.models.model import Model


async def evaluate_alerts(
    db: AsyncSession,
    uptime_checks: list[UptimeCheck],
) -> list[Alert]:
    """Evaluate alert rules against uptime check results.

    Processes all enabled rules and creates alerts for matching conditions.
    Handles deduplication: won't create duplicate alerts for same ongoing incident.

    Args:
        db: Database session for querying rules and creating alerts.
        uptime_checks: List of uptime check results to evaluate.

    Returns:
        List of newly created Alert instances.
    """
    # Get all enabled rules
    stmt = select(AlertRule).where(AlertRule.enabled == True)
    result = await db.execute(stmt)
    rules = result.scalars().all()

    new_alerts: list[Alert] = []

    for rule in rules:
        alerts = await _evaluate_rule(db, rule, uptime_checks)
        new_alerts.extend(alerts)

    return new_alerts


async def _evaluate_rule(
    db: AsyncSession,
    rule: AlertRule,
    uptime_checks: list[UptimeCheck],
) -> list[Alert]:
    """Evaluate a single rule against uptime checks.

    Args:
        db: Database session.
        rule: Alert rule to evaluate.
        uptime_checks: List of uptime check results.

    Returns:
        List of newly created alerts for this rule.
    """
    if rule.rule_type == "any_model_down":
        return await _evaluate_any_model_down(db, rule, uptime_checks)
    elif rule.rule_type == "specific_model_down":
        return await _evaluate_specific_model_down(db, rule, uptime_checks)
    elif rule.rule_type == "model_unavailable_everywhere":
        return await _evaluate_model_unavailable_everywhere(db, rule, uptime_checks)
    else:
        # Unknown rule type, skip
        return []


async def _evaluate_any_model_down(
    db: AsyncSession,
    rule: AlertRule,
    uptime_checks: list[UptimeCheck],
) -> list[Alert]:
    """Evaluate any_model_down rule: alert when any monitored model goes down.

    Creates one alert per model that is down, with deduplication.

    Args:
        db: Database session.
        rule: The any_model_down rule.
        uptime_checks: List of uptime check results.

    Returns:
        List of newly created alerts.
    """
    new_alerts: list[Alert] = []

    # Find all models that are down
    down_checks = [c for c in uptime_checks if c.status == "down"]

    for check in down_checks:
        # Check for existing unacknowledged alert for this model + rule
        if await _has_active_incident(db, rule.id, check.model_id):
            continue

        # Create new alert
        alert = Alert(
            rule_id=rule.id,
            model_id=check.model_id,
            message=f"Model is down: {check.error or 'Health check failed'}",
            acknowledged=False,
        )
        db.add(alert)
        new_alerts.append(alert)

    return new_alerts


async def _evaluate_specific_model_down(
    db: AsyncSession,
    rule: AlertRule,
    uptime_checks: list[UptimeCheck],
) -> list[Alert]:
    """Evaluate specific_model_down rule: alert when a specific model goes down.

    Args:
        db: Database session.
        rule: The specific_model_down rule (has target_model_id).
        uptime_checks: List of uptime check results.

    Returns:
        List of newly created alerts (0 or 1).
    """
    if not rule.target_model_id:
        return []

    # Find check for the target model
    target_check = next(
        (c for c in uptime_checks if c.model_id == rule.target_model_id),
        None,
    )

    if not target_check or target_check.status != "down":
        return []

    # Check for existing unacknowledged alert
    if await _has_active_incident(db, rule.id, target_check.model_id):
        return []

    # Create alert
    alert = Alert(
        rule_id=rule.id,
        model_id=target_check.model_id,
        message=f"Monitored model is down: {target_check.error or 'Health check failed'}",
        acknowledged=False,
    )
    db.add(alert)
    return [alert]


async def _evaluate_model_unavailable_everywhere(
    db: AsyncSession,
    rule: AlertRule,
    uptime_checks: list[UptimeCheck],
) -> list[Alert]:
    """Evaluate model_unavailable_everywhere rule.

    Alert when a model (by name pattern) is down across all providers.
    Requires loading model info to match by model_id string.

    Args:
        db: Database session.
        rule: The model_unavailable_everywhere rule (has target_model_name).
        uptime_checks: List of uptime check results.

    Returns:
        List of newly created alerts (0 or 1).
    """
    if not rule.target_model_name:
        return []

    # Import here to avoid circular imports
    from app.models.model import Model

    # Get all models matching the target name pattern
    stmt = select(Model).where(Model.model_id.ilike(f"%{rule.target_model_name}%"))
    result = await db.execute(stmt)
    matching_models = result.scalars().all()

    if not matching_models:
        return []

    # Get model IDs
    matching_model_ids = {m.id for m in matching_models}

    # Find checks for matching models
    relevant_checks = [c for c in uptime_checks if c.model_id in matching_model_ids]

    if not relevant_checks:
        return []

    # Check if ALL are down
    all_down = all(c.status == "down" for c in relevant_checks)

    if not all_down:
        return []

    # Check for existing unacknowledged alert for this rule (no specific model_id)
    if await _has_active_incident(db, rule.id, None):
        return []

    # Create alert
    alert = Alert(
        rule_id=rule.id,
        model_id=None,  # Not tied to specific model
        message=f"Model '{rule.target_model_name}' is unavailable across all {len(relevant_checks)} provider(s)",
        acknowledged=False,
    )
    db.add(alert)
    return [alert]


async def _has_active_incident(
    db: AsyncSession,
    rule_id: uuid.UUID,
    model_id: uuid.UUID | None,
) -> bool:
    """Check if there's an active (unacknowledged) incident for this rule/model.

    Used for deduplication - prevents creating new alerts while an incident
    is still ongoing (unacknowledged).

    Args:
        db: Database session.
        rule_id: Alert rule ID.
        model_id: Model ID (optional, None for cross-model rules).

    Returns:
        True if there's an active incident, False otherwise.
    """
    conditions = [
        Alert.rule_id == rule_id,
        Alert.acknowledged == False,
    ]

    if model_id is not None:
        conditions.append(Alert.model_id == model_id)
    else:
        conditions.append(Alert.model_id.is_(None))

    stmt = select(Alert).where(and_(*conditions)).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def check_recoveries(
    db: AsyncSession,
    uptime_checks: list[UptimeCheck],
) -> list[Alert]:
    """Check for model recoveries and optionally create recovery alerts.

    Note: This is informational. Per requirements, we don't auto-acknowledge
    alerts. Users must manually acknowledge.

    This function could be extended to create "recovery" type alerts
    or update existing alerts with recovery status.

    Args:
        db: Database session.
        uptime_checks: List of uptime check results.

    Returns:
        List of recovery-related updates (currently empty, for future use).
    """
    # Per requirements: Do not auto-acknowledge alerts
    # This function is a placeholder for future recovery tracking
    # Could be used to create "recovery" type alerts if needed
    return []
