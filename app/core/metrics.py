"""Metrics collection utilities for TTFT, TPS, and cost estimation.

This module provides precise measurement of:
- TTFT (Time To First Token): Time from request start to first content token
- TPS (Tokens Per Second): Both including and excluding TTFT
- Cost estimation: Based on model pricing data

References:
- NVIDIA NIM benchmarking: https://docs.nvidia.com/nim/benchmarking/llm/latest/metrics.html
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


# Model pricing data (USD per 1M tokens)
# Sources:
# - OpenAI: https://openai.com/api/pricing/
# - Anthropic: https://www.anthropic.com/pricing
# - Google: https://ai.google.dev/pricing
# - AWS Bedrock: https://aws.amazon.com/bedrock/pricing/
MODEL_PRICING = {
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    # Anthropic Claude 4.5 (https://platform.claude.com/docs/en/about-claude/pricing)
    "claude-opus-4-5-20251101": {"input": 5.00, "output": 25.00},
    "claude-opus-4-5": {"input": 5.00, "output": 25.00},
    "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4-5": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5-20251001": {"input": 1.00, "output": 5.00},
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
    # Anthropic Claude 4.x
    "claude-opus-4-1-20250805": {"input": 15.00, "output": 75.00},
    "claude-opus-4-0": {"input": 15.00, "output": 75.00},
    "claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-0": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    # Anthropic Claude 3.7
    "claude-3-7-sonnet-20250219": {"input": 3.00, "output": 15.00},
    "claude-3-7-sonnet-latest": {"input": 3.00, "output": 15.00},
    # Anthropic Claude 3.5
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
    "claude-3-5-haiku-latest": {"input": 0.80, "output": 4.00},
    # Anthropic Claude 3 (legacy)
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    "claude-3-opus-latest": {"input": 15.00, "output": 75.00},
    "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    # Google
    "gemini-2.0-flash-exp": {"input": 0.00, "output": 0.00},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    # AWS Bedrock
    "anthropic.claude-3-5-sonnet-20241022-v2:0": {"input": 3.00, "output": 15.00},
    "anthropic.claude-3-5-haiku-20241022-v1:0": {"input": 0.80, "output": 4.00},
}


@dataclass
class MetricsCollector:
    """Collects timing and token metrics during LLM completion.

    Usage:
        collector = MetricsCollector()
        collector.start()

        async for chunk in stream:
            content = extract_content(chunk)
            if content:
                collector.record_token(content)

        metrics = collector.finalize(model_id="gpt-4o")
    """

    start_time: float | None = None
    ttft_time: float | None = None
    end_time: float | None = None
    token_count: int = 0
    first_token_recorded: bool = False
    input_tokens: int = 0
    output_tokens: int = 0

    def start(self) -> None:
        """Start timing measurement."""
        self.start_time = time.perf_counter()
        self.ttft_time = None
        self.end_time = None
        self.token_count = 0
        self.first_token_recorded = False

    def record_token(self, content: str | None = None) -> None:
        """Record a token generation event.

        Args:
            content: Token content. If None or empty, token is not counted
                    (used to skip metadata/role-only chunks).
        """
        if not content:
            return

        if not self.first_token_recorded:
            self.ttft_time = time.perf_counter()
            self.first_token_recorded = True

        self.token_count += 1

    def finalize(
        self,
        model_id: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Finalize metrics collection and calculate results.

        Args:
            model_id: Model identifier for cost estimation
            input_tokens: Actual input token count (if available)
            output_tokens: Actual output token count (if available)

        Returns:
            Dictionary with metrics:
            - ttft_ms: Time to first token in milliseconds
            - tps: Tokens per second (including TTFT)
            - tps_excluding_ttft: Tokens per second (excluding TTFT)
            - total_latency_ms: Total request latency in milliseconds
            - input_tokens: Input token count
            - output_tokens: Output token count
            - estimated_cost: Estimated cost in USD (if model pricing available)
        """
        self.end_time = time.perf_counter()

        if not self.start_time:
            return self._empty_metrics()

        # Use provided token counts or fall back to chunk count
        self.input_tokens = input_tokens or 0
        self.output_tokens = output_tokens or self.token_count

        total_time_s = self.end_time - self.start_time
        total_time_ms = total_time_s * 1000

        # Calculate TTFT
        if self.ttft_time and self.first_token_recorded:
            ttft_ms = (self.ttft_time - self.start_time) * 1000
        else:
            # Non-streaming or no content tokens
            ttft_ms = total_time_ms

        # Calculate TPS
        tps = self.output_tokens / total_time_s if total_time_s > 0 else 0.0

        # Calculate TPS excluding TTFT
        generation_time_s = max(total_time_s - (ttft_ms / 1000), 0.0)
        tps_excluding_ttft = (
            self.output_tokens / generation_time_s if generation_time_s > 0 else 0.0
        )

        # Estimate cost
        estimated_cost = None
        if model_id:
            estimated_cost = estimate_cost(
                model_id=model_id,
                input_tokens=self.input_tokens,
                output_tokens=self.output_tokens,
            )

        return {
            "ttft_ms": ttft_ms,
            "tps": tps,
            "tps_excluding_ttft": tps_excluding_ttft,
            "total_latency_ms": total_time_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "estimated_cost": estimated_cost,
        }

    def _empty_metrics(self) -> dict[str, Any]:
        """Return empty metrics for failed/invalid measurements."""
        return {
            "ttft_ms": 0.0,
            "tps": 0.0,
            "tps_excluding_ttft": 0.0,
            "total_latency_ms": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost": None,
        }


def estimate_cost(
    model_id: str,
    input_tokens: int,
    output_tokens: int,
) -> float | None:
    """Estimate cost for a completion based on model pricing.

    Args:
        model_id: Model identifier (e.g., "gpt-4o", "claude-3-5-sonnet-20241022")
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Estimated cost in USD, or None if pricing not available
    """
    # Normalize model ID (remove provider prefixes)
    normalized_id = model_id
    for prefix in ["openai/", "anthropic/", "google/", "bedrock/", "azure/"]:
        if model_id.startswith(prefix):
            normalized_id = model_id[len(prefix) :]
            break

    pricing = MODEL_PRICING.get(normalized_id)
    if not pricing:
        return None

    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]

    return input_cost + output_cost


def extract_chunk_content(chunk: Any) -> str | None:
    """Extract content from a streaming chunk.

    Handles both dict and object-based chunk formats from LiteLLM.

    Args:
        chunk: Streaming chunk from LiteLLM

    Returns:
        Content string if present, None otherwise
    """
    # Dict format
    if isinstance(chunk, dict):
        choices = chunk.get("choices") or []
        if choices:
            delta = choices[0].get("delta") or {}
            return delta.get("content")

    # Object format
    choices = getattr(chunk, "choices", None)
    if choices:
        delta = getattr(choices[0], "delta", None)
        if delta:
            return getattr(delta, "content", None)

    return None
