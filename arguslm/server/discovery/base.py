"""Base protocol and types for model discovery."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from arguslm.server.models.provider import ProviderAccount


class DiscoveryError(Exception):
    """Raised when a model discovery call fails operationally.

    Use this for AWS auth failures, network timeouts, missing dependencies,
    or any condition where the caller should know discovery did NOT succeed.
    The legacy contract was "return [] on failure" — that produced silent
    misleading "0 models discovered" responses indistinguishable from the
    legitimate "no models enabled in this account" case. New implementations
    should raise this instead; existing implementations that still return []
    will be migrated incrementally.
    """


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
            List of discovered model descriptors. May be legitimately empty
            if the account has no enabled models — that is NOT a failure.

        Raises:
            DiscoveryError: When discovery fails operationally (auth error,
                network timeout, missing dependency). Callers can translate
                this to an HTTP error with the original cause as ``__cause__``.

        Migration note: legacy implementations may still return [] on
        failure (the old contract). New implementations MUST raise
        DiscoveryError so failure cases are distinguishable from
        "account has no models" success cases.
        """
        ...

    def supports_discovery(self) -> bool:
        """Return True if this provider supports dynamic model discovery.

        Returns:
            True for providers with /v1/models or similar API.
            False for providers requiring static/curated model lists.
        """
        ...
