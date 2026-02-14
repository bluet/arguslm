"""Tests for export API endpoints."""

import json
import os
import uuid
from datetime import datetime, timezone
from io import StringIO

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from arguslm.server.core.security import CredentialEncryption
from arguslm.server.db.init import get_db
from arguslm.server.main import app
from arguslm.server.models.base import Base
from arguslm.server.models.benchmark import BenchmarkResult, BenchmarkRun
from arguslm.server.models.model import Model
from arguslm.server.models.monitoring import UptimeCheck
from arguslm.server.models.provider import ProviderAccount

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Test encryption key
TEST_ENCRYPTION_KEY = CredentialEncryption.generate_key()


@pytest.fixture(scope="function")
async def db_session() -> AsyncSession:
    """Create a test database session."""
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
def client(db_session: AsyncSession):
    """Create test client with database override."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
async def sample_benchmark_run(db_session: AsyncSession):
    """Create a sample benchmark run with results for testing."""
    # Create provider account
    provider = ProviderAccount(
        provider_type="openai",
        display_name="Test OpenAI Account",
        enabled=True,
    )
    provider.credentials = {"api_key": "sk-test-key"}
    db_session.add(provider)
    await db_session.flush()

    # Create model
    model = Model(
        provider_account_id=provider.id,
        model_id="gpt-4o",
        custom_name="GPT-4o Test",
        source="manual",
        enabled_for_benchmark=True,
        model_metadata={},
    )
    db_session.add(model)
    await db_session.flush()

    # Create benchmark run
    run = BenchmarkRun(
        name="Test Benchmark Run",
        model_ids=[str(model.id)],
        prompt_pack="shakespeare",
        status="completed",
        triggered_by="user",
        started_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        completed_at=datetime(2024, 1, 1, 12, 5, 0, tzinfo=timezone.utc),
    )
    db_session.add(run)
    await db_session.flush()

    # Create benchmark results
    result1 = BenchmarkResult(
        run_id=run.id,
        model_id=model.id,
        ttft_ms=150.5,
        tps=25.3,
        tps_excluding_ttft=28.1,
        total_latency_ms=2500.0,
        input_tokens=100,
        output_tokens=200,
        estimated_cost=0.005,
        error=None,
    )
    result2 = BenchmarkResult(
        run_id=run.id,
        model_id=model.id,
        ttft_ms=145.2,
        tps=26.1,
        tps_excluding_ttft=29.0,
        total_latency_ms=2450.0,
        input_tokens=100,
        output_tokens=200,
        estimated_cost=0.005,
        error=None,
    )
    db_session.add_all([result1, result2])
    await db_session.commit()

    return {"run": run, "model": model, "results": [result1, result2]}


@pytest.mark.asyncio
async def test_export_benchmark_json(client: TestClient, sample_benchmark_run: dict):
    """Test exporting benchmark results as JSON."""
    run = sample_benchmark_run["run"]
    model = sample_benchmark_run["model"]

    # Make request
    response = client.get(f"/api/v1/benchmarks/{run.id}/export?format=json")

    # Verify response
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert "content-disposition" in response.headers
    assert f"benchmark_{run.id}.json" in response.headers["content-disposition"]

    # Verify JSON content
    data = response.json()
    assert "run_id" in data
    assert "run_name" in data
    assert "results" in data
    assert len(data["results"]) == 2

    # Verify result fields
    result = data["results"][0]
    assert "model_name" in result
    assert result["model_name"] == "GPT-4o Test"
    assert "provider" in result
    assert "ttft_ms" in result
    assert "tps" in result
    assert "tps_excluding_ttft" in result
    assert "total_latency_ms" in result
    assert "input_tokens" in result
    assert "output_tokens" in result
    assert "error" in result
    assert "timestamp" in result


@pytest.mark.asyncio
async def test_export_benchmark_csv(client: TestClient, sample_benchmark_run: dict):
    """Test exporting benchmark results as CSV."""
    run = sample_benchmark_run["run"]
    model = sample_benchmark_run["model"]

    # Make request
    response = client.get(f"/api/v1/benchmarks/{run.id}/export?format=csv")

    # Verify response
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert "content-disposition" in response.headers
    assert f"benchmark_{run.id}.csv" in response.headers["content-disposition"]

    # Verify CSV content
    csv_content = response.text
    lines = csv_content.strip().split("\n")

    # Check header
    assert len(lines) >= 2  # Header + at least 1 data row
    header = lines[0]
    assert "model_name" in header
    assert "provider" in header
    assert "ttft_ms" in header
    assert "tps" in header
    assert "tps_excluding_ttft" in header
    assert "total_latency_ms" in header
    assert "input_tokens" in header
    assert "output_tokens" in header
    assert "error" in header
    assert "timestamp" in header

    # Check data rows
    assert len(lines) == 3  # Header + 2 results
    assert "GPT-4o Test" in lines[1]
    assert "openai" in lines[1]


@pytest.fixture
async def sample_uptime_checks(db_session: AsyncSession):
    """Create sample uptime checks for testing."""
    # Create provider account
    provider = ProviderAccount(
        provider_type="anthropic",
        display_name="Test Anthropic Account",
        enabled=True,
    )
    provider.credentials = {"api_key": "sk-ant-test-key"}
    db_session.add(provider)
    await db_session.flush()

    # Create model
    model = Model(
        provider_account_id=provider.id,
        model_id="claude-3-opus",
        custom_name="Claude 3 Opus Test",
        source="manual",
        enabled_for_monitoring=True,
        model_metadata={},
    )
    db_session.add(model)
    await db_session.flush()

    # Create uptime checks
    check1 = UptimeCheck(
        model_id=model.id,
        status="up",
        latency_ms=250.5,
        error=None,
    )
    check2 = UptimeCheck(
        model_id=model.id,
        status="down",
        latency_ms=None,
        error="Connection timeout",
    )
    db_session.add_all([check1, check2])
    await db_session.commit()

    return {"model": model, "checks": [check1, check2]}


@pytest.mark.asyncio
async def test_export_uptime_json(client: TestClient, sample_uptime_checks: dict):
    """Test exporting uptime history as JSON."""
    model = sample_uptime_checks["model"]

    # Make request
    response = client.get("/api/v1/monitoring/uptime/export?format=json")

    # Verify response
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert "content-disposition" in response.headers
    assert "uptime_history.json" in response.headers["content-disposition"]

    # Verify JSON content
    data = response.json()
    assert "checks" in data
    assert len(data["checks"]) == 2

    # Verify check fields
    check = data["checks"][0]
    assert "model_name" in check
    assert "provider" in check
    assert "status" in check
    assert "latency_ms" in check
    assert "error" in check
    assert "timestamp" in check


@pytest.mark.asyncio
async def test_export_uptime_csv_with_filters(client: TestClient, sample_uptime_checks: dict):
    """Test exporting uptime history as CSV with date filters."""
    model = sample_uptime_checks["model"]

    # Make request with model filter
    response = client.get(f"/api/v1/monitoring/uptime/export?format=csv&model_id={model.id}")

    # Verify response
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert "content-disposition" in response.headers
    assert "uptime_history.csv" in response.headers["content-disposition"]

    # Verify CSV content
    csv_content = response.text
    lines = csv_content.strip().split("\n")

    # Check header
    assert len(lines) >= 2  # Header + at least 1 data row
    header = lines[0]
    assert "model_name" in header
    assert "provider" in header
    assert "status" in header
    assert "latency_ms" in header
    assert "error" in header
    assert "timestamp" in header

    # Check data rows
    assert len(lines) == 3  # Header + 2 checks
    assert "Claude 3 Opus Test" in lines[1]
    assert "anthropic" in lines[1]
