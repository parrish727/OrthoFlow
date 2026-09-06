"""Tests for eligibility precognitive alerts and dormant Stedi MCP scaffold."""
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.api.routes.eligibility import _build_alerts
from app.services.stedi_mcp import StediMCPClient, StediMCPUnavailable


def _sub(**kw):
    base = dict(
        termination_date=None, ortho_lifetime_max=None, ortho_lifetime_used=None,
        annual_max=None, annual_used=None, last_eligibility_check=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_alert_coverage_inactive():
    alerts = _build_alerts(_sub(), coverage_active=False, remaining_benefit=None,
                           ortho_remaining=None, deductible_remaining=None, today=date.today())
    assert any(a.code == "COVERAGE_INACTIVE" and a.severity == "critical" for a in alerts)


def test_alert_ortho_max_exhausted():
    sub = _sub(ortho_lifetime_max=Decimal("1000"), ortho_lifetime_used=Decimal("1000"))
    alerts = _build_alerts(sub, coverage_active=True, remaining_benefit=None,
                           ortho_remaining=0.0, deductible_remaining=None, today=date.today())
    assert any(a.code == "ORTHO_MAX_EXHAUSTED" for a in alerts)


def test_alert_ortho_near_limit():
    sub = _sub(ortho_lifetime_max=Decimal("1000"), ortho_lifetime_used=Decimal("900"))
    alerts = _build_alerts(sub, coverage_active=True, remaining_benefit=None,
                           ortho_remaining=100.0, deductible_remaining=None, today=date.today())
    assert any(a.code == "ORTHO_MAX_NEAR_LIMIT" for a in alerts)


def test_alert_plan_terminating_soon():
    sub = _sub(termination_date=date.today() + timedelta(days=30))
    alerts = _build_alerts(sub, coverage_active=True, remaining_benefit=None,
                           ortho_remaining=None, deductible_remaining=None, today=date.today())
    assert any(a.code == "PLAN_TERMINATING_SOON" for a in alerts)


def test_alert_deductible_outstanding():
    alerts = _build_alerts(_sub(), coverage_active=True, remaining_benefit=None,
                           ortho_remaining=None, deductible_remaining=50.0, today=date.today())
    assert any(a.code == "DEDUCTIBLE_OUTSTANDING" for a in alerts)


def test_alert_verification_stale():
    sub = _sub(last_eligibility_check=datetime.now(timezone.utc) - timedelta(days=45))
    alerts = _build_alerts(sub, coverage_active=True, remaining_benefit=None,
                           ortho_remaining=None, deductible_remaining=None, today=date.today())
    assert any(a.code == "VERIFICATION_STALE" for a in alerts)


def test_healthy_plan_has_no_critical_alerts():
    sub = _sub(ortho_lifetime_max=Decimal("2000"), ortho_lifetime_used=Decimal("200"),
               annual_max=Decimal("2000"), annual_used=Decimal("100"),
               last_eligibility_check=datetime.now(timezone.utc))
    alerts = _build_alerts(sub, coverage_active=True, remaining_benefit=1900.0,
                           ortho_remaining=1800.0, deductible_remaining=0.0, today=date.today())
    assert not any(a.severity == "critical" for a in alerts)


@pytest.mark.asyncio
async def test_mcp_is_dormant_by_default():
    client = StediMCPClient(api_key="test_dummy")
    # Dormant unless STEDI_MCP_ENABLED — settings default is False.
    with pytest.raises(StediMCPUnavailable):
        await client.search_for_payer("cigna")


def test_mcp_status_reports_dormant():
    status = StediMCPClient(api_key="test_dummy").status()
    assert status["enabled"] is False
    assert "2025-07-11" in status["url"]
