"""Comprehensive finance demo seed — insurance, claims, line items, ledger, ERA postings.

Gives EVERY demo patient a realistic financial profile so Insurance, Claims, Payments,
Ledger, and Reports pages all show rich, interactive data that a 10-year Treatment
Coordinator would recognize as authentic:

  • Varied payers (mapped to Stedi dental test payers) and plan types (PPO/HMO/Medicaid)
  • Real benefit tracking (annual max/used, ortho lifetime max/used, deductible, copay)
  • Claims across the full lifecycle (draft/submitted/accepted/paid/denied/appealed)
  • Claim line items with CDT codes, allowed/paid/adjustment/patient-responsibility splits
  • Full patient ledger histories (charges → insurance payments → patient payments → adjustments)
  • ERA/835 payment postings tied to paid claims

Idempotent: keyed on existing InsuranceSubscriber per patient. Safe to re-run.

Run standalone: docker compose exec backend python -m app.seeds.demo_finance
"""
import uuid
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal

from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.models import Practice
from app.models.clinical import Patient
from app.models.finance import (
    InsuranceSubscriber, ClaimLineItem, PatientLedgerEntry, PaymentPosting,
)
from app.models.claims import InsuranceClaim

DEMO_PRACTICE_ID = uuid.UUID("82fe9d87-6250-4b15-ac7d-26de094a4be8")


def _d(v) -> Decimal:
    return Decimal(str(v)).quantize(Decimal("0.01"))


# Canonical demo patient order (must match seeds/demo_flow.DEMO_PATIENTS). Profiles and
# claim scenarios are indexed to THIS list by (first_name, last_name) so the seed is robust
# even when the practice contains other (non-demo) patients.
DEMO_PATIENT_NAMES = [
    ("Priscilla", "Knowles"), ("Marcus", "Johnson"), ("Aaliyah", "Washington"),
    ("Devon", "Brooks"), ("Jasmine", "Carter"), ("Tyler", "Robinson"),
    ("Imani", "Williams"), ("Elijah", "Davis"), ("Zara", "Thompson"),
    ("Kai", "Anderson"), ("Nia", "Harris"),
]


# ── Per-patient insurance profiles (indexed to DEMO_PATIENTS) ───────────────────
# payer_id values map to Stedi test payers via services/stedi_payers.INTERNAL_PAYER_TO_STEDI,
# so an eligibility check on any of these patients round-trips to Stedi test mode.
INSURANCE_PROFILES = [
    # 0 — Priscilla Knowles (adult, active comprehensive, mid-treatment)
    dict(payer_name="Delta Dental of Wisconsin", payer_id="DELTA-WI", plan_type="PPO",
         plan_name="Delta Dental PPO Plus", subscriber_suffix="0001", group="GRP-MELANIN-2026",
         relationship="self", annual_max=2000, annual_used=650, ortho_max=2500, ortho_used=1200,
         ortho_pct=50, deductible=50, deductible_met=50, copay=25, months_effective=20, term_months=None),
    # 1 — Marcus Johnson (child, active, Cigna)
    dict(payer_name="Cigna Dental", payer_id="CIGNA-DENTAL", plan_type="PPO",
         plan_name="Cigna Dental Care Access", subscriber_suffix="1102", group="CIG-4821",
         relationship="child", annual_max=1500, annual_used=300, ortho_max=1500, ortho_used=750,
         ortho_pct=50, deductible=50, deductible_met=50, copay=0, months_effective=14, term_months=None),
    # 2 — Aaliyah Washington (teen, bonding, MetLife — ortho near limit)
    dict(payer_name="MetLife Dental", payer_id="METLIFE-DENTAL", plan_type="PPO",
         plan_name="MetLife PDP Plus", subscriber_suffix="2203", group="MET-9910",
         relationship="child", annual_max=1500, annual_used=1100, ortho_max=1000, ortho_used=900,
         ortho_pct=50, deductible=50, deductible_met=25, copay=0, months_effective=22, term_months=None),
    # 3 — Devon Brooks (child, observation, Ameritas)
    dict(payer_name="Ameritas Dental", payer_id="AMERITAS-DENTAL", plan_type="PPO",
         plan_name="Ameritas PrimeStar", subscriber_suffix="3304", group="AMR-3321",
         relationship="child", annual_max=1000, annual_used=120, ortho_max=1500, ortho_used=0,
         ortho_pct=50, deductible=75, deductible_met=0, copay=0, months_effective=8, term_months=None),
    # 4 — Jasmine Carter (teen, finishing, Anthem CA)
    dict(payer_name="Anthem Blue Cross Dental (CA)", payer_id="ANTHEM-CA", plan_type="PPO",
         plan_name="Anthem Dental Complete", subscriber_suffix="4405", group="ANT-7788",
         relationship="child", annual_max=2000, annual_used=1450, ortho_max=2000, ortho_used=1800,
         ortho_pct=50, deductible=50, deductible_met=50, copay=0, months_effective=26, term_months=None),
    # 5 — Tyler Robinson (child, active, UHC)
    dict(payer_name="UnitedHealthcare Dental", payer_id="UHC-DENTAL", plan_type="PPO",
         plan_name="UHC Dental Options PPO", subscriber_suffix="5506", group="UHC-1200",
         relationship="child", annual_max=1500, annual_used=475, ortho_max=1750, ortho_used=875,
         ortho_pct=50, deductible=50, deductible_met=50, copay=0, months_effective=16, term_months=None),
    # 6 — Imani Williams (teen, retention, Guardian — plan terminating soon)
    dict(payer_name="Guardian Dental", payer_id="GUARDIAN-DENTAL", plan_type="PPO",
         plan_name="Guardian DentalGuard Preferred", subscriber_suffix="6607", group="GRD-5560",
         relationship="child", annual_max=1500, annual_used=900, ortho_max=1500, ortho_used=1500,
         ortho_pct=50, deductible=50, deductible_met=50, copay=0, months_effective=30, term_months=1),
    # 7 — Elijah Davis (child, consultation, Aetna)
    dict(payer_name="Aetna Dental", payer_id="AETNA-DENTAL", plan_type="PPO",
         plan_name="Aetna Dental PPO", subscriber_suffix="7708", group="AET-3040",
         relationship="child", annual_max=1250, annual_used=0, ortho_max=1500, ortho_used=0,
         ortho_pct=50, deductible=50, deductible_met=0, copay=0, months_effective=3, term_months=None),
    # 8 — Zara Thompson (teen, active, BCBS-WI)
    dict(payer_name="Blue Cross Blue Shield of WI Dental", payer_id="BCBS-WI", plan_type="PPO",
         plan_name="BCBS WI Dental Blue", subscriber_suffix="8809", group="BCBS-2211",
         relationship="child", annual_max=1750, annual_used=560, ortho_max=2000, ortho_used=1000,
         ortho_pct=50, deductible=50, deductible_met=50, copay=0, months_effective=18, term_months=None),
    # 9 — Kai Anderson (child, records, Humana)
    dict(payer_name="Humana Dental", payer_id="HUMANA-DENTAL", plan_type="HMO",
         plan_name="Humana Dental HMO", subscriber_suffix="9910", group="HUM-8080",
         relationship="child", annual_max=1000, annual_used=85, ortho_max=1250, ortho_used=0,
         ortho_pct=50, deductible=0, deductible_met=0, copay=20, months_effective=6, term_months=None),
    # 10 — Nia Harris (teen, active, WI Medicaid)
    dict(payer_name="Wisconsin Medicaid (ForwardHealth)", payer_id="WI-MEDICAID", plan_type="Medicaid",
         plan_name="BadgerCare Plus Dental", subscriber_suffix="1011", group=None,
         relationship="self", annual_max=None, annual_used=0, ortho_max=1500, ortho_used=300,
         ortho_pct=100, deductible=0, deductible_met=0, copay=0, months_effective=12, term_months=None),
]

# Claim scenarios per patient: (status, cdt, description, fee, days_ago). Multiple per patient.
# Statuses exercise the full lifecycle so Claims + Reports show a realistic mix.
CLAIM_SCENARIOS = [
    # idx 0 Priscilla — paid comprehensive + submitted adjustment + denied pano
    [("paid", "D8080", "Comprehensive orthodontic treatment (adolescent)", 600, 45),
     ("paid", "D8670", "Periodic orthodontic treatment visit", 185, 20),
     ("submitted", "D8670", "Periodic orthodontic treatment visit", 185, 4),
     ("denied", "D0330", "Panoramic radiographic image", 130, 30)],
    # idx 1 Marcus — paid records + submitted adjustment
    [("paid", "D8080", "Comprehensive orthodontic treatment (adolescent)", 550, 60),
     ("submitted", "D8670", "Periodic orthodontic treatment visit", 175, 6)],
    # idx 2 Aaliyah — accepted bonding + paid adjustment (ortho near limit)
    [("accepted", "D8080", "Comprehensive orthodontic treatment (adolescent)", 600, 15),
     ("paid", "D8670", "Periodic orthodontic treatment visit", 185, 25)],
    # idx 3 Devon — draft records
    [("draft", "D0470", "Diagnostic casts (study models)", 80, 2),
     ("draft", "D0340", "2D cephalometric radiographic image", 135, 2)],
    # idx 4 Jasmine — paid + appealed (annual max nearly hit)
    [("paid", "D8090", "Comprehensive orthodontic treatment (adult)", 650, 90),
     ("appealed", "D8680", "Orthodontic retention (removable)", 350, 10)],
    # idx 5 Tyler — paid comprehensive + submitted
    [("paid", "D8080", "Comprehensive orthodontic treatment (adolescent)", 600, 50),
     ("submitted", "D8670", "Periodic orthodontic treatment visit", 185, 5)],
    # idx 6 Imani — paid retention (plan terminating soon)
    [("paid", "D8680", "Orthodontic retention", 350, 40),
     ("paid", "D8670", "Periodic orthodontic treatment visit", 185, 15)],
    # idx 7 Elijah — draft consult
    [("draft", "D8660", "Pre-orthodontic treatment examination", 250, 1)],
    # idx 8 Zara — paid + submitted
    [("paid", "D8080", "Comprehensive orthodontic treatment (adolescent)", 600, 55),
     ("submitted", "D8670", "Periodic orthodontic treatment visit", 185, 3)],
    # idx 9 Kai — draft records
    [("draft", "D0470", "Diagnostic casts (study models)", 80, 2)],
    # idx 10 Nia — paid Medicaid comprehensive (100% coverage)
    [("paid", "D8080", "Comprehensive orthodontic treatment (adolescent)", 550, 35),
     ("paid", "D8670", "Periodic orthodontic treatment visit", 175, 12)],
]


async def seed_comprehensive_finance(db, patients: list) -> None:
    """Seed insurance, claims, line items, ledger, and ERA postings for all demo patients."""
    if not patients:
        print("  ⚠️  No patients passed to finance seed; skipping")
        return

    # Build a name → patient lookup and resolve the canonical 11 demo patients in order.
    by_name = {(p.first_name, p.last_name): p for p in patients}
    demo_patients = [by_name.get(name) for name in DEMO_PATIENT_NAMES]

    # Idempotency: if the 2nd demo patient already has insurance, assume this ran already.
    if demo_patients[1] is not None:
        exists = await db.execute(
            select(InsuranceSubscriber).where(InsuranceSubscriber.patient_id == demo_patients[1].id)
        )
        if exists.scalar_one_or_none():
            print("  ✅ Comprehensive finance: already seeded")
            return

    claim_seq = 200
    seeded_subs = seeded_claims = seeded_lines = seeded_ledger = seeded_postings = 0

    for idx, patient in enumerate(demo_patients):
        if patient is None or idx >= len(INSURANCE_PROFILES):
            continue
        prof = INSURANCE_PROFILES[idx]
        today = date.today()
        effective = today - timedelta(days=prof["months_effective"] * 30)
        termination = (today + timedelta(days=prof["term_months"] * 30)) if prof["term_months"] else None
        member_id = f"{prof['payer_id'].replace('-', '')}-{prof['subscriber_suffix']}"

        # Skip if this specific patient already has a subscriber (partial-run safety).
        already = (await db.execute(
            select(InsuranceSubscriber).where(InsuranceSubscriber.patient_id == patient.id)
        )).scalar_one_or_none()
        if already:
            continue

        sub = InsuranceSubscriber(
            id=uuid.uuid4(), practice_id=DEMO_PRACTICE_ID, patient_id=patient.id,
            relationship=prof["relationship"], subscriber_id=member_id,
            group_number=prof["group"], payer_id=prof["payer_id"], payer_name=prof["payer_name"],
            plan_name=prof["plan_name"], plan_type=prof["plan_type"], coverage_type="primary",
            subscriber_first_name=patient.first_name, subscriber_last_name=patient.last_name,
            subscriber_dob=patient.date_of_birth,
            effective_date=effective, termination_date=termination,
            copay_amount=_d(prof["copay"]) if prof["copay"] else None,
            deductible_amount=_d(prof["deductible"]) if prof["deductible"] else None,
            deductible_met=_d(prof["deductible_met"]),
            annual_max=_d(prof["annual_max"]) if prof["annual_max"] is not None else None,
            annual_used=_d(prof["annual_used"]),
            ortho_lifetime_max=_d(prof["ortho_max"]) if prof["ortho_max"] is not None else None,
            ortho_lifetime_used=_d(prof["ortho_used"]),
            ortho_coverage_pct=prof["ortho_pct"], is_active=True,
            eligibility_status="active",
        )
        db.add(sub)
        seeded_subs += 1

        # Ledger running balance is rebuilt chronologically per patient.
        ledger_events: list[tuple] = []  # (posted_date, entry_type, description, amount, cdt, claim_id, method, ref)

        for (status, cdt, desc, fee, days_ago) in CLAIM_SCENARIOS[idx]:
            claim_seq += 1
            service_date = today - timedelta(days=days_ago)
            billed = _d(fee)
            coverage = Decimal(prof["ortho_pct"]) / 100

            claim = InsuranceClaim(
                id=uuid.uuid4(), practice_id=DEMO_PRACTICE_ID,
                patient_id=str(patient.id), patient_name=f"{patient.first_name} {patient.last_name}",
                subscriber_id=member_id, payer_id=prof["payer_id"],
                payer_type=("medicaid" if prof["plan_type"] == "Medicaid" else "commercial"),
                state_code="WI",
                claim_number=f"CLM-2026-{claim_seq:05d}",
                status=status,
                cdt_codes=[{"code": cdt, "description": desc, "fee": float(billed)}],
                total_billed=billed,
                rendering_provider_npi="1999999984", billing_provider_npi="1999999984",
                service_date=service_date,
            )

            # Line item for the claim
            line = ClaimLineItem(
                id=uuid.uuid4(), claim_id=claim.id, line_number=1,
                cdt_code=cdt, description=desc, quantity=1, billed_amount=billed,
                service_date=service_date,
            )

            # Charge always hits the ledger on service date.
            ledger_events.append((service_date, "charge", f"{cdt} — {desc}", billed, cdt, claim.id, None, None))

            if status in ("submitted", "accepted"):
                claim.submission_date = datetime.combine(service_date + timedelta(days=2), datetime.min.time(), tzinfo=timezone.utc)
                claim.coordination_of_benefits = {"submitted_837d": True}

            elif status == "paid":
                allowed = (billed * Decimal("0.92")).quantize(Decimal("0.01"))
                paid = (allowed * coverage).quantize(Decimal("0.01"))
                patient_resp = (billed - paid).quantize(Decimal("0.01"))
                adjustment = (billed - allowed).quantize(Decimal("0.01"))
                claim.total_allowed, claim.total_paid, claim.patient_responsibility = allowed, paid, patient_resp
                claim.submission_date = datetime.combine(service_date + timedelta(days=2), datetime.min.time(), tzinfo=timezone.utc)
                adj_date = service_date + timedelta(days=14)
                claim.adjudication_date = datetime.combine(adj_date, datetime.min.time(), tzinfo=timezone.utc)
                era_trace = f"ERA{claim_seq:09d}"
                claim.era_reference = era_trace
                line.allowed_amount, line.paid_amount = allowed, paid
                line.adjustment_amount, line.patient_responsibility = adjustment, patient_resp

                # ERA payment posting for this paid claim.
                posting = PaymentPosting(
                    id=uuid.uuid4(), practice_id=DEMO_PRACTICE_ID, source="era",
                    payer_name=prof["payer_name"], check_number=None, check_date=adj_date,
                    total_amount=paid, applied_amount=paid, unapplied_amount=Decimal("0"),
                    era_trace_number=era_trace,
                    era_data={"claims": [{"claim_id": str(claim.id), "paid_amount": float(paid),
                                          "allowed_amount": float(allowed), "patient_resp": float(patient_resp)}],
                              "simulated": True},
                    status="complete", posted_date=adj_date,
                )
                db.add(posting)
                seeded_postings += 1

                # Contractual write-off + insurance payment + partial patient payment on ledger.
                ledger_events.append((adj_date, "adjustment", f"Contractual adjustment (CO-45) — {prof['payer_name']}",
                                      -adjustment, cdt, claim.id, None, era_trace))
                ledger_events.append((adj_date, "payment", f"Insurance payment — {prof['payer_name']} — ERA {era_trace}",
                                      -paid, cdt, claim.id, "insurance", era_trace))
                # Patient pays part of their responsibility (leaves a realistic small balance).
                pt_payment = (patient_resp * Decimal("0.6")).quantize(Decimal("0.01"))
                if pt_payment > 0:
                    ledger_events.append((adj_date + timedelta(days=5), "payment",
                                          "Patient payment — card on file", -pt_payment, cdt, claim.id, "card", None))

            elif status == "denied":
                claim.total_allowed = Decimal("0.00")
                claim.total_paid = Decimal("0.00")
                claim.patient_responsibility = billed
                claim.submission_date = datetime.combine(service_date + timedelta(days=2), datetime.min.time(), tzinfo=timezone.utc)
                claim.adjudication_date = datetime.combine(service_date + timedelta(days=12), datetime.min.time(), tzinfo=timezone.utc)
                claim.denial_codes = ["CO-96"]
                claim.denial_reason = "Non-covered service under current plan benefit period"
                line.allowed_amount = Decimal("0.00")
                line.paid_amount = Decimal("0.00")
                line.patient_responsibility = billed
                line.denial_code = "CO-96"
                line.denial_reason = "Non-covered service"

            elif status == "appealed":
                claim.submission_date = datetime.combine(service_date + timedelta(days=2), datetime.min.time(), tzinfo=timezone.utc)
                claim.adjudication_date = datetime.combine(service_date + timedelta(days=9), datetime.min.time(), tzinfo=timezone.utc)
                claim.denial_codes = ["CO-197"]
                claim.denial_reason = "Precertification/authorization absent — appeal submitted with narrative"
                claim.coordination_of_benefits = {"appeal_narrative_submitted": True}

            db.add(claim)
            db.add(line)
            seeded_claims += 1
            seeded_lines += 1

        # Write the ledger chronologically with a rolling running balance.
        running = Decimal("0.00")
        for (pdate, etype, pdesc, amount, cdt, claim_id, method, ref) in sorted(ledger_events, key=lambda e: e[0]):
            running = (running + amount).quantize(Decimal("0.01"))
            db.add(PatientLedgerEntry(
                id=uuid.uuid4(), practice_id=DEMO_PRACTICE_ID, patient_id=patient.id,
                entry_type=etype, description=pdesc, amount=amount, running_balance=running,
                cdt_code=cdt, claim_id=claim_id, payment_method=method, reference_number=ref,
                posted_date=pdate,
            ))
            seeded_ledger += 1

    await db.flush()
    print(f"  ✅ Comprehensive finance: {seeded_subs} plans, {seeded_claims} claims, "
          f"{seeded_lines} line items, {seeded_ledger} ledger entries, {seeded_postings} ERA postings")


async def seed_demo_finance():
    """Standalone entry point."""
    async with SessionLocal() as db:
        practice = (await db.execute(select(Practice).where(Practice.id == DEMO_PRACTICE_ID))).scalar_one_or_none()
        if not practice:
            print("❌ Demo practice not found. Run demo_accounts + demo_flow first.")
            return
        patients = (await db.execute(
            select(Patient).where(Patient.practice_id == DEMO_PRACTICE_ID).order_by(Patient.created_at)
        )).scalars().all()
        await seed_comprehensive_finance(db, list(patients))
        await db.commit()
    print("✅ Demo finance seeding complete!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(seed_demo_finance())
