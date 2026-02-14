"""Throttle manager for rate limiting and concurrency control.

This module provides a centralized throttle manager that enforces:
- Global concurrency limits across all requests
- Per-provider concurrency limits
- Per-model concurrency limits

The throttle manager uses asyncio.Semaphore to control concurrent access
and provides context manager support for easy integration.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator


@dataclass
class ThrottleProfile:
    """Configuration profile for throttle limits.

    Attributes:
        global_limit: Maximum concurrent requests across all providers/models
        provider_limit: Maximum concurrent requests per provider
        model_limit: Maximum concurrent requests per model
    """

    global_limit: int = 50
    provider_limit: int = 10
    model_limit: int = 3

    def __post_init__(self) -> None:
        """Validate throttle limits."""
        if self.global_limit <= 0:
            raise ValueError("global_limit must be positive")
        if self.provider_limit <= 0:
            raise ValueError("provider_limit must be positive")
        if self.model_limit <= 0:
            raise ValueError("model_limit must be positive")


class ThrottleManager:
    """Manages concurrency limits for LLM API requests.

    This class provides hierarchical throttling:
    1. Global limit: Total concurrent requests across all providers
    2. Provider limit: Concurrent requests per provider (e.g., OpenAI, Anthropic)
    3. Model limit: Concurrent requests per specific model

    Usage:
        manager = ThrottleManager()
        async with manager.acquire("openai", "gpt-4"):
            # Make API request here
            response = await client.complete(...)
    """

    def __init__(self, profile: ThrottleProfile | None = None) -> None:
        """Initialize throttle manager with optional profile.

        Args:
            profile: Throttle configuration profile. Uses defaults if not provided.
        """
        self.profile = profile or ThrottleProfile()
        self._global_semaphore = asyncio.Semaphore(self.profile.global_limit)
        self._provider_semaphores: dict[str, asyncio.Semaphore] = {}
        self._model_semaphores: dict[str, asyncio.Semaphore] = {}
        self._lock = asyncio.Lock()

    async def _get_provider_semaphore(self, provider_key: str) -> asyncio.Semaphore:
        """Get or create semaphore for provider.

        Args:
            provider_key: Provider identifier (e.g., "openai", "anthropic")

        Returns:
            Semaphore for the provider
        """
        if provider_key not in self._provider_semaphores:
            async with self._lock:
                # Double-check after acquiring lock
                if provider_key not in self._provider_semaphores:
                    self._provider_semaphores[provider_key] = asyncio.Semaphore(
                        self.profile.provider_limit
                    )
        return self._provider_semaphores[provider_key]

    async def _get_model_semaphore(self, model_key: str) -> asyncio.Semaphore:
        """Get or create semaphore for model.

        Args:
            model_key: Model identifier (e.g., "gpt-4", "claude-3-opus")

        Returns:
            Semaphore for the model
        """
        if model_key not in self._model_semaphores:
            async with self._lock:
                # Double-check after acquiring lock
                if model_key not in self._model_semaphores:
                    self._model_semaphores[model_key] = asyncio.Semaphore(self.profile.model_limit)
        return self._model_semaphores[model_key]

    @asynccontextmanager
    async def acquire(self, provider_key: str, model_key: str) -> AsyncIterator[None]:
        """Acquire all necessary semaphores for a request.

        This context manager acquires semaphores in order:
        1. Global semaphore
        2. Provider semaphore
        3. Model semaphore

        Args:
            provider_key: Provider identifier
            model_key: Model identifier

        Yields:
            None (context manager for semaphore acquisition)

        Example:
            async with manager.acquire("openai", "gpt-4"):
                response = await client.complete(...)
        """
        provider_sem = await self._get_provider_semaphore(provider_key)
        model_sem = await self._get_model_semaphore(model_key)

        async with self._global_semaphore:
            async with provider_sem:
                async with model_sem:
                    yield

    def get_semaphores_dict(self) -> dict[str, Any]:
        """Get semaphores in dictionary format for backward compatibility.

        This method provides compatibility with the inline throttling
        implementation used in benchmark_engine.py.

        Returns:
            Dictionary with 'global', 'provider', and 'model' semaphores
        """
        return {
            "global": self._global_semaphore,
            "provider": self._provider_semaphores,
            "model": self._model_semaphores,
        }

    async def get_stats(self) -> dict[str, Any]:
        """Get current throttle statistics.

        Returns:
            Dictionary with current semaphore values and limits
        """
        return {
            "global": {
                "limit": self.profile.global_limit,
                "available": self._global_semaphore._value,
            },
            "providers": {
                key: {
                    "limit": self.profile.provider_limit,
                    "available": sem._value,
                }
                for key, sem in self._provider_semaphores.items()
            },
            "models": {
                key: {
                    "limit": self.profile.model_limit,
                    "available": sem._value,
                }
                for key, sem in self._model_semaphores.items()
            },
        }

    def reset(self) -> None:
        """Reset all semaphores to initial state.

        Warning: This should only be called when no requests are in progress.
        """
        self._global_semaphore = asyncio.Semaphore(self.profile.global_limit)
        self._provider_semaphores.clear()
        self._model_semaphores.clear()
