from typing import Any

from app.core.litellm_client import LiteLLMClient
from app.models.benchmark import BenchmarkResult
from app.models.model import Model

class BenchmarkConfig:
    models: list[Model]
    prompt_pack: str
    max_tokens: int
    num_runs: int
    warmup_runs: int

class ThrottleConfig:
    global_concurrency: int
    per_provider_concurrency: int
    per_model_concurrency: int

def calculate_statistics(values: list[float]) -> dict[str, float]: ...
async def run_benchmark(config: BenchmarkConfig) -> list[BenchmarkResult]: ...
async def benchmark_single_model(
    model: Model,
    prompt_pack: str,
    max_tokens: int,
    semaphores: dict[str, Any],
    is_warmup: bool,
    run_id: Any,
) -> BenchmarkResult: ...
