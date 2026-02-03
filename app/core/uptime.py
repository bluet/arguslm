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
        model: Model instance to check (must have provider_account loaded)

    Returns:
        UptimeCheck with status (up/down), latency_ms, and optional error message
    """
    provider_account = getattr(model, "provider_account", None)
    credentials = provider_account.credentials if provider_account else {}
    api_key = credentials.get("api_key")
    api_base = credentials.get("base_url")

    start = time.perf_counter()
    try:
        response = await complete(
            model=model.model_id,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=1,
            timeout=10,
            api_key=api_key,
            api_base=api_base,
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
