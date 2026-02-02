"""Tests for Benchmark API endpoints."""

import os
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import CredentialEncryption
from app.db.init import get_db
from app.main import app
from app.models.base import Base
from app.models.benchmark import BenchmarkResult, BenchmarkRun
from app.models.model import Model
from app.models.provider import ProviderAccount

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


@pytest.fixture
async def test_models(db_session: AsyncSession, provider_account: ProviderAccount) -> list[Model]:
    """Create multiple test models.

    Args:
        db_session: Test database session
        provider_account: Test provider account

    Returns:
        List of Model instances
    """
    models = []
    for i, model_id in enumerate(["gpt-4o", "gpt-3.5-turbo", "claude-3-opus"]):
        model = Model(
            provider_account_id=provider_account.id,
            model_id=model_id,
            custom_name=f"Test Model {i}",
            source="discovered",
            enabled_for_monitoring=True,
            enabled_for_benchmark=True,
            model_metadata={},
        )
        db_session.add(model)
        models.append(model)

    await db_session.commit()
    for model in models:
        await db_session.refresh(model)

    return models


@pytest.fixture
async def test_benchmark_run(db_session: AsyncSession, test_model: Model) -> BenchmarkRun:
    """Create a test benchmark run.

    Args:
        db_session: Test database session
        test_model: Test model

    Returns:
        BenchmarkRun instance
    """
    run = BenchmarkRun(
        name="Test Benchmark Run",
        model_ids=[str(test_model.id)],
        prompt_pack="shakespeare",
        status="completed",
        triggered_by="user",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)

    # Add some results
    result = BenchmarkResult(
        run_id=run.id,
        model_id=test_model.id,
        ttft_ms=150.5,
        tps=45.2,
        tps_excluding_ttft=52.3,
        total_latency_ms=2500.0,
        input_tokens=50,
        output_tokens=100,
        estimated_cost=0.005,
        error=None,
    )
    db_session.add(result)
    await db_session.commit()
    await db_session.refresh(run)

    return run


@pytest.fixture
async def test_benchmark_runs(db_session: AsyncSession, test_model: Model) -> list[BenchmarkRun]:
    """Create multiple test benchmark runs with different statuses.

    Args:
        db_session: Test database session
        test_model: Test model

    Returns:
        List of BenchmarkRun instances
    """
    runs = []
    statuses = ["pending", "running", "completed", "failed"]

    for i, status in enumerate(statuses):
        run = BenchmarkRun(
            name=f"Benchmark Run {i}",
            model_ids=[str(test_model.id)],
            prompt_pack="shakespeare",
            status=status,
            triggered_by="user",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc) if status in ["completed", "failed"] else None,
        )
        db_session.add(run)
        runs.append(run)

    await db_session.commit()
    for run in runs:
        await db_session.refresh(run)

    return runs


# Test 1: Create benchmark (returns pending status)
@pytest.mark.asyncio
async def test_create_benchmark_returns_pending(
    client: TestClient, db_session: AsyncSession, test_model: Model
) -> None:
    """Test creating a benchmark returns pending status."""
    create_data = {
        "model_ids": [str(test_model.id)],
        "prompt_pack": "shakespeare",
        "name": "Test Benchmark",
        "max_tokens": 200,
        "num_runs": 3,
    }

    # Mock the background task to prevent actual execution
    with patch("app.api.benchmarks._run_benchmark_task", new_callable=AsyncMock):
        response = client.post("/api/v1/benchmarks", json=create_data)

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "pending"
    assert "id" in data
    assert data["message"] == "Benchmark run started"


# Test 2: List benchmarks (empty)
@pytest.mark.asyncio
async def test_list_benchmarks_empty(client: TestClient) -> None:
    """Test listing benchmarks when database is empty."""
    response = client.get("/api/v1/benchmarks")

    assert response.status_code == 200
    data = response.json()
    assert data["runs"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["per_page"] == 20


# Test 3: List benchmarks (with data)
@pytest.mark.asyncio
async def test_list_benchmarks_with_data(
    client: TestClient, db_session: AsyncSession, test_benchmark_runs: list[BenchmarkRun]
) -> None:
    """Test listing benchmarks with data in database."""
    response = client.get("/api/v1/benchmarks")

    assert response.status_code == 200
    data = response.json()
    assert len(data["runs"]) == 4
    assert data["total"] == 4


# Test 4: Get benchmark by ID
@pytest.mark.asyncio
async def test_get_benchmark_by_id(
    client: TestClient, db_session: AsyncSession, test_benchmark_run: BenchmarkRun
) -> None:
    """Test getting a benchmark by ID."""
    response = client.get(f"/api/v1/benchmarks/{test_benchmark_run.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_benchmark_run.id)
    assert data["name"] == "Test Benchmark Run"
    assert data["status"] == "completed"
    assert data["prompt_pack"] == "shakespeare"
    assert len(data["results"]) == 1
    assert "statistics" in data


# Test 5: Get benchmark results
@pytest.mark.asyncio
async def test_get_benchmark_results(
    client: TestClient, db_session: AsyncSession, test_benchmark_run: BenchmarkRun
) -> None:
    """Test getting detailed results for a benchmark run."""
    response = client.get(f"/api/v1/benchmarks/{test_benchmark_run.id}/results")

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1
    assert data["total"] == 1

    result = data["results"][0]
    assert result["ttft_ms"] == 150.5
    assert result["tps"] == 45.2
    assert result["tps_excluding_ttft"] == 52.3


# Test 6: List benchmarks with status filter
@pytest.mark.asyncio
async def test_list_benchmarks_with_status_filter(
    client: TestClient, db_session: AsyncSession, test_benchmark_runs: list[BenchmarkRun]
) -> None:
    """Test filtering benchmarks by status."""
    response = client.get("/api/v1/benchmarks?status=completed")

    assert response.status_code == 200
    data = response.json()
    assert len(data["runs"]) == 1
    assert data["runs"][0]["status"] == "completed"
    assert data["total"] == 1


# Test 7: Get non-existent benchmark (404)
@pytest.mark.asyncio
async def test_get_benchmark_not_found(client: TestClient) -> None:
    """Test getting a non-existent benchmark returns 404."""
    fake_id = uuid.uuid4()
    response = client.get(f"/api/v1/benchmarks/{fake_id}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# Test 8: Create benchmark with invalid model_ids (400)
@pytest.mark.asyncio
async def test_create_benchmark_invalid_model_ids(client: TestClient) -> None:
    """Test creating a benchmark with invalid model IDs returns 400."""
    fake_id = uuid.uuid4()
    create_data = {
        "model_ids": [str(fake_id)],
        "prompt_pack": "shakespeare",
    }

    response = client.post("/api/v1/benchmarks", json=create_data)

    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()


# Test 9: Get results for non-existent benchmark (404)
@pytest.mark.asyncio
async def test_get_benchmark_results_not_found(client: TestClient) -> None:
    """Test getting results for a non-existent benchmark returns 404."""
    fake_id = uuid.uuid4()
    response = client.get(f"/api/v1/benchmarks/{fake_id}/results")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# Test 10: Create benchmark with minimal data
@pytest.mark.asyncio
async def test_create_benchmark_minimal(
    client: TestClient, db_session: AsyncSession, test_model: Model
) -> None:
    """Test creating a benchmark with minimal required data."""
    create_data = {
        "model_ids": [str(test_model.id)],
        "prompt_pack": "synthetic_short",
    }

    with patch("app.api.benchmarks._run_benchmark_task", new_callable=AsyncMock):
        response = client.post("/api/v1/benchmarks", json=create_data)

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "pending"


# Test 11: List benchmarks with pagination
@pytest.mark.asyncio
async def test_list_benchmarks_pagination(
    client: TestClient, db_session: AsyncSession, test_model: Model
) -> None:
    """Test benchmark list pagination."""
    # Create 5 benchmark runs
    for i in range(5):
        run = BenchmarkRun(
            name=f"Benchmark {i}",
            model_ids=[str(test_model.id)],
            prompt_pack="shakespeare",
            status="completed",
            triggered_by="user",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        db_session.add(run)
    await db_session.commit()

    # Get first page with per_page=2
    response = client.get("/api/v1/benchmarks?page=1&per_page=2")

    assert response.status_code == 200
    data = response.json()
    assert len(data["runs"]) == 2
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["per_page"] == 2

    # Get second page
    response = client.get("/api/v1/benchmarks?page=2&per_page=2")

    assert response.status_code == 200
    data = response.json()
    assert len(data["runs"]) == 2
    assert data["page"] == 2


# Test 12: Benchmark detail includes statistics
@pytest.mark.asyncio
async def test_benchmark_detail_includes_statistics(
    client: TestClient, db_session: AsyncSession, test_model: Model
) -> None:
    """Test that benchmark detail response includes statistics."""
    # Create a run with multiple results
    run = BenchmarkRun(
        name="Stats Test Run",
        model_ids=[str(test_model.id)],
        prompt_pack="shakespeare",
        status="completed",
        triggered_by="user",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)

    # Add multiple results for statistics calculation
    for i, (ttft, tps) in enumerate([(100, 40), (150, 45), (200, 50)]):
        result = BenchmarkResult(
            run_id=run.id,
            model_id=test_model.id,
            ttft_ms=float(ttft),
            tps=float(tps),
            tps_excluding_ttft=float(tps + 5),
            total_latency_ms=2000.0 + i * 100,
            input_tokens=50,
            output_tokens=100,
            estimated_cost=0.005,
            error=None,
        )
        db_session.add(result)
    await db_session.commit()

    response = client.get(f"/api/v1/benchmarks/{run.id}")

    assert response.status_code == 200
    data = response.json()

    assert "statistics" in data
    stats = data["statistics"]
    assert "ttft_p50" in stats
    assert "ttft_p95" in stats
    assert "ttft_p99" in stats
    assert "tps_p50" in stats
    assert "tps_p95" in stats
    assert "tps_p99" in stats
    # P50 should be around the middle value (150 for ttft, 45 for tps)
    assert stats["ttft_p50"] == 150.0
    assert stats["tps_p50"] == 45.0


# Test 13: Create benchmark with empty model_ids (validation error)
@pytest.mark.asyncio
async def test_create_benchmark_empty_model_ids(client: TestClient) -> None:
    """Test creating a benchmark with empty model_ids returns validation error."""
    create_data = {
        "model_ids": [],
        "prompt_pack": "shakespeare",
    }

    response = client.post("/api/v1/benchmarks", json=create_data)

    # Pydantic validation error (422) for empty list violating min_length=1
    assert response.status_code == 422


# Test 14: WebSocket connection test (mock)
@pytest.mark.asyncio
async def test_websocket_connection(
    client: TestClient, db_session: AsyncSession, test_benchmark_run: BenchmarkRun
) -> None:
    """Test WebSocket connection for benchmark streaming."""
    # Use the WebSocket test client
    with client.websocket_connect(
        f"/api/v1/benchmarks/{test_benchmark_run.id}/stream"
    ) as websocket:
        # Send a ping
        websocket.send_text("ping")
        # Expect a pong response
        response = websocket.receive_text()
        assert response == "pong"
