"""Tests for the AR long-tail policy (pure functions, CI-safe, no DB)."""
from datetime import date, timedelta

import pytest

from app.core.config import settings
from app.services import ar_longtail as lt

TODAY = date(2026, 11, 20)


@pytest.fixture(autouse=True)
def default_window(monkeypatch):
    monkeypatch.setattr(settings, "AR_LONGTAIL_START_DAYS", 120)
    monkeypatch.setattr(settings, "AR_LONGTAIL_CAP_DAYS", 180)


def d(days_ago: int) -> date:
    return TODAY - timedelta(days=days_ago)


def test_window_defaults_and_guard(monkeypatch):
    assert lt.window() == lt.Window(120, 180)
    monkeypatch.setattr(settings, "AR_LONGTAIL_CAP_DAYS", 60)  # misconfigured below start
    assert lt.window().cap_days == 120


def test_no_balance_is_not_delinquent():
    assert lt.classify(0, 200) == lt.NOT_DELINQUENT
    assert lt.classify(-50, 200) == lt.NOT_DELINQUENT
    assert lt.classify(100, None) == lt.NOT_DELINQUENT


@pytest.mark.parametrize("days,expected", [
    (30, lt.UPSTREAM),
    (90, lt.UPSTREAM),
    (120, lt.UPSTREAM),   # still inside the upstream window: strictly after
    (121, lt.ACTIVE),
    (180, lt.ACTIVE),     # cap is inclusive
    (181, lt.PAST_CAP),
    (400, lt.PAST_CAP),
])
def test_window_boundaries(days, expected):
    assert lt.classify(500, days) == expected


def test_clock_uses_last_payment_then_oldest_charge():
    assert lt.delinquent_days(TODAY, d(10), d(400)) == 10   # paying patient is not long-tail
    assert lt.delinquent_days(TODAY, None, d(150)) == 150   # never paid: oldest charge
    assert lt.delinquent_days(TODAY, None, None) is None


def test_handoff_opens_window_immediately_and_counts_forward():
    handoff = d(0)
    days = lt.delinquent_days(TODAY, None, handoff, handoff_date=handoff)
    assert days == 120
    assert lt.classify(900, days, handed_off=lt.released_by_upstream(None, handoff)) == lt.ACTIVE
    # 60 days later the handed-off account reaches the cap boundary, then passes it.
    later = TODAY + timedelta(days=60)
    assert lt.delinquent_days(later, None, handoff, handoff_date=handoff) == 180
    assert lt.delinquent_days(later + timedelta(days=1), None, handoff, handoff_date=handoff) == 181


def test_payment_after_handoff_returns_to_normal_rule():
    handoff = d(30)
    paid = d(5)
    assert lt.released_by_upstream(paid, handoff) is False
    days = lt.delinquent_days(TODAY, paid, handoff, handoff_date=handoff)
    assert days == 5
    assert lt.classify(400, days, handed_off=False) == lt.UPSTREAM


def test_payment_before_handoff_does_not_cancel_release():
    handoff = d(10)
    assert lt.released_by_upstream(d(100), handoff) is True
