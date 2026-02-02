"""Tests for throttle manager."""

from __future__ import annotations

import asyncio

import pytest

from app.core.throttle import ThrottleManager, ThrottleProfile


class TestThrottleProfile:
    """Tests for ThrottleProfile configuration."""

    def test_default_values(self) -> None:
        """Test default throttle profile values."""
        profile = ThrottleProfile()
        assert profile.global_limit == 50
        assert profile.provider_limit == 10
        assert profile.model_limit == 3

    def test_custom_values(self) -> None:
        """Test custom throttle profile values."""
        profile = ThrottleProfile(
            global_limit=100,
            provider_limit=20,
            model_limit=5,
        )
        assert profile.global_limit == 100
        assert profile.provider_limit == 20
        assert profile.model_limit == 5

    def test_validation_global_limit(self) -> None:
        """Test validation of global_limit."""
        with pytest.raises(ValueError, match="global_limit must be positive"):
            ThrottleProfile(global_limit=0)

        with pytest.raises(ValueError, match="global_limit must be positive"):
            ThrottleProfile(global_limit=-1)

    def test_validation_provider_limit(self) -> None:
        """Test validation of provider_limit."""
        with pytest.raises(ValueError, match="provider_limit must be positive"):
            ThrottleProfile(provider_limit=0)

        with pytest.raises(ValueError, match="provider_limit must be positive"):
            ThrottleProfile(provider_limit=-1)

    def test_validation_model_limit(self) -> None:
        """Test validation of model_limit."""
        with pytest.raises(ValueError, match="model_limit must be positive"):
            ThrottleProfile(model_limit=0)

        with pytest.raises(ValueError, match="model_limit must be positive"):
            ThrottleProfile(model_limit=-1)


class TestThrottleManager:
    """Tests for ThrottleManager."""

    def test_initialization_default_profile(self) -> None:
        """Test initialization with default profile."""
        manager = ThrottleManager()
        assert manager.profile.global_limit == 50
        assert manager.profile.provider_limit == 10
        assert manager.profile.model_limit == 3

    def test_initialization_custom_profile(self) -> None:
        """Test initialization with custom profile."""
        profile = ThrottleProfile(global_limit=100, provider_limit=20, model_limit=5)
        manager = ThrottleManager(profile)
        assert manager.profile.global_limit == 100
        assert manager.profile.provider_limit == 20
        assert manager.profile.model_limit == 5

    @pytest.mark.asyncio
    async def test_acquire_single_request(self) -> None:
        """Test acquiring semaphores for a single request."""
        manager = ThrottleManager()

        async with manager.acquire("openai", "gpt-4"):
            # Inside context, semaphores should be acquired
            stats = await manager.get_stats()
            assert stats["global"]["available"] == 49  # 50 - 1
            assert stats["providers"]["openai"]["available"] == 9  # 10 - 1
            assert stats["models"]["gpt-4"]["available"] == 2  # 3 - 1

        # After context, semaphores should be released
        stats = await manager.get_stats()
        assert stats["global"]["available"] == 50
        assert stats["providers"]["openai"]["available"] == 10
        assert stats["models"]["gpt-4"]["available"] == 3

    @pytest.mark.asyncio
    async def test_global_limit_enforcement(self) -> None:
        """Test that global limit is enforced."""
        profile = ThrottleProfile(global_limit=2, provider_limit=10, model_limit=10)
        manager = ThrottleManager(profile)

        acquired_count = 0

        async def acquire_and_hold() -> None:
            nonlocal acquired_count
            async with manager.acquire("openai", "gpt-4"):
                acquired_count += 1
                await asyncio.sleep(0.1)

        # Start 3 tasks, but only 2 should run concurrently
        tasks = [asyncio.create_task(acquire_and_hold()) for _ in range(3)]

        # Wait a bit for first 2 to acquire
        await asyncio.sleep(0.05)
        assert acquired_count == 2  # Only 2 should be running

        # Wait for all to complete
        await asyncio.gather(*tasks)
        assert acquired_count == 3  # All should have run eventually

    @pytest.mark.asyncio
    async def test_provider_limit_enforcement(self) -> None:
        """Test that per-provider limit is enforced."""
        profile = ThrottleProfile(global_limit=10, provider_limit=2, model_limit=10)
        manager = ThrottleManager(profile)

        acquired_count = 0

        async def acquire_and_hold(provider: str) -> None:
            nonlocal acquired_count
            async with manager.acquire(provider, "model-1"):
                acquired_count += 1
                await asyncio.sleep(0.1)

        # Start 3 tasks for same provider, but only 2 should run concurrently
        tasks = [asyncio.create_task(acquire_and_hold("openai")) for _ in range(3)]

        # Wait a bit for first 2 to acquire
        await asyncio.sleep(0.05)
        assert acquired_count == 2  # Only 2 should be running

        # Wait for all to complete
        await asyncio.gather(*tasks)
        assert acquired_count == 3  # All should have run eventually

    @pytest.mark.asyncio
    async def test_model_limit_enforcement(self) -> None:
        """Test that per-model limit is enforced."""
        profile = ThrottleProfile(global_limit=10, provider_limit=10, model_limit=2)
        manager = ThrottleManager(profile)

        acquired_count = 0

        async def acquire_and_hold(model: str) -> None:
            nonlocal acquired_count
            async with manager.acquire("openai", model):
                acquired_count += 1
                await asyncio.sleep(0.1)

        # Start 3 tasks for same model, but only 2 should run concurrently
        tasks = [asyncio.create_task(acquire_and_hold("gpt-4")) for _ in range(3)]

        # Wait a bit for first 2 to acquire
        await asyncio.sleep(0.05)
        assert acquired_count == 2  # Only 2 should be running

        # Wait for all to complete
        await asyncio.gather(*tasks)
        assert acquired_count == 3  # All should have run eventually

    @pytest.mark.asyncio
    async def test_multiple_providers_independent(self) -> None:
        """Test that different providers have independent limits."""
        profile = ThrottleProfile(global_limit=10, provider_limit=2, model_limit=10)
        manager = ThrottleManager(profile)

        openai_count = 0
        anthropic_count = 0

        async def acquire_openai() -> None:
            nonlocal openai_count
            async with manager.acquire("openai", "gpt-4"):
                openai_count += 1
                await asyncio.sleep(0.1)

        async def acquire_anthropic() -> None:
            nonlocal anthropic_count
            async with manager.acquire("anthropic", "claude-3"):
                anthropic_count += 1
                await asyncio.sleep(0.1)

        # Start 2 tasks for each provider
        tasks = [
            asyncio.create_task(acquire_openai()),
            asyncio.create_task(acquire_openai()),
            asyncio.create_task(acquire_anthropic()),
            asyncio.create_task(acquire_anthropic()),
        ]

        # Wait a bit - all 4 should be running (2 per provider)
        await asyncio.sleep(0.05)
        assert openai_count == 2
        assert anthropic_count == 2

        await asyncio.gather(*tasks)

    @pytest.mark.asyncio
    async def test_multiple_models_independent(self) -> None:
        """Test that different models have independent limits."""
        profile = ThrottleProfile(global_limit=10, provider_limit=10, model_limit=2)
        manager = ThrottleManager(profile)

        gpt4_count = 0
        gpt35_count = 0

        async def acquire_gpt4() -> None:
            nonlocal gpt4_count
            async with manager.acquire("openai", "gpt-4"):
                gpt4_count += 1
                await asyncio.sleep(0.1)

        async def acquire_gpt35() -> None:
            nonlocal gpt35_count
            async with manager.acquire("openai", "gpt-3.5-turbo"):
                gpt35_count += 1
                await asyncio.sleep(0.1)

        # Start 2 tasks for each model
        tasks = [
            asyncio.create_task(acquire_gpt4()),
            asyncio.create_task(acquire_gpt4()),
            asyncio.create_task(acquire_gpt35()),
            asyncio.create_task(acquire_gpt35()),
        ]

        # Wait a bit - all 4 should be running (2 per model)
        await asyncio.sleep(0.05)
        assert gpt4_count == 2
        assert gpt35_count == 2

        await asyncio.gather(*tasks)

    @pytest.mark.asyncio
    async def test_get_semaphores_dict_backward_compatibility(self) -> None:
        """Test get_semaphores_dict for backward compatibility."""
        manager = ThrottleManager()

        # Acquire some semaphores to populate the dicts
        async with manager.acquire("openai", "gpt-4"):
            semaphores = manager.get_semaphores_dict()

            assert "global" in semaphores
            assert "provider" in semaphores
            assert "model" in semaphores

            assert "openai" in semaphores["provider"]
            assert "gpt-4" in semaphores["model"]

            # Verify they're actual semaphores
            assert isinstance(semaphores["global"], asyncio.Semaphore)
            assert isinstance(semaphores["provider"]["openai"], asyncio.Semaphore)
            assert isinstance(semaphores["model"]["gpt-4"], asyncio.Semaphore)

    @pytest.mark.asyncio
    async def test_get_stats(self) -> None:
        """Test get_stats returns correct statistics."""
        manager = ThrottleManager()

        # Initial stats
        stats = await manager.get_stats()
        assert stats["global"]["limit"] == 50
        assert stats["global"]["available"] == 50
        assert len(stats["providers"]) == 0
        assert len(stats["models"]) == 0

        # After acquiring
        async with manager.acquire("openai", "gpt-4"):
            stats = await manager.get_stats()
            assert stats["global"]["available"] == 49
            assert stats["providers"]["openai"]["available"] == 9
            assert stats["models"]["gpt-4"]["available"] == 2

    def test_reset(self) -> None:
        """Test reset clears all semaphores."""
        manager = ThrottleManager()

        # Manually add some semaphores
        manager._provider_semaphores["openai"] = asyncio.Semaphore(5)
        manager._model_semaphores["gpt-4"] = asyncio.Semaphore(2)

        assert len(manager._provider_semaphores) == 1
        assert len(manager._model_semaphores) == 1

        # Reset
        manager.reset()

        assert len(manager._provider_semaphores) == 0
        assert len(manager._model_semaphores) == 0
        assert manager._global_semaphore._value == 50

    @pytest.mark.asyncio
    async def test_concurrent_semaphore_creation(self) -> None:
        """Test that concurrent semaphore creation is thread-safe."""
        manager = ThrottleManager()

        async def acquire_same_provider() -> None:
            async with manager.acquire("openai", "gpt-4"):
                await asyncio.sleep(0.01)

        # Start many tasks concurrently that will all try to create
        # the same provider semaphore
        tasks = [asyncio.create_task(acquire_same_provider()) for _ in range(20)]
        await asyncio.gather(*tasks)

        # Should only have created one semaphore for the provider
        assert len(manager._provider_semaphores) == 1
        assert "openai" in manager._provider_semaphores

    @pytest.mark.asyncio
    async def test_hierarchical_throttling(self) -> None:
        """Test that all three levels of throttling work together."""
        profile = ThrottleProfile(global_limit=5, provider_limit=3, model_limit=2)
        manager = ThrottleManager(profile)

        results: list[str] = []

        async def make_request(provider: str, model: str, request_id: str) -> None:
            async with manager.acquire(provider, model):
                results.append(f"start-{request_id}")
                await asyncio.sleep(0.05)
                results.append(f"end-{request_id}")

        # Create 10 requests across 2 providers and 2 models each
        tasks = []
        for i in range(5):
            tasks.append(asyncio.create_task(make_request("openai", "gpt-4", f"openai-gpt4-{i}")))
            tasks.append(
                asyncio.create_task(make_request("anthropic", "claude-3", f"anthropic-claude-{i}"))
            )

        await asyncio.gather(*tasks)

        # All requests should have completed
        assert len(results) == 20  # 10 starts + 10 ends
        assert results.count("start-openai-gpt4-0") == 1
        assert results.count("end-openai-gpt4-0") == 1
