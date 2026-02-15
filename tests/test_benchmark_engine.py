# pyright: ignore
"""Tests for benchmark engine orchestration and metrics."""

from __future__ import annotations

import asyncio
import importlib
import time
import uuid
from typing import Any, AsyncIterator, cast
from unittest.mock import patch

pytest = importlib.import_module("pytest")

from arguslm.server.core import benchmark_engine
from arguslm.server.core.benchmark_engine import BenchmarkConfig, BenchmarkResult
from arguslm.server.models.model import Model
from arguslm.server.models.provider import ProviderAccount


@pytest.fixture(autouse=True)
def _mock_credentials():
    with patch(
        "arguslm.server.models.provider.decrypt_credentials",
        return_value={"api_key": "test-key"},
    ):
        yield


def _make_model(index: int, provider_type: str = "openai") -> Model:
    provider_account = ProviderAccount(
        provider_type=provider_type,
        display_name=f"provider-{index}",
        credentials_encrypted="encrypted",
        enabled=True,
    )
    model = Model(
        provider_account_id=uuid.uuid4(),
        model_id=f"model-{index}",
        custom_name=None,
        source="manual",
        enabled_for_monitoring=False,
        enabled_for_benchmark=True,
        model_metadata={},
    )
    model.provider_account = provider_account
    return model


@pytest.mark.asyncio
async def test_parallel_execution(monkeypatch: Any) -> None:
    models = [_make_model(i) for i in range(5)]
    config = BenchmarkConfig(models=models, prompt_pack="pack", num_runs=1, warmup_runs=0)
    start_times: list[float] = []

    async def fake_benchmark_single_model(
        model: Model,
        prompt_pack: str,
        max_tokens: int,
        semaphores: dict[str, Any],
        is_warmup: bool,
        run_id: uuid.UUID,
    ) -> BenchmarkResult:
        _ = (prompt_pack, max_tokens, semaphores, is_warmup)
        start_times.append(time.perf_counter())
        await asyncio.sleep(0.05)
        return BenchmarkResult(
            run_id=run_id,
            model_id=model.id,
            ttft_ms=1.0,
            tps=1.0,
            tps_excluding_ttft=1.0,
            total_latency_ms=1.0,
            input_tokens=0,
            output_tokens=1,
            estimated_cost=None,
            error=None,
        )

    monkeypatch.setattr(benchmark_engine, "benchmark_single_model", fake_benchmark_single_model)

    start = time.perf_counter()
    results = await benchmark_engine.run_benchmark(config)
    elapsed = time.perf_counter() - start

    assert len(results) == 5
    assert elapsed < 0.2
    assert max(start_times) - min(start_times) < 0.05


@pytest.mark.asyncio
async def test_warmup_runs_excluded(monkeypatch: Any) -> None:
    models = [_make_model(0), _make_model(1)]
    config = BenchmarkConfig(models=models, prompt_pack="pack", num_runs=3, warmup_runs=1)

    async def fake_benchmark_single_model(
        model: Model,
        prompt_pack: str,
        max_tokens: int,
        semaphores: dict[str, Any],
        is_warmup: bool,
        run_id: uuid.UUID,
    ) -> BenchmarkResult:
        _ = (prompt_pack, max_tokens, semaphores, is_warmup)
        return BenchmarkResult(
            run_id=run_id,
            model_id=model.id,
            ttft_ms=1.0,
            tps=1.0,
            tps_excluding_ttft=1.0,
            total_latency_ms=1.0,
            input_tokens=0,
            output_tokens=1,
            estimated_cost=None,
            error=None,
        )

    monkeypatch.setattr(benchmark_engine, "benchmark_single_model", fake_benchmark_single_model)

    results = await benchmark_engine.run_benchmark(config)
    # warmup_runs are additional runs on top of num_runs, only num_runs are returned
    assert len(results) == len(models) * config.num_runs


def test_calculate_statistics() -> None:
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    benchmark_engine_any = cast(Any, benchmark_engine)
    stats = benchmark_engine_any.calculate_statistics(values)
    assert stats["p50"] == pytest.approx(3.0)
    assert stats["p95"] == pytest.approx(4.8)
    assert stats["p99"] == pytest.approx(4.96)


@pytest.mark.asyncio
async def test_throttling_limits_respected() -> None:
    model = _make_model(0, provider_type="openai")
    semaphores = {
        "global": asyncio.Semaphore(2),
        "provider": {"openai": asyncio.Semaphore(1)},
        "model": {str(model.id): asyncio.Semaphore(1)},
    }
    state = {"active": 0, "max_active": 0}
    lock = asyncio.Lock()

    async def stream_generator() -> AsyncIterator[dict[str, Any]]:
        async with lock:
            state["active"] += 1
            state["max_active"] = max(state["max_active"], state["active"])
        try:
            await asyncio.sleep(0.05)
            yield {"choices": [{"delta": {"content": "x"}}]}
        finally:
            async with lock:
                state["active"] -= 1

    async def fake_complete_stream(self: object, **kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        _ = kwargs
        async for chunk in stream_generator():
            yield chunk

    with patch.object(benchmark_engine.LiteLLMClient, "complete_stream", fake_complete_stream):
        run_id = uuid.uuid4()
        tasks = [
            benchmark_engine.benchmark_single_model(
                model=model,
                prompt_pack="health_check",
                max_tokens=5,
                semaphores=semaphores,
                is_warmup=False,
                run_id=run_id,
            )
            for _ in range(3)
        ]

        results = await asyncio.gather(*tasks)
        for r in results:
            assert r.error is None, f"benchmark_single_model failed: {r.error}"
        assert state["max_active"] == 1


@pytest.mark.asyncio
async def test_error_handling(monkeypatch: Any) -> None:
    models = [_make_model(0)]
    config = BenchmarkConfig(models=models, prompt_pack="pack", num_runs=1, warmup_runs=0)

    async def fake_benchmark_single_model(*args: Any, **kwargs: Any) -> BenchmarkResult:
        _ = (args, kwargs)
        raise RuntimeError("boom")

    monkeypatch.setattr(benchmark_engine, "benchmark_single_model", fake_benchmark_single_model)

    results = await benchmark_engine.run_benchmark(config)
    assert len(results) == 1
    assert results[0].error == "boom"
