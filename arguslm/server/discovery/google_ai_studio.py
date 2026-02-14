"""Google AI Studio (Gemini API) model source adapter.

Discovers models via Google's /v1beta/models API endpoint.
Ref: https://ai.google.dev/api/models
"""

import logging
from typing import TYPE_CHECKING

import httpx

from arguslm.server.discovery.base import ModelDescriptor

if TYPE_CHECKING:
    from arguslm.server.models.provider import ProviderAccount

logger = logging.getLogger(__name__)

GOOGLE_AI_STUDIO_API_BASE = "https://generativelanguage.googleapis.com"


class GoogleAIStudioModelSource:
    """Model source for Google AI Studio (Gemini API).

    Calls /v1beta/models endpoint to discover available Gemini models.
    Uses x-goog-api-key header for authentication.
    """

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout

    async def list_models(self, account: "ProviderAccount") -> list[ModelDescriptor]:
        """Fetch available models from Google AI Studio /v1beta/models endpoint."""
        try:
            credentials = account.credentials
            api_key = credentials.get("api_key", "")

            if not api_key:
                logger.error("No API key configured for Google AI Studio provider")
                return []

            headers = {
                "x-goog-api-key": api_key,
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{GOOGLE_AI_STUDIO_API_BASE}/v1beta/models",
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()

            models: list[ModelDescriptor] = []
            for model_data in data.get("models", []):
                # Model name format: "models/gemini-1.5-pro" -> extract "gemini-1.5-pro"
                model_name = model_data.get("name", "")
                model_id = model_name.replace("models/", "") if model_name else ""

                if not model_id:
                    continue

                models.append(
                    ModelDescriptor(
                        id=model_id,
                        provider_type=account.provider_type,
                        owned_by="google",
                        created=None,
                        metadata={
                            "display_name": model_data.get("displayName"),
                            "description": model_data.get("description"),
                            "input_token_limit": model_data.get("inputTokenLimit"),
                            "output_token_limit": model_data.get("outputTokenLimit"),
                            "supported_generation_methods": model_data.get(
                                "supportedGenerationMethods", []
                            ),
                        },
                    )
                )

            logger.info(
                "Discovered %d models from %s (google_ai_studio)",
                len(models),
                account.display_name,
            )
            return models

        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error discovering Google AI Studio models: %s %s",
                e.response.status_code,
                e.response.text[:200] if e.response.text else "",
            )
            return []
        except httpx.RequestError as e:
            logger.error("Request error discovering Google AI Studio models: %s", str(e))
            return []
        except Exception as e:
            logger.exception("Unexpected error discovering Google AI Studio models: %s", str(e))
            return []

    def supports_discovery(self) -> bool:
        return True
