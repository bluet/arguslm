"""Async benchmark orchestration utilities."""

from __future__ import annotations

import asyncio
import math
import time
import uuid
from dataclasses import dataclass
from typing import Any

from app.core.litellm_client import LiteLLMClient
from app.models.benchmark import BenchmarkResult
from app.models.model import Model


@dataclass
class BenchmarkConfig:
    models: list[Model]
    prompt_pack: str
    max_tokens: int = 200
    num_runs: int = 3
    warmup_runs: int = 1


@dataclass
class ThrottleConfig:
    global_concurrency: int = 50
    per_provider_concurrency: int = 10
    per_model_concurrency: int = 3


def _get_provider_key(model: Model) -> str:
    provider_account = getattr(model, "provider_account", None)
    provider_type = getattr(provider_account, "provider_type", None)
    return provider_type or "unknown"


def _init_semaphores(throttle: ThrottleConfig) -> dict[str, Any]:
    return {
        "global": asyncio.Semaphore(throttle.global_concurrency),
        "provider": {},
        "model": {},
    }


def _error_result(run_id: uuid.UUID, model: Model, error: Exception) -> BenchmarkResult:
    return BenchmarkResult(
        run_id=run_id,
        model_id=model.id,
        ttft_ms=0.0,
        tps=0.0,
        tps_excluding_ttft=0.0,
        total_latency_ms=0.0,
        input_tokens=0,
        output_tokens=0,
        estimated_cost=None,
        error=str(error),
    )


def _get_chunk_content(chunk: Any) -> str | None:
    if isinstance(chunk, dict):
        choices = chunk.get("choices") or []
        if choices:
            delta = choices[0].get("delta") or {}
            return delta.get("content")

    choices = getattr(chunk, "choices", None)
    if choices:
        delta = getattr(choices[0], "delta", None)
        return getattr(delta, "content", None)

    return None


def calculate_statistics(values: list[float]) -> dict[str, float]:
    if not values:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0}

    ordered = sorted(values)

    def percentile(p: float) -> float:
        if len(ordered) == 1:
            return ordered[0]
        position = (len(ordered) - 1) * (p / 100)
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return ordered[int(position)]
        fraction = position - lower
        return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction

    return {
        "p50": percentile(50),
        "p95": percentile(95),
        "p99": percentile(99),
    }


async def run_benchmark(config: BenchmarkConfig) -> list[BenchmarkResult]:
    """Run benchmarks on all models in parallel with throttling."""
    throttle = ThrottleConfig()
    semaphores = _init_semaphores(throttle)
    tasks: list[tuple[Model, asyncio.Task[BenchmarkResult], bool]] = []
    run_id = uuid.uuid4()

    for model in config.models:
        provider_key = _get_provider_key(model)
        if provider_key not in semaphores["provider"]:
            semaphores["provider"][provider_key] = asyncio.Semaphore(
                throttle.per_provider_concurrency
            )

        model_key = str(model.id)
        if model_key not in semaphores["model"]:
            semaphores["model"][model_key] = asyncio.Semaphore(throttle.per_model_concurrency)

        for run_idx in range(config.num_runs):
            is_warmup = run_idx < config.warmup_runs
            task = asyncio.create_task(
                benchmark_single_model(
                    model=model,
                    prompt_pack=config.prompt_pack,
                    max_tokens=config.max_tokens,
                    semaphores=semaphores,
                    is_warmup=is_warmup,
                    run_id=run_id,
                )
            )
            tasks.append((model, task, is_warmup))

    results = await asyncio.gather(*(task for _, task, _ in tasks), return_exceptions=True)

    aggregated: list[BenchmarkResult] = []
    for (model, _task, is_warmup), result in zip(tasks, results, strict=True):
        if is_warmup:
            continue
        if isinstance(result, Exception):
            aggregated.append(_error_result(run_id, model, result))
        else:
            aggregated.append(result)

    return aggregated


async def benchmark_single_model(
    model: Model,
    prompt_pack: str,
    max_tokens: int,
    semaphores: dict[str, Any],
    is_warmup: bool,
    run_id: uuid.UUID,
) -> BenchmarkResult:
    """Measure TTFT and TPS for a single model."""
    _ = is_warmup
    provider_key = _get_provider_key(model)
    model_key = str(model.id)
    client = LiteLLMClient()

    async with (
        semaphores["global"],
        semaphores["provider"][provider_key],
        semaphores["model"][model_key],
    ):
        start_time = time.perf_counter()
        ttft_ms = 0.0
        tokens_generated = 0
        first_content_received = False

        try:
            stream = client.complete_stream(
                model=model.model_id,
                messages=[{"role": "user", "content": prompt_pack}],
                max_tokens=max_tokens,
            )

            async for chunk in stream:
                content = _get_chunk_content(chunk)
                if not first_content_received and content:
                    ttft_ms = (time.perf_counter() - start_time) * 1000
                    first_content_received = True
                tokens_generated += 1

            total_time_ms = (time.perf_counter() - start_time) * 1000
            generation_time_ms = max(total_time_ms - ttft_ms, 0.0)
            tps = tokens_generated / (total_time_ms / 1000) if total_time_ms > 0 else 0.0
            tps_excluding_ttft = (
                tokens_generated / (generation_time_ms / 1000) if generation_time_ms > 0 else 0.0
            )

            return BenchmarkResult(
                run_id=run_id,
                model_id=model.id,
                ttft_ms=ttft_ms,
                tps=tps,
                tps_excluding_ttft=tps_excluding_ttft,
                total_latency_ms=total_time_ms,
                input_tokens=0,
                output_tokens=tokens_generated,
                estimated_cost=None,
                error=None,
            )
        except Exception as e:
            return BenchmarkResult(
                run_id=run_id,
                model_id=model.id,
                ttft_ms=0.0,
                tps=0.0,
                tps_excluding_ttft=0.0,
                total_latency_ms=0.0,
                input_tokens=0,
                output_tokens=0,
                estimated_cost=None,
                error=str(e),
            )
