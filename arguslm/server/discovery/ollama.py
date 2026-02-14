"""Ollama model source adapter.

Discovers locally installed models via Ollama's /api/tags endpoint.
Ref: https://docs.ollama.com/api/tags
"""

import logging
from typing import TYPE_CHECKING

import httpx

from arguslm.server.discovery.base import ModelDescriptor

if TYPE_CHECKING:
    from arguslm.server.models.provider import ProviderAccount

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_URL = "http://localhost:11434"


class OllamaModelSource:
    """Model source for Ollama local server.

    Calls /api/tags endpoint to discover installed models.
    No authentication required for local Ollama instances.
    """

    def __init__(self, timeout: float = 10.0) -> None:
        """Initialize Ollama model source.

        Args:
            timeout: HTTP request timeout in seconds.
        """
        self.timeout = timeout

    async def list_models(self, account: "ProviderAccount") -> list[ModelDescriptor]:
        """Fetch installed models from /api/tags endpoint.

        Args:
            account: Provider account (credentials may contain base_url).

        Returns:
            List of ModelDescriptor for each installed model.
            Returns empty list on error (error is logged).
        """
        credentials = account.credentials
        base_url = credentials.get("base_url", DEFAULT_OLLAMA_URL)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{base_url.rstrip('/')}/api/tags")
                response.raise_for_status()
                data = response.json()

            models: list[ModelDescriptor] = []
            for model_data in data.get("models", []):
                # Ollama model names follow format: name:tag (e.g., llama3:8b)
                model_name = model_data.get("name", "")
                details = model_data.get("details", {})

                models.append(
                    ModelDescriptor(
                        id=model_name,
                        provider_type="ollama",
                        owned_by=None,  # Ollama doesn't track ownership
                        created=None,  # modified_at is available but different semantic
                        metadata={
                            "size": model_data.get("size"),
                            "digest": model_data.get("digest"),
                            "modified_at": model_data.get("modified_at"),
                            "format": details.get("format"),
                            "family": details.get("family"),
                            "families": details.get("families"),
                            "parameter_size": details.get("parameter_size"),
                            "quantization_level": details.get("quantization_level"),
                        },
                    )
                )

            logger.info(
                "Discovered %d models from Ollama at %s",
                len(models),
                base_url,
            )
            return models

        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error discovering Ollama models: %s %s",
                e.response.status_code,
                e.response.text[:200] if e.response.text else "",
            )
            return []
        except httpx.ConnectError:
            logger.warning(
                "Cannot connect to Ollama at %s - server may not be running",
                credentials.get("base_url", DEFAULT_OLLAMA_URL),
            )
            return []
        except httpx.RequestError as e:
            logger.error("Request error discovering Ollama models: %s", str(e))
            return []
        except Exception as e:
            logger.exception("Unexpected error discovering Ollama models: %s", str(e))
            return []

    def supports_discovery(self) -> bool:
        """Return True - Ollama supports /api/tags for model listing."""
        return True
