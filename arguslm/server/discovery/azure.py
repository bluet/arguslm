"""Azure OpenAI model source adapter.

Discovers available models from Azure OpenAI's /openai/models endpoint.
Note: This returns available base models, not deployments. Users still need
to manually specify their deployment names when adding models for monitoring.
"""

import logging
from typing import TYPE_CHECKING

import httpx

from arguslm.server.discovery.base import ModelDescriptor

if TYPE_CHECKING:
    from arguslm.server.models.provider import ProviderAccount

logger = logging.getLogger(__name__)


class AzureOpenAIModelSource:
    """Model source for Azure OpenAI.

    Calls /openai/models endpoint to discover available models.
    Uses api-key header for authentication (Azure-specific).

    Note: Azure requires deployment names for actual API calls.
    This discovery returns available base models that can be deployed.
    Users should add models with their specific deployment names.
    """

    DEFAULT_API_VERSION = "2024-10-21"

    def __init__(self, timeout: float = 30.0) -> None:
        """Initialize Azure OpenAI model source.

        Args:
            timeout: HTTP request timeout in seconds.
        """
        self.timeout = timeout

    async def list_models(self, account: "ProviderAccount") -> list[ModelDescriptor]:
        """Fetch available models from Azure OpenAI /openai/models endpoint.

        Args:
            account: Provider account with api_key and base_url in credentials.

        Returns:
            List of ModelDescriptor for each available model.
            Returns empty list on error (error is logged).
        """
        try:
            credentials = account.credentials
            api_key = credentials.get("api_key", "")
            base_url = credentials.get("base_url", "")
            api_version = credentials.get("api_version", self.DEFAULT_API_VERSION)

            if not base_url:
                logger.error(
                    "No base_url configured for Azure OpenAI provider %s",
                    account.display_name,
                )
                return []

            if not api_key:
                logger.error(
                    "No api_key configured for Azure OpenAI provider %s",
                    account.display_name,
                )
                return []

            # Azure uses api-key header, not Bearer token
            headers = {"api-key": api_key}

            models_url = f"{base_url.rstrip('/')}/openai/models"
            params = {"api-version": api_version}

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    models_url,
                    headers=headers,
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

            models: list[ModelDescriptor] = []
            for model_data in data.get("data", []):
                model_id = model_data.get("id", "")
                capabilities = model_data.get("capabilities", {})
                if not capabilities.get("chat_completion", True):
                    continue

                models.append(
                    ModelDescriptor(
                        id=model_id,
                        provider_type=account.provider_type,
                        owned_by=model_data.get("owned_by", "azure"),
                        created=model_data.get("created_at"),
                        metadata={
                            "status": model_data.get("status"),
                            "capabilities": capabilities,
                            "lifecycle_status": model_data.get("lifecycle_status"),
                            "is_base_model": True,
                            "note": "Use your deployment name when adding for monitoring",
                        },
                    )
                )

            logger.info(
                "Discovered %d models from Azure OpenAI %s",
                len(models),
                account.display_name,
            )
            return models

        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error discovering models from Azure OpenAI %s: %s %s",
                account.display_name,
                e.response.status_code,
                e.response.text[:200] if e.response.text else "",
            )
            return []
        except httpx.RequestError as e:
            logger.error(
                "Request error discovering models from Azure OpenAI %s: %s",
                account.display_name,
                str(e),
            )
            return []
        except Exception as e:
            logger.exception(
                "Unexpected error discovering models from Azure OpenAI %s: %s",
                account.display_name,
                str(e),
            )
            return []

    def supports_discovery(self) -> bool:
        """Return True - Azure OpenAI supports /openai/models endpoint."""
        return True
