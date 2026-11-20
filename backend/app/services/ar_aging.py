"""AR aging: one source of truth for how late a patient balance is.

Used by the Ledger roster AND the /reports/ar-aging report so they can never disagree.

How lateness is measured
------------------------
1. If the patient has a payment-plan schedule (PaymentPlanInstallment), lateness is days since the
   OLDEST installment that patient payments have not covered (first-in-first-out). This is real
   "past due" measured against due dates. due_source = "schedule".
2. If there is no schedule (older accounts, manual ledgers), we fall back to days since the last
   patient payment, or since the oldest charge if the patient never paid. This is an estimate.
   due_source = "estimated".

A patient with no positive ledger balance is never delinquent (a credit balance is never chased).

Collections cadence
-------------------
Reminder milestones are 30, 60, 90, 120 and 180 days past due. Nothing runs past the cap
(AR_OUTREACH_CAP_DAYS, default 180). Days 120 to the cap are the "long tail" that many billing
tools stop tracking.

Pure functions first (unit tested), DB loader at the bottom.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

MILESTONES: tuple[int, ...] = (30, 60, 90, 120, 180)
LONG_TAIL_FROM_DAYS = 120

_CENT = Decimal("0.01")


# ── Cadence policy ──────────────────────────────────────────────────────────────

def cap_days() -> int:
    """Last day OrthoFlow follows up. Never below the first milestone."""
    return max(int(settings.AR_OUTREACH_CAP_DAYS), MILESTONES[0])


def active_milestones() -> tuple[int, ...]:
    return tuple(m for m in MILESTONES if m <= cap_days())


def bucket_for(days: int) -> str:
    """Canonical aging bucket (used by the report; the roster maps two labels, see roster_bucket)."""
    if days <= 30:
        return "0-30"
    if days <= 60:
        return "31-60"
    if days <= 90:
        return "61-90"
    if days <= 120:
        return "91-120"
    return "120+"


def roster_bucket(days: int) -> str:
    """Ledger roster label for the same bucket (kept for the existing UI)."""
    b = bucket_for(days)
    return {"0-30": "current", "91-120": "90-120"}.get(b, b)


def milestone_reached(days: int | None) -> int | None:
    """Highest milestone the account has reached, or None if under 30 days (or not delinquent)."""
    if days is None:
        return None
    reached = [m for m in active_milestones() if m <= days]
    return reached[-1] if reached else None


def past_cap(days: int | None) -> bool:
    return days is not None and days > cap_days()


def milestones_to_send(days: int | None, already_sent: set[int]) -> tuple[int | None, list[int]]:
    """Decide what the automatic reminder does today.

    Returns (milestone_to_send, superseded). Only the highest unsent milestone is sent; lower
    unsent ones are returned as superseded so they are recorded and never sent late (a patient
    first seen at day 130 gets the 120-day message, not four messages at once).
    """
    if days is None or past_cap(days):
        return None, []
    due = [m for m in active_milestones() if m <= days and m not in already_sent]
    if not due:
        return None, []
    return due[-1], due[:-1]


# ── Payment-plan schedule ───────────────────────────────────────────────────────

def add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    year, month = d.year + y, m + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def build_schedule(first_due: date, months: int, total: Decimal) -> list[tuple[date, Decimal]]:
    """Split `total` into `months` monthly installments starting on `first_due`.

    Day-of-month is preserved (clamped for short months). Amounts are rounded to cents and the
    last installment absorbs the rounding so the schedule sums exactly to `total`.
    """
    if months < 1:
        raise ValueError("months must be at least 1")
    total = Decimal(total).quantize(_CENT, rounding=ROUND_HALF_UP)
    if total <= 0:
        raise ValueError("total must be positive")
    base = (total / months).quantize(_CENT, rounding=ROUND_HALF_UP)
    out: list[tuple[date, Decimal]] = []
    running = Decimal("0")
    for i in range(months):
        amt = base if i < months - 1 else total - running
        running += amt
        out.append((add_months(first_due, i), amt))
    return out


def installment_statuses(
    today: date, installments: list[tuple[date, Decimal]], plan_paid: Decimal
) -> list[dict]:
    """Per-installment status for display: paid, partial, overdue, due (today) or upcoming."""
    remaining = max(Decimal(plan_paid or 0), Decimal("0"))
    out = []
    for due, amt in sorted(installments, key=lambda x: x[0]):
        covered = min(amt, remaining)
        remaining -= covered
        if covered >= amt:
            st = "paid"
        elif due < today:
            st = "overdue"
        elif due == today:
            st = "due"
        else:
            st = "upcoming"
        if 0 < covered < amt and st != "overdue":
            st = "partial" if due <= today else st
        out.append({"due_date": due, "amount": float(amt), "covered": float(covered), "status": st})
    return out


@dataclass
class Aging:
    """Result of evaluating one patient."""
    balance: float = 0.0
    days_past_due: int | None = None
    amount_past_due: float = 0.0
    due_source: str = "none"               # schedule | estimated | none
    oldest_uncovered_due: date | None = None
    next_due_date: date | None = None
    next_due_amount: float | None = None


def evaluate(
    today: date,
    balance: Decimal,
    installments: list[tuple[date, Decimal]],
    plan_paid: Decimal,
    last_payment: date | None,
    oldest_charge: date | None,
) -> Aging:
    """Compute lateness for one patient (pure)."""
    bal = Decimal(balance or 0)
    res = Aging(balance=float(bal))

    if installments:
        res.due_source = "schedule"
        remaining_paid = max(Decimal(plan_paid or 0), Decimal("0"))
        arrears = Decimal("0")
        for due, amt in sorted(installments, key=lambda x: x[0]):
            covered = min(amt, remaining_paid)
            remaining_paid -= covered
            short = amt - covered
            if due <= today:
                if short > 0:
                    arrears += short
                    if res.oldest_uncovered_due is None:
                        res.oldest_uncovered_due = due
            elif res.next_due_date is None:
                res.next_due_date = due
                res.next_due_amount = float(short if short > 0 else amt)
        if bal > 0 and arrears > 0 and res.oldest_uncovered_due is not None:
            res.days_past_due = (today - res.oldest_uncovered_due).days
            res.amount_past_due = float(min(arrears, bal))
        return res

    # Estimated clock for accounts without a schedule.
    anchor = last_payment or oldest_charge
    if bal > 0 and anchor is not None:
        res.due_source = "estimated"
        res.days_past_due = max((today - anchor).days, 0)
        res.amount_past_due = float(bal)
    return res


# ── DB loader ───────────────────────────────────────────────────────────────────

@dataclass
class PatientAging:
    patient_id: str
    total_charges: float
    total_payments: float          # negative, as stored
    plan_paid: Decimal = Decimal("0")   # patient payments applicable to the schedule
    aging: Aging = field(default_factory=Aging)


async def load_aging(
    db: AsyncSession,
    practice_id,
    today: date | None = None,
    patient_id=None,
) -> list[PatientAging]:
    """Evaluate every patient with ledger activity or a schedule (or one patient)."""
    from app.models.finance import PatientLedgerEntry as L, PaymentPlanInstallment as I
    from app.models.ortho_ops import PatientInsuranceContract as C

    today = today or date.today()

    ledger_q = select(
        L.patient_id,
        func.sum(L.amount),
        func.sum(func.greatest(L.amount, 0)),
        func.sum(func.least(L.amount, 0)),
        func.min(func.coalesce(L.service_date, L.posted_date)).filter(L.amount > 0),
        func.max(L.posted_date).filter(L.entry_type == "payment"),
        # Patient-paid money: payments/credits not tied to an insurance claim or ERA posting.
        func.sum(case(
            (
                (L.entry_type.in_(["payment", "credit"]))
                & (L.claim_id.is_(None))
                & (L.payment_posting_id.is_(None)),
                -L.amount,
            ),
            else_=0,
        )),
    ).where(L.practice_id == practice_id).group_by(L.patient_id)
    if patient_id is not None:
        ledger_q = ledger_q.where(L.patient_id == patient_id)
    ledger = {str(r[0]): r[1:] for r in (await db.execute(ledger_q)).all()}

    inst_q = select(I.patient_id, I.contract_id, I.due_date, I.amount).where(
        I.practice_id == practice_id, I.canceled.is_(False))
    if patient_id is not None:
        inst_q = inst_q.where(I.patient_id == patient_id)
    sched: dict[str, list[tuple[date, Decimal]]] = {}
    contract_ids: dict[str, set] = {}
    for pid, cid, due, amt in (await db.execute(inst_q)).all():
        sched.setdefault(str(pid), []).append((due, Decimal(amt)))
        if cid:
            contract_ids.setdefault(str(pid), set()).add(cid)

    # Down payments are posted to the ledger as patient payments but are not part of the
    # installment total, so remove them before applying payments to the schedule.
    all_cids = {c for s in contract_ids.values() for c in s}
    down: dict = {}
    if all_cids:
        down = {
            r[0]: Decimal(r[1] or 0)
            for r in (await db.execute(
                select(C.id, C.down_payment).where(C.id.in_(all_cids)))).all()
        }

    out: list[PatientAging] = []
    for pid in sorted(set(ledger) | set(sched)):
        bal, charges, payments, oldest, last_pay, patient_paid = ledger.get(
            pid, (Decimal(0), Decimal(0), Decimal(0), None, None, Decimal(0)))
        patient_down = sum((down.get(c, Decimal(0)) for c in contract_ids.get(pid, ())), Decimal(0))
        plan_paid = max(Decimal(patient_paid or 0) - patient_down, Decimal(0))
        ag = evaluate(today, Decimal(bal or 0), sched.get(pid, []), plan_paid, last_pay, oldest)
        out.append(PatientAging(
            patient_id=pid,
            total_charges=float(charges or 0),
            total_payments=float(payments or 0),
            plan_paid=plan_paid,
            aging=ag,
        ))
    return out
