"""Tests for the demo reseed health signal and Eastern-time scheduling.

Covers the two reseed defects fixed this session:
  1. TODAY/scheduling must track the US Eastern calendar date via a real IANA zone, and the
     daily reseed must wake AFTER Eastern midnight (never a second before, which seeded the
     prior day).
  2. Reseed failures must be observable (health signal) instead of silently swallowed.
"""
import importlib
from datetime import datetime, timezone, timedelta

from app.core.timeutil import (
    EASTERN,
    eastern_today,
    eastern_now,
    seconds_until_next_eastern_midnight,
)


def test_eastern_zone_is_new_york():
    assert str(EASTERN) == "America/New_York"


def test_eastern_today_matches_eastern_now_date():
    assert eastern_today() == eastern_now().date()


def test_wait_lands_after_next_eastern_midnight():
    """The computed wait must land strictly in the NEXT ET day (never pre-midnight)."""
    now = eastern_now()
    margin = 10
    wait = seconds_until_next_eastern_midnight(margin_minutes=margin)
    assert wait > 0
    target = now + timedelta(seconds=wait)
    # Target is on a later ET calendar day than now (never pre-midnight).
    assert target.date() > now.date()
    # Target is within the first hour of the new ET day, at/after the margin point.
    next_midnight = datetime.combine(
        now.date() + timedelta(days=1), datetime.min.time(), tzinfo=EASTERN
    )
    assert target >= next_midnight  # strictly after midnight
    assert target <= next_midnight + timedelta(minutes=margin + 1)  # and close to the margin


def _fresh_status():
    """Reload the module to reset its process-local state between assertions."""
    import app.core.reseed_status as rs
    return importlib.reload(rs)


def test_status_starts_healthy_and_not_stale():
    rs = _fresh_status()
    snap = rs.snapshot()
    assert snap["ok"] is True
    assert snap["stale"] is False
    assert snap["healthy"] is True
    assert snap["last_success_at"] is None


def test_record_success_sets_target_date_and_healthy():
    rs = _fresh_status()
    rs.record_success("2026-10-02")
    snap = rs.snapshot()
    assert snap["ok"] is True
    assert snap["healthy"] is True
    assert snap["last_target_date"] == "2026-10-02"
    assert snap["consecutive_failures"] == 0
    assert snap["last_error"] is None


def test_record_failure_marks_unhealthy_and_counts():
    rs = _fresh_status()
    rs.record_failure("boom")
    rs.record_failure("boom again")
    snap = rs.snapshot()
    assert snap["ok"] is False
    assert snap["healthy"] is False
    assert snap["consecutive_failures"] == 2
    assert snap["last_error"] == "boom again"


def test_success_after_failure_recovers():
    rs = _fresh_status()
    rs.record_failure("boom")
    rs.record_success("2026-10-02")
    snap = rs.snapshot()
    assert snap["ok"] is True
    assert snap["healthy"] is True
    assert snap["consecutive_failures"] == 0


def test_stale_detection_when_last_success_is_old():
    rs = _fresh_status()
    rs.record_success("2026-10-02")
    # Backdate the last success beyond the stale threshold.
    old = (datetime.now(timezone.utc) - timedelta(hours=rs.STALE_AFTER_HOURS + 1)).isoformat()
    rs._status.last_success_at = old
    snap = rs.snapshot()
    assert snap["stale"] is True
    assert snap["healthy"] is False
