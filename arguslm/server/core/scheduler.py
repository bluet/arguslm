"""Background scheduler for monitoring tasks.

Uses APScheduler's AsyncIOScheduler to run uptime checks at configured intervals.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from arguslm.server.db.init import AsyncSessionLocal
from arguslm.server.models.monitoring import MonitoringConfig

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()

# Job ID for monitoring task
MONITORING_JOB_ID = "uptime_monitoring"


async def _get_monitoring_config() -> tuple[bool, int]:
    """Get current monitoring configuration from database.

    Returns:
        Tuple of (enabled, interval_minutes).
    """
    async with AsyncSessionLocal() as db:
        stmt = select(MonitoringConfig).limit(1)
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()

        if config is None:
            return True, 15  # Default values

        return config.enabled, config.interval_minutes


async def _run_monitoring_job() -> None:
    """Wrapper to run the uptime checks task.

    Imports run_uptime_checks_task here to avoid circular imports.
    """
    from arguslm.server.api.monitoring import run_uptime_checks_task

    logger.info("Scheduler: Running scheduled uptime checks")
    await run_uptime_checks_task()


async def configure_scheduler(interval_minutes: int, enabled: bool) -> None:
    """Reconfigure scheduler job with new settings.

    Removes existing job and adds new one if enabled.

    Args:
        interval_minutes: Interval between uptime checks in minutes.
        enabled: Whether monitoring is enabled.
    """
    existing_job = scheduler.get_job(MONITORING_JOB_ID)
    if existing_job:
        scheduler.remove_job(MONITORING_JOB_ID)
        logger.info("Scheduler: Removed existing monitoring job")

    if enabled:
        scheduler.add_job(
            _run_monitoring_job,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id=MONITORING_JOB_ID,
            name="Uptime Monitoring",
            replace_existing=True,
        )
        logger.info(f"Scheduler: Added monitoring job with {interval_minutes} minute interval")
    else:
        logger.info("Scheduler: Monitoring disabled, no job scheduled")


async def start_scheduler() -> None:
    """Initialize and start the scheduler.

    Reads configuration from database and sets up initial job.
    """
    enabled, interval_minutes = await _get_monitoring_config()
    await configure_scheduler(interval_minutes, enabled)
    scheduler.start()
    logger.info("Scheduler: Started")


async def stop_scheduler() -> None:
    """Gracefully shutdown scheduler."""
    scheduler.shutdown(wait=True)
    logger.info("Scheduler: Stopped")
