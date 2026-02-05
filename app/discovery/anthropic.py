"""Anthropic model source adapter.

Discovers models via Anthropic's /v1/models API endpoint.
Ref: https://docs.anthropic.com/en/api/models-list
"""

import logging
from typing import TYPE_CHECKING

import httpx

from app.discovery.base import ModelDescriptor

if TYPE_CHECKING:
    from app.models.provider import ProviderAccount

logger = logging.getLogger(__name__)

ANTHROPIC_API_BASE = "https://api.anthropic.com"


class AnthropicModelSource:
    """Model source for Anthropic API.

    Calls /v1/models endpoint to discover available Claude models.
    Uses x-api-key header for authentication.
    """

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout

    async def list_models(self, account: "ProviderAccount") -> list[ModelDescriptor]:
        """Fetch available models from Anthropic /v1/models endpoint."""
        try:
            credentials = account.credentials
            api_key = credentials.get("api_key", "")

            if not api_key:
                logger.error("No API key configured for Anthropic provider")
                return []

            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{ANTHROPIC_API_BASE}/v1/models",
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()

            models: list[ModelDescriptor] = []
            for model_data in data.get("data", []):
                models.append(
                    ModelDescriptor(
                        id=model_data.get("id", ""),
                        provider_type=account.provider_type,
                        owned_by="anthropic",
                        created=model_data.get("created_at"),
                        metadata={
                            k: v
                            for k, v in model_data.items()
                            if k not in ("id", "created_at", "type")
                        },
                    )
                )

            logger.info(
                "Discovered %d models from %s (anthropic)",
                len(models),
                account.display_name,
            )
            return models

        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error discovering Anthropic models: %s %s",
                e.response.status_code,
                e.response.text[:200] if e.response.text else "",
            )
            return []
        except httpx.RequestError as e:
            logger.error("Request error discovering Anthropic models: %s", str(e))
            return []
        except Exception as e:
            logger.exception("Unexpected error discovering Anthropic models: %s", str(e))
            return []

    def supports_discovery(self) -> bool:
        return True
