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
# Updated: 2025-02 from https://platform.claude.com/docs/en/api
ANTHROPIC_MODELS: list[dict] = [
    # Claude 4.5 series (latest flagship)
    {"id": "claude-opus-4-5-20251101", "owned_by": "anthropic"},
    {"id": "claude-sonnet-4-5-20250929", "owned_by": "anthropic"},
    {"id": "claude-haiku-4-5-20251001", "owned_by": "anthropic"},
    # Claude 4.5 aliases (point to latest dated version)
    {"id": "claude-opus-4-5", "owned_by": "anthropic"},
    {"id": "claude-sonnet-4-5", "owned_by": "anthropic"},
    {"id": "claude-haiku-4-5", "owned_by": "anthropic"},
    # Claude 4.1 series
    {"id": "claude-opus-4-1-20250805", "owned_by": "anthropic"},
    # Claude 4.0 series
    {"id": "claude-opus-4-0", "owned_by": "anthropic"},
    {"id": "claude-opus-4-20250514", "owned_by": "anthropic"},
    {"id": "claude-sonnet-4-0", "owned_by": "anthropic"},
    {"id": "claude-sonnet-4-20250514", "owned_by": "anthropic"},
    # Claude 3.7 series (extended thinking)
    {"id": "claude-3-7-sonnet-20250219", "owned_by": "anthropic"},
    {"id": "claude-3-7-sonnet-latest", "owned_by": "anthropic"},
    # Claude 3.5 series
    {"id": "claude-3-5-sonnet-20241022", "owned_by": "anthropic"},
    {"id": "claude-3-5-haiku-20241022", "owned_by": "anthropic"},
    {"id": "claude-3-5-haiku-latest", "owned_by": "anthropic"},
    # Claude 3 series (legacy)
    {"id": "claude-3-opus-20240229", "owned_by": "anthropic"},
    {"id": "claude-3-opus-latest", "owned_by": "anthropic"},
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

GOOGLE_AI_STUDIO_MODELS: list[dict] = [
    {"id": "gemini-2.0-flash-exp", "owned_by": "google"},
    {"id": "gemini-1.5-pro", "owned_by": "google"},
    {"id": "gemini-1.5-flash", "owned_by": "google"},
    {"id": "gemini-1.5-flash-8b", "owned_by": "google"},
]

# Google Vertex AI curated model registry
# Ref: https://cloud.google.com/vertex-ai/generative-ai/docs/learn/models
GOOGLE_VERTEX_MODELS: list[dict] = [
    {"id": "gemini-2.0-flash-001", "owned_by": "google"},
    {"id": "gemini-2.0-pro-exp-02-05", "owned_by": "google"},
    {"id": "gemini-1.5-pro-002", "owned_by": "google"},
    {"id": "gemini-1.5-flash-002", "owned_by": "google"},
    {"id": "gemini-1.0-pro-002", "owned_by": "google"},
    {"id": "claude-3-5-sonnet-v2@20241022", "owned_by": "anthropic"},
    {"id": "claude-3-5-haiku@20241022", "owned_by": "anthropic"},
    {"id": "claude-3-opus@20240229", "owned_by": "anthropic"},
    {"id": "claude-3-haiku@20240307", "owned_by": "anthropic"},
    {"id": "llama-3.2-90b-vision-instruct-maas", "owned_by": "meta"},
    {"id": "llama-3.1-405b-instruct-maas", "owned_by": "meta"},
    {"id": "mistral-large@2407", "owned_by": "mistral"},
    {"id": "mistral-nemo@2407", "owned_by": "mistral"},
]

# AWS Bedrock curated model registry
# Ref: https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html
# Updated: 2025-02
AWS_BEDROCK_MODELS: list[dict] = [
    # Claude 4.x series
    {"id": "anthropic.claude-opus-4-5-20251101-v1:0", "owned_by": "anthropic"},
    {"id": "anthropic.claude-sonnet-4-5-20250929-v1:0", "owned_by": "anthropic"},
    {"id": "anthropic.claude-haiku-4-5-20251001-v1:0", "owned_by": "anthropic"},
    {"id": "anthropic.claude-opus-4-1-20250805-v1:0", "owned_by": "anthropic"},
    {"id": "anthropic.claude-sonnet-4-20250514-v1:0", "owned_by": "anthropic"},
    # Claude 3.x series
    {"id": "anthropic.claude-3-5-haiku-20241022-v1:0", "owned_by": "anthropic"},
    {"id": "anthropic.claude-3-haiku-20240307-v1:0", "owned_by": "anthropic"},
    # Meta Llama 4 models
    {"id": "meta.llama4-maverick-17b-instruct-v1:0", "owned_by": "meta"},
    {"id": "meta.llama4-scout-17b-instruct-v1:0", "owned_by": "meta"},
    # Meta Llama 3.x models
    {"id": "meta.llama3-3-70b-instruct-v1:0", "owned_by": "meta"},
    {"id": "meta.llama3-2-90b-instruct-v1:0", "owned_by": "meta"},
    {"id": "meta.llama3-2-11b-instruct-v1:0", "owned_by": "meta"},
    {"id": "meta.llama3-2-3b-instruct-v1:0", "owned_by": "meta"},
    {"id": "meta.llama3-2-1b-instruct-v1:0", "owned_by": "meta"},
    {"id": "meta.llama3-1-405b-instruct-v1:0", "owned_by": "meta"},
    {"id": "meta.llama3-1-70b-instruct-v1:0", "owned_by": "meta"},
    {"id": "meta.llama3-1-8b-instruct-v1:0", "owned_by": "meta"},
    {"id": "meta.llama3-70b-instruct-v1:0", "owned_by": "meta"},
    {"id": "meta.llama3-8b-instruct-v1:0", "owned_by": "meta"},
    # Mistral models
    {"id": "mistral.mistral-large-3-675b-instruct", "owned_by": "mistral"},
    {"id": "mistral.mistral-large-2407-v1:0", "owned_by": "mistral"},
    {"id": "mistral.mistral-small-2402-v1:0", "owned_by": "mistral"},
    {"id": "mistral.mixtral-8x7b-instruct-v0:1", "owned_by": "mistral"},
    {"id": "mistral.mistral-7b-instruct-v0:2", "owned_by": "mistral"},
    # Amazon Titan text models
    {"id": "amazon.titan-text-premier-v1:0", "owned_by": "amazon"},
    {"id": "amazon.titan-text-express-v1", "owned_by": "amazon"},
    {"id": "amazon.titan-text-lite-v1", "owned_by": "amazon"},
    {"id": "amazon.titan-tg1-large", "owned_by": "amazon"},
    # Cohere models
    {"id": "cohere.command-r-plus-v1:0", "owned_by": "cohere"},
    {"id": "cohere.command-r-v1:0", "owned_by": "cohere"},
    # AI21 Labs models
    {"id": "ai21.jamba-1-5-large-v1:0", "owned_by": "ai21"},
    {"id": "ai21.jamba-1-5-mini-v1:0", "owned_by": "ai21"},
]

# Providers without dynamic discovery APIs (others use dedicated ModelSource classes)
STATIC_REGISTRIES: dict[str, list[dict]] = {
    "mistral": MISTRAL_MODELS,
    "google_vertex": GOOGLE_VERTEX_MODELS,
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
