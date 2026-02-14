"""End-to-End tests for complete user flows through the ArgusLM API.

Tests cover three main user journeys:
1. Provider → Models → Benchmark
2. Monitoring Configuration → Uptime Checks → Results
3. Alert Rules → Trigger → Notifications
"""

import os
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from arguslm.server.core.security import CredentialEncryption
from arguslm.server.db.init import get_db
from arguslm.server.main import app
from arguslm.server.models.base import Base
from arguslm.server.models.benchmark import BenchmarkResult, BenchmarkRun
from arguslm.server.models.model import Model
from arguslm.server.models.monitoring import MonitoringConfig, UptimeCheck
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
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# =============================================================================
# FLOW 1: Provider → Models → Benchmark
# =============================================================================


class TestFlow1ProviderModelsBenchmark:
    """E2E tests for Provider → Models → Benchmark flow."""

    @pytest.mark.asyncio
    async def test_complete_provider_to_benchmark_flow(
        self, client: TestClient, db_session: AsyncSession
    ) -> None:
        """Test complete flow: create provider, discover models, run benchmark, export results."""

        # Step 1: Create a provider account via API
        provider_response = client.post(
            "/api/v1/providers",
            json={
                "provider_type": "openai",
                "display_name": "E2E Test OpenAI",
                "credentials": {"api_key": "sk-test-e2e-key"},
            },
        )
        assert provider_response.status_code == 201
        provider_data = provider_response.json()
        provider_id = provider_data["id"]
        assert provider_data["provider_type"] == "openai"
        assert provider_data["display_name"] == "E2E Test OpenAI"
        assert provider_data["enabled"] is True
        assert "credentials" not in provider_data  # Should not expose credentials

        # Step 2: Trigger model discovery (mock the OpenAI model source)
        with patch("arguslm.server.api.providers.OpenAIModelSource") as mock_source_class:
            mock_source = AsyncMock()
            mock_source.list_models = AsyncMock(
                return_value=[
                    MagicMock(id="gpt-4o", provider_type="openai", metadata={"max_tokens": 128000}),
                    MagicMock(
                        id="gpt-4-turbo", provider_type="openai", metadata={"max_tokens": 128000}
                    ),
                    MagicMock(
                        id="gpt-3.5-turbo", provider_type="openai", metadata={"max_tokens": 16385}
                    ),
                ]
            )
            mock_source_class.return_value = mock_source

            refresh_response = client.post(f"/api/v1/providers/{provider_id}/refresh-models")

            assert refresh_response.status_code == 200
            refresh_data = refresh_response.json()
            assert refresh_data["success"] is True
            assert refresh_data["models_discovered"] == 3
            assert "3 new" in refresh_data["message"]

        # Step 3: Verify models are created in database via API
        models_response = client.get(f"/api/v1/models?provider_id={provider_id}")
        assert models_response.status_code == 200
        models_data = models_response.json()
        assert models_data["total"] == 3

        model_ids = [m["model_id"] for m in models_data["items"]]
        assert "gpt-4o" in model_ids
        assert "gpt-4-turbo" in model_ids
        assert "gpt-3.5-turbo" in model_ids

        # Get the first model's ID for benchmark
        first_model = models_data["items"][0]
        first_model_id = first_model["id"]

        # Step 4: Run benchmark on discovered models (mock LiteLLM completion)
        with patch("arguslm.server.api.benchmarks._run_benchmark_task", new_callable=AsyncMock):
            benchmark_response = client.post(
                "/api/v1/benchmarks",
                json={
                    "model_ids": [first_model_id],
                    "prompt_pack": "shakespeare",
                    "name": "E2E Benchmark Test",
                    "max_tokens": 100,
                    "num_runs": 1,
                },
            )

            assert benchmark_response.status_code == 202
            benchmark_data = benchmark_response.json()
            assert benchmark_data["status"] == "pending"
            benchmark_run_id = benchmark_data["id"]

        # Step 5: Simulate completed benchmark by adding results directly to DB
        # (In real scenario, background task would do this)
        from sqlalchemy import select

        result = await db_session.execute(
            select(BenchmarkRun).where(BenchmarkRun.id == uuid.UUID(benchmark_run_id))
        )
        benchmark_run = result.scalar_one()
        benchmark_run.status = "completed"
        benchmark_run.started_at = datetime.now(timezone.utc)
        benchmark_run.completed_at = datetime.now(timezone.utc)

        # Get model from DB
        model_result = await db_session.execute(
            select(Model).where(Model.id == uuid.UUID(first_model_id))
        )
        model = model_result.scalar_one()

        # Add benchmark result
        result_obj = BenchmarkResult(
            run_id=benchmark_run.id,
            model_id=model.id,
            ttft_ms=150.5,
            tps=45.2,
            tps_excluding_ttft=52.3,
            total_latency_ms=2500.0,
            input_tokens=50,
            output_tokens=100,
            estimated_cost=0.005,
            error=None,
        )
        db_session.add(result_obj)
        await db_session.commit()

        # Step 6: Verify benchmark results are stored correctly via API
        get_benchmark_response = client.get(f"/api/v1/benchmarks/{benchmark_run_id}")
        assert get_benchmark_response.status_code == 200
        benchmark_detail = get_benchmark_response.json()
        assert benchmark_detail["status"] == "completed"
        assert benchmark_detail["name"] == "E2E Benchmark Test"
        assert len(benchmark_detail["results"]) == 1
        assert benchmark_detail["results"][0]["ttft_ms"] == 150.5
        assert benchmark_detail["results"][0]["tps"] == 45.2

        # Step 7: Export benchmark results as JSON
        export_json_response = client.get(
            f"/api/v1/benchmarks/{benchmark_run_id}/export?format=json"
        )
        assert export_json_response.status_code == 200
        assert export_json_response.headers["content-type"] == "application/json"
        export_data = export_json_response.json()
        assert "results" in export_data
        assert len(export_data["results"]) == 1

        # Step 8: Export benchmark results as CSV
        export_csv_response = client.get(f"/api/v1/benchmarks/{benchmark_run_id}/export?format=csv")
        assert export_csv_response.status_code == 200
        assert export_csv_response.headers["content-type"] == "text/csv; charset=utf-8"
        csv_content = export_csv_response.text
        assert "model_name" in csv_content
        assert "ttft_ms" in csv_content
        assert "tps" in csv_content

    @pytest.mark.asyncio
    async def test_test_provider_connection(
        self, client: TestClient, db_session: AsyncSession
    ) -> None:
        """Test provider connection test endpoint."""
        # Create provider
        provider_response = client.post(
            "/api/v1/providers",
            json={
                "provider_type": "openai",
                "display_name": "Connection Test Provider",
                "credentials": {"api_key": "sk-test-key"},
            },
        )
        provider_id = provider_response.json()["id"]

        # Test connection (mock LiteLLM)
        with patch("arguslm.server.api.providers.LiteLLMClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.complete = AsyncMock(return_value={"id": "test-response-id", "choices": []})
            mock_client_class.return_value = mock_client

            test_response = client.post(f"/api/v1/providers/{provider_id}/test")

            assert test_response.status_code == 200
            test_data = test_response.json()
            assert test_data["success"] is True
            assert "successfully connected" in test_data["message"].lower()


# =============================================================================
# FLOW 2: Monitoring Configuration → Uptime Checks → Results
# =============================================================================


class TestFlow2MonitoringUptimeResults:
    """E2E tests for Monitoring Configuration → Uptime Checks → Results flow."""

    @pytest.mark.asyncio
    async def test_complete_monitoring_flow(
        self, client: TestClient, db_session: AsyncSession
    ) -> None:
        """Test complete flow: configure monitoring, run uptime checks, get history, export."""

        # Step 1: Create provider and model
        provider = ProviderAccount(
            provider_type="openai",
            display_name="Monitoring Test Provider",
            enabled=True,
        )
        provider.credentials = {"api_key": "sk-test-key"}
        db_session.add(provider)
        await db_session.commit()
        await db_session.refresh(provider)

        model = Model(
            provider_account_id=provider.id,
            model_id="gpt-4o-monitoring",
            custom_name="GPT-4o Monitored",
            source="discovered",
            enabled_for_monitoring=True,
            enabled_for_benchmark=False,
            model_metadata={},
        )
        db_session.add(model)
        await db_session.commit()
        await db_session.refresh(model)

        # Step 2: Get default monitoring config
        config_response = client.get("/api/v1/monitoring/config")
        assert config_response.status_code == 200
        config_data = config_response.json()
        assert config_data["interval_minutes"] == 15  # Default
        assert config_data["enabled"] is True

        # Step 3: Configure monitoring (set interval, enable)
        update_config_response = client.patch(
            "/api/v1/monitoring/config",
            json={
                "interval_minutes": 5,
                "prompt_pack": "synthetic_short",
                "enabled": True,
            },
        )
        assert update_config_response.status_code == 200
        updated_config = update_config_response.json()
        assert updated_config["interval_minutes"] == 5
        assert updated_config["prompt_pack"] == "synthetic_short"

        # Step 4: Trigger manual uptime run
        run_response = client.post("/api/v1/monitoring/run")
        assert run_response.status_code == 200
        run_data = run_response.json()
        assert run_data["status"] == "queued"
        assert run_data["run_id"] is not None

        # Step 5: Simulate uptime checks being stored (background task)
        check1 = UptimeCheck(
            model_id=model.id,
            status="up",
            latency_ms=150.5,
        )
        check2 = UptimeCheck(
            model_id=model.id,
            status="up",
            latency_ms=145.0,
        )
        check3 = UptimeCheck(
            model_id=model.id,
            status="down",
            error="Connection timeout",
        )
        db_session.add_all([check1, check2, check3])
        await db_session.commit()

        # Step 6: Get uptime history via API
        history_response = client.get("/api/v1/monitoring/uptime")
        assert history_response.status_code == 200
        history_data = history_response.json()
        # We created 3 checks, but the trigger run may add more depending on implementation
        assert history_data["total"] >= 3
        assert len(history_data["items"]) >= 3

        # Verify we have both up and down statuses
        statuses = [item["status"] for item in history_data["items"]]
        assert "up" in statuses
        assert "down" in statuses

        # Step 7: Filter uptime history by model
        filtered_response = client.get(f"/api/v1/monitoring/uptime?model_id={model.id}")
        assert filtered_response.status_code == 200
        filtered_data = filtered_response.json()
        # We created 3 checks, but the trigger run may add more depending on implementation
        assert filtered_data["total"] >= 3

        # Step 8: Filter by status
        up_only_response = client.get("/api/v1/monitoring/uptime?status=up")
        assert up_only_response.status_code == 200
        up_data = up_only_response.json()
        assert up_data["total"] == 2
        assert all(item["status"] == "up" for item in up_data["items"])

        # Step 9: Export uptime history as JSON
        export_json_response = client.get("/api/v1/monitoring/uptime/export?format=json")
        assert export_json_response.status_code == 200
        assert export_json_response.headers["content-type"] == "application/json"
        export_data = export_json_response.json()
        assert "checks" in export_data
        # We created 3 checks, but the trigger run may add more depending on implementation
        assert len(export_data["checks"]) >= 3

        # Step 10: Export uptime history as CSV
        export_csv_response = client.get("/api/v1/monitoring/uptime/export?format=csv")
        assert export_csv_response.status_code == 200
        assert export_csv_response.headers["content-type"] == "text/csv; charset=utf-8"
        csv_content = export_csv_response.text
        assert "model_name" in csv_content
        assert "status" in csv_content
        assert "latency_ms" in csv_content

    @pytest.mark.asyncio
    async def test_uptime_pagination(self, client: TestClient, db_session: AsyncSession) -> None:
        """Test uptime history pagination."""
        # Create provider and model
        provider = ProviderAccount(
            provider_type="openai",
            display_name="Pagination Test Provider",
            enabled=True,
        )
        provider.credentials = {"api_key": "sk-test-key"}
        db_session.add(provider)
        await db_session.commit()
        await db_session.refresh(provider)

        model = Model(
            provider_account_id=provider.id,
            model_id="gpt-4o-pagination",
            source="discovered",
            enabled_for_monitoring=True,
        )
        db_session.add(model)
        await db_session.commit()
        await db_session.refresh(model)

        # Create multiple uptime checks
        for i in range(10):
            check = UptimeCheck(
                model_id=model.id,
                status="up",
                latency_ms=100.0 + i,
            )
            db_session.add(check)
        await db_session.commit()

        # Test pagination
        page1_response = client.get("/api/v1/monitoring/uptime?limit=3&offset=0")
        assert page1_response.status_code == 200
        page1_data = page1_response.json()
        assert len(page1_data["items"]) == 3
        assert page1_data["total"] == 10
        assert page1_data["limit"] == 3
        assert page1_data["offset"] == 0

        page2_response = client.get("/api/v1/monitoring/uptime?limit=3&offset=3")
        assert page2_response.status_code == 200
        page2_data = page2_response.json()
        assert len(page2_data["items"]) == 3
        assert page2_data["offset"] == 3


# =============================================================================
# FLOW 3: Alert Rules → Trigger → Notifications
# =============================================================================


class TestFlow3AlertRulesNotifications:
    """E2E tests for Alert Rules → Trigger → Notifications flow."""

    @pytest.mark.asyncio
    async def test_complete_alert_flow(self, client: TestClient, db_session: AsyncSession) -> None:
        """Test complete flow: create rules, simulate model down, verify alerts triggered."""
        from arguslm.server.core.alert_evaluator import evaluate_alerts
        from arguslm.server.models.alert import Alert, AlertRule

        # Step 1: Create provider and models
        provider = ProviderAccount(
            provider_type="openai",
            display_name="Alert Test Provider",
            enabled=True,
        )
        provider.credentials = {"api_key": "sk-test-key"}
        db_session.add(provider)
        await db_session.commit()
        await db_session.refresh(provider)

        model1 = Model(
            provider_account_id=provider.id,
            model_id="gpt-4o",
            custom_name="GPT-4o Alert Test",
            source="discovered",
            enabled_for_monitoring=True,
        )
        model2 = Model(
            provider_account_id=provider.id,
            model_id="gpt-4o",  # Same model_id for unavailable_everywhere test
            custom_name="GPT-4o Alert Test 2",
            source="discovered",
            enabled_for_monitoring=True,
        )
        db_session.add_all([model1, model2])
        await db_session.commit()
        await db_session.refresh(model1)
        await db_session.refresh(model2)

        # Step 2: Create alert rules (all 3 types) via API
        # Rule 1: any_model_down
        rule1_response = client.post(
            "/api/v1/alerts/rules",
            json={
                "name": "Any Model Down Alert",
                "rule_type": "any_model_down",
                "enabled": True,
                "notify_in_app": True,
            },
        )
        assert rule1_response.status_code == 201
        rule1_id = rule1_response.json()["id"]

        # Rule 2: specific_model_down
        rule2_response = client.post(
            "/api/v1/alerts/rules",
            json={
                "name": "Specific GPT-4o Down",
                "rule_type": "specific_model_down",
                "target_model_id": str(model1.id),
                "enabled": True,
                "notify_in_app": True,
            },
        )
        assert rule2_response.status_code == 201
        rule2_id = rule2_response.json()["id"]

        # Rule 3: model_unavailable_everywhere
        rule3_response = client.post(
            "/api/v1/alerts/rules",
            json={
                "name": "GPT-4o Unavailable Everywhere",
                "rule_type": "model_unavailable_everywhere",
                "target_model_name": "gpt-4o",
                "enabled": True,
                "notify_in_app": True,
            },
        )
        assert rule3_response.status_code == 201
        rule3_id = rule3_response.json()["id"]

        # Step 3: Verify all rules are listed
        rules_response = client.get("/api/v1/alerts/rules")
        assert rules_response.status_code == 200
        rules = rules_response.json()
        assert len(rules) == 3

        # Step 4: Simulate model going down (mock failure response)
        # Create uptime checks that indicate both models are down
        down_check1 = UptimeCheck(
            model_id=model1.id,
            status="down",
            error="Connection refused",
        )
        down_check2 = UptimeCheck(
            model_id=model2.id,
            status="down",
            error="Service unavailable",
        )
        db_session.add_all([down_check1, down_check2])
        await db_session.commit()

        # Step 5: Run alert evaluation (simulating what happens after uptime check)
        alerts = await evaluate_alerts(db_session, [down_check1, down_check2])

        # Save alerts to database
        for alert in alerts:
            db_session.add(alert)
        await db_session.commit()

        # Step 6: Verify alerts are triggered
        # We expect:
        # - 2 alerts from any_model_down (one per down model)
        # - 1 alert from specific_model_down (for model1)
        # - 1 alert from model_unavailable_everywhere (both models with same model_id are down)
        alerts_response = client.get("/api/v1/alerts")
        assert alerts_response.status_code == 200
        alerts_data = alerts_response.json()

        # Check that multiple alerts were created
        assert alerts_data["unacknowledged_count"] >= 3  # At least one per rule type
        assert len(alerts_data["items"]) >= 3

        # Step 7: Check unread count endpoint shows correct count
        initial_unread = alerts_data["unacknowledged_count"]
        assert initial_unread >= 3

        # Step 8: Acknowledge first alert
        first_alert_id = alerts_data["items"][0]["id"]
        ack_response = client.patch(f"/api/v1/alerts/{first_alert_id}/acknowledge")
        assert ack_response.status_code == 200
        assert ack_response.json()["acknowledged"] is True

        # Step 9: Verify unread count decreased
        alerts_after_ack = client.get("/api/v1/alerts").json()
        assert alerts_after_ack["unacknowledged_count"] == initial_unread - 1

        # Step 10: Filter alerts by rule_id
        filtered_response = client.get(f"/api/v1/alerts?rule_id={rule1_id}")
        assert filtered_response.status_code == 200
        filtered_data = filtered_response.json()
        assert all(a["rule_id"] == rule1_id for a in filtered_data["items"])

    @pytest.mark.asyncio
    async def test_alert_deduplication(self, client: TestClient, db_session: AsyncSession) -> None:
        """Test that duplicate alerts are not created for active incidents."""
        from arguslm.server.core.alert_evaluator import evaluate_alerts
        from arguslm.server.models.alert import Alert, AlertRule

        # Create provider and model
        provider = ProviderAccount(
            provider_type="openai",
            display_name="Dedup Test Provider",
            enabled=True,
        )
        provider.credentials = {"api_key": "sk-test-key"}
        db_session.add(provider)
        await db_session.commit()
        await db_session.refresh(provider)

        model = Model(
            provider_account_id=provider.id,
            model_id="gpt-4o-dedup",
            source="discovered",
            enabled_for_monitoring=True,
        )
        db_session.add(model)
        await db_session.commit()
        await db_session.refresh(model)

        # Create alert rule
        rule_response = client.post(
            "/api/v1/alerts/rules",
            json={
                "name": "Dedup Test Rule",
                "rule_type": "any_model_down",
                "enabled": True,
                "notify_in_app": True,
            },
        )
        rule_id = rule_response.json()["id"]

        # First outage - should create alert
        down_check1 = UptimeCheck(
            model_id=model.id,
            status="down",
            error="First outage",
        )
        alerts1 = await evaluate_alerts(db_session, [down_check1])
        for alert in alerts1:
            db_session.add(alert)
        await db_session.commit()

        assert len(alerts1) == 1

        # Second outage while first is still unacknowledged - should NOT create duplicate
        down_check2 = UptimeCheck(
            model_id=model.id,
            status="down",
            error="Still down",
        )
        alerts2 = await evaluate_alerts(db_session, [down_check2])

        assert len(alerts2) == 0  # No new alert created

        # Acknowledge the first alert
        alerts_response = client.get("/api/v1/alerts")
        first_alert_id = alerts_response.json()["items"][0]["id"]
        client.patch(f"/api/v1/alerts/{first_alert_id}/acknowledge")

        # Third outage after acknowledgment - should create new alert
        down_check3 = UptimeCheck(
            model_id=model.id,
            status="down",
            error="Down again after recovery",
        )
        alerts3 = await evaluate_alerts(db_session, [down_check3])

        assert len(alerts3) == 1  # New alert created

    @pytest.mark.asyncio
    async def test_disabled_rules_not_evaluated(
        self, client: TestClient, db_session: AsyncSession
    ) -> None:
        """Test that disabled alert rules are not evaluated."""
        from arguslm.server.core.alert_evaluator import evaluate_alerts

        # Create provider and model
        provider = ProviderAccount(
            provider_type="openai",
            display_name="Disabled Rule Test Provider",
            enabled=True,
        )
        provider.credentials = {"api_key": "sk-test-key"}
        db_session.add(provider)
        await db_session.commit()
        await db_session.refresh(provider)

        model = Model(
            provider_account_id=provider.id,
            model_id="gpt-4o-disabled",
            source="discovered",
            enabled_for_monitoring=True,
        )
        db_session.add(model)
        await db_session.commit()
        await db_session.refresh(model)

        # Create disabled alert rule
        rule_response = client.post(
            "/api/v1/alerts/rules",
            json={
                "name": "Disabled Test Rule",
                "rule_type": "any_model_down",
                "enabled": False,  # Disabled
                "notify_in_app": True,
            },
        )
        assert rule_response.status_code == 201

        # Model goes down
        down_check = UptimeCheck(
            model_id=model.id,
            status="down",
            error="Should not trigger disabled rule",
        )
        alerts = await evaluate_alerts(db_session, [down_check])

        # No alerts should be created for disabled rule
        assert len(alerts) == 0


# =============================================================================
# ERROR SCENARIO TESTS
# =============================================================================


class TestErrorScenarios:
    """E2E tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_provider_connection_failure(
        self, client: TestClient, db_session: AsyncSession
    ) -> None:
        """Test provider connection failure handling."""
        # Create provider
        provider_response = client.post(
            "/api/v1/providers",
            json={
                "provider_type": "openai",
                "display_name": "Connection Failure Test",
                "credentials": {"api_key": "invalid-key"},
            },
        )
        provider_id = provider_response.json()["id"]

        # Test connection with failure
        with patch("arguslm.server.api.providers.LiteLLMClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.complete = AsyncMock(
                side_effect=Exception("Authentication failed: Invalid API key")
            )
            mock_client_class.return_value = mock_client

            test_response = client.post(f"/api/v1/providers/{provider_id}/test")

            assert test_response.status_code == 200
            test_data = test_response.json()
            assert test_data["success"] is False
            assert "failed" in test_data["message"].lower()
            assert "details" in test_data

    @pytest.mark.asyncio
    async def test_model_discovery_failure(
        self, client: TestClient, db_session: AsyncSession
    ) -> None:
        """Test model discovery failure handling."""
        # Create provider
        provider_response = client.post(
            "/api/v1/providers",
            json={
                "provider_type": "openai",
                "display_name": "Discovery Failure Test",
                "credentials": {"api_key": "sk-test-key"},
            },
        )
        provider_id = provider_response.json()["id"]

        # Model discovery fails
        with patch("arguslm.server.api.providers.OpenAIModelSource") as mock_source_class:
            mock_source = AsyncMock()
            mock_source.list_models = AsyncMock(side_effect=Exception("API rate limit exceeded"))
            mock_source_class.return_value = mock_source

            refresh_response = client.post(f"/api/v1/providers/{provider_id}/refresh-models")

            assert refresh_response.status_code == 500
            assert "failed" in refresh_response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_benchmark_with_nonexistent_model(
        self, client: TestClient, db_session: AsyncSession
    ) -> None:
        """Test benchmark creation with non-existent model ID."""
        fake_model_id = str(uuid.uuid4())

        benchmark_response = client.post(
            "/api/v1/benchmarks",
            json={
                "model_ids": [fake_model_id],
                "prompt_pack": "shakespeare",
                "name": "Should Fail",
            },
        )

        assert benchmark_response.status_code == 400
        assert "not found" in benchmark_response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_nonexistent_provider(self, client: TestClient) -> None:
        """Test getting a non-existent provider."""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/providers/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_nonexistent_benchmark(self, client: TestClient) -> None:
        """Test getting a non-existent benchmark run."""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/benchmarks/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_acknowledge_nonexistent_alert(self, client: TestClient) -> None:
        """Test acknowledging a non-existent alert."""
        fake_id = str(uuid.uuid4())
        response = client.patch(f"/api/v1/alerts/{fake_id}/acknowledge")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_monitoring_config(self, client: TestClient) -> None:
        """Test invalid monitoring configuration."""
        # Invalid interval (0)
        response = client.patch(
            "/api/v1/monitoring/config",
            json={"interval_minutes": 0},
        )
        assert response.status_code == 422

        # Invalid prompt pack
        response = client.patch(
            "/api/v1/monitoring/config",
            json={"prompt_pack": "invalid_pack"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_specific_model_down_without_target(self, client: TestClient) -> None:
        """Test creating specific_model_down rule without target_model_id."""
        response = client.post(
            "/api/v1/alerts/rules",
            json={
                "name": "Missing Target",
                "rule_type": "specific_model_down",
                "enabled": True,
                "notify_in_app": True,
            },
        )

        assert response.status_code == 400
        assert "target_model_id" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_provider_with_history(
        self, client: TestClient, db_session: AsyncSession
    ) -> None:
        """Test deleting a provider with benchmark history fails."""
        # Create provider
        provider = ProviderAccount(
            provider_type="openai",
            display_name="Has History Provider",
            enabled=True,
        )
        provider.credentials = {"api_key": "sk-test-key"}
        db_session.add(provider)
        await db_session.commit()
        await db_session.refresh(provider)

        # Create model
        model = Model(
            provider_account_id=provider.id,
            model_id="gpt-4o-history",
            source="discovered",
            enabled_for_benchmark=True,
        )
        db_session.add(model)
        await db_session.commit()
        await db_session.refresh(model)

        # Create benchmark run and result
        run = BenchmarkRun(
            name="History Test",
            model_ids=[str(model.id)],
            prompt_pack="shakespeare",
            status="completed",
            triggered_by="user",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        db_session.add(run)
        await db_session.commit()
        await db_session.refresh(run)

        result = BenchmarkResult(
            run_id=run.id,
            model_id=model.id,
            ttft_ms=100.0,
            tps=50.0,
            tps_excluding_ttft=55.0,
            total_latency_ms=2000.0,
            input_tokens=50,
            output_tokens=100,
            estimated_cost=0.01,
        )
        db_session.add(result)
        await db_session.commit()

        # Try to delete provider - should fail
        delete_response = client.delete(f"/api/v1/providers/{provider.id}")
        assert delete_response.status_code == 409
        assert "benchmark history" in delete_response.json()["detail"].lower()


# =============================================================================
# INTEGRATION TESTS - Combined Flows
# =============================================================================


class TestCombinedFlows:
    """Tests that combine multiple user flows."""

    @pytest.mark.asyncio
    async def test_full_monitoring_alert_flow(
        self, client: TestClient, db_session: AsyncSession
    ) -> None:
        """Test complete flow from model setup to alert notification."""
        from arguslm.server.core.alert_evaluator import evaluate_alerts

        # Step 1: Create provider via API
        provider_response = client.post(
            "/api/v1/providers",
            json={
                "provider_type": "openai",
                "display_name": "Full Flow Test",
                "credentials": {"api_key": "sk-full-flow-test"},
            },
        )
        assert provider_response.status_code == 201
        provider_id = provider_response.json()["id"]

        # Step 2: Add models via mock discovery
        with patch("arguslm.server.api.providers.OpenAIModelSource") as mock_source_class:
            mock_source = AsyncMock()
            mock_source.list_models = AsyncMock(
                return_value=[
                    MagicMock(id="gpt-4o", provider_type="openai", metadata={}),
                ]
            )
            mock_source_class.return_value = mock_source

            client.post(f"/api/v1/providers/{provider_id}/refresh-models")

        # Get the created model
        models_response = client.get(f"/api/v1/models?provider_id={provider_id}")
        model_data = models_response.json()["items"][0]

        # Step 3: Enable monitoring for the model
        client.patch(
            f"/api/v1/models/{model_data['id']}",
            json={"enabled_for_monitoring": True},
        )

        # Step 4: Set up alert rule
        rule_response = client.post(
            "/api/v1/alerts/rules",
            json={
                "name": "Full Flow Alert",
                "rule_type": "any_model_down",
                "enabled": True,
                "notify_in_app": True,
            },
        )
        assert rule_response.status_code == 201

        # Step 5: Configure monitoring
        client.patch(
            "/api/v1/monitoring/config",
            json={"interval_minutes": 5, "enabled": True},
        )

        # Step 6: Simulate uptime check (model down)
        from sqlalchemy import select

        model_result = await db_session.execute(
            select(Model).where(Model.id == uuid.UUID(model_data["id"]))
        )
        model = model_result.scalar_one()

        down_check = UptimeCheck(
            model_id=model.id,
            status="down",
            error="Simulated outage",
        )
        db_session.add(down_check)
        await db_session.commit()

        # Step 7: Evaluate alerts
        alerts = await evaluate_alerts(db_session, [down_check])
        for alert in alerts:
            db_session.add(alert)
        await db_session.commit()

        # Step 8: Verify alert was created
        alerts_response = client.get("/api/v1/alerts")
        assert alerts_response.status_code == 200
        alerts_data = alerts_response.json()
        assert alerts_data["unacknowledged_count"] == 1
        assert "down" in alerts_data["items"][0]["message"].lower()

        # Step 9: Check uptime history shows the outage
        uptime_response = client.get("/api/v1/monitoring/uptime?status=down")
        assert uptime_response.status_code == 200
        uptime_data = uptime_response.json()
        assert uptime_data["total"] >= 1

        # Step 10: Model recovers
        up_check = UptimeCheck(
            model_id=model.id,
            status="up",
            latency_ms=150.0,
        )
        db_session.add(up_check)
        await db_session.commit()

        # Step 11: Verify recovery is tracked
        all_uptime = client.get("/api/v1/monitoring/uptime").json()
        statuses = [item["status"] for item in all_uptime["items"]]
        assert "up" in statuses
        assert "down" in statuses
