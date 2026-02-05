"""Lightweight uptime health checks for LLM models."""

import logging
from typing import TYPE_CHECKING

from app.core.litellm_client import LiteLLMClient
from app.core.metrics import MetricsCollector, extract_chunk_content
from app.core.prompt_packs import get_prompt
from app.core.providers import get_litellm_model_name
from app.models.monitoring import UptimeCheck

if TYPE_CHECKING:
    from app.models.model import Model

logger = logging.getLogger(__name__)


def _get_litellm_model_name(model: "Model") -> str:
    provider_account = getattr(model, "provider_account", None)
    provider_type = getattr(provider_account, "provider_type", None) or "openai"
    return get_litellm_model_name(provider_type, model.model_id)


async def check_uptime(model: "Model", prompt_pack: str = "health_check") -> UptimeCheck:
    """Run health check with TTFT and TPS metrics via streaming."""
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
            messages=[{"role": "user", "content": get_prompt(prompt_pack)}],
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
            tps=metrics["tps_excluding_ttft"],
            output_tokens=metrics["output_tokens"],
        )
    except Exception as e:
        logger.error(f"check_uptime FAILED for {model.model_id}: {e}", exc_info=True)
        return UptimeCheck(
            model_id=model.id,
            status="down",
            error=str(e),
        )
