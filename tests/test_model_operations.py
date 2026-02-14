"""Tests for manual model operations and custom naming."""

import os
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from arguslm.server.core.security import CredentialEncryption
from arguslm.server.models.base import Base
from arguslm.server.models.model import Model, create_manual_model, update_custom_name, validate_model_id
from arguslm.server.models.provider import ProviderAccount

# Test encryption key
TEST_ENCRYPTION_KEY = CredentialEncryption.generate_key()


@pytest.fixture
async def db_session():
    """Create in-memory SQLite database for testing."""
    # Set encryption key for tests
    os.environ["ENCRYPTION_KEY"] = TEST_ENCRYPTION_KEY

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def provider_account(db_session: AsyncSession):
    """Create a test provider account."""
    account = ProviderAccount(
        provider_type="openai",
        display_name="Test Account",
        credentials={"api_key": "test-key"},
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    return account


@pytest.mark.asyncio
async def test_create_manual_model(db_session: AsyncSession, provider_account: ProviderAccount):
    """Test creating a manual model with custom name."""
    model = await create_manual_model(
        db_session=db_session,
        provider_account_id=provider_account.id,
        model_id="custom-model-v1",
        custom_name="My Custom Model",
        metadata={"description": "A manually added model"},
    )

    assert model.id is not None
    assert model.model_id == "custom-model-v1"
    assert model.custom_name == "My Custom Model"
    assert model.source == "manual"
    assert model.provider_account_id == provider_account.id
    assert model.model_metadata == {"description": "A manually added model"}
    assert model.enabled_for_benchmark is True


@pytest.mark.asyncio
async def test_create_manual_model_without_custom_name(
    db_session: AsyncSession, provider_account: ProviderAccount
):
    """Test creating a manual model without custom name."""
    model = await create_manual_model(
        db_session=db_session,
        provider_account_id=provider_account.id,
        model_id="another-model",
        custom_name=None,
        metadata={},
    )

    assert model.model_id == "another-model"
    assert model.custom_name is None
    assert model.source == "manual"


@pytest.mark.asyncio
async def test_update_custom_name(db_session: AsyncSession, provider_account: ProviderAccount):
    """Test updating custom name of a model."""
    # Create a discovered model
    model = Model(
        provider_account_id=provider_account.id,
        model_id="gpt-4",
        source="discovered",
        model_metadata={},
    )
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)

    # Update custom name
    updated_model = await update_custom_name(
        db_session=db_session, model=model, new_name="GPT-4 Production"
    )

    assert updated_model.custom_name == "GPT-4 Production"
    assert updated_model.model_id == "gpt-4"
    assert updated_model.source == "discovered"


@pytest.mark.asyncio
async def test_update_custom_name_to_none(
    db_session: AsyncSession, provider_account: ProviderAccount
):
    """Test clearing custom name by setting to None."""
    model = Model(
        provider_account_id=provider_account.id,
        model_id="gpt-4",
        custom_name="Old Name",
        source="discovered",
        model_metadata={},
    )
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)

    updated_model = await update_custom_name(db_session=db_session, model=model, new_name=None)

    assert updated_model.custom_name is None


@pytest.mark.asyncio
async def test_validate_model_id_valid():
    """Test validation of valid model IDs."""
    assert validate_model_id("gpt-4") is True
    assert validate_model_id("claude-3-opus") is True
    assert validate_model_id("custom-model-v1") is True
    assert validate_model_id("model_with_underscore") is True
    assert validate_model_id("model123") is True


@pytest.mark.asyncio
async def test_validate_model_id_invalid():
    """Test validation of invalid model IDs."""
    assert validate_model_id("") is False
    assert validate_model_id("   ") is False
    assert validate_model_id("model with spaces") is False
    assert validate_model_id("model@special") is False
    assert validate_model_id("model/slash") is False


@pytest.mark.asyncio
async def test_persistence_across_sessions():
    """Test that custom names persist across database sessions."""
    # Set encryption key for tests
    os.environ["ENCRYPTION_KEY"] = TEST_ENCRYPTION_KEY

    # Create first session
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Session 1: Create model with custom name
    async with async_session() as session1:
        account = ProviderAccount(
            provider_type="openai",
            display_name="Test Account",
            credentials={"api_key": "test-key"},
        )
        session1.add(account)
        await session1.commit()
        await session1.refresh(account)

        model = await create_manual_model(
            db_session=session1,
            provider_account_id=account.id,
            model_id="persistent-model",
            custom_name="Persistent Name",
            metadata={},
        )
        model_id = model.id
        await session1.commit()

    # Session 2: Retrieve and verify
    async with async_session() as session2:
        from sqlalchemy import select

        stmt = select(Model).where(Model.id == model_id)
        result = await session2.execute(stmt)
        retrieved_model = result.scalar_one()

        assert retrieved_model.custom_name == "Persistent Name"
        assert retrieved_model.model_id == "persistent-model"
        assert retrieved_model.source == "manual"

    await engine.dispose()


@pytest.mark.asyncio
async def test_custom_model_in_benchmark(
    db_session: AsyncSession, provider_account: ProviderAccount
):
    """Test that custom models can be used in benchmarks."""
    model = await create_manual_model(
        db_session=db_session,
        provider_account_id=provider_account.id,
        model_id="benchmark-model",
        custom_name="Benchmark Test Model",
        metadata={},
    )

    # Verify model is enabled for benchmarks
    assert model.enabled_for_benchmark is True

    # Verify model can be queried for benchmarks
    from sqlalchemy import select

    stmt = select(Model).where(Model.enabled_for_benchmark == True)  # noqa: E712
    result = await db_session.execute(stmt)
    models = result.scalars().all()

    assert model in models
