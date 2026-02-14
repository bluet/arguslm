"""ArgusLM — Open-source LLM monitoring & benchmarking SDK."""

from arguslm.client import ArgusLMClient, AsyncArgusLMClient
from arguslm.exceptions import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    ArgusLMError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    RateLimitError,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "ArgusLMClient",
    "AsyncArgusLMClient",
    "ArgusLMError",
    "APIError",
    "APIStatusError",
    "APIConnectionError",
    "APITimeoutError",
    "AuthenticationError",
    "BadRequestError",
    "InternalServerError",
    "NotFoundError",
    "RateLimitError",
]
