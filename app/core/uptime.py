"""Lightweight uptime health checks for LLM models."""

import logging
from typing import TYPE_CHECKING

from app.core.litellm_client import LiteLLMClient
from app.core.metrics import MetricsCollector, extract_chunk_content
from app.models.monitoring import UptimeCheck

if TYPE_CHECKING:
    from app.models.model import Model

logger = logging.getLogger(__name__)


LITELLM_PROVIDER_PREFIXES: dict[str, str] = {
    "openai": "",
    "anthropic": "anthropic/",
    "azure": "azure/",
    "azure_openai": "azure/",
    "bedrock": "bedrock/",
    "aws_bedrock": "bedrock/",
    "vertex_ai": "vertex_ai/",
    "google_vertex": "vertex_ai/",
    "google_ai_studio": "gemini/",
    "cohere": "cohere/",
    "together_ai": "together_ai/",
    "groq": "groq/",
    "mistral": "mistral/",
    "deepseek": "deepseek/",
    "ollama": "ollama/",
    "lm_studio": "lm_studio/",
    "custom_openai_compatible": "openai/",
    "openrouter": "openrouter/",
    "xai": "xai/",
    "fireworks_ai": "fireworks_ai/",
}


def _get_litellm_model_name(model: "Model") -> str:
    """Build LiteLLM model name with correct provider prefix for LiteLLM routing."""
    provider_account = getattr(model, "provider_account", None)
    provider_type = getattr(provider_account, "provider_type", None) or "openai"
    prefix = LITELLM_PROVIDER_PREFIXES.get(provider_type, "")
    model_id = model.model_id
    if prefix and not model_id.startswith(prefix):
        return f"{prefix}{model_id}"
    return model_id


HEALTH_CHECK_PROMPT = "Count from 1 to 20, each number on a new line."


async def check_uptime(model: "Model") -> UptimeCheck:
    """
    Health check with TTFT and TPS metrics via streaming.
    Uses a consistent prompt that elicits ~25-30 tokens for meaningful metrics.

    Args:
        model: Model instance to check (must have provider_account loaded)

    Returns:
        UptimeCheck with status, latency_ms, ttft_ms, tps, output_tokens
    """
    provider_account = getattr(model, "provider_account", None)
    provider_type = getattr(provider_account, "provider_type", None)
    credentials = provider_account.credentials if provider_account else {}
    api_key = credentials.get("api_key")
    api_base = credentials.get("base_url")

    # LiteLLM with openai/ prefix requires an api_key (creates "Bearer {api_key}" header).
    # For local servers like LM Studio that don't require auth, use a dummy key
    # to prevent LiteLLM from sending "Bearer None" which causes streaming errors.
    if not api_key and api_base:
        api_key = "not-needed"

    extra_kwargs: dict = {}
    if provider_type == "aws_bedrock":
        extra_kwargs["aws_region_name"] = credentials.get("region", "us-east-1")

    client = LiteLLMClient()
    collector = MetricsCollector()
    collector.start()

    try:
        litellm_model = _get_litellm_model_name(model)
        logger.info(
            f"check_uptime: model={litellm_model}, api_key_set={bool(api_key)}, "
            f"api_base={api_base}, provider={provider_type}"
        )
        async for chunk in client.complete_stream(
            model=litellm_model,
            messages=[{"role": "user", "content": HEALTH_CHECK_PROMPT}],
            max_tokens=100,
            temperature=1,
            timeout=15,
            api_key=api_key,
            api_base=api_base,
            **extra_kwargs,
        ):
            content = extract_chunk_content(chunk)
            if content:
                collector.record_token(content)

        metrics = collector.finalize()

        return UptimeCheck(
            model_id=model.id,
            status="up",
            latency_ms=metrics["total_latency_ms"],
            ttft_ms=metrics["ttft_ms"],
            tps=metrics["tps"],
            output_tokens=metrics["output_tokens"],
        )
    except Exception as e:
        logger.error(f"check_uptime FAILED for {model.model_id}: {e}", exc_info=True)
        return UptimeCheck(
            model_id=model.id,
            status="down",
            error=str(e),
        )
