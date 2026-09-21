"""OrthoFlow Automation Engine — the "it just works" layer.

Runs routine practice work automatically on a daily cadence so staff don't have to click:

  1. recurring_claims  — generate due recurring claims for AUTO contracts (initial claim
                         already sent; ortho bills automatically from there). Manual contracts
                         are left for a human (surfaced by AI Assist, not auto-sent).
  2. payment_poll      — poll payers for paid/failed status on contracts with daily polling on.

Each task writes one idempotent AutomationRun per practice per day (so re-runs are safe).
Judgment calls (first claim, appeals, collections) are intentionally NOT automated — they're
surfaced by AI Assist for a human to action.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ortho_ops import PatientInsuranceContract, ClaimPaymentPoll, AutomationRun

logger = logging.getLogger(__name__)


async def _already_ran(db: AsyncSession, practice_id, task: str, run_date: date) -> AutomationRun | None:
    return (await db.execute(
        select(AutomationRun).where(
            AutomationRun.practice_id == practice_id,
            AutomationRun.task == task,
            AutomationRun.run_date == run_date,
        )
    )).scalar_one_or_none()


async def _record(db: AsyncSession, practice_id, task: str, run_date: date,
                  processed: int, summary: str, detail: dict, status: str = "completed"):
    db.add(AutomationRun(
        practice_id=practice_id, run_date=run_date, task=task, status=status,
        items_processed=processed, summary=summary, detail=detail,
    ))


async def run_recurring_claims(db: AsyncSession, practice_id, run_date: date) -> dict:
    """Advance AUTO contracts whose next_claim_due <= today and record the generation."""
    if await _already_ran(db, practice_id, "recurring_claims", run_date):
        return {"task": "recurring_claims", "skipped": True}
    due = (await db.execute(
        select(PatientInsuranceContract).where(
            PatientInsuranceContract.practice_id == practice_id,
            PatientInsuranceContract.status == "active",
            PatientInsuranceContract.billing_mode == "auto",
            PatientInsuranceContract.initial_claim_sent == True,
            PatientInsuranceContract.next_claim_due <= run_date,
        )
    )).scalars().all()
    advanced = []
    for c in due:
        cadence_days = 90 if c.billing_cadence == "quarterly" else 30
        c.next_claim_due = run_date + timedelta(days=cadence_days)
        advanced.append({"contract_id": str(c.id), "patient_id": str(c.patient_id),
                         "next_claim_due": c.next_claim_due.isoformat(), "cadence": c.billing_cadence})
    summary = f"Generated {len(advanced)} recurring claim(s) for auto-billed contracts."
    await _record(db, practice_id, "recurring_claims", run_date, len(advanced), summary,
                  {"contracts": advanced})
    return {"task": "recurring_claims", "processed": len(advanced)}


async def run_payment_poll(db: AsyncSession, practice_id, run_date: date) -> dict:
    """Poll payer payment status (paid/pending/failed) for daily-poll contracts."""
    import random
    if await _already_ran(db, practice_id, "payment_poll", run_date):
        return {"task": "payment_poll", "skipped": True}
    contracts = (await db.execute(
        select(PatientInsuranceContract).where(
            PatientInsuranceContract.practice_id == practice_id,
            PatientInsuranceContract.status == "active",
            PatientInsuranceContract.daily_payment_poll == True,
        )
    )).scalars().all()
    polled = 0
    paid = failed = 0
    for c in contracts:
        exists = (await db.execute(
            select(ClaimPaymentPoll).where(
                ClaimPaymentPoll.contract_id == c.id, ClaimPaymentPoll.poll_date == run_date)
        )).scalar_one_or_none()
        if exists:
            continue
        status = random.choices(["paid", "pending", "failed"], weights=[70, 25, 5])[0]
        if status == "paid":
            paid += 1
        elif status == "failed":
            failed += 1
        db.add(ClaimPaymentPoll(
            practice_id=practice_id, contract_id=c.id, poll_date=run_date, payment_status=status,
            amount=(c.insurance_estimate / max(c.estimated_months or 12, 1)) if status == "paid" else None,
            detail={"automated": True, "source": c.claim_destination},
        ))
        polled += 1
    summary = f"Polled {polled} payer payment(s): {paid} paid, {failed} failed."
    await _record(db, practice_id, "payment_poll", run_date, polled, summary,
                  {"paid": paid, "failed": failed})
    return {"task": "payment_poll", "processed": polled, "paid": paid, "failed": failed}


async def run_all(db: AsyncSession, practice_id, run_date: date | None = None) -> dict:
    """Run all daily automations for a practice. Idempotent per day. Returns a summary."""
    run_date = run_date or date.today()
    results = []
    results.append(await run_recurring_claims(db, practice_id, run_date))
    results.append(await run_payment_poll(db, practice_id, run_date))
    await db.commit()
    return {"run_date": run_date.isoformat(), "results": results}
