"""Tests for uptime health checks."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.core.uptime import check_uptime
from app.models.model import Model
from app.models.monitoring import UptimeCheck


@pytest.fixture
def mock_model():
    """Create a mock model for testing."""
    model = Model(
        id=uuid.uuid4(),
        provider_account_id=uuid.uuid4(),
        model_id="gpt-4o",
        source="discovered",
        enabled_for_monitoring=True,
    )
    return model


@pytest.mark.asyncio
async def test_check_uptime_success(mock_model):
    """Test successful uptime check."""
    with patch("app.core.uptime.complete") as mock_complete:
        mock_complete.return_value = {
            "choices": [{"message": {"content": "Hi"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }

        result = await check_uptime(mock_model)

        assert isinstance(result, UptimeCheck)
        assert result.model_id == mock_model.id
        assert result.status == "up"
        assert result.latency_ms is not None
        assert result.latency_ms > 0
        assert result.error is None


@pytest.mark.asyncio
async def test_check_uptime_timeout(mock_model):
    """Test uptime check with timeout."""
    with patch("app.core.uptime.complete") as mock_complete:
        mock_complete.side_effect = TimeoutError("Request timed out")

        result = await check_uptime(mock_model)

        assert isinstance(result, UptimeCheck)
        assert result.model_id == mock_model.id
        assert result.status == "down"
        assert result.latency_ms is None
        assert "timed out" in result.error.lower()


@pytest.mark.asyncio
async def test_check_uptime_auth_error(mock_model):
    """Test uptime check with authentication error."""
    with patch("app.core.uptime.complete") as mock_complete:
        mock_complete.side_effect = Exception("Authentication failed")

        result = await check_uptime(mock_model)

        assert isinstance(result, UptimeCheck)
        assert result.model_id == mock_model.id
        assert result.status == "down"
        assert result.latency_ms is None
        assert "Authentication failed" in result.error


@pytest.mark.asyncio
async def test_check_uptime_service_unavailable(mock_model):
    """Test uptime check with service unavailable."""
    with patch("app.core.uptime.complete") as mock_complete:
        mock_complete.side_effect = Exception("Service unavailable")

        result = await check_uptime(mock_model)

        assert isinstance(result, UptimeCheck)
        assert result.model_id == mock_model.id
        assert result.status == "down"
        assert result.error == "Service unavailable"


@pytest.mark.asyncio
async def test_check_uptime_latency_recorded(mock_model):
    """Test that latency is correctly recorded for successful checks."""
    with patch("app.core.uptime.complete") as mock_complete:
        mock_complete.return_value = {
            "choices": [{"message": {"content": "Hi"}}],
        }

        result = await check_uptime(mock_model)

        assert result.status == "up"
        assert result.latency_ms is not None
        assert isinstance(result.latency_ms, float)
        assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_check_uptime_no_latency_on_failure(mock_model):
    """Test that latency is not recorded for failed checks."""
    with patch("app.core.uptime.complete") as mock_complete:
        mock_complete.side_effect = Exception("Connection error")

        result = await check_uptime(mock_model)

        assert result.status == "down"
        assert result.latency_ms is None
        assert result.error is not None


@pytest.mark.asyncio
async def test_check_uptime_uses_minimal_tokens(mock_model):
    """Test that uptime check uses minimal tokens (max_tokens=1)."""
    with patch("app.core.uptime.complete") as mock_complete:
        mock_complete.return_value = {
            "choices": [{"message": {"content": "Hi"}}],
        }

        await check_uptime(mock_model)

        # Verify the call was made with max_tokens=1
        mock_complete.assert_called_once()
        call_kwargs = mock_complete.call_args[1]
        assert call_kwargs["max_tokens"] == 1


@pytest.mark.asyncio
async def test_check_uptime_uses_timeout(mock_model):
    """Test that uptime check uses 10 second timeout."""
    with patch("app.core.uptime.complete") as mock_complete:
        mock_complete.return_value = {
            "choices": [{"message": {"content": "Hi"}}],
        }

        await check_uptime(mock_model)

        # Verify the call was made with timeout=10
        mock_complete.assert_called_once()
        call_kwargs = mock_complete.call_args[1]
        assert call_kwargs["timeout"] == 10


@pytest.mark.asyncio
async def test_check_uptime_uses_simple_prompt(mock_model):
    """Test that uptime check uses simple 'Hi' prompt."""
    with patch("app.core.uptime.complete") as mock_complete:
        mock_complete.return_value = {
            "choices": [{"message": {"content": "Hi"}}],
        }

        await check_uptime(mock_model)

        # Verify the call was made with simple prompt
        mock_complete.assert_called_once()
        call_kwargs = mock_complete.call_args[1]
        assert call_kwargs["messages"] == [{"role": "user", "content": "Hi"}]


@pytest.mark.asyncio
async def test_check_uptime_uses_correct_model_id(mock_model):
    """Test that uptime check uses the model's model_id."""
    with patch("app.core.uptime.complete") as mock_complete:
        mock_complete.return_value = {
            "choices": [{"message": {"content": "Hi"}}],
        }

        await check_uptime(mock_model)

        # Verify the call was made with correct model_id
        mock_complete.assert_called_once()
        call_kwargs = mock_complete.call_args[1]
        assert call_kwargs["model"] == mock_model.model_id
