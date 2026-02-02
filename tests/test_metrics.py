"""Tests for metrics collection utilities."""

import time
from unittest.mock import MagicMock

import pytest

from app.core.metrics import (
    MODEL_PRICING,
    MetricsCollector,
    estimate_cost,
    extract_chunk_content,
)


class TestMetricsCollector:
    """Test MetricsCollector class."""

    def test_start_initializes_state(self):
        """Test that start() initializes timing state."""
        collector = MetricsCollector()
        collector.start()

        assert collector.start_time is not None
        assert collector.ttft_time is None
        assert collector.end_time is None
        assert collector.token_count == 0
        assert collector.first_token_recorded is False

    def test_record_token_sets_ttft_on_first_content(self):
        """Test that first content token sets TTFT."""
        collector = MetricsCollector()
        collector.start()

        time.sleep(0.01)  # Simulate delay
        collector.record_token("Hello")

        assert collector.ttft_time is not None
        assert collector.first_token_recorded is True
        assert collector.token_count == 1

    def test_record_token_ignores_empty_content(self):
        """Test that empty/None content doesn't count as first token."""
        collector = MetricsCollector()
        collector.start()

        collector.record_token(None)
        collector.record_token("")
        collector.record_token("   ")  # Whitespace still counts as content

        assert collector.first_token_recorded is True  # Whitespace counted
        assert collector.token_count == 1

    def test_record_token_counts_subsequent_tokens(self):
        """Test that subsequent tokens are counted."""
        collector = MetricsCollector()
        collector.start()

        collector.record_token("Hello")
        collector.record_token(" world")
        collector.record_token("!")

        assert collector.token_count == 3
        assert collector.first_token_recorded is True

    def test_finalize_calculates_metrics_with_streaming(self):
        """Test finalize() with streaming tokens."""
        collector = MetricsCollector()
        collector.start()

        time.sleep(0.01)  # Simulate TTFT delay
        collector.record_token("Hello")

        time.sleep(0.01)  # Simulate generation time
        collector.record_token(" world")

        metrics = collector.finalize(model_id="gpt-4o", output_tokens=2)

        assert metrics["ttft_ms"] > 0
        assert metrics["ttft_ms"] < metrics["total_latency_ms"]
        assert metrics["tps"] > 0
        assert metrics["tps_excluding_ttft"] > 0
        assert metrics["output_tokens"] == 2
        assert metrics["estimated_cost"] is not None

    def test_finalize_handles_non_streaming(self):
        """Test finalize() when no tokens recorded (non-streaming)."""
        collector = MetricsCollector()
        collector.start()

        time.sleep(0.01)
        metrics = collector.finalize(model_id="gpt-4o", output_tokens=10)

        # TTFT should equal total latency for non-streaming
        assert metrics["ttft_ms"] == metrics["total_latency_ms"]
        assert metrics["tps"] > 0
        assert metrics["output_tokens"] == 10

    def test_finalize_handles_empty_response(self):
        """Test finalize() with zero tokens."""
        collector = MetricsCollector()
        collector.start()

        time.sleep(0.01)
        metrics = collector.finalize(model_id="gpt-4o", output_tokens=0)

        assert metrics["ttft_ms"] > 0
        assert metrics["tps"] == 0.0
        assert metrics["tps_excluding_ttft"] == 0.0
        assert metrics["output_tokens"] == 0

    def test_finalize_without_start_returns_empty(self):
        """Test finalize() without calling start() returns empty metrics."""
        collector = MetricsCollector()
        metrics = collector.finalize()

        assert metrics["ttft_ms"] == 0.0
        assert metrics["tps"] == 0.0
        assert metrics["tps_excluding_ttft"] == 0.0
        assert metrics["total_latency_ms"] == 0.0
        assert metrics["estimated_cost"] is None

    def test_finalize_uses_token_count_fallback(self):
        """Test finalize() uses chunk count when output_tokens not provided."""
        collector = MetricsCollector()
        collector.start()

        collector.record_token("Hello")
        collector.record_token(" world")

        metrics = collector.finalize(model_id="gpt-4o")

        # Should use token_count as fallback
        assert metrics["output_tokens"] == 2

    def test_finalize_calculates_tps_correctly(self):
        """Test TPS calculation accuracy."""
        collector = MetricsCollector()
        collector.start()

        # Record TTFT
        time.sleep(0.1)  # 100ms TTFT
        collector.record_token("First")

        # Record more tokens
        time.sleep(0.1)  # 100ms generation
        for _ in range(9):
            collector.record_token("token")

        metrics = collector.finalize(output_tokens=10)

        # Total time ~200ms, 10 tokens
        # TPS including TTFT: 10 / 0.2 = 50 tokens/s
        assert 40 < metrics["tps"] < 60  # Allow some timing variance

        # Generation time ~100ms, 10 tokens
        # TPS excluding TTFT: 10 / 0.1 = 100 tokens/s
        assert 80 < metrics["tps_excluding_ttft"] < 120


class TestEstimateCost:
    """Test cost estimation function."""

    def test_estimate_cost_for_known_model(self):
        """Test cost estimation for model with known pricing."""
        cost = estimate_cost(
            model_id="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
        )

        # gpt-4o: $2.50/1M input, $10.00/1M output
        # Expected: (1000/1M * 2.50) + (500/1M * 10.00) = 0.0025 + 0.005 = 0.0075
        assert cost is not None
        assert abs(cost - 0.0075) < 0.0001

    def test_estimate_cost_with_provider_prefix(self):
        """Test cost estimation strips provider prefixes."""
        cost_openai = estimate_cost("openai/gpt-4o", 1000, 500)
        cost_no_prefix = estimate_cost("gpt-4o", 1000, 500)

        assert cost_openai == cost_no_prefix

    def test_estimate_cost_anthropic_model(self):
        """Test cost estimation for Anthropic model."""
        cost = estimate_cost(
            model_id="anthropic/claude-3-5-sonnet-20241022",
            input_tokens=1000,
            output_tokens=500,
        )

        # claude-3-5-sonnet: $3.00/1M input, $15.00/1M output
        # Expected: (1000/1M * 3.00) + (500/1M * 15.00) = 0.003 + 0.0075 = 0.0105
        assert cost is not None
        assert abs(cost - 0.0105) < 0.0001

    def test_estimate_cost_unknown_model_returns_none(self):
        """Test cost estimation returns None for unknown models."""
        cost = estimate_cost(
            model_id="unknown-model-xyz",
            input_tokens=1000,
            output_tokens=500,
        )

        assert cost is None

    def test_estimate_cost_zero_tokens(self):
        """Test cost estimation with zero tokens."""
        cost = estimate_cost(
            model_id="gpt-4o",
            input_tokens=0,
            output_tokens=0,
        )

        assert cost == 0.0

    def test_estimate_cost_free_model(self):
        """Test cost estimation for free tier model."""
        cost = estimate_cost(
            model_id="gemini-2.0-flash-exp",
            input_tokens=1000,
            output_tokens=500,
        )

        assert cost == 0.0


class TestExtractChunkContent:
    """Test chunk content extraction."""

    def test_extract_from_dict_format(self):
        """Test extraction from dict-based chunk."""
        chunk = {
            "choices": [
                {
                    "delta": {
                        "content": "Hello world",
                    }
                }
            ]
        }

        content = extract_chunk_content(chunk)
        assert content == "Hello world"

    def test_extract_from_object_format(self):
        """Test extraction from object-based chunk."""
        delta = MagicMock()
        delta.content = "Hello world"

        choice = MagicMock()
        choice.delta = delta

        chunk = MagicMock()
        chunk.choices = [choice]

        content = extract_chunk_content(chunk)
        assert content == "Hello world"

    def test_extract_returns_none_for_empty_choices(self):
        """Test extraction returns None when choices is empty."""
        chunk = {"choices": []}
        content = extract_chunk_content(chunk)
        assert content is None

    def test_extract_returns_none_for_missing_content(self):
        """Test extraction returns None when content field missing."""
        chunk = {
            "choices": [
                {
                    "delta": {
                        "role": "assistant",
                    }
                }
            ]
        }

        content = extract_chunk_content(chunk)
        assert content is None

    def test_extract_returns_none_for_invalid_chunk(self):
        """Test extraction returns None for invalid chunk format."""
        chunk = {"invalid": "format"}
        content = extract_chunk_content(chunk)
        assert content is None

    def test_extract_handles_none_delta(self):
        """Test extraction handles None delta gracefully."""
        chunk = {
            "choices": [
                {
                    "delta": None,
                }
            ]
        }

        content = extract_chunk_content(chunk)
        assert content is None


class TestModelPricing:
    """Test model pricing data."""

    def test_pricing_data_structure(self):
        """Test that all pricing entries have required fields."""
        for model_id, pricing in MODEL_PRICING.items():
            assert "input" in pricing, f"Missing 'input' for {model_id}"
            assert "output" in pricing, f"Missing 'output' for {model_id}"
            assert isinstance(pricing["input"], (int, float))
            assert isinstance(pricing["output"], (int, float))
            assert pricing["input"] >= 0
            assert pricing["output"] >= 0

    def test_pricing_includes_major_providers(self):
        """Test that pricing includes models from major providers."""
        # Check for at least one model from each major provider
        has_openai = any(model.startswith("gpt-") for model in MODEL_PRICING)
        has_anthropic = any(model.startswith("claude-") for model in MODEL_PRICING)
        has_google = any(model.startswith("gemini-") for model in MODEL_PRICING)

        assert has_openai, "Missing OpenAI models"
        assert has_anthropic, "Missing Anthropic models"
        assert has_google, "Missing Google models"


class TestMetricsIntegration:
    """Integration tests for metrics collection workflow."""

    def test_full_streaming_workflow(self):
        """Test complete streaming metrics collection workflow."""
        collector = MetricsCollector()
        collector.start()

        # Simulate streaming response
        chunks = [
            {"choices": [{"delta": {"role": "assistant"}}]},  # Role chunk (ignored)
            {"choices": [{"delta": {"content": "Hello"}}]},  # First content
            {"choices": [{"delta": {"content": " world"}}]},
            {"choices": [{"delta": {"content": "!"}}]},
        ]

        for chunk in chunks:
            content = extract_chunk_content(chunk)
            collector.record_token(content)

        metrics = collector.finalize(
            model_id="gpt-4o",
            input_tokens=10,
            output_tokens=3,
        )

        assert metrics["ttft_ms"] > 0
        assert metrics["tps"] > 0
        assert metrics["tps_excluding_ttft"] > 0
        assert metrics["input_tokens"] == 10
        assert metrics["output_tokens"] == 3
        assert metrics["estimated_cost"] is not None

    def test_non_streaming_workflow(self):
        """Test non-streaming metrics collection workflow."""
        collector = MetricsCollector()
        collector.start()

        # Simulate non-streaming response (no record_token calls)
        time.sleep(0.01)

        metrics = collector.finalize(
            model_id="claude-3-5-haiku-20241022",
            input_tokens=50,
            output_tokens=100,
        )

        assert metrics["ttft_ms"] == metrics["total_latency_ms"]
        assert metrics["tps"] > 0
        assert metrics["estimated_cost"] is not None
