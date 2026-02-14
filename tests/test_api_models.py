"""Tests for Model Management API endpoints."""

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from arguslm.server.core.security import CredentialEncryption
from arguslm.server.db.init import get_db
from arguslm.server.main import app
from arguslm.server.models.base import Base
from arguslm.server.models.model import Model
from arguslm.server.models.provider import ProviderAccount

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Test encryption key
TEST_ENCRYPTION_KEY = CredentialEncryption.generate_key()


@pytest.fixture(scope="function")
async def db_session() -> AsyncSession:
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
    """Create a test client with dependency override.

    Args:
        db_session: Test database session

    Returns:
        TestClient with overridden database dependency
    """

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture
async def provider_account(db_session: AsyncSession) -> ProviderAccount:
    """Create a test provider account.

    Args:
        db_session: Test database session

    Returns:
        ProviderAccount instance
    """
    account = ProviderAccount(
        provider_type="openai",
        display_name="Test OpenAI Account",
        enabled=True,
    )
    account.credentials = {"api_key": "sk-test-key"}

    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)

    return account


@pytest.fixture
async def test_model(db_session: AsyncSession, provider_account: ProviderAccount) -> Model:
    """Create a test model.

    Args:
        db_session: Test database session
        provider_account: Test provider account

    Returns:
        Model instance
    """
    model = Model(
        provider_account_id=provider_account.id,
        model_id="gpt-4o",
        custom_name="GPT-4 Optimized",
        source="discovered",
        enabled_for_monitoring=True,
        enabled_for_benchmark=True,
        model_metadata={"max_tokens": 8192},
    )

    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)

    return model


@pytest.mark.asyncio
async def test_list_models_empty(client: TestClient) -> None:
    """Test listing models when database is empty."""
    response = client.get("/api/v1/models")

    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["limit"] == 50
    assert data["offset"] == 0


@pytest.mark.asyncio
async def test_list_models_with_data(
    client: TestClient, db_session: AsyncSession, provider_account: ProviderAccount
) -> None:
    """Test listing models with data in database."""
    # Create multiple models
    for i in range(3):
        model = Model(
            provider_account_id=provider_account.id,
            model_id=f"model-{i}",
            custom_name=f"Model {i}",
            source="discovered",
            enabled_for_monitoring=True,
            enabled_for_benchmark=True,
            model_metadata={},
        )
        db_session.add(model)

    await db_session.commit()

    response = client.get("/api/v1/models")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 3
    assert data["total"] == 3
    assert data["limit"] == 50
    assert data["offset"] == 0


@pytest.mark.asyncio
async def test_list_models_filter_by_provider(client: TestClient, db_session: AsyncSession) -> None:
    """Test filtering models by provider_id."""
    # Create two provider accounts
    account1 = ProviderAccount(
        provider_type="openai",
        display_name="OpenAI Account",
        enabled=True,
    )
    account1.credentials = {"api_key": "sk-test-1"}

    account2 = ProviderAccount(
        provider_type="anthropic",
        display_name="Anthropic Account",
        enabled=True,
    )
    account2.credentials = {"api_key": "sk-test-2"}

    db_session.add(account1)
    db_session.add(account2)
    await db_session.commit()
    await db_session.refresh(account1)
    await db_session.refresh(account2)

    # Create models for each account
    model1 = Model(
        provider_account_id=account1.id,
        model_id="gpt-4o",
        source="discovered",
        enabled_for_monitoring=True,
        enabled_for_benchmark=True,
        model_metadata={},
    )
    model2 = Model(
        provider_account_id=account2.id,
        model_id="claude-3",
        source="discovered",
        enabled_for_monitoring=True,
        enabled_for_benchmark=True,
        model_metadata={},
    )

    db_session.add(model1)
    db_session.add(model2)
    await db_session.commit()

    # Filter by account1
    response = client.get(f"/api/v1/models?provider_id={account1.id}")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["model_id"] == "gpt-4o"
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_list_models_filter_by_monitoring(
    client: TestClient, db_session: AsyncSession, provider_account: ProviderAccount
) -> None:
    """Test filtering models by enabled_for_monitoring."""
    # Create models with different monitoring status
    model1 = Model(
        provider_account_id=provider_account.id,
        model_id="monitored-model",
        source="discovered",
        enabled_for_monitoring=True,
        enabled_for_benchmark=True,
        model_metadata={},
    )
    model2 = Model(
        provider_account_id=provider_account.id,
        model_id="unmonitored-model",
        source="discovered",
        enabled_for_monitoring=False,
        enabled_for_benchmark=True,
        model_metadata={},
    )

    db_session.add(model1)
    db_session.add(model2)
    await db_session.commit()

    # Filter by monitoring enabled
    response = client.get("/api/v1/models?enabled_for_monitoring=true")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["model_id"] == "monitored-model"


@pytest.mark.asyncio
async def test_list_models_filter_by_benchmark(
    client: TestClient, db_session: AsyncSession, provider_account: ProviderAccount
) -> None:
    """Test filtering models by enabled_for_benchmark."""
    # Create models with different benchmark status
    model1 = Model(
        provider_account_id=provider_account.id,
        model_id="benchmark-model",
        source="discovered",
        enabled_for_monitoring=True,
        enabled_for_benchmark=True,
        model_metadata={},
    )
    model2 = Model(
        provider_account_id=provider_account.id,
        model_id="no-benchmark-model",
        source="discovered",
        enabled_for_monitoring=True,
        enabled_for_benchmark=False,
        model_metadata={},
    )

    db_session.add(model1)
    db_session.add(model2)
    await db_session.commit()

    # Filter by benchmark enabled
    response = client.get("/api/v1/models?enabled_for_benchmark=true")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["model_id"] == "benchmark-model"


@pytest.mark.asyncio
async def test_list_models_search_by_model_id(
    client: TestClient, db_session: AsyncSession, provider_account: ProviderAccount
) -> None:
    """Test searching models by model_id."""
    # Create models
    model1 = Model(
        provider_account_id=provider_account.id,
        model_id="gpt-4o",
        source="discovered",
        enabled_for_monitoring=True,
        enabled_for_benchmark=True,
        model_metadata={},
    )
    model2 = Model(
        provider_account_id=provider_account.id,
        model_id="claude-3",
        source="discovered",
        enabled_for_monitoring=True,
        enabled_for_benchmark=True,
        model_metadata={},
    )

    db_session.add(model1)
    db_session.add(model2)
    await db_session.commit()

    # Search for gpt
    response = client.get("/api/v1/models?search=gpt")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["model_id"] == "gpt-4o"


@pytest.mark.asyncio
async def test_list_models_search_by_custom_name(
    client: TestClient, db_session: AsyncSession, provider_account: ProviderAccount
) -> None:
    """Test searching models by custom_name."""
    # Create models
    model1 = Model(
        provider_account_id=provider_account.id,
        model_id="gpt-4o",
        custom_name="My GPT Model",
        source="discovered",
        enabled_for_monitoring=True,
        enabled_for_benchmark=True,
        model_metadata={},
    )
    model2 = Model(
        provider_account_id=provider_account.id,
        model_id="claude-3",
        custom_name="Claude Production",
        source="discovered",
        enabled_for_monitoring=True,
        enabled_for_benchmark=True,
        model_metadata={},
    )

    db_session.add(model1)
    db_session.add(model2)
    await db_session.commit()

    # Search for "production"
    response = client.get("/api/v1/models?search=production")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["custom_name"] == "Claude Production"


@pytest.mark.asyncio
async def test_list_models_pagination(
    client: TestClient, db_session: AsyncSession, provider_account: ProviderAccount
) -> None:
    """Test pagination of model list."""
    # Create 10 models
    for i in range(10):
        model = Model(
            provider_account_id=provider_account.id,
            model_id=f"model-{i:02d}",
            source="discovered",
            enabled_for_monitoring=True,
            enabled_for_benchmark=True,
            model_metadata={},
        )
        db_session.add(model)

    await db_session.commit()

    # Get first page with limit 5
    response = client.get("/api/v1/models?limit=5&offset=0")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 5
    assert data["total"] == 10
    assert data["limit"] == 5
    assert data["offset"] == 0

    # Get second page
    response = client.get("/api/v1/models?limit=5&offset=5")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 5
    assert data["total"] == 10
    assert data["offset"] == 5


@pytest.mark.asyncio
async def test_get_model_by_id(
    client: TestClient, db_session: AsyncSession, test_model: Model
) -> None:
    """Test getting a model by ID."""
    response = client.get(f"/api/v1/models/{test_model.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_model.id)
    assert data["model_id"] == "gpt-4o"
    assert data["custom_name"] == "GPT-4 Optimized"
    assert data["source"] == "discovered"
    assert data["enabled_for_monitoring"] is True
    assert data["enabled_for_benchmark"] is True


@pytest.mark.asyncio
async def test_get_model_not_found(client: TestClient) -> None:
    """Test getting a non-existent model."""
    fake_id = uuid.uuid4()
    response = client.get(f"/api/v1/models/{fake_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Model not found"


@pytest.mark.asyncio
async def test_update_model_custom_name(
    client: TestClient, db_session: AsyncSession, test_model: Model
) -> None:
    """Test updating a model's custom name."""
    update_data = {"custom_name": "Updated GPT-4"}

    response = client.patch(f"/api/v1/models/{test_model.id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["custom_name"] == "Updated GPT-4"

    # Verify in database
    result = await db_session.execute(select(Model).where(Model.id == test_model.id))
    updated_model = result.scalar_one()
    assert updated_model.custom_name == "Updated GPT-4"


@pytest.mark.asyncio
async def test_update_model_clear_custom_name(
    client: TestClient, db_session: AsyncSession, test_model: Model
) -> None:
    """Test clearing a model's custom name."""
    update_data = {"custom_name": None}

    response = client.patch(f"/api/v1/models/{test_model.id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["custom_name"] is None


@pytest.mark.asyncio
async def test_update_model_monitoring_flag(
    client: TestClient, db_session: AsyncSession, test_model: Model
) -> None:
    """Test updating a model's monitoring flag."""
    update_data = {"enabled_for_monitoring": False}

    response = client.patch(f"/api/v1/models/{test_model.id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["enabled_for_monitoring"] is False

    # Verify in database
    result = await db_session.execute(select(Model).where(Model.id == test_model.id))
    updated_model = result.scalar_one()
    assert updated_model.enabled_for_monitoring is False


@pytest.mark.asyncio
async def test_update_model_benchmark_flag(
    client: TestClient, db_session: AsyncSession, test_model: Model
) -> None:
    """Test updating a model's benchmark flag."""
    update_data = {"enabled_for_benchmark": False}

    response = client.patch(f"/api/v1/models/{test_model.id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["enabled_for_benchmark"] is False


@pytest.mark.asyncio
async def test_update_model_multiple_fields(
    client: TestClient, db_session: AsyncSession, test_model: Model
) -> None:
    """Test updating multiple fields at once."""
    update_data = {
        "custom_name": "New Name",
        "enabled_for_monitoring": False,
        "enabled_for_benchmark": False,
    }

    response = client.patch(f"/api/v1/models/{test_model.id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["custom_name"] == "New Name"
    assert data["enabled_for_monitoring"] is False
    assert data["enabled_for_benchmark"] is False


@pytest.mark.asyncio
async def test_update_model_not_found(client: TestClient) -> None:
    """Test updating a non-existent model."""
    fake_id = uuid.uuid4()
    update_data = {"custom_name": "New Name"}

    response = client.patch(f"/api/v1/models/{fake_id}", json=update_data)

    assert response.status_code == 404
    assert response.json()["detail"] == "Model not found"


@pytest.mark.asyncio
async def test_create_manual_model(
    client: TestClient, db_session: AsyncSession, provider_account: ProviderAccount
) -> None:
    """Test creating a new manual model."""
    create_data = {
        "provider_account_id": str(provider_account.id),
        "model_id": "custom-model-v1",
        "custom_name": "My Custom Model",
        "metadata": {"custom_field": "value"},
    }

    response = client.post("/api/v1/models", json=create_data)

    assert response.status_code == 201
    data = response.json()
    assert data["model_id"] == "custom-model-v1"
    assert data["custom_name"] == "My Custom Model"
    assert data["source"] == "manual"
    assert data["model_metadata"]["custom_field"] == "value"

    # Verify in database
    result = await db_session.execute(select(Model).where(Model.model_id == "custom-model-v1"))
    created_model = result.scalar_one()
    assert created_model.source == "manual"


@pytest.mark.asyncio
async def test_create_manual_model_minimal(
    client: TestClient, db_session: AsyncSession, provider_account: ProviderAccount
) -> None:
    """Test creating a manual model with minimal data."""
    create_data = {
        "provider_account_id": str(provider_account.id),
        "model_id": "minimal-model",
    }

    response = client.post("/api/v1/models", json=create_data)

    assert response.status_code == 201
    data = response.json()
    assert data["model_id"] == "minimal-model"
    assert data["custom_name"] is None
    assert data["model_metadata"] == {}


@pytest.mark.asyncio
async def test_create_model_invalid_model_id(
    client: TestClient, provider_account: ProviderAccount
) -> None:
    """Test creating a model with invalid model_id."""
    create_data = {
        "provider_account_id": str(provider_account.id),
        "model_id": "invalid model!@#",  # Invalid characters
    }

    response = client.post("/api/v1/models", json=create_data)

    assert response.status_code == 400
    assert "Invalid model_id format" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_model_empty_model_id(
    client: TestClient, provider_account: ProviderAccount
) -> None:
    """Test creating a model with empty model_id."""
    create_data = {
        "provider_account_id": str(provider_account.id),
        "model_id": "",
    }

    response = client.post("/api/v1/models", json=create_data)

    # Pydantic validation error (422) for empty string violating min_length=1
    assert response.status_code == 422
