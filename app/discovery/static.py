"""Static/curated model source adapter.

For providers without model listing APIs (Anthropic, Mistral, Cohere),
returns curated model lists from built-in registry.
"""

import logging
from typing import TYPE_CHECKING

from app.discovery.base import ModelDescriptor

if TYPE_CHECKING:
    from app.models.provider import ProviderAccount

logger = logging.getLogger(__name__)

# Curated model registries by provider type
# Ref: Official pricing/model pages for each provider
ANTHROPIC_MODELS: list[dict] = [
    {"id": "claude-3-5-sonnet-20241022", "owned_by": "anthropic"},
    {"id": "claude-3-5-haiku-20241022", "owned_by": "anthropic"},
    {"id": "claude-3-opus-20240229", "owned_by": "anthropic"},
    {"id": "claude-3-sonnet-20240229", "owned_by": "anthropic"},
    {"id": "claude-3-haiku-20240307", "owned_by": "anthropic"},
]

MISTRAL_MODELS: list[dict] = [
    {"id": "mistral-large-latest", "owned_by": "mistral"},
    {"id": "mistral-medium-latest", "owned_by": "mistral"},
    {"id": "mistral-small-latest", "owned_by": "mistral"},
    {"id": "open-mistral-nemo", "owned_by": "mistral"},
    {"id": "codestral-latest", "owned_by": "mistral"},
]

GOOGLE_GEMINI_MODELS: list[dict] = [
    {"id": "gemini-2.0-flash-exp", "owned_by": "google"},
    {"id": "gemini-1.5-pro", "owned_by": "google"},
    {"id": "gemini-1.5-flash", "owned_by": "google"},
    {"id": "gemini-1.5-flash-8b", "owned_by": "google"},
]

# Registry mapping provider types to curated model lists
STATIC_REGISTRIES: dict[str, list[dict]] = {
    "anthropic": ANTHROPIC_MODELS,
    "mistral": MISTRAL_MODELS,
    "google_gemini": GOOGLE_GEMINI_MODELS,
}


class StaticModelSource:
    """Model source for providers without discovery API.

    Returns curated model lists from built-in registry.
    """

    def __init__(self, provider_type: str) -> None:
        """Initialize static model source.

        Args:
            provider_type: Provider type to get models for.
        """
        self.provider_type = provider_type

    async def list_models(self, account: "ProviderAccount") -> list[ModelDescriptor]:
        """Return curated model list from built-in registry.

        Args:
            account: Provider account (used for provider_type validation).

        Returns:
            List of curated ModelDescriptor instances.
            Returns empty list if provider not in registry.
        """
        provider = account.provider_type
        registry = STATIC_REGISTRIES.get(provider, [])

        if not registry:
            logger.warning(
                "No curated model registry for provider %s",
                provider,
            )
            return []

        models = [
            ModelDescriptor(
                id=model["id"],
                provider_type=provider,
                owned_by=model.get("owned_by"),
                created=None,
                metadata={},
            )
            for model in registry
        ]

        logger.info(
            "Returned %d curated models for %s (%s)",
            len(models),
            account.display_name,
            provider,
        )
        return models

    def supports_discovery(self) -> bool:
        """Return False - static sources don't support dynamic discovery."""
        return False


def get_source_for_provider(provider_type: str) -> "StaticModelSource | None":
    """Get appropriate model source for a provider type.

    Args:
        provider_type: Provider type string.

    Returns:
        StaticModelSource if provider uses static registry, None otherwise.
    """
    if not provider_type:
        return None
    if provider_type in STATIC_REGISTRIES:
        return StaticModelSource(provider_type)
    return None
