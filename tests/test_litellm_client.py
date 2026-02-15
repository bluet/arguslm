"""
Tests for LiteLLM async client wrapper.

Tests cover:
- Non-streaming completions
- Streaming completions
- Error handling (auth, rate limit, timeout, bad request)
- Retry logic with exponential backoff
- Provider configuration mapping
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncIterator

from arguslm.server.core.litellm_client import (
    LiteLLMClient,
    CompletionConfig,
    complete,
)
from litellm.exceptions import (
    APIError,
    Timeout,
    RateLimitError,
    AuthenticationError,
    BadRequestError,
    ServiceUnavailableError,
)


@pytest.fixture
def client():
    """Create LiteLLMClient instance for testing."""
    return LiteLLMClient(
        default_timeout=10.0,
        default_max_retries=3,
        default_retry_delay=0.1,  # Fast retries for tests
        default_retry_multiplier=2.0,
    )


@pytest.fixture
def mock_messages():
    """Sample messages for testing."""
    return [{"role": "user", "content": "Hello, how are you?"}]


class TestLiteLLMClientNonStreaming:
    """Tests for non-streaming completions."""

    @pytest.mark.asyncio
    async def test_successful_completion(self, client, mock_messages):
        """Test successful non-streaming completion."""
        mock_response = {
            "id": "chatcmpl-123",
            "choices": [
                {
                    "message": {"role": "assistant", "content": "I'm doing well, thank you!"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
        }

        with patch(
            "arguslm.server.core.litellm_client.acompletion", new_callable=AsyncMock
        ) as mock_acompletion:
            mock_acompletion.return_value = mock_response

            response = await client.complete(
                model="gpt-4",
                messages=mock_messages,
            )

            assert response == mock_response
            mock_acompletion.assert_called_once()
            call_kwargs = mock_acompletion.call_args.kwargs
            assert call_kwargs["model"] == "gpt-4"
            assert call_kwargs["messages"] == mock_messages
            assert call_kwargs["stream"] is False

    @pytest.mark.asyncio
    async def test_completion_with_parameters(self, client, mock_messages):
        """Test completion with custom parameters."""
        mock_response = {"id": "test"}

        with patch(
            "arguslm.server.core.litellm_client.acompletion", new_callable=AsyncMock
        ) as mock_acompletion:
            mock_acompletion.return_value = mock_response

            await client.complete(
                model="gpt-4",
                messages=mock_messages,
                temperature=0.5,
                max_tokens=100,
                timeout=30.0,
            )

            call_kwargs = mock_acompletion.call_args.kwargs
            assert call_kwargs["temperature"] == 0.5
            assert call_kwargs["max_tokens"] == 100
            assert call_kwargs["timeout"] == 30.0

    @pytest.mark.asyncio
    async def test_authentication_error_no_retry(self, client, mock_messages):
        """Authentication errors should not be retried."""
        with patch(
            "arguslm.server.core.litellm_client.acompletion", new_callable=AsyncMock
        ) as mock_acompletion:
            mock_acompletion.side_effect = AuthenticationError(
                message="Invalid API key", llm_provider="openai", model="gpt-4"
            )

            with pytest.raises(AuthenticationError):
                await client.complete(model="gpt-4", messages=mock_messages)

            # Should only be called once (no retries)
            assert mock_acompletion.call_count == 1

    @pytest.mark.asyncio
    async def test_bad_request_error_no_retry(self, client, mock_messages):
        """Bad request errors should not be retried."""
        with patch(
            "arguslm.server.core.litellm_client.acompletion", new_callable=AsyncMock
        ) as mock_acompletion:
            mock_acompletion.side_effect = BadRequestError(
                message="Invalid parameter", model="gpt-4", llm_provider="openai"
            )

            with pytest.raises(BadRequestError):
                await client.complete(model="gpt-4", messages=mock_messages)

            assert mock_acompletion.call_count == 1

    @pytest.mark.asyncio
    async def test_rate_limit_retry_success(self, client, mock_messages):
        """Rate limit errors should be retried and eventually succeed."""
        mock_response = {"id": "success"}

        with patch(
            "arguslm.server.core.litellm_client.acompletion", new_callable=AsyncMock
        ) as mock_acompletion:
            # Fail twice, then succeed
            mock_acompletion.side_effect = [
                RateLimitError(message="Rate limit exceeded", llm_provider="openai", model="gpt-4"),
                RateLimitError(message="Rate limit exceeded", llm_provider="openai", model="gpt-4"),
                mock_response,
            ]

            response = await client.complete(model="gpt-4", messages=mock_messages)

            assert response == mock_response
            assert mock_acompletion.call_count == 3

    @pytest.mark.asyncio
    async def test_rate_limit_retry_exhausted(self, client, mock_messages):
        """Rate limit errors should raise after max retries."""
        with patch(
            "arguslm.server.core.litellm_client.acompletion", new_callable=AsyncMock
        ) as mock_acompletion:
            mock_acompletion.side_effect = RateLimitError(
                message="Rate limit exceeded", llm_provider="openai", model="gpt-4"
            )

            with pytest.raises(RateLimitError):
                await client.complete(model="gpt-4", messages=mock_messages, max_retries=3)

            assert mock_acompletion.call_count == 3

    @pytest.mark.asyncio
    async def test_timeout_retry(self, client, mock_messages):
        """Timeout errors should be retried."""
        mock_response = {"id": "success"}

        with patch(
            "arguslm.server.core.litellm_client.acompletion", new_callable=AsyncMock
        ) as mock_acompletion:
            mock_acompletion.side_effect = [
                Timeout(message="Request timeout", model="gpt-4", llm_provider="openai"),
                mock_response,
            ]

            response = await client.complete(model="gpt-4", messages=mock_messages)

            assert response == mock_response
            assert mock_acompletion.call_count == 2

    @pytest.mark.asyncio
    async def test_service_unavailable_retry(self, client, mock_messages):
        """Service unavailable errors should be retried."""
        mock_response = {"id": "success"}

        with patch(
            "arguslm.server.core.litellm_client.acompletion", new_callable=AsyncMock
        ) as mock_acompletion:
            mock_acompletion.side_effect = [
                ServiceUnavailableError(
                    message="Service unavailable", llm_provider="openai", model="gpt-4"
                ),
                mock_response,
            ]

            response = await client.complete(model="gpt-4", messages=mock_messages)

            assert response == mock_response
            assert mock_acompletion.call_count == 2


class TestLiteLLMClientStreaming:
    """Tests for streaming completions."""

    async def mock_stream_response(self, chunks):
        """Helper to create async iterator for streaming."""
        for chunk in chunks:
            yield chunk

    @pytest.mark.asyncio
    async def test_successful_streaming(self, client, mock_messages):
        """Test successful streaming completion."""
        mock_chunks = [
            {"choices": [{"delta": {"content": "Hello"}}]},
            {"choices": [{"delta": {"content": " world"}}]},
            {"choices": [{"delta": {"content": "!"}}]},
        ]

        with patch(
            "arguslm.server.core.litellm_client.acompletion", new_callable=AsyncMock
        ) as mock_acompletion:
            mock_acompletion.return_value = self.mock_stream_response(mock_chunks)

            chunks = []
            async for chunk in client.complete_stream(
                model="gpt-4",
                messages=mock_messages,
            ):
                chunks.append(chunk)

            assert len(chunks) == 3
            assert chunks == mock_chunks
            mock_acompletion.assert_called_once()
            call_kwargs = mock_acompletion.call_args.kwargs
            assert call_kwargs["stream"] is True

    @pytest.mark.asyncio
    async def test_streaming_authentication_error(self, client, mock_messages):
        """Streaming authentication errors should not be retried."""
        with patch(
            "arguslm.server.core.litellm_client.acompletion", new_callable=AsyncMock
        ) as mock_acompletion:
            mock_acompletion.side_effect = AuthenticationError(
                message="Invalid API key", llm_provider="openai", model="gpt-4"
            )

            with pytest.raises(AuthenticationError):
                async for _ in client.complete_stream(model="gpt-4", messages=mock_messages):
                    pass

            assert mock_acompletion.call_count == 1

    @pytest.mark.asyncio
    async def test_streaming_rate_limit_retry(self, client, mock_messages):
        """Streaming rate limit errors should be retried."""
        mock_chunks = [{"choices": [{"delta": {"content": "Success"}}]}]

        with patch(
            "arguslm.server.core.litellm_client.acompletion", new_callable=AsyncMock
        ) as mock_acompletion:
            # Fail once, then succeed
            mock_acompletion.side_effect = [
                RateLimitError(message="Rate limit exceeded", llm_provider="openai", model="gpt-4"),
                self.mock_stream_response(mock_chunks),
            ]

            chunks = []
            async for chunk in client.complete_stream(model="gpt-4", messages=mock_messages):
                chunks.append(chunk)

            assert len(chunks) == 1
            assert mock_acompletion.call_count == 2

    @pytest.mark.asyncio
    async def test_streaming_timeout_retry_exhausted(self, client, mock_messages):
        """Streaming timeout should raise after max retries."""
        with patch(
            "arguslm.server.core.litellm_client.acompletion", new_callable=AsyncMock
        ) as mock_acompletion:
            mock_acompletion.side_effect = Timeout(
                message="Request timeout", model="gpt-4", llm_provider="openai"
            )

            with pytest.raises(Timeout):
                async for _ in client.complete_stream(
                    model="gpt-4",
                    messages=mock_messages,
                    max_retries=2,
                ):
                    pass

            assert mock_acompletion.call_count == 2


class TestConvenienceFunction:
    """Tests for convenience complete() function."""

    @pytest.mark.asyncio
    async def test_convenience_complete(self, mock_messages):
        """Test convenience function creates client and completes."""
        mock_response = {"id": "test"}

        with patch(
            "arguslm.server.core.litellm_client.acompletion", new_callable=AsyncMock
        ) as mock_acompletion:
            mock_acompletion.return_value = mock_response

            response = await complete(model="gpt-4", messages=mock_messages)

            assert response == mock_response
            mock_acompletion.assert_called_once()


class TestCompletionConfig:
    """Tests for CompletionConfig dataclass."""

    def test_default_values(self):
        """Test CompletionConfig default values."""
        config = CompletionConfig(
            model="gpt-4",
            messages=[{"role": "user", "content": "test"}],
        )

        assert config.temperature == 0.7
        assert config.max_tokens is None
        assert config.stream is False
        assert config.timeout == 60.0
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.retry_multiplier == 2.0

    def test_custom_values(self):
        """Test CompletionConfig with custom values."""
        config = CompletionConfig(
            model="gpt-4",
            messages=[{"role": "user", "content": "test"}],
            temperature=0.5,
            max_tokens=100,
            stream=True,
            timeout=30.0,
            max_retries=5,
        )

        assert config.temperature == 0.5
        assert config.max_tokens == 100
        assert config.stream is True
        assert config.timeout == 30.0
        assert config.max_retries == 5


class TestExponentialBackoff:
    """Tests for exponential backoff behavior."""

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self, client, mock_messages):
        """Test that retry delays follow exponential backoff."""
        with patch(
            "arguslm.server.core.litellm_client.acompletion", new_callable=AsyncMock
        ) as mock_acompletion:
            mock_acompletion.side_effect = RateLimitError(
                message="Rate limit", llm_provider="openai", model="gpt-4"
            )

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                with pytest.raises(RateLimitError):
                    await client.complete(
                        model="gpt-4",
                        messages=mock_messages,
                        max_retries=3,
                    )

                # Should sleep twice (after 1st and 2nd attempts)
                assert mock_sleep.call_count == 2

                # Check exponential backoff: 0.1s, then 0.2s
                sleep_calls = [call.args[0] for call in mock_sleep.call_args_list]
                assert sleep_calls[0] == 0.1  # First retry delay
                assert sleep_calls[1] == 0.2  # Second retry delay (0.1 * 2)
