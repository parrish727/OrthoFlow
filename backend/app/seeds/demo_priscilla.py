"""Flagship demo patient enrichment — Priscilla Knowles.

Priscilla is the primary showcase patient across the MyPatient portal AND the insurance /
claims / ledger surfaces. This makes her record the fullest, most realistic example so a
demo can walk through every capability on one patient:

  • Complete Delta Dental PPO benefit tracking (annual max, ortho lifetime, deductible, copay,
    coverage %) so eligibility checks return rich data + precognitive alerts.
  • Claim line items on each of her claims (so Claims detail + Reports show real procedures).
  • A clean, chronologically-consistent ledger with running balances.

Idempotent-ish: safe to re-run; it upserts benefit fields and only adds line items/ledger
rows when missing.

Run: docker compose exec backend python -m app.seeds.demo_priscilla
"""
import asyncio
import uuid
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal

from sqlalchemy import select, delete
from app.core.database import SessionLocal
from app.models.clinical import Patient
from app.models.finance import InsuranceSubscriber, ClaimLineItem, PatientLedgerEntry
from app.models.claims import InsuranceClaim

DEMO_PRACTICE_ID = uuid.UUID("82fe9d87-6250-4b15-ac7d-26de094a4be8")


def _d(v) -> Decimal:
    return Decimal(str(v)).quantize(Decimal("0.01"))


# CDT descriptions for line items keyed by the codes on Priscilla's claims.
CDT_DESC = {
    "D8080": "Comprehensive orthodontic treatment of the adolescent dentition",
    "D8670": "Periodic orthodontic treatment visit",
    "D0330": "Panoramic radiographic image",
}


async def enrich_priscilla(db) -> None:
    patient = (await db.execute(
        select(Patient).where(
            Patient.practice_id == DEMO_PRACTICE_ID,
            Patient.first_name == "Priscilla", Patient.last_name == "Knowles",
        )
    )).scalar_one_or_none()
    if not patient:
        print("  ⚠️  Priscilla Knowles not found")
        return

    # ── 1. Complete her Delta Dental benefit profile ──────────────────────────
    sub = (await db.execute(
        select(InsuranceSubscriber).where(InsuranceSubscriber.patient_id == patient.id)
    )).scalar_one_or_none()
    if sub:
        sub.plan_type = "PPO"
        sub.plan_name = "Delta Dental PPO Plus"
        sub.annual_max = _d(2000)
        sub.annual_used = _d(650)
        sub.ortho_lifetime_max = _d(2500)
        sub.ortho_lifetime_used = _d(1200)
        sub.ortho_coverage_pct = 50
        sub.deductible_amount = _d(50)
        sub.deductible_met = _d(50)
        sub.copay_amount = _d(25)
        sub.effective_date = date(2025, 1, 1)
        sub.is_active = True
        sub.eligibility_status = "active"
        if not sub.group_number:
            sub.group_number = "GRP-MELANIN-2026"
        print("  ✅ Priscilla: benefit profile completed (annual max, ortho lifetime, deductible, copay)")

    # ── 2. Add line items to her claims (if missing) ──────────────────────────
    claims = (await db.execute(
        select(InsuranceClaim).where(
            InsuranceClaim.practice_id == DEMO_PRACTICE_ID,
            InsuranceClaim.patient_id == str(patient.id),
        ).order_by(InsuranceClaim.created_at)
    )).scalars().all()

    lines_added = 0
    for claim in claims:
        existing = (await db.execute(
            select(ClaimLineItem).where(ClaimLineItem.claim_id == claim.id)
        )).scalars().first()
        if existing:
            continue
        # Derive the CDT from the claim's stored cdt_codes JSON (fallback D8670).
        code = "D8670"
        if isinstance(claim.cdt_codes, list) and claim.cdt_codes:
            code = claim.cdt_codes[0].get("code", code)
        billed = _d(claim.total_billed)
        li = ClaimLineItem(
            id=uuid.uuid4(), claim_id=claim.id, line_number=1,
            cdt_code=code, description=CDT_DESC.get(code, "Orthodontic service"),
            quantity=1, billed_amount=billed, service_date=claim.service_date,
        )
        if claim.status == "paid":
            li.allowed_amount = claim.total_allowed or _d(billed * Decimal("0.92"))
            li.paid_amount = claim.total_paid or _d(li.allowed_amount * Decimal("0.5"))
            li.adjustment_amount = _d(billed - li.allowed_amount)
            li.patient_responsibility = claim.patient_responsibility or _d(billed - li.paid_amount)
        elif claim.status == "denied":
            li.allowed_amount = _d(0)
            li.paid_amount = _d(0)
            li.patient_responsibility = billed
            li.denial_code = "CO-96"
            li.denial_reason = "Non-covered service under current plan benefit period"
        db.add(li)
        lines_added += 1
    print(f"  ✅ Priscilla: {lines_added} claim line item(s) added")

    # ── 3. Rebuild a clean ledger with running balances ───────────────────────
    await db.execute(
        delete(PatientLedgerEntry).where(PatientLedgerEntry.patient_id == patient.id)
    )
    today = date.today()
    # Chronological, realistic ortho financial story.
    events = [
        (today - timedelta(days=210), "charge",     "Comprehensive orthodontic treatment (D8080) — treatment contract", _d(5500), "D8080", None, None),
        (today - timedelta(days=205), "payment",    "Down payment — credit card", _d(-1000), None, "card", "RCPT-1001"),
        (today - timedelta(days=180), "payment",    "Insurance payment — Delta Dental — ERA 835", _d(-1200), "D8080", "insurance", "ERA-DDW-0142"),
        (today - timedelta(days=180), "adjustment", "Contractual adjustment (CO-45) — Delta Dental", _d(-300), "D8080", None, "ERA-DDW-0142"),
        (today - timedelta(days=150), "payment",    "Monthly auto-pay — card on file", _d(-275), None, "card", "AUTOPAY-03"),
        (today - timedelta(days=120), "payment",    "Monthly auto-pay — card on file", _d(-275), None, "card", "AUTOPAY-04"),
        (today - timedelta(days=90),  "payment",    "Monthly auto-pay — card on file", _d(-275), None, "card", "AUTOPAY-05"),
        (today - timedelta(days=60),  "payment",    "Monthly auto-pay — card on file", _d(-275), None, "card", "AUTOPAY-06"),
        (today - timedelta(days=30),  "charge",     "Periodic orthodontic visit (D8670)", _d(185), "D8670", None, None),
        (today - timedelta(days=28),  "payment",    "Insurance payment — Delta Dental — ERA 835", _d(-92), "D8670", "insurance", "ERA-DDW-0187"),
        (today - timedelta(days=14),  "charge",     "Panoramic radiographic image (D0330) — denied, patient responsibility", _d(125), "D0330", None, "CLM-2026-00195"),
        (today - timedelta(days=5),   "payment",    "Patient payment — card on file", _d(-200), None, "card", "RCPT-1042"),
    ]
    running = Decimal("0.00")
    for (pdate, etype, desc, amount, cdt, method, ref) in events:
        running = (running + amount).quantize(Decimal("0.01"))
        db.add(PatientLedgerEntry(
            id=uuid.uuid4(), practice_id=DEMO_PRACTICE_ID, patient_id=patient.id,
            entry_type=etype, description=desc, amount=amount, running_balance=running,
            cdt_code=cdt, payment_method=method, reference_number=ref, posted_date=pdate,
        ))
    print(f"  ✅ Priscilla: ledger rebuilt — {len(events)} entries, ending balance ${running:,.2f}")

    await db.flush()


async def main():
    async with SessionLocal() as db:
        await enrich_priscilla(db)
        await db.commit()
    print("✅ Priscilla Knowles flagship enrichment complete!")


if __name__ == "__main__":
    asyncio.run(main())
