"""Tests for Alert Rules API endpoints."""

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from arguslm.server.core.security import CredentialEncryption
from arguslm.server.db.init import get_db
from arguslm.server.main import app
from arguslm.server.models.alert import Alert, AlertRule
from arguslm.server.models.base import Base

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
async def alert_rule(db_session: AsyncSession) -> AlertRule:
    """Create a test alert rule.

    Args:
        db_session: Test database session

    Returns:
        AlertRule instance
    """
    rule = AlertRule(
        name="Test Rule",
        rule_type="any_model_down",
        enabled=True,
        notify_in_app=True,
    )
    db_session.add(rule)
    await db_session.commit()
    await db_session.refresh(rule)
    return rule


@pytest.fixture
async def alert(db_session: AsyncSession, alert_rule: AlertRule) -> Alert:
    """Create a test alert.

    Args:
        db_session: Test database session
        alert_rule: Test alert rule

    Returns:
        Alert instance
    """
    alert_obj = Alert(
        rule_id=alert_rule.id,
        message="Test alert message",
        acknowledged=False,
    )
    db_session.add(alert_obj)
    await db_session.commit()
    await db_session.refresh(alert_obj)
    return alert_obj


class TestListAlertRules:
    """Tests for GET /api/v1/alerts/rules endpoint."""

    def test_list_rules_empty(self, client: TestClient) -> None:
        """Test listing alert rules when none exist."""
        response = client.get("/api/v1/alerts/rules")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_rules_with_data(self, client: TestClient, alert_rule: AlertRule) -> None:
        """Test listing alert rules with existing data."""
        response = client.get("/api/v1/alerts/rules")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Rule"
        assert data[0]["rule_type"] == "any_model_down"
        assert data[0]["enabled"] is True


class TestCreateAlertRule:
    """Tests for POST /api/v1/alerts/rules endpoint."""

    def test_create_any_model_down_rule(self, client: TestClient) -> None:
        """Test creating an any_model_down rule."""
        payload = {
            "name": "Any Model Down",
            "rule_type": "any_model_down",
            "enabled": True,
            "notify_in_app": True,
        }
        response = client.post("/api/v1/alerts/rules", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Any Model Down"
        assert data["rule_type"] == "any_model_down"
        assert data["enabled"] is True
        assert data["notify_in_app"] is True
        assert "id" in data
        assert "created_at" in data

    def test_create_specific_model_down_rule(self, client: TestClient) -> None:
        """Test creating a specific_model_down rule with target_model_id."""
        model_id = str(uuid.uuid4())
        payload = {
            "name": "Specific Model Down",
            "rule_type": "specific_model_down",
            "target_model_id": model_id,
            "enabled": True,
            "notify_in_app": True,
        }
        response = client.post("/api/v1/alerts/rules", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Specific Model Down"
        assert data["rule_type"] == "specific_model_down"
        assert data["target_model_id"] == model_id

    def test_create_specific_model_down_without_target_fails(self, client: TestClient) -> None:
        """Test creating specific_model_down rule without target_model_id fails."""
        payload = {
            "name": "Specific Model Down",
            "rule_type": "specific_model_down",
            "enabled": True,
            "notify_in_app": True,
        }
        response = client.post("/api/v1/alerts/rules", json=payload)
        assert response.status_code == 400
        assert "target_model_id" in response.json()["detail"]

    def test_create_model_unavailable_everywhere_rule(self, client: TestClient) -> None:
        """Test creating a model_unavailable_everywhere rule with target_model_name."""
        payload = {
            "name": "Model Unavailable",
            "rule_type": "model_unavailable_everywhere",
            "target_model_name": "gpt-4",
            "enabled": True,
            "notify_in_app": True,
        }
        response = client.post("/api/v1/alerts/rules", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["target_model_name"] == "gpt-4"

    def test_create_model_unavailable_everywhere_without_target_fails(
        self, client: TestClient
    ) -> None:
        """Test creating model_unavailable_everywhere rule without target_model_name fails."""
        payload = {
            "name": "Model Unavailable",
            "rule_type": "model_unavailable_everywhere",
            "enabled": True,
            "notify_in_app": True,
        }
        response = client.post("/api/v1/alerts/rules", json=payload)
        assert response.status_code == 400
        assert "target_model_name" in response.json()["detail"]


class TestUpdateAlertRule:
    """Tests for PATCH /api/v1/alerts/rules/{id} endpoint."""

    def test_update_rule_name(self, client: TestClient, alert_rule: AlertRule) -> None:
        """Test updating rule name."""
        payload = {"name": "Updated Rule Name"}
        response = client.patch(f"/api/v1/alerts/rules/{alert_rule.id}", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Rule Name"
        assert data["id"] == str(alert_rule.id)

    def test_update_rule_enabled(self, client: TestClient, alert_rule: AlertRule) -> None:
        """Test updating rule enabled status."""
        payload = {"enabled": False}
        response = client.patch(f"/api/v1/alerts/rules/{alert_rule.id}", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False

    def test_update_rule_notify_in_app(self, client: TestClient, alert_rule: AlertRule) -> None:
        """Test updating rule notify_in_app status."""
        payload = {"notify_in_app": False}
        response = client.patch(f"/api/v1/alerts/rules/{alert_rule.id}", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["notify_in_app"] is False

    def test_update_nonexistent_rule(self, client: TestClient) -> None:
        """Test updating a nonexistent rule returns 404."""
        fake_id = uuid.uuid4()
        payload = {"name": "Updated"}
        response = client.patch(f"/api/v1/alerts/rules/{fake_id}", json=payload)
        assert response.status_code == 404


class TestDeleteAlertRule:
    """Tests for DELETE /api/v1/alerts/rules/{id} endpoint."""

    def test_delete_rule(self, client: TestClient, alert_rule: AlertRule) -> None:
        """Test deleting an alert rule."""
        response = client.delete(f"/api/v1/alerts/rules/{alert_rule.id}")
        assert response.status_code == 204

        # Verify it's deleted
        response = client.get("/api/v1/alerts/rules")
        assert response.status_code == 200
        assert response.json() == []

    def test_delete_nonexistent_rule(self, client: TestClient) -> None:
        """Test deleting a nonexistent rule returns 404."""
        fake_id = uuid.uuid4()
        response = client.delete(f"/api/v1/alerts/rules/{fake_id}")
        assert response.status_code == 404


class TestListAlerts:
    """Tests for GET /api/v1/alerts endpoint."""

    def test_list_alerts_empty(self, client: TestClient) -> None:
        """Test listing alerts when none exist."""
        response = client.get("/api/v1/alerts")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["unacknowledged_count"] == 0
        assert data["limit"] == 50
        assert data["offset"] == 0

    def test_list_alerts_with_data(self, client: TestClient, alert: Alert) -> None:
        """Test listing alerts with existing data."""
        response = client.get("/api/v1/alerts")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["message"] == "Test alert message"
        assert data["items"][0]["acknowledged"] is False
        assert data["unacknowledged_count"] == 1

    def test_list_alerts_filter_by_rule_id(self, client: TestClient, alert: Alert) -> None:
        """Test filtering alerts by rule_id."""
        response = client.get(f"/api/v1/alerts?rule_id={alert.rule_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["rule_id"] == str(alert.rule_id)

    def test_list_alerts_filter_by_acknowledged(self, client: TestClient, alert: Alert) -> None:
        """Test filtering alerts by acknowledged status."""
        response = client.get("/api/v1/alerts?acknowledged=false")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1

        response = client.get("/api/v1/alerts?acknowledged=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 0

    @pytest.mark.asyncio
    async def test_list_alerts_pagination(
        self, client: TestClient, db_session: AsyncSession, alert_rule: AlertRule
    ) -> None:
        """Test pagination of alerts."""
        # Create multiple alerts
        for i in range(5):
            alert_obj = Alert(
                rule_id=alert_rule.id,
                message=f"Alert {i}",
                acknowledged=False,
            )
            db_session.add(alert_obj)
        await db_session.commit()

        # Test limit
        response = client.get("/api/v1/alerts?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["limit"] == 2

        # Test offset
        response = client.get("/api/v1/alerts?limit=2&offset=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["offset"] == 2


class TestAcknowledgeAlert:
    """Tests for PATCH /api/v1/alerts/{id}/acknowledge endpoint."""

    def test_acknowledge_alert(self, client: TestClient, alert: Alert) -> None:
        """Test acknowledging an alert."""
        response = client.patch(f"/api/v1/alerts/{alert.id}/acknowledge")
        assert response.status_code == 200
        data = response.json()
        assert data["acknowledged"] is True
        assert data["id"] == str(alert.id)

    def test_acknowledge_nonexistent_alert(self, client: TestClient) -> None:
        """Test acknowledging a nonexistent alert returns 404."""
        fake_id = uuid.uuid4()
        response = client.patch(f"/api/v1/alerts/{fake_id}/acknowledge")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_unacknowledged_count_after_acknowledge(
        self, client: TestClient, db_session: AsyncSession, alert_rule: AlertRule
    ) -> None:
        """Test that unacknowledged count decreases after acknowledging."""
        # Create 2 alerts
        alert1 = Alert(rule_id=alert_rule.id, message="Alert 1", acknowledged=False)
        alert2 = Alert(rule_id=alert_rule.id, message="Alert 2", acknowledged=False)
        db_session.add(alert1)
        db_session.add(alert2)
        await db_session.commit()

        # Check initial count
        response = client.get("/api/v1/alerts")
        assert response.json()["unacknowledged_count"] == 2

        # Acknowledge one
        client.patch(f"/api/v1/alerts/{alert1.id}/acknowledge")

        # Check updated count
        response = client.get("/api/v1/alerts")
        assert response.json()["unacknowledged_count"] == 1
