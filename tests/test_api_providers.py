"""Tests for Provider Account CRUD API endpoints."""

import os
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from arguslm.server.core.security import CredentialEncryption
from arguslm.server.db.init import get_db
from arguslm.server.main import app
from arguslm.server.models.base import Base
from arguslm.server.models.benchmark import BenchmarkResult
from arguslm.server.models.model import Model
from arguslm.server.models.provider import ProviderAccount

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Test encryption key
TEST_ENCRYPTION_KEY = CredentialEncryption.generate_key()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session.

    Yields:
        AsyncSession for testing.
    """
    # Set encryption key for tests
    os.environ["ENCRYPTION_KEY"] = TEST_ENCRYPTION_KEY

    # Create async engine
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Provide session
    async with async_session() as session:
        yield session

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
def client(db_session: AsyncSession) -> TestClient:
    """Create test client with database session override.

    Args:
        db_session: Test database session

    Returns:
        TestClient instance
    """

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_provider(client: TestClient) -> None:
    """Test creating a provider account."""
    response = client.post(
        "/api/v1/providers",
        json={
            "provider_type": "openai",
            "display_name": "OpenAI Production",
            "credentials": {"api_key": "sk-test-key-12345"},
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["provider_type"] == "openai"
    assert data["display_name"] == "OpenAI Production"
    assert data["enabled"] is True
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    # Credentials should NOT be in response
    assert "credentials" not in data
    assert "credentials_encrypted" not in data


@pytest.mark.asyncio
async def test_list_providers(client: TestClient, db_session: AsyncSession) -> None:
    """Test listing all provider accounts."""
    # Create test providers
    provider1 = ProviderAccount(
        provider_type="openai",
        display_name="OpenAI Test",
        enabled=True,
    )
    provider1.credentials = {"api_key": "test1"}

    provider2 = ProviderAccount(
        provider_type="anthropic",
        display_name="Anthropic Test",
        enabled=False,
    )
    provider2.credentials = {"api_key": "test2"}

    db_session.add(provider1)
    db_session.add(provider2)
    await db_session.commit()

    response = client.get("/api/v1/providers")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["providers"]) == 2

    # Verify no credentials in response
    for provider in data["providers"]:
        assert "credentials" not in provider
        assert "credentials_encrypted" not in provider


@pytest.mark.asyncio
async def test_get_provider(client: TestClient, db_session: AsyncSession) -> None:
    """Test getting a single provider account by ID."""
    # Create test provider
    provider = ProviderAccount(
        provider_type="openai",
        display_name="Test Provider",
        enabled=True,
    )
    provider.credentials = {"api_key": "test-key"}

    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)

    response = client.get(f"/api/v1/providers/{provider.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(provider.id)
    assert data["provider_type"] == "openai"
    assert data["display_name"] == "Test Provider"
    assert data["enabled"] is True
    # Credentials should NOT be in response
    assert "credentials" not in data


@pytest.mark.asyncio
async def test_get_provider_not_found(client: TestClient) -> None:
    """Test getting a non-existent provider returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/providers/{fake_id}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_update_provider(client: TestClient, db_session: AsyncSession) -> None:
    """Test updating a provider account."""
    # Create test provider
    provider = ProviderAccount(
        provider_type="openai",
        display_name="Original Name",
        enabled=True,
    )
    provider.credentials = {"api_key": "old-key"}

    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)

    # Update provider
    response = client.patch(
        f"/api/v1/providers/{provider.id}",
        json={
            "display_name": "Updated Name",
            "credentials": {"api_key": "new-key", "org": "test-org"},
            "enabled": False,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "Updated Name"
    assert data["enabled"] is False

    # Verify credentials were updated in database
    await db_session.refresh(provider)
    assert provider.credentials["api_key"] == "new-key"
    assert provider.credentials["org"] == "test-org"


@pytest.mark.asyncio
async def test_update_provider_partial(client: TestClient, db_session: AsyncSession) -> None:
    """Test partial update of provider account."""
    # Create test provider
    provider = ProviderAccount(
        provider_type="openai",
        display_name="Original Name",
        enabled=True,
    )
    provider.credentials = {"api_key": "original-key"}

    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)

    # Update only display_name
    response = client.patch(
        f"/api/v1/providers/{provider.id}",
        json={"display_name": "New Name Only"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "New Name Only"
    assert data["enabled"] is True  # Should remain unchanged

    # Verify credentials unchanged
    await db_session.refresh(provider)
    assert provider.credentials["api_key"] == "original-key"


@pytest.mark.asyncio
async def test_delete_provider_no_history(client: TestClient, db_session: AsyncSession) -> None:
    """Test deleting a provider with no benchmark history."""
    # Create test provider
    provider = ProviderAccount(
        provider_type="openai",
        display_name="To Delete",
        enabled=True,
    )
    provider.credentials = {"api_key": "test"}

    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)

    provider_id = provider.id

    # Delete provider
    response = client.delete(f"/api/v1/providers/{provider_id}")

    assert response.status_code == 204

    # Verify provider was deleted
    response = client.get(f"/api/v1/providers/{provider_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_provider_with_history(client: TestClient, db_session: AsyncSession) -> None:
    """Test deleting a provider with benchmark history returns 409."""
    from datetime import datetime, timezone

    from arguslm.server.models.benchmark import BenchmarkRun

    # Create test provider
    provider = ProviderAccount(
        provider_type="openai",
        display_name="Has History",
        enabled=True,
    )
    provider.credentials = {"api_key": "test"}

    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)

    # Create model with benchmark result
    model = Model(
        provider_account_id=provider.id,
        model_id="gpt-4",
        source="discovered",
        enabled_for_benchmark=True,
        model_metadata={},
    )
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)

    # Create benchmark run first
    benchmark_run = BenchmarkRun(
        name="Test Run",
        model_ids=["gpt-4"],
        prompt_pack="standard",
        status="completed",
        triggered_by="user",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(benchmark_run)
    await db_session.commit()
    await db_session.refresh(benchmark_run)

    # Create benchmark result
    benchmark = BenchmarkResult(
        run_id=benchmark_run.id,
        model_id=model.id,
        ttft_ms=200.0,
        tps=100.0,
        tps_excluding_ttft=120.0,
        total_latency_ms=1500.0,
        input_tokens=100,
        output_tokens=50,
        estimated_cost=0.01,
        error=None,
    )
    db_session.add(benchmark)
    await db_session.commit()

    # Try to delete provider
    response = client.delete(f"/api/v1/providers/{provider.id}")

    assert response.status_code == 409
    assert "benchmark history" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_test_provider_connection_success(
    client: TestClient, db_session: AsyncSession
) -> None:
    """Test provider connection test endpoint with successful connection."""
    # Create test provider
    provider = ProviderAccount(
        provider_type="openai",
        display_name="Test Connection",
        enabled=True,
    )
    provider.credentials = {"api_key": "test-key"}

    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)

    # Mock LiteLLM client
    with patch("arguslm.server.api.providers.LiteLLMClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(return_value={"id": "test-response-id", "choices": []})
        mock_client_class.return_value = mock_client

        response = client.post(f"/api/v1/providers/{provider.id}/test")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "successfully connected" in data["message"].lower()
        assert data["details"]["model_tested"] == "gpt-3.5-turbo"


@pytest.mark.asyncio
async def test_test_provider_connection_failure(
    client: TestClient, db_session: AsyncSession
) -> None:
    """Test provider connection test endpoint with failed connection."""
    # Create test provider
    provider = ProviderAccount(
        provider_type="openai",
        display_name="Test Connection Fail",
        enabled=True,
    )
    provider.credentials = {"api_key": "invalid-key"}

    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)

    # Mock LiteLLM client to raise exception
    with patch("arguslm.server.api.providers.LiteLLMClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(side_effect=Exception("Authentication failed"))
        mock_client_class.return_value = mock_client

        response = client.post(f"/api/v1/providers/{provider.id}/test")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "failed" in data["message"].lower()


@pytest.mark.asyncio
async def test_refresh_provider_models(client: TestClient, db_session: AsyncSession) -> None:
    """Test refreshing models for a provider."""
    # Create test provider
    provider = ProviderAccount(
        provider_type="openai",
        display_name="Refresh Models",
        enabled=True,
    )
    provider.credentials = {"api_key": "test-key"}

    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)

    # Mock OpenAIModelSource
    with patch("arguslm.server.api.providers.OpenAIModelSource") as mock_source_class:
        mock_source = AsyncMock()
        mock_source.list_models = AsyncMock(
            return_value=[
                MagicMock(id="gpt-4", provider_type="openai", metadata={}),
                MagicMock(id="gpt-3.5-turbo", provider_type="openai", metadata={}),
            ]
        )
        mock_source_class.return_value = mock_source

        response = client.post(f"/api/v1/providers/{provider.id}/refresh-models")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["models_discovered"] == 2
        assert "2 new" in data["message"]


@pytest.mark.asyncio
async def test_refresh_provider_models_unsupported(
    client: TestClient, db_session: AsyncSession
) -> None:
    """Test refreshing models for unsupported provider type."""
    # Create test provider with unsupported type
    provider = ProviderAccount(
        provider_type="unsupported_provider",
        display_name="Unsupported",
        enabled=True,
    )
    provider.credentials = {"api_key": "test"}

    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)

    response = client.post(f"/api/v1/providers/{provider.id}/refresh-models")

    assert response.status_code == 400
    assert "not supported" in response.json()["detail"].lower()
