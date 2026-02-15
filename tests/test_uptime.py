"""Tests for uptime health checks."""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from arguslm.server.core.uptime import check_uptime
from arguslm.server.models.model import Model
from arguslm.server.models.monitoring import UptimeCheck


async def _mock_stream(*chunks):
    for chunk in chunks:
        yield chunk


@pytest.fixture
def mock_model():
    provider_account = MagicMock()
    provider_account.provider_type = "openai"
    provider_account.credentials = {"api_key": "test-key"}

    model = Model(
        id=uuid.uuid4(),
        provider_account_id=uuid.uuid4(),
        model_id="gpt-4o",
        source="discovered",
        enabled_for_monitoring=True,
    )
    model.provider_account = provider_account
    return model


@pytest.fixture(autouse=True)
def _patch_providers():
    with patch(
        "arguslm.server.core.uptime.get_litellm_model_name",
        return_value="openai/gpt-4o",
    ):
        yield


@pytest.mark.asyncio
async def test_check_uptime_success(mock_model):
    chunks = [
        {"choices": [{"delta": {"content": "Hello"}}]},
        {"choices": [{"delta": {"content": " world"}}]},
    ]
    with patch("arguslm.server.core.uptime.LiteLLMClient") as cls:
        cls.return_value.complete_stream = MagicMock(return_value=_mock_stream(*chunks))
        result = await check_uptime(mock_model)

    assert isinstance(result, UptimeCheck)
    assert result.model_id == mock_model.id
    assert result.status == "up"
    assert result.latency_ms is not None
    assert result.latency_ms > 0
    assert result.error is None


@pytest.mark.asyncio
async def test_check_uptime_timeout(mock_model):
    with patch("arguslm.server.core.uptime.LiteLLMClient") as cls:
        cls.return_value.complete_stream = MagicMock(side_effect=TimeoutError("Request timed out"))
        result = await check_uptime(mock_model)

    assert isinstance(result, UptimeCheck)
    assert result.model_id == mock_model.id
    assert result.status == "down"
    assert result.latency_ms is None
    assert "timed out" in result.error.lower()


@pytest.mark.asyncio
async def test_check_uptime_auth_error(mock_model):
    with patch("arguslm.server.core.uptime.LiteLLMClient") as cls:
        cls.return_value.complete_stream = MagicMock(
            side_effect=Exception("Authentication failed"),
        )
        result = await check_uptime(mock_model)

    assert isinstance(result, UptimeCheck)
    assert result.model_id == mock_model.id
    assert result.status == "down"
    assert result.latency_ms is None
    assert "Authentication failed" in result.error


@pytest.mark.asyncio
async def test_check_uptime_service_unavailable(mock_model):
    with patch("arguslm.server.core.uptime.LiteLLMClient") as cls:
        cls.return_value.complete_stream = MagicMock(
            side_effect=Exception("Service unavailable"),
        )
        result = await check_uptime(mock_model)

    assert isinstance(result, UptimeCheck)
    assert result.model_id == mock_model.id
    assert result.status == "down"
    assert result.error == "Service unavailable"


@pytest.mark.asyncio
async def test_check_uptime_latency_recorded(mock_model):
    chunks = [{"choices": [{"delta": {"content": "Hi"}}]}]
    with patch("arguslm.server.core.uptime.LiteLLMClient") as cls:
        cls.return_value.complete_stream = MagicMock(return_value=_mock_stream(*chunks))
        result = await check_uptime(mock_model)

    assert result.status == "up"
    assert result.latency_ms is not None
    assert isinstance(result.latency_ms, float)
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_check_uptime_no_latency_on_failure(mock_model):
    with patch("arguslm.server.core.uptime.LiteLLMClient") as cls:
        cls.return_value.complete_stream = MagicMock(
            side_effect=Exception("Connection error"),
        )
        result = await check_uptime(mock_model)

    assert result.status == "down"
    assert result.latency_ms is None
    assert result.error is not None


@pytest.mark.asyncio
async def test_check_uptime_uses_max_tokens(mock_model):
    chunks = [{"choices": [{"delta": {"content": "Hi"}}]}]
    with patch("arguslm.server.core.uptime.LiteLLMClient") as cls:
        cls.return_value.complete_stream = MagicMock(return_value=_mock_stream(*chunks))
        await check_uptime(mock_model)

        cls.return_value.complete_stream.assert_called_once()
        call_kwargs = cls.return_value.complete_stream.call_args[1]
        assert call_kwargs["max_tokens"] == 100


@pytest.mark.asyncio
async def test_check_uptime_uses_timeout(mock_model):
    chunks = [{"choices": [{"delta": {"content": "Hi"}}]}]
    with patch("arguslm.server.core.uptime.LiteLLMClient") as cls:
        cls.return_value.complete_stream = MagicMock(return_value=_mock_stream(*chunks))
        await check_uptime(mock_model)

        cls.return_value.complete_stream.assert_called_once()
        call_kwargs = cls.return_value.complete_stream.call_args[1]
        assert call_kwargs["timeout"] == 15


@pytest.mark.asyncio
async def test_check_uptime_uses_health_check_prompt(mock_model):
    chunks = [{"choices": [{"delta": {"content": "Hi"}}]}]
    with patch("arguslm.server.core.uptime.LiteLLMClient") as cls:
        cls.return_value.complete_stream = MagicMock(return_value=_mock_stream(*chunks))
        await check_uptime(mock_model)

        cls.return_value.complete_stream.assert_called_once()
        call_kwargs = cls.return_value.complete_stream.call_args[1]
        messages = call_kwargs["messages"]
        assert messages[0]["role"] == "user"
        assert "Count from 1 to 20" in messages[0]["content"]


@pytest.mark.asyncio
async def test_check_uptime_uses_correct_model_id(mock_model):
    chunks = [{"choices": [{"delta": {"content": "Hi"}}]}]
    with patch("arguslm.server.core.uptime.LiteLLMClient") as cls:
        cls.return_value.complete_stream = MagicMock(return_value=_mock_stream(*chunks))
        await check_uptime(mock_model)

        cls.return_value.complete_stream.assert_called_once()
        call_kwargs = cls.return_value.complete_stream.call_args[1]
        assert call_kwargs["model"] == "openai/gpt-4o"
