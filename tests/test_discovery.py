"""Tests for model discovery adapters."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.discovery.base import ModelDescriptor
from app.discovery.ollama import OllamaModelSource
from app.discovery.openai import OpenAIModelSource
from app.discovery.static import (
    ANTHROPIC_MODELS,
    GOOGLE_GEMINI_MODELS,
    MISTRAL_MODELS,
    StaticModelSource,
    get_source_for_provider,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_openai_account():
    """Create mock OpenAI provider account."""
    account = MagicMock()
    account.provider_type = "openai"
    account.display_name = "OpenAI Main"
    account.credentials = {"api_key": "sk-test-key"}
    return account


@pytest.fixture
def mock_ollama_account():
    """Create mock Ollama provider account."""
    account = MagicMock()
    account.provider_type = "ollama"
    account.display_name = "Local Ollama"
    account.credentials = {}
    return account


@pytest.fixture
def mock_anthropic_account():
    """Create mock Anthropic provider account."""
    account = MagicMock()
    account.provider_type = "anthropic"
    account.display_name = "Anthropic Main"
    account.credentials = {"api_key": "sk-ant-test"}
    return account


@pytest.fixture
def mock_mistral_account():
    """Create mock Mistral provider account."""
    account = MagicMock()
    account.provider_type = "mistral"
    account.display_name = "Mistral Main"
    account.credentials = {"api_key": "mistral-key"}
    return account


# ============================================================================
# OpenAI Model Source Tests
# ============================================================================


class TestOpenAIModelSource:
    """Tests for OpenAI-compatible model source."""

    @pytest.mark.asyncio
    async def test_list_models_success(self, mock_openai_account):
        """Test successful model listing from OpenAI."""
        source = OpenAIModelSource()

        mock_response_data = {
            "data": [
                {"id": "gpt-4o", "owned_by": "openai", "created": 1699999999},
                {"id": "gpt-4o-mini", "owned_by": "openai", "created": 1699999998},
                {"id": "gpt-3.5-turbo", "owned_by": "openai", "created": 1699999997},
            ]
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            models = await source.list_models(mock_openai_account)

        assert len(models) == 3
        assert models[0].id == "gpt-4o"
        assert models[0].provider_type == "openai"
        assert models[0].owned_by == "openai"
        assert models[0].created == 1699999999

    @pytest.mark.asyncio
    async def test_list_models_http_error(self, mock_openai_account, caplog):
        """Test HTTP error handling returns empty list."""
        source = OpenAIModelSource()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                message="401 Unauthorized",
                request=MagicMock(),
                response=mock_response,
            )
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with caplog.at_level(logging.ERROR):
                models = await source.list_models(mock_openai_account)

        assert models == []
        assert "HTTP error" in caplog.text

    @pytest.mark.asyncio
    async def test_list_models_connection_error(self, mock_openai_account, caplog):
        """Test connection error handling returns empty list."""
        source = OpenAIModelSource()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.RequestError("Connection refused"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with caplog.at_level(logging.ERROR):
                models = await source.list_models(mock_openai_account)

        assert models == []
        assert "Request error" in caplog.text

    @pytest.mark.asyncio
    async def test_list_models_custom_base_url(self, mock_openai_account):
        """Test custom base_url from credentials is used."""
        source = OpenAIModelSource()
        mock_openai_account.credentials = {
            "api_key": "sk-test",
            "base_url": "https://custom.api.com/v1",
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {"data": []}
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            await source.list_models(mock_openai_account)

            # Verify custom URL was used
            mock_client.get.assert_called_once()
            call_url = mock_client.get.call_args[0][0]
            assert call_url == "https://custom.api.com/v1/models"

    def test_supports_discovery(self):
        """Test OpenAI source supports discovery."""
        source = OpenAIModelSource()
        assert source.supports_discovery() is True

    @pytest.mark.asyncio
    async def test_list_models_no_base_url(self, caplog):
        """Test error when provider has no base URL configured."""
        source = OpenAIModelSource()
        account = MagicMock()
        account.provider_type = "unknown_provider"
        account.display_name = "Unknown"
        account.credentials = {"api_key": "test"}

        with caplog.at_level(logging.ERROR):
            models = await source.list_models(account)

        assert models == []
        assert "No base_url configured" in caplog.text


# ============================================================================
# Ollama Model Source Tests
# ============================================================================


class TestOllamaModelSource:
    """Tests for Ollama model source."""

    @pytest.mark.asyncio
    async def test_list_models_success(self, mock_ollama_account):
        """Test successful model listing from Ollama."""
        source = OllamaModelSource()

        mock_response_data = {
            "models": [
                {
                    "name": "llama3:8b",
                    "size": 3338801804,
                    "digest": "abc123",
                    "modified_at": "2025-01-01T00:00:00Z",
                    "details": {
                        "format": "gguf",
                        "family": "llama",
                        "parameter_size": "8B",
                        "quantization_level": "Q4_K_M",
                    },
                },
                {
                    "name": "gemma3",
                    "size": 2000000000,
                    "digest": "def456",
                    "details": {"format": "gguf", "family": "gemma"},
                },
            ]
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            models = await source.list_models(mock_ollama_account)

        assert len(models) == 2
        assert models[0].id == "llama3:8b"
        assert models[0].provider_type == "ollama"
        assert models[0].metadata["family"] == "llama"
        assert models[0].metadata["parameter_size"] == "8B"
        assert models[1].id == "gemma3"

    @pytest.mark.asyncio
    async def test_list_models_custom_url(self, mock_ollama_account):
        """Test custom Ollama URL from credentials."""
        source = OllamaModelSource()
        mock_ollama_account.credentials = {"base_url": "http://remote-ollama:11434"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {"models": []}
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            await source.list_models(mock_ollama_account)

            call_url = mock_client.get.call_args[0][0]
            assert call_url == "http://remote-ollama:11434/api/tags"

    @pytest.mark.asyncio
    async def test_list_models_connection_error(self, mock_ollama_account, caplog):
        """Test connection error when Ollama not running."""
        source = OllamaModelSource()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with caplog.at_level(logging.WARNING):
                models = await source.list_models(mock_ollama_account)

        assert models == []
        assert "Cannot connect to Ollama" in caplog.text

    def test_supports_discovery(self):
        """Test Ollama source supports discovery."""
        source = OllamaModelSource()
        assert source.supports_discovery() is True


# ============================================================================
# Static Model Source Tests
# ============================================================================


class TestStaticModelSource:
    """Tests for static/curated model source."""

    @pytest.mark.asyncio
    async def test_list_anthropic_models(self, mock_anthropic_account):
        """Test Anthropic curated model list."""
        source = StaticModelSource("anthropic")
        models = await source.list_models(mock_anthropic_account)

        assert len(models) == len(ANTHROPIC_MODELS)
        model_ids = [m.id for m in models]
        assert "claude-3-5-sonnet-20241022" in model_ids
        assert "claude-3-opus-20240229" in model_ids
        assert all(m.provider_type == "anthropic" for m in models)
        assert all(m.owned_by == "anthropic" for m in models)

    @pytest.mark.asyncio
    async def test_list_mistral_models(self, mock_mistral_account):
        """Test Mistral curated model list."""
        source = StaticModelSource("mistral")
        models = await source.list_models(mock_mistral_account)

        assert len(models) == len(MISTRAL_MODELS)
        model_ids = [m.id for m in models]
        assert "mistral-large-latest" in model_ids
        assert "codestral-latest" in model_ids

    @pytest.mark.asyncio
    async def test_list_google_gemini_models(self):
        """Test Google Gemini curated model list."""
        account = MagicMock()
        account.provider_type = "google_gemini"
        account.display_name = "Gemini API"
        account.credentials = {}

        source = StaticModelSource("google_gemini")
        models = await source.list_models(account)

        assert len(models) == len(GOOGLE_GEMINI_MODELS)
        model_ids = [m.id for m in models]
        assert "gemini-2.0-flash-exp" in model_ids
        assert "gemini-1.5-pro" in model_ids

    @pytest.mark.asyncio
    async def test_list_unknown_provider(self, caplog):
        """Test unknown provider returns empty list with warning."""
        account = MagicMock()
        account.provider_type = "unknown_provider"
        account.display_name = "Unknown"
        account.credentials = {}

        source = StaticModelSource("unknown_provider")

        with caplog.at_level(logging.WARNING):
            models = await source.list_models(account)

        assert models == []
        assert "No curated model registry" in caplog.text

    def test_supports_discovery(self):
        """Test static source does not support discovery."""
        source = StaticModelSource("anthropic")
        assert source.supports_discovery() is False


class TestGetSourceForProvider:
    """Tests for get_source_for_provider factory function."""

    def test_anthropic_returns_static_source(self):
        """Test Anthropic gets static source."""
        source = get_source_for_provider("anthropic")
        assert isinstance(source, StaticModelSource)
        assert source.provider_type == "anthropic"

    def test_mistral_returns_static_source(self):
        """Test Mistral gets static source."""
        source = get_source_for_provider("mistral")
        assert isinstance(source, StaticModelSource)
        assert source.provider_type == "mistral"

    def test_openai_returns_none(self):
        """Test OpenAI returns None (uses OpenAIModelSource directly)."""
        source = get_source_for_provider("openai")
        assert source is None

    def test_unknown_returns_none(self):
        """Test unknown provider returns None."""
        source = get_source_for_provider("unknown")
        assert source is None


# ============================================================================
# ModelDescriptor Tests
# ============================================================================


class TestModelDescriptor:
    """Tests for ModelDescriptor dataclass."""

    def test_create_descriptor(self):
        """Test creating model descriptor."""
        descriptor = ModelDescriptor(
            id="gpt-4o",
            provider_type="openai",
            owned_by="openai",
            created=1699999999,
            metadata={"capabilities": ["chat", "function_calling"]},
        )

        assert descriptor.id == "gpt-4o"
        assert descriptor.provider_type == "openai"
        assert descriptor.owned_by == "openai"
        assert descriptor.created == 1699999999
        assert descriptor.metadata["capabilities"] == ["chat", "function_calling"]

    def test_create_minimal_descriptor(self):
        """Test creating descriptor with minimal fields."""
        descriptor = ModelDescriptor(id="llama3:8b", provider_type="ollama")

        assert descriptor.id == "llama3:8b"
        assert descriptor.provider_type == "ollama"
        assert descriptor.owned_by is None
        assert descriptor.created is None
        assert descriptor.metadata == {}
