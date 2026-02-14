"""Tests for database models, focusing on ProviderAccount with encryption."""

import os
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from arguslm.server.core.security import CredentialEncryption
from arguslm.server.models.base import Base
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


@pytest.mark.asyncio
async def test_create_provider_account(db_session: AsyncSession) -> None:
    """Test creating a ProviderAccount with encrypted credentials."""
    # Create provider account
    credentials = {
        "api_key": "sk-test-key-12345",
        "organization": "test-org",
    }

    account = ProviderAccount(
        provider_type="openai",
        display_name="My OpenAI Account",
        enabled=True,
    )
    account.credentials = credentials

    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)

    # Verify account was created
    assert account.id is not None
    assert account.provider_type == "openai"
    assert account.display_name == "My OpenAI Account"
    assert account.enabled is True
    assert account.created_at is not None
    assert account.updated_at is not None

    # Verify credentials are encrypted in database
    assert account.credentials_encrypted != str(credentials)
    assert "sk-test-key-12345" not in account.credentials_encrypted

    # Verify credentials can be decrypted
    decrypted = account.credentials
    assert decrypted == credentials
    assert decrypted["api_key"] == "sk-test-key-12345"
    assert decrypted["organization"] == "test-org"


@pytest.mark.asyncio
async def test_query_provider_account(db_session: AsyncSession) -> None:
    """Test querying and decrypting ProviderAccount credentials."""
    # Create provider account
    credentials = {
        "api_key": "sk-anthropic-test",
        "region": "us-west-2",
    }

    account = ProviderAccount(
        provider_type="anthropic",
        display_name="Anthropic Production",
        enabled=True,
    )
    account.credentials = credentials

    db_session.add(account)
    await db_session.commit()

    account_id = account.id

    # Clear session to force fresh query
    await db_session.close()

    # Query account
    result = await db_session.execute(
        select(ProviderAccount).where(ProviderAccount.id == account_id)
    )
    queried_account = result.scalar_one()

    # Verify credentials are decrypted correctly
    assert queried_account.credentials == credentials
    assert queried_account.credentials["api_key"] == "sk-anthropic-test"
    assert queried_account.credentials["region"] == "us-west-2"


@pytest.mark.asyncio
async def test_update_provider_account_credentials(db_session: AsyncSession) -> None:
    """Test updating ProviderAccount credentials."""
    # Create provider account
    original_credentials = {"api_key": "old-key"}

    account = ProviderAccount(
        provider_type="openai",
        display_name="Test Account",
        enabled=True,
    )
    account.credentials = original_credentials

    db_session.add(account)
    await db_session.commit()

    # Update credentials
    new_credentials = {"api_key": "new-key", "endpoint": "https://api.example.com"}
    account.credentials = new_credentials

    await db_session.commit()
    await db_session.refresh(account)

    # Verify credentials were updated
    assert account.credentials == new_credentials
    assert account.credentials["api_key"] == "new-key"
    assert account.credentials["endpoint"] == "https://api.example.com"


@pytest.mark.asyncio
async def test_delete_provider_account(db_session: AsyncSession) -> None:
    """Test deleting a ProviderAccount."""
    # Create provider account
    account = ProviderAccount(
        provider_type="openai",
        display_name="To Be Deleted",
        enabled=True,
    )
    account.credentials = {"api_key": "test"}

    db_session.add(account)
    await db_session.commit()

    account_id = account.id

    # Delete account
    await db_session.delete(account)
    await db_session.commit()

    # Verify account was deleted
    result = await db_session.execute(
        select(ProviderAccount).where(ProviderAccount.id == account_id)
    )
    deleted_account = result.scalar_one_or_none()

    assert deleted_account is None
