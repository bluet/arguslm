"""Lightweight uptime health checks for LLM models."""

import time
from typing import TYPE_CHECKING

from app.core.litellm_client import complete
from app.models.monitoring import UptimeCheck

if TYPE_CHECKING:
    from app.models.model import Model


LITELLM_PROVIDER_PREFIXES: dict[str, str] = {
    "openai": "",
    "anthropic": "anthropic/",
    "azure": "azure/",
    "bedrock": "bedrock/",
    "vertex_ai": "vertex_ai/",
    "cohere": "cohere/",
    "together_ai": "together_ai/",
    "groq": "groq/",
    "mistral": "mistral/",
    "deepseek": "deepseek/",
    "ollama": "ollama/",
    "lm_studio": "openai/",
    "custom_openai_compatible": "openai/",
}


def _get_litellm_model_name(model: "Model") -> str:
    provider_account = getattr(model, "provider_account", None)
    provider_type = getattr(provider_account, "provider_type", None) or "openai"
    prefix = LITELLM_PROVIDER_PREFIXES.get(provider_type, "")
    model_id = model.model_id
    if prefix and not model_id.startswith(prefix):
        return f"{prefix}{model_id}"
    return model_id


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
        litellm_model = _get_litellm_model_name(model)
        response = await complete(
            model=litellm_model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=10,
            temperature=1,  # gpt-5 models only support temperature=1
            timeout=10,
            api_key=api_key or "sk-not-needed",
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
