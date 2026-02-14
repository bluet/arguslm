"""Base protocol and types for model discovery."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from arguslm.server.models.provider import ProviderAccount


@dataclass
class ModelDescriptor:
    """Descriptor for a discovered model.

    Contains essential model information returned from provider discovery APIs.
    """

    id: str  # Model identifier (e.g., "gpt-4o", "llama3:8b")
    provider_type: str  # Provider type (e.g., "openai", "ollama")
    owned_by: str | None = None  # Model owner/organization
    created: int | None = None  # Unix timestamp of creation
    metadata: dict[str, Any] = field(default_factory=dict)  # Additional provider-specific data


class ModelSource(Protocol):
    """Protocol for model discovery adapters.

    Implementations query provider APIs to discover available models.
    Supports both dynamic discovery (API calls) and static registries.
    """

    async def list_models(self, account: "ProviderAccount") -> list[ModelDescriptor]:
        """Return available models for this account.

        Args:
            account: Provider account with credentials.

        Returns:
            List of discovered model descriptors.
            Returns empty list on discovery failure (logs error internally).
        """
        ...

    def supports_discovery(self) -> bool:
        """Return True if this provider supports dynamic model discovery.

        Returns:
            True for providers with /v1/models or similar API.
            False for providers requiring static/curated model lists.
        """
        ...
