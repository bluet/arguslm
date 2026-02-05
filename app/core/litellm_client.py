"""
LiteLLM async completion wrapper with streaming, error handling, and retries.

Provides a unified interface for calling LLM APIs through LiteLLM with:
- Async streaming support
- Exponential backoff retry logic
- Comprehensive error handling
- Provider configuration mapping
- Timeout management
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Optional

import litellm
from litellm import acompletion
from litellm.exceptions import (
    APIError,
    Timeout,
    RateLimitError,
    AuthenticationError,
    BadRequestError,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)


@dataclass
class CompletionConfig:
    """Configuration for LLM completion requests."""

    model: str
    messages: List[Dict[str, str]]
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    timeout: float = 60.0
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_multiplier: float = 2.0
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LiteLLMClient:
    """
    Async wrapper for LiteLLM with streaming, error handling, and retries.

    Usage:
        client = LiteLLMClient()

        # Non-streaming
        response = await client.complete(
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}]
        )

        # Streaming
        async for chunk in client.complete_stream(
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}]
        ):
            print(chunk)
    """

    def __init__(
        self,
        default_timeout: float = 60.0,
        default_max_retries: int = 3,
        default_retry_delay: float = 1.0,
        default_retry_multiplier: float = 2.0,
    ):
        """
        Initialize LiteLLM client.

        Args:
            default_timeout: Default request timeout in seconds
            default_max_retries: Default number of retry attempts
            default_retry_delay: Initial retry delay in seconds
            default_retry_multiplier: Exponential backoff multiplier
        """
        self.default_timeout = default_timeout
        self.default_max_retries = default_max_retries
        self.default_retry_delay = default_retry_delay
        self.default_retry_multiplier = default_retry_multiplier

        # Configure LiteLLM logging
        litellm.suppress_debug_info = True

    async def complete(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute non-streaming completion with retry logic.

        Args:
            model: LiteLLM model name (e.g., "gpt-4", "anthropic/claude-3-opus")
            messages: List of message dicts with "role" and "content"
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
            max_retries: Number of retry attempts
            api_key: Optional API key override
            api_base: Optional API base URL override
            metadata: Optional metadata dict for LiteLLM
            **kwargs: Additional arguments passed to litellm.acompletion

        Returns:
            Completion response dict

        Raises:
            AuthenticationError: Invalid API credentials
            RateLimitError: Rate limit exceeded (after retries)
            Timeout: Request timeout (after retries)
            APIError: Other API errors
        """
        config = CompletionConfig(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
            timeout=timeout or self.default_timeout,
            max_retries=max_retries or self.default_max_retries,
            retry_delay=self.default_retry_delay,
            retry_multiplier=self.default_retry_multiplier,
            api_key=api_key,
            api_base=api_base,
            metadata=metadata,
        )

        return await self._execute_with_retry(config, **kwargs)

    async def complete_stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute streaming completion with retry logic.

        Args:
            model: LiteLLM model name
            messages: List of message dicts
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
            max_retries: Number of retry attempts
            api_key: Optional API key override
            api_base: Optional API base URL override
            metadata: Optional metadata dict
            **kwargs: Additional arguments passed to litellm.acompletion

        Yields:
            Streaming response chunks

        Raises:
            AuthenticationError: Invalid API credentials
            RateLimitError: Rate limit exceeded (after retries)
            Timeout: Request timeout (after retries)
            APIError: Other API errors
        """
        config = CompletionConfig(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            timeout=timeout or self.default_timeout,
            max_retries=max_retries or self.default_max_retries,
            retry_delay=self.default_retry_delay,
            retry_multiplier=self.default_retry_multiplier,
            api_key=api_key,
            api_base=api_base,
            metadata=metadata,
        )

        async for chunk in self._execute_stream_with_retry(config, **kwargs):
            yield chunk

    async def _execute_with_retry(
        self,
        config: CompletionConfig,
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute non-streaming completion with exponential backoff retry."""
        last_exception = None
        retry_delay = config.retry_delay

        for attempt in range(config.max_retries):
            try:
                logger.debug(
                    f"Completion attempt {attempt + 1}/{config.max_retries} "
                    f"for model {config.model}"
                )

                # Build kwargs, omitting None api_key/api_base (for local providers like LM Studio)
                completion_kwargs = {
                    "model": config.model,
                    "messages": config.messages,
                    "temperature": config.temperature,
                    "max_tokens": config.max_tokens,
                    "stream": False,
                    "timeout": config.timeout,
                    "metadata": config.metadata,
                    **kwargs,
                }
                if config.api_key:
                    completion_kwargs["api_key"] = config.api_key
                if config.api_base:
                    completion_kwargs["api_base"] = config.api_base

                response = await acompletion(**completion_kwargs)

                logger.debug(f"Completion successful for model {config.model}")
                return response

            except AuthenticationError as e:
                # Don't retry authentication errors
                logger.error(f"Authentication failed for model {config.model}: {e}")
                raise

            except BadRequestError as e:
                # Don't retry bad requests (invalid parameters)
                logger.error(f"Bad request for model {config.model}: {e}")
                raise

            except (RateLimitError, Timeout, ServiceUnavailableError, APIError) as e:
                last_exception = e

                if attempt < config.max_retries - 1:
                    logger.warning(
                        f"Attempt {attempt + 1} failed for model {config.model}: {e}. "
                        f"Retrying in {retry_delay}s..."
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay *= config.retry_multiplier
                else:
                    logger.error(
                        f"All {config.max_retries} attempts failed for model {config.model}: {e}"
                    )

            except Exception as e:
                # Catch unexpected errors
                logger.error(f"Unexpected error for model {config.model}: {e}")
                raise RuntimeError(f"Unexpected error: {e}") from e

        # If we exhausted all retries, raise the last exception
        if last_exception:
            raise last_exception

        raise RuntimeError(f"Completion failed after all retry attempts for model {config.model}")

    async def _execute_stream_with_retry(
        self,
        config: CompletionConfig,
        **kwargs,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Execute streaming completion with exponential backoff retry."""
        last_exception = None
        retry_delay = config.retry_delay

        for attempt in range(config.max_retries):
            try:
                logger.debug(
                    f"Streaming attempt {attempt + 1}/{config.max_retries} for model {config.model}"
                )

                # Build kwargs, omitting None api_key/api_base (for local providers like LM Studio)
                stream_kwargs = {
                    "model": config.model,
                    "messages": config.messages,
                    "temperature": config.temperature,
                    "max_tokens": config.max_tokens,
                    "stream": True,
                    "timeout": config.timeout,
                    "metadata": config.metadata,
                    **kwargs,
                }
                if config.api_key:
                    stream_kwargs["api_key"] = config.api_key
                if config.api_base:
                    stream_kwargs["api_base"] = config.api_base

                response = await acompletion(**stream_kwargs)

                # Stream chunks
                async for chunk in response:
                    yield chunk

                logger.debug(f"Streaming completed for model {config.model}")
                return  # Success, exit retry loop

            except AuthenticationError as e:
                logger.error(f"Authentication failed for model {config.model}: {e}")
                raise

            except BadRequestError as e:
                logger.error(f"Bad request for model {config.model}: {e}")
                raise

            except (RateLimitError, Timeout, ServiceUnavailableError, APIError) as e:
                last_exception = e

                if attempt < config.max_retries - 1:
                    logger.warning(
                        f"Streaming attempt {attempt + 1} failed for model {config.model}: {e}. "
                        f"Retrying in {retry_delay}s..."
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay *= config.retry_multiplier
                else:
                    logger.error(
                        f"All {config.max_retries} streaming attempts failed for model {config.model}: {e}"
                    )

            except Exception as e:
                logger.error(f"Unexpected streaming error for model {config.model}: {e}")
                raise RuntimeError(f"Unexpected streaming error: {e}") from e

        # If we exhausted all retries, raise the last exception
        if last_exception:
            raise last_exception

        raise RuntimeError(f"Streaming failed after all retry attempts for model {config.model}")


# Convenience function for quick usage
async def complete(
    model: str,
    messages: List[Dict[str, str]],
    **kwargs,
) -> Dict[str, Any]:
    """
    Convenience function for one-off completions.

    Args:
        model: LiteLLM model name
        messages: List of message dicts
        **kwargs: Additional arguments

    Returns:
        Completion response dict
    """
    client = LiteLLMClient()
    return await client.complete(model=model, messages=messages, **kwargs)
