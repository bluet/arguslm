"""Lightweight uptime health checks for LLM models."""

import time
from typing import TYPE_CHECKING

from app.core.litellm_client import complete
from app.models.monitoring import UptimeCheck

if TYPE_CHECKING:
    from app.models.model import Model


async def check_uptime(model: "Model") -> UptimeCheck:
    """
    Lightweight health check - NOT a full benchmark.
    Uses minimal tokens to verify endpoint is responding.

    Args:
        model: Model instance to check

    Returns:
        UptimeCheck with status (up/down), latency_ms, and optional error message
    """
    start = time.perf_counter()
    try:
        response = await complete(
            model=model.model_id,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=1,
            timeout=10,
        )
        latency = (time.perf_counter() - start) * 1000
        return UptimeCheck(
            model_id=model.id,
            status="up",
            latency_ms=latency,
        )
    except Exception as e:
        return UptimeCheck(
            model_id=model.id,
            status="down",
            error=str(e),
        )
