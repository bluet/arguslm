"""OpenAI-compatible model source adapter.

Supports OpenAI and other providers with /v1/models API:
- OpenAI
- OpenRouter
- Together AI
- LM Studio
- vLLM
- Custom OpenAI-compatible endpoints
"""

import logging
from typing import TYPE_CHECKING

import httpx

from arguslm.server.discovery.base import ModelDescriptor

if TYPE_CHECKING:
    from arguslm.server.models.provider import ProviderAccount

logger = logging.getLogger(__name__)

# Default endpoints per provider type
DEFAULT_ENDPOINTS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "together_ai": "https://api.together.xyz/v1",
    "groq": "https://api.groq.com/openai/v1",
    "lm_studio": "http://localhost:1234/v1",
    "custom_openai_compatible": "",  # Must be provided in credentials
}


class OpenAIModelSource:
    """Model source for OpenAI-compatible providers.

    Calls /v1/models endpoint to discover available models.
    Handles authentication via Bearer token.
    """

    def __init__(self, timeout: float = 30.0) -> None:
        """Initialize OpenAI model source.

        Args:
            timeout: HTTP request timeout in seconds.
        """
        self.timeout = timeout

    async def list_models(self, account: "ProviderAccount") -> list[ModelDescriptor]:
        """Fetch available models from /v1/models endpoint.

        Args:
            account: Provider account with api_key in credentials.

        Returns:
            List of ModelDescriptor for each available model.
            Returns empty list on error (error is logged).
        """
        try:
            credentials = account.credentials
            api_key = credentials.get("api_key", "")
            base_url = self._get_base_url(account.provider_type, credentials)

            if not base_url:
                logger.error(
                    "No base_url configured for provider %s",
                    account.provider_type,
                )
                return []

            # Build headers - only include Authorization if api_key is provided
            # (LM Studio and other local servers don't require auth)
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{base_url.rstrip('/')}/models",
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
                        owned_by=model_data.get("owned_by"),
                        created=model_data.get("created"),
                        metadata={
                            k: v
                            for k, v in model_data.items()
                            if k not in ("id", "owned_by", "created", "object")
                        },
                    )
                )

            logger.info(
                "Discovered %d models from %s (%s)",
                len(models),
                account.display_name,
                account.provider_type,
            )
            return models

        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error discovering models from %s: %s %s",
                account.display_name,
                e.response.status_code,
                e.response.text[:200] if e.response.text else "",
            )
            return []
        except httpx.RequestError as e:
            logger.error(
                "Request error discovering models from %s: %s",
                account.display_name,
                str(e),
            )
            return []
        except Exception as e:
            logger.exception(
                "Unexpected error discovering models from %s: %s",
                account.display_name,
                str(e),
            )
            return []

    def supports_discovery(self) -> bool:
        """Return True - OpenAI-compatible providers support /v1/models."""
        return True

    def _get_base_url(self, provider_type: str, credentials: dict) -> str:
        """Get base URL for the provider.

        Args:
            provider_type: Type of provider.
            credentials: Account credentials dict.

        Returns:
            Base URL for API calls.
        """
        # Check credentials first for custom base_url
        if "base_url" in credentials:
            return credentials["base_url"]

        # Fall back to default endpoints
        return DEFAULT_ENDPOINTS.get(provider_type, "")
