"""ArgusLM SDK exceptions."""

from __future__ import annotations

from typing import Any

import httpx


class ArgusLMError(Exception):
    """Base exception for all ArgusLM SDK errors."""


class APIError(ArgusLMError):
    """Raised when an API request fails."""

    message: str
    request: httpx.Request

    def __init__(self, message: str, *, request: httpx.Request) -> None:
        super().__init__(message)
        self.message = message
        self.request = request


class APIStatusError(APIError):
    """Raised when the API returns an HTTP error status (4xx or 5xx)."""

    response: httpx.Response
    status_code: int
    body: Any

    def __init__(self, message: str, *, response: httpx.Response, body: Any = None) -> None:
        super().__init__(message, request=response.request)
        self.response = response
        self.status_code = response.status_code
        self.body = body

    @classmethod
    def from_response(cls, response: httpx.Response) -> APIStatusError:
        try:
            body = response.json()
            detail = body.get("detail", response.text)
        except Exception:
            body = None
            detail = response.text

        message = f"HTTP {response.status_code}: {detail}"

        status_to_class: dict[int, type[APIStatusError]] = {
            400: BadRequestError,
            401: AuthenticationError,
            403: PermissionDeniedError,
            404: NotFoundError,
            409: ConflictError,
            422: UnprocessableEntityError,
            429: RateLimitError,
        }

        error_cls = status_to_class.get(response.status_code, APIStatusError)
        if error_cls is APIStatusError and response.status_code >= 500:
            error_cls = InternalServerError

        return error_cls(message, response=response, body=body)


class APIConnectionError(APIError):
    """Raised when the client cannot connect to the API."""

    def __init__(self, *, message: str = "Connection error.", request: httpx.Request) -> None:
        super().__init__(message, request=request)


class APITimeoutError(APIConnectionError):
    """Raised when an API request times out."""

    def __init__(self, request: httpx.Request) -> None:
        super().__init__(message="Request timed out.", request=request)


class BadRequestError(APIStatusError):
    """HTTP 400."""


class AuthenticationError(APIStatusError):
    """HTTP 401."""


class PermissionDeniedError(APIStatusError):
    """HTTP 403."""


class NotFoundError(APIStatusError):
    """HTTP 404."""


class ConflictError(APIStatusError):
    """HTTP 409."""


class UnprocessableEntityError(APIStatusError):
    """HTTP 422."""


class RateLimitError(APIStatusError):
    """HTTP 429."""


class InternalServerError(APIStatusError):
    """HTTP 5xx."""
