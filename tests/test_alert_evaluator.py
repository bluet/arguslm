"""Tests for alert evaluation service."""

import os
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.alert_evaluator import (
    _evaluate_any_model_down,
    _evaluate_model_unavailable_everywhere,
    _evaluate_specific_model_down,
    _has_active_incident,
    evaluate_alerts,
)
from app.core.security import CredentialEncryption
from app.models.alert import Alert, AlertRule
from app.models.base import Base
from app.models.model import Model
from app.models.monitoring import UptimeCheck
from app.models.provider import ProviderAccount

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Test encryption key
TEST_ENCRYPTION_KEY = CredentialEncryption.generate_key()


@pytest.fixture(scope="function")
async def db_session() -> AsyncSession:
    """Create a test database session."""
    os.environ["ENCRYPTION_KEY"] = TEST_ENCRYPTION_KEY

    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def provider_account(db_session: AsyncSession) -> ProviderAccount:
    """Create a test provider account."""
    account = ProviderAccount(
        display_name="Test Provider",
        provider_type="openai",
        enabled=True,
        credentials_encrypted="encrypted_test_key",
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    return account


@pytest.fixture
async def test_model(db_session: AsyncSession, provider_account: ProviderAccount) -> Model:
    """Create a test model."""
    model = Model(
        provider_account_id=provider_account.id,
        model_id="gpt-4o",
        source="discovered",
        enabled_for_monitoring=True,
    )
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)
    return model


@pytest.fixture
async def test_model_2(db_session: AsyncSession, provider_account: ProviderAccount) -> Model:
    """Create a second test model with same name."""
    model = Model(
        provider_account_id=provider_account.id,
        model_id="gpt-4o",
        source="discovered",
        enabled_for_monitoring=True,
    )
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)
    return model


@pytest.fixture
async def any_model_down_rule(db_session: AsyncSession) -> AlertRule:
    """Create an any_model_down rule."""
    rule = AlertRule(
        name="Any Model Down",
        rule_type="any_model_down",
        enabled=True,
        notify_in_app=True,
    )
    db_session.add(rule)
    await db_session.commit()
    await db_session.refresh(rule)
    return rule


@pytest.fixture
async def specific_model_down_rule(db_session: AsyncSession, test_model: Model) -> AlertRule:
    """Create a specific_model_down rule."""
    rule = AlertRule(
        name="Specific Model Down",
        rule_type="specific_model_down",
        target_model_id=test_model.id,
        enabled=True,
        notify_in_app=True,
    )
    db_session.add(rule)
    await db_session.commit()
    await db_session.refresh(rule)
    return rule


@pytest.fixture
async def model_unavailable_rule(db_session: AsyncSession) -> AlertRule:
    """Create a model_unavailable_everywhere rule."""
    rule = AlertRule(
        name="GPT-4o Unavailable Everywhere",
        rule_type="model_unavailable_everywhere",
        target_model_name="gpt-4o",
        enabled=True,
        notify_in_app=True,
    )
    db_session.add(rule)
    await db_session.commit()
    await db_session.refresh(rule)
    return rule


class TestAnyModelDown:
    """Tests for any_model_down rule type."""

    @pytest.mark.asyncio
    async def test_creates_alert_when_model_down(
        self, db_session: AsyncSession, any_model_down_rule: AlertRule, test_model: Model
    ) -> None:
        """Test alert created when any model is down."""
        uptime_check = UptimeCheck(
            model_id=test_model.id,
            status="down",
            error="Connection timeout",
        )

        alerts = await _evaluate_any_model_down(db_session, any_model_down_rule, [uptime_check])

        assert len(alerts) == 1
        assert alerts[0].rule_id == any_model_down_rule.id
        assert alerts[0].model_id == test_model.id
        assert "down" in alerts[0].message.lower()

    @pytest.mark.asyncio
    async def test_no_alert_when_model_up(
        self, db_session: AsyncSession, any_model_down_rule: AlertRule, test_model: Model
    ) -> None:
        """Test no alert created when model is up."""
        uptime_check = UptimeCheck(
            model_id=test_model.id,
            status="up",
            latency_ms=150.0,
        )

        alerts = await _evaluate_any_model_down(db_session, any_model_down_rule, [uptime_check])

        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_multiple_models_down_creates_multiple_alerts(
        self,
        db_session: AsyncSession,
        any_model_down_rule: AlertRule,
        test_model: Model,
        test_model_2: Model,
    ) -> None:
        """Test creates separate alerts for each down model."""
        checks = [
            UptimeCheck(model_id=test_model.id, status="down", error="Error 1"),
            UptimeCheck(model_id=test_model_2.id, status="down", error="Error 2"),
        ]

        alerts = await _evaluate_any_model_down(db_session, any_model_down_rule, checks)

        assert len(alerts) == 2
        model_ids = {a.model_id for a in alerts}
        assert test_model.id in model_ids
        assert test_model_2.id in model_ids


class TestSpecificModelDown:
    """Tests for specific_model_down rule type."""

    @pytest.mark.asyncio
    async def test_creates_alert_for_target_model(
        self, db_session: AsyncSession, specific_model_down_rule: AlertRule, test_model: Model
    ) -> None:
        """Test alert created when specific target model is down."""
        uptime_check = UptimeCheck(
            model_id=test_model.id,
            status="down",
            error="API error",
        )

        alerts = await _evaluate_specific_model_down(
            db_session, specific_model_down_rule, [uptime_check]
        )

        assert len(alerts) == 1
        assert alerts[0].model_id == test_model.id

    @pytest.mark.asyncio
    async def test_no_alert_for_other_model(
        self,
        db_session: AsyncSession,
        specific_model_down_rule: AlertRule,
        test_model_2: Model,
    ) -> None:
        """Test no alert when different model is down."""
        uptime_check = UptimeCheck(
            model_id=test_model_2.id,
            status="down",
            error="API error",
        )

        alerts = await _evaluate_specific_model_down(
            db_session, specific_model_down_rule, [uptime_check]
        )

        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_no_alert_when_target_up(
        self, db_session: AsyncSession, specific_model_down_rule: AlertRule, test_model: Model
    ) -> None:
        """Test no alert when target model is up."""
        uptime_check = UptimeCheck(
            model_id=test_model.id,
            status="up",
            latency_ms=100.0,
        )

        alerts = await _evaluate_specific_model_down(
            db_session, specific_model_down_rule, [uptime_check]
        )

        assert len(alerts) == 0


class TestModelUnavailableEverywhere:
    """Tests for model_unavailable_everywhere rule type."""

    @pytest.mark.asyncio
    async def test_creates_alert_when_all_instances_down(
        self,
        db_session: AsyncSession,
        model_unavailable_rule: AlertRule,
        test_model: Model,
        test_model_2: Model,
    ) -> None:
        """Test alert when model is down across all providers."""
        checks = [
            UptimeCheck(model_id=test_model.id, status="down", error="Error 1"),
            UptimeCheck(model_id=test_model_2.id, status="down", error="Error 2"),
        ]

        alerts = await _evaluate_model_unavailable_everywhere(
            db_session, model_unavailable_rule, checks
        )

        assert len(alerts) == 1
        assert "unavailable" in alerts[0].message.lower()
        assert alerts[0].model_id is None  # Cross-model alert

    @pytest.mark.asyncio
    async def test_no_alert_when_some_up(
        self,
        db_session: AsyncSession,
        model_unavailable_rule: AlertRule,
        test_model: Model,
        test_model_2: Model,
    ) -> None:
        """Test no alert when at least one instance is up."""
        checks = [
            UptimeCheck(model_id=test_model.id, status="down", error="Error"),
            UptimeCheck(model_id=test_model_2.id, status="up", latency_ms=100.0),
        ]

        alerts = await _evaluate_model_unavailable_everywhere(
            db_session, model_unavailable_rule, checks
        )

        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_no_alert_when_all_up(
        self,
        db_session: AsyncSession,
        model_unavailable_rule: AlertRule,
        test_model: Model,
        test_model_2: Model,
    ) -> None:
        """Test no alert when all instances are up."""
        checks = [
            UptimeCheck(model_id=test_model.id, status="up", latency_ms=100.0),
            UptimeCheck(model_id=test_model_2.id, status="up", latency_ms=150.0),
        ]

        alerts = await _evaluate_model_unavailable_everywhere(
            db_session, model_unavailable_rule, checks
        )

        assert len(alerts) == 0


class TestDeduplication:
    """Tests for alert deduplication logic."""

    @pytest.mark.asyncio
    async def test_no_duplicate_for_active_incident(
        self, db_session: AsyncSession, any_model_down_rule: AlertRule, test_model: Model
    ) -> None:
        """Test no duplicate alert when incident is already active."""
        # Create existing unacknowledged alert
        existing_alert = Alert(
            rule_id=any_model_down_rule.id,
            model_id=test_model.id,
            message="Already alerting",
            acknowledged=False,
        )
        db_session.add(existing_alert)
        await db_session.commit()

        # Try to create another alert for same model
        uptime_check = UptimeCheck(
            model_id=test_model.id,
            status="down",
            error="Still down",
        )

        alerts = await _evaluate_any_model_down(db_session, any_model_down_rule, [uptime_check])

        assert len(alerts) == 0  # No new alert created

    @pytest.mark.asyncio
    async def test_new_alert_after_acknowledged(
        self, db_session: AsyncSession, any_model_down_rule: AlertRule, test_model: Model
    ) -> None:
        """Test new alert can be created after previous is acknowledged."""
        # Create acknowledged alert
        acknowledged_alert = Alert(
            rule_id=any_model_down_rule.id,
            model_id=test_model.id,
            message="Previously acknowledged",
            acknowledged=True,
        )
        db_session.add(acknowledged_alert)
        await db_session.commit()

        # Should create new alert
        uptime_check = UptimeCheck(
            model_id=test_model.id,
            status="down",
            error="Down again",
        )

        alerts = await _evaluate_any_model_down(db_session, any_model_down_rule, [uptime_check])

        assert len(alerts) == 1

    @pytest.mark.asyncio
    async def test_has_active_incident_true(
        self, db_session: AsyncSession, any_model_down_rule: AlertRule, test_model: Model
    ) -> None:
        """Test _has_active_incident returns True for unacknowledged alert."""
        alert = Alert(
            rule_id=any_model_down_rule.id,
            model_id=test_model.id,
            message="Active",
            acknowledged=False,
        )
        db_session.add(alert)
        await db_session.commit()

        result = await _has_active_incident(db_session, any_model_down_rule.id, test_model.id)

        assert result is True

    @pytest.mark.asyncio
    async def test_has_active_incident_false_when_acknowledged(
        self, db_session: AsyncSession, any_model_down_rule: AlertRule, test_model: Model
    ) -> None:
        """Test _has_active_incident returns False for acknowledged alert."""
        alert = Alert(
            rule_id=any_model_down_rule.id,
            model_id=test_model.id,
            message="Acknowledged",
            acknowledged=True,
        )
        db_session.add(alert)
        await db_session.commit()

        result = await _has_active_incident(db_session, any_model_down_rule.id, test_model.id)

        assert result is False


class TestEvaluateAlerts:
    """Tests for main evaluate_alerts function."""

    @pytest.mark.asyncio
    async def test_evaluates_all_enabled_rules(
        self,
        db_session: AsyncSession,
        any_model_down_rule: AlertRule,
        specific_model_down_rule: AlertRule,
        test_model: Model,
    ) -> None:
        """Test that all enabled rules are evaluated."""
        uptime_check = UptimeCheck(
            model_id=test_model.id,
            status="down",
            error="Error",
        )

        alerts = await evaluate_alerts(db_session, [uptime_check])

        # Both rules should trigger for this model
        assert len(alerts) == 2
        rule_ids = {a.rule_id for a in alerts}
        assert any_model_down_rule.id in rule_ids
        assert specific_model_down_rule.id in rule_ids

    @pytest.mark.asyncio
    async def test_skips_disabled_rules(
        self, db_session: AsyncSession, any_model_down_rule: AlertRule, test_model: Model
    ) -> None:
        """Test that disabled rules are skipped."""
        # Disable the rule
        any_model_down_rule.enabled = False
        await db_session.commit()

        uptime_check = UptimeCheck(
            model_id=test_model.id,
            status="down",
            error="Error",
        )

        alerts = await evaluate_alerts(db_session, [uptime_check])

        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_empty_uptime_checks(
        self, db_session: AsyncSession, any_model_down_rule: AlertRule
    ) -> None:
        """Test with empty uptime checks list."""
        alerts = await evaluate_alerts(db_session, [])

        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_no_rules_configured(self, db_session: AsyncSession, test_model: Model) -> None:
        """Test when no alert rules exist."""
        uptime_check = UptimeCheck(
            model_id=test_model.id,
            status="down",
            error="Error",
        )

        alerts = await evaluate_alerts(db_session, [uptime_check])

        assert len(alerts) == 0


class TestRecoveryDetection:
    """Tests for recovery detection (informational)."""

    @pytest.mark.asyncio
    async def test_no_auto_acknowledge_on_recovery(
        self, db_session: AsyncSession, any_model_down_rule: AlertRule, test_model: Model
    ) -> None:
        """Test that alerts are NOT auto-acknowledged when model recovers."""
        # Create unacknowledged alert
        alert = Alert(
            rule_id=any_model_down_rule.id,
            model_id=test_model.id,
            message="Model down",
            acknowledged=False,
        )
        db_session.add(alert)
        await db_session.commit()

        # Model recovers
        uptime_check = UptimeCheck(
            model_id=test_model.id,
            status="up",
            latency_ms=100.0,
        )

        # Evaluate alerts
        await evaluate_alerts(db_session, [uptime_check])
        await db_session.refresh(alert)

        # Alert should still be unacknowledged
        assert alert.acknowledged is False
