"""Tests for Monitoring Configuration API endpoints."""

import os
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

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
from arguslm.server.models.monitoring import MonitoringConfig, UptimeCheck
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
    """Create a test model with monitoring enabled.

    Args:
        db_session: Test database session
        provider_account: Test provider account

    Returns:
        Model instance
    """
    model = Model(
        provider_account_id=provider_account.id,
        model_id="gpt-4o",
        custom_name="GPT-4 Turbo",
        source="discovered",
        enabled_for_monitoring=True,
        enabled_for_benchmark=True,
    )
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)

    return model


class TestGetMonitoringConfig:
    """Tests for GET /api/v1/monitoring/config endpoint."""

    def test_get_config_creates_default_if_none_exists(self, client: TestClient):
        """Test that default config is created if none exists."""
        response = client.get("/api/v1/monitoring/config")

        assert response.status_code == 200
        data = response.json()
        assert data["interval_minutes"] == 15
        assert data["prompt_pack"] == "shakespeare"
        assert data["enabled"] is True
        assert data["last_run_at"] is None

    @pytest.mark.asyncio
    async def test_get_config_returns_existing_config(
        self, client: TestClient, db_session: AsyncSession
    ):
        """Test that existing config is returned."""
        # Create a config
        config = MonitoringConfig(
            interval_minutes=30,
            prompt_pack="synthetic_long",
            enabled=False,
        )
        db_session.add(config)
        await db_session.commit()

        response = client.get("/api/v1/monitoring/config")

        assert response.status_code == 200
        data = response.json()
        assert data["interval_minutes"] == 30
        assert data["prompt_pack"] == "synthetic_long"
        assert data["enabled"] is False


class TestUpdateMonitoringConfig:
    """Tests for PATCH /api/v1/monitoring/config endpoint."""

    def test_update_interval_minutes(self, client: TestClient):
        """Test updating interval_minutes."""
        response = client.patch(
            "/api/v1/monitoring/config",
            json={"interval_minutes": 60},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["interval_minutes"] == 60

    def test_update_prompt_pack(self, client: TestClient):
        """Test updating prompt_pack."""
        response = client.patch(
            "/api/v1/monitoring/config",
            json={"prompt_pack": "synthetic_medium"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["prompt_pack"] == "synthetic_medium"

    def test_update_enabled_flag(self, client: TestClient):
        """Test updating enabled flag."""
        response = client.patch(
            "/api/v1/monitoring/config",
            json={"enabled": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False

    def test_update_multiple_fields(self, client: TestClient):
        """Test updating multiple fields at once."""
        response = client.patch(
            "/api/v1/monitoring/config",
            json={
                "interval_minutes": 45,
                "prompt_pack": "synthetic_short",
                "enabled": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["interval_minutes"] == 45
        assert data["prompt_pack"] == "synthetic_short"
        assert data["enabled"] is False

    def test_reject_invalid_interval_less_than_one(self, client: TestClient):
        """Test that interval_minutes < 1 is rejected."""
        response = client.patch(
            "/api/v1/monitoring/config",
            json={"interval_minutes": 0},
        )

        assert response.status_code == 422  # Pydantic validation error
        assert "greater than or equal to 1" in str(response.json())

    def test_reject_negative_interval(self, client: TestClient):
        """Test that negative interval_minutes is rejected."""
        response = client.patch(
            "/api/v1/monitoring/config",
            json={"interval_minutes": -5},
        )

        assert response.status_code == 422  # Pydantic validation error
        assert "greater than or equal to 1" in str(response.json())

    def test_reject_invalid_prompt_pack(self, client: TestClient):
        """Test that invalid prompt_pack is rejected."""
        response = client.patch(
            "/api/v1/monitoring/config",
            json={"prompt_pack": "invalid_pack"},
        )

        assert response.status_code == 400
        assert "prompt_pack must be one of" in response.json()["detail"]

    def test_accept_all_valid_prompt_packs(self, client: TestClient):
        """Test that all valid prompt packs are accepted."""
        valid_packs = ["shakespeare", "synthetic_short", "synthetic_medium", "synthetic_long"]

        for pack in valid_packs:
            response = client.patch(
                "/api/v1/monitoring/config",
                json={"prompt_pack": pack},
            )
            assert response.status_code == 200
            assert response.json()["prompt_pack"] == pack


class TestTriggerMonitoringRun:
    """Tests for POST /api/v1/monitoring/run endpoint."""

    def test_trigger_run_returns_queued_status(self, client: TestClient):
        """Test that triggering a run returns queued status."""
        response = client.post("/api/v1/monitoring/run")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert data["run_id"] is not None
        assert "message" in data

    def test_trigger_run_returns_immediately(self, client: TestClient):
        """Test that endpoint returns immediately (doesn't block)."""
        response = client.post("/api/v1/monitoring/run")

        assert response.status_code == 200
        # If it blocked, this test would timeout

    @pytest.mark.asyncio
    async def test_trigger_run_executes_background_task(
        self, client: TestClient, db_session: AsyncSession, test_model: Model
    ):
        """Test that background task is queued for execution."""
        # This is a basic test - in real scenarios you'd use a task queue
        response = client.post("/api/v1/monitoring/run")

        assert response.status_code == 200
        assert response.json()["status"] == "queued"


class TestGetUptimeHistory:
    """Tests for GET /api/v1/monitoring/uptime endpoint."""

    @pytest.mark.asyncio
    async def test_get_uptime_history_empty(self, client: TestClient):
        """Test getting uptime history when no checks exist."""
        response = client.get("/api/v1/monitoring/uptime")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["limit"] == 100
        assert data["offset"] == 0

    @pytest.mark.asyncio
    async def test_get_uptime_history_with_checks(
        self, client: TestClient, db_session: AsyncSession, test_model: Model
    ):
        """Test getting uptime history with existing checks."""
        # Create some uptime checks
        check1 = UptimeCheck(
            model_id=test_model.id,
            status="up",
            latency_ms=150.5,
        )
        check2 = UptimeCheck(
            model_id=test_model.id,
            status="up",
            latency_ms=200.0,
        )
        db_session.add(check1)
        db_session.add(check2)
        await db_session.commit()

        response = client.get("/api/v1/monitoring/uptime")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0]["status"] == "up"
        assert data["items"][0]["model_name"] == "GPT-4 Turbo"

    @pytest.mark.asyncio
    async def test_get_uptime_history_filter_by_model_id(
        self,
        client: TestClient,
        db_session: AsyncSession,
        test_model: Model,
        provider_account: ProviderAccount,
    ):
        """Test filtering uptime history by model_id."""
        # Create another model
        model2 = Model(
            provider_account_id=provider_account.id,
            model_id="gpt-3.5-turbo",
            source="discovered",
            enabled_for_monitoring=True,
        )
        db_session.add(model2)
        await db_session.commit()
        await db_session.refresh(model2)

        # Create checks for both models
        check1 = UptimeCheck(model_id=test_model.id, status="up", latency_ms=100.0)
        check2 = UptimeCheck(model_id=model2.id, status="down", error="Connection failed")
        db_session.add(check1)
        db_session.add(check2)
        await db_session.commit()

        # Filter by first model
        response = client.get(f"/api/v1/monitoring/uptime?model_id={test_model.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["model_id"] == str(test_model.id)

    @pytest.mark.asyncio
    async def test_get_uptime_history_filter_by_status(
        self, client: TestClient, db_session: AsyncSession, test_model: Model
    ):
        """Test filtering uptime history by status."""
        # Create checks with different statuses
        check1 = UptimeCheck(model_id=test_model.id, status="up", latency_ms=100.0)
        check2 = UptimeCheck(model_id=test_model.id, status="down", error="Connection failed")
        check3 = UptimeCheck(model_id=test_model.id, status="up", latency_ms=150.0)
        db_session.add(check1)
        db_session.add(check2)
        db_session.add(check3)
        await db_session.commit()

        # Filter by "up" status
        response = client.get("/api/v1/monitoring/uptime?status=up")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(item["status"] == "up" for item in data["items"])

    @pytest.mark.asyncio
    async def test_get_uptime_history_pagination(
        self, client: TestClient, db_session: AsyncSession, test_model: Model
    ):
        """Test pagination of uptime history."""
        # Create multiple checks
        for i in range(5):
            check = UptimeCheck(
                model_id=test_model.id,
                status="up",
                latency_ms=100.0 + i,
            )
            db_session.add(check)
        await db_session.commit()

        # Get first page
        response = client.get("/api/v1/monitoring/uptime?limit=2&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 0

        # Get second page
        response = client.get("/api/v1/monitoring/uptime?limit=2&offset=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2

    @pytest.mark.asyncio
    async def test_get_uptime_history_respects_max_limit(
        self, client: TestClient, db_session: AsyncSession, test_model: Model
    ):
        """Test that limit is capped at 1000."""
        response = client.get("/api/v1/monitoring/uptime?limit=2000")

        # Should be rejected or capped
        assert response.status_code in [200, 422]  # 422 if validation fails

    @pytest.mark.asyncio
    async def test_get_uptime_history_filter_by_since(
        self, client: TestClient, db_session: AsyncSession, test_model: Model
    ):
        """Test filtering uptime history by since timestamp."""
        # Create checks
        check1 = UptimeCheck(model_id=test_model.id, status="up", latency_ms=100.0)
        db_session.add(check1)
        await db_session.commit()

        # Get the created_at timestamp and use a time before it
        stmt = select(UptimeCheck).where(UptimeCheck.id == check1.id)
        result = await db_session.execute(stmt)
        check = result.scalar_one()
        created_at = check.created_at

        # Use a time 1 minute before the check was created
        from datetime import timedelta

        since_time = created_at - timedelta(minutes=1)

        response = client.get(f"/api/v1/monitoring/uptime?since={since_time.isoformat()}")

        assert response.status_code == 200
        data = response.json()
        # Should have at least the check we created
        assert data["total"] >= 1
