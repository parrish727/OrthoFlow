"""Tests for AR aging, payment-plan schedules and the 30/60/90/120/180 cadence (pure, no DB)."""
from datetime import date, datetime, time, timezone
from decimal import Decimal

import pytest

from app.core.config import settings
from app.services import ar_aging as a
from app.services import ar_outreach as o

TODAY = date(2026, 11, 20)
D = Decimal


@pytest.fixture(autouse=True)
def defaults(monkeypatch):
    monkeypatch.setattr(settings, "AR_OUTREACH_CAP_DAYS", 180)
    monkeypatch.setattr(settings, "AR_OUTREACH_TZ", "America/New_York")
    monkeypatch.setattr(settings, "AR_OUTREACH_START_HOUR", 10)
    monkeypatch.setattr(settings, "AR_OUTREACH_END_HOUR", 17)


# ── schedule ──
def test_schedule_sums_exactly_and_keeps_day_of_month():
    plan = a.build_schedule(date(2026, 1, 31), 3, D("1000.00"))
    assert [d for d, _ in plan] == [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)]
    assert sum(x for _, x in plan) == D("1000.00")
    assert plan[0][1] == D("333.33") and plan[-1][1] == D("333.34")


def test_schedule_rejects_bad_input():
    with pytest.raises(ValueError):
        a.build_schedule(TODAY, 0, D("100"))
    with pytest.raises(ValueError):
        a.build_schedule(TODAY, 3, D("0"))


# ── evaluate: schedule path ──
def sched(*pairs):
    return [(date.fromisoformat(d), D(x)) for d, x in pairs]


def test_on_schedule_patient_is_not_late():
    inst = sched(("2026-10-20", "250"), ("2026-11-20", "250"), ("2026-12-20", "250"))
    r = a.evaluate(TODAY, D("750"), inst, D("500"), date(2026, 11, 20), date(2026, 1, 1))
    assert r.days_past_due is None and r.due_source == "schedule"
    assert r.next_due_date == date(2026, 12, 20) and r.next_due_amount == 250.0


def test_missed_installment_ages_from_its_due_date_not_charge_date():
    inst = sched(("2026-07-20", "250"), ("2026-08-20", "250"), ("2026-09-20", "250"))
    # paid only the first installment; oldest uncovered is 2026-08-20
    r = a.evaluate(TODAY, D("500"), inst, D("250"), date(2026, 7, 20), date(2025, 1, 1))
    assert r.days_past_due == (TODAY - date(2026, 8, 20)).days == 92
    assert r.amount_past_due == 500.0


def test_partial_payment_covers_oldest_first():
    inst = sched(("2026-09-20", "250"), ("2026-10-20", "250"))
    r = a.evaluate(TODAY, D("500"), inst, D("300"), None, None)
    # 300 covers all of #1 and 50 of #2, so #2 is the oldest uncovered
    assert r.oldest_uncovered_due == date(2026, 10, 20)
    assert r.amount_past_due == 200.0


def test_credit_balance_is_never_delinquent():
    inst = sched(("2026-08-20", "250"))
    r = a.evaluate(TODAY, D("-100"), inst, D("0"), None, None)
    assert r.days_past_due is None


# ── evaluate: estimated path ──
def test_no_schedule_uses_last_payment_then_oldest_charge():
    r = a.evaluate(TODAY, D("400"), [], D("0"), date(2026, 10, 21), date(2026, 1, 1))
    assert (r.days_past_due, r.due_source) == (30, "estimated")
    r = a.evaluate(TODAY, D("400"), [], D("0"), None, date(2026, 6, 23))
    assert r.days_past_due == 150
    assert a.evaluate(TODAY, D("0"), [], D("0"), None, date(2026, 1, 1)).days_past_due is None


# ── buckets: report and roster must agree ──
@pytest.mark.parametrize("days,key,label", [
    (0, "0-30", "current"), (30, "0-30", "current"), (31, "31-60", "31-60"),
    (60, "31-60", "31-60"), (61, "61-90", "61-90"), (90, "61-90", "61-90"),
    (91, "91-120", "90-120"), (120, "91-120", "90-120"), (121, "120+", "120+"),
])
def test_buckets(days, key, label):
    assert a.bucket_for(days) == key and a.roster_bucket(days) == label


# ── cadence ──
@pytest.mark.parametrize("days,reached", [(None, None), (29, None), (30, 30), (89, 60), (120, 120), (179, 120), (180, 180), (400, 180)])
def test_milestone_reached(days, reached):
    assert a.milestone_reached(days) == reached


def test_cap_stops_everything():
    assert not a.past_cap(180) and a.past_cap(181)
    assert a.milestones_to_send(181, set()) == (None, [])


def test_first_seen_late_sends_only_highest_and_supersedes_lower():
    assert a.milestones_to_send(130, set()) == (120, [30, 60, 90])
    assert a.milestones_to_send(130, {30, 60, 90, 120}) == (None, [])
    assert a.milestones_to_send(95, {30}) == (90, [60])


def test_cap_lowered_drops_later_milestones(monkeypatch):
    monkeypatch.setattr(settings, "AR_OUTREACH_CAP_DAYS", 100)
    assert a.active_milestones() == (30, 60, 90)
    assert a.milestones_to_send(150, set()) == (None, [])


def test_installment_statuses():
    inst = sched(("2026-10-20", "250"), ("2026-11-20", "250"), ("2026-12-20", "250"))
    st = [x["status"] for x in a.installment_statuses(TODAY, inst, D("250"))]
    assert st == ["paid", "due", "upcoming"]
    st = [x["status"] for x in a.installment_statuses(TODAY, inst, D("0"))]
    assert st == ["overdue", "due", "upcoming"]


# ── outreach helpers ──
def test_message_is_generic_and_points_to_portal():
    for m in (30, 60, 90, 120, 180):
        t = o.message_for(m)
        assert "/portal?section=billing" in t and "STOP" in t
        assert "$" not in t and "day" not in t.lower().replace("today", "")
        assert not any(ch.isdigit() for ch in t.split("http")[0])


def test_send_window_uses_practice_timezone():
    # 15:00 UTC on Nov 20 = 10:00 EST
    assert o.in_send_window(datetime(2026, 11, 20, 15, 0, tzinfo=timezone.utc))
    assert not o.in_send_window(datetime(2026, 11, 20, 14, 59, tzinfo=timezone.utc))
    assert not o.in_send_window(datetime(2026, 11, 20, 22, 0, tzinfo=timezone.utc))  # 17:00 EST


def test_quiet_hours_overnight_and_daytime():
    noon_et = datetime(2026, 11, 20, 17, 0, tzinfo=timezone.utc)
    assert not o.in_quiet_hours(noon_et, None, None)
    assert o.in_quiet_hours(noon_et, time(11, 0), time(13, 0))
    assert not o.in_quiet_hours(noon_et, time(20, 0), time(8, 0))
    late = datetime(2026, 11, 21, 3, 0, tzinfo=timezone.utc)  # 22:00 ET
    assert o.in_quiet_hours(late, time(20, 0), time(8, 0))
