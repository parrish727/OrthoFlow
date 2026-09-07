"""Scale the demo practice to 100 patients with insurance coverage.

Generates realistic orthodontic patients (varied names, ages, phases) up to a total of 100
for the demo practice, and gives each an insurance subscriber with a varied payer/plan/benefit
profile so the Insurance roster shows a full, real-practice-sized book of business.

Priscilla Knowles remains the prime demo candidate (untouched here — enriched separately by
demo_priscilla). Existing patients are preserved; this only ADDS up to the target count.

Idempotent: re-running stops once the practice already has TARGET_TOTAL patients.

Run: docker compose exec backend python -m app.seeds.demo_scale
"""
import asyncio
import random
import uuid
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal

from sqlalchemy import select, func
from app.core.database import SessionLocal
from app.models.clinical import Patient
from app.models.finance import InsuranceSubscriber, PatientLedgerEntry
from app.models.claims import InsuranceClaim

DEMO_PRACTICE_ID = uuid.UUID("82fe9d87-6250-4b15-ac7d-26de094a4be8")
TARGET_TOTAL = 100

FIRST_NAMES = [
    "Aaliyah","Marcus","Devon","Jasmine","Tyler","Imani","Elijah","Zara","Kai","Nia",
    "Amara","Malik","Layla","Xavier","Simone","Andre","Kayla","Jerome","Destiny","Terrence",
    "Aisha","DeShawn","Kiara","Marquis","Tiana","Darnell","Jada","Rashad","Ebony","Isaiah",
    "Camille","Darius","Maya","Trevon","Alicia","Jamal","Bria","Kendrick","Sanaa","Omari",
    "Selena","Mateo","Valentina","Diego","Lucia","Santiago","Camila","Emilio","Gabriela","Rafael",
    "Grace","Owen","Chloe","Julian","Hannah","Nathan","Ava","Caleb","Sofia","Ethan",
    "Priya","Arjun","Anaya","Rohan","Diya","Vikram","Meera","Dev","Kiran","Anika",
    "Mei","Jin","Hana","Wei","Yuki","Chen","Sana","Tao","Lian","Ren",
    "Fatima","Omar","Layla2","Yusuf","Amina","Bilal","Zainab","Hassan","Noor","Idris",
]
LAST_NAMES = [
    "Washington","Johnson","Brooks","Carter","Robinson","Williams","Davis","Thompson","Anderson","Harris",
    "Jackson","Coleman","Bryant","Mitchell","Freeman","Grant","Hayes","Bell","Reed","Foster",
    "Rivera","Torres","Ramirez","Flores","Gomez","Diaz","Cruz","Ortiz","Morales","Reyes",
    "Nguyen","Patel","Kim","Singh","Chen","Wong","Shah","Lee","Park","Gupta",
    "Bennett","Powell","Ross","Ward","Cox","Butler","Simmons","Perry","Barnes","Fisher",
]
PHASES = ["consultation","records","active","bonding","observation_1","finishing","retention"]
GENDERS = ["male","female"]

# Payer profiles for variety (payer_id keys map to Stedi in stedi_payers.INTERNAL_PAYER_TO_STEDI)
PAYERS = [
    ("Delta Dental of Wisconsin", "DELTA-WI", "PPO"),
    ("Cigna Dental", "CIGNA-DENTAL", "PPO"),
    ("MetLife Dental", "METLIFE-DENTAL", "PPO"),
    ("Ameritas Dental", "AMERITAS-DENTAL", "PPO"),
    ("Anthem Blue Cross Dental (CA)", "ANTHEM-CA", "PPO"),
    ("UnitedHealthcare Dental", "UHC-DENTAL", "PPO"),
    ("Aetna Dental", "AETNA-DENTAL", "PPO"),
    ("Guardian Dental", "GUARDIAN-DENTAL", "PPO"),
    ("Blue Cross Blue Shield of WI Dental", "BCBS-WI", "PPO"),
    ("Humana Dental", "HUMANA-DENTAL", "HMO"),
    ("Wisconsin Medicaid (ForwardHealth)", "WI-MEDICAID", "Medicaid"),
]


def _d(v) -> Decimal:
    return Decimal(str(v)).quantize(Decimal("0.01"))


async def seed_scale_to_100(db) -> None:
    rng = random.Random(4242)  # deterministic for reproducible demos

    current = (await db.execute(
        select(func.count(Patient.id)).where(Patient.practice_id == DEMO_PRACTICE_ID)
    )).scalar() or 0

    if current >= TARGET_TOTAL:
        print(f"  ✅ Scale: practice already has {current} patients (>= {TARGET_TOTAL})")
        return

    # Avoid duplicate name collisions with existing patients.
    existing_names = {
        (r[0], r[1]) for r in (await db.execute(
            select(Patient.first_name, Patient.last_name).where(Patient.practice_id == DEMO_PRACTICE_ID)
        )).all()
    }

    to_add = TARGET_TOTAL - current
    added = subs_added = claims_added = ledger_added = 0
    attempts = 0
    seq = 5000

    while added < to_add and attempts < to_add * 20:
        attempts += 1
        fn = rng.choice(FIRST_NAMES).replace("2", "")
        ln = rng.choice(LAST_NAMES)
        if (fn, ln) in existing_names:
            continue
        existing_names.add((fn, ln))

        # Age skew toward ortho demographics (kids/teens/young adults).
        age = rng.choices([9, 11, 12, 13, 14, 15, 16, 17, 24, 31, 38], k=1)[0]
        dob = date.today() - timedelta(days=age * 365 + rng.randint(0, 364))
        phase = rng.choice(PHASES)
        gender = rng.choice(GENDERS)
        pid = uuid.uuid4()

        db.add(Patient(
            id=pid, practice_id=DEMO_PRACTICE_ID, first_name=fn, last_name=ln,
            date_of_birth=dob, gender=gender,
            phone=f"(414) 555-{rng.randint(1000,9999)}",
            email=f"{fn.lower()}.{ln.lower()}{rng.randint(1,99)}@example.com",
            status="active", treatment_phase=phase,
            address=f"{rng.randint(100,9999)} {rng.choice(['Oak','Maple','Cedar','Pine','Elm','Birch'])} St, Milwaukee, WI 5320{rng.randint(1,9)}",
        ))
        added += 1

        # Insurance subscriber with a varied benefit profile.
        seq += 1
        payer_name, payer_id, plan_type = rng.choice(PAYERS)
        annual_max = None if plan_type == "Medicaid" else rng.choice([1000, 1500, 1750, 2000])
        annual_used = rng.randint(0, int((annual_max or 1500) * 0.8))
        ortho_max = rng.choice([1000, 1250, 1500, 1750, 2000, 2500])
        ortho_used = rng.randint(0, ortho_max)
        ortho_pct = 100 if plan_type == "Medicaid" else 50
        eff = date.today() - timedelta(days=rng.randint(120, 900))
        member_id = f"{payer_id.replace('-', '')}-{seq:05d}"

        db.add(InsuranceSubscriber(
            id=uuid.uuid4(), practice_id=DEMO_PRACTICE_ID, patient_id=pid,
            relationship=rng.choice(["self", "child"]), subscriber_id=member_id,
            group_number=None if plan_type == "Medicaid" else f"GRP-{rng.randint(1000,9999)}",
            payer_id=payer_id, payer_name=payer_name, plan_name=f"{payer_name} {plan_type}",
            plan_type=plan_type, coverage_type="primary",
            subscriber_first_name=fn, subscriber_last_name=ln, subscriber_dob=dob,
            effective_date=eff, termination_date=None,
            copay_amount=_d(rng.choice([0, 0, 20, 25])) or None,
            deductible_amount=_d(50) if plan_type != "Medicaid" else None,
            deductible_met=_d(rng.choice([0, 25, 50])),
            annual_max=_d(annual_max) if annual_max is not None else None,
            annual_used=_d(annual_used),
            ortho_lifetime_max=_d(ortho_max), ortho_lifetime_used=_d(ortho_used),
            ortho_coverage_pct=ortho_pct, is_active=True, eligibility_status="active",
        ))
        subs_added += 1

        # ~55% of patients also get a claim + a couple ledger entries for roster richness.
        if rng.random() < 0.55:
            seq += 1
            status = rng.choice(["paid", "paid", "submitted", "denied", "draft"])
            cdt, desc, fee = rng.choice([
                ("D8080", "Comprehensive orthodontic treatment (adolescent)", 5500),
                ("D8090", "Comprehensive orthodontic treatment (adult)", 6000),
                ("D8670", "Periodic orthodontic treatment visit", 185),
                ("D8660", "Pre-orthodontic treatment examination", 250),
            ])
            svc = date.today() - timedelta(days=rng.randint(5, 120))
            billed = _d(fee)
            claim = InsuranceClaim(
                id=uuid.uuid4(), practice_id=DEMO_PRACTICE_ID, patient_id=str(pid),
                patient_name=f"{fn} {ln}", subscriber_id=member_id, payer_id=payer_id,
                payer_type=("medicaid" if plan_type == "Medicaid" else "commercial"),
                state_code="WI", claim_number=f"CLM-2026-{seq:05d}", status=status,
                cdt_codes=[{"code": cdt, "description": desc, "fee": float(billed)}],
                total_billed=billed, rendering_provider_npi="1999999984",
                billing_provider_npi="1999999984", service_date=svc,
            )
            if status == "paid":
                claim.total_allowed = _d(billed * Decimal("0.92"))
                claim.total_paid = _d(claim.total_allowed * (Decimal(ortho_pct) / 100))
                claim.patient_responsibility = _d(billed - claim.total_paid)
                claim.adjudication_date = datetime.combine(svc + timedelta(days=14), datetime.min.time(), tzinfo=timezone.utc)
            elif status == "denied":
                claim.total_allowed = _d(0); claim.total_paid = _d(0)
                claim.patient_responsibility = billed
                claim.denial_codes = ["CO-96"]; claim.denial_reason = "Non-covered service"
            db.add(claim)
            claims_added += 1

            # Simple ledger: charge + (payment if paid).
            db.add(PatientLedgerEntry(
                id=uuid.uuid4(), practice_id=DEMO_PRACTICE_ID, patient_id=pid,
                entry_type="charge", description=f"{cdt} — {desc}", amount=billed,
                running_balance=billed, cdt_code=cdt, posted_date=svc,
            ))
            ledger_added += 1
            if status == "paid" and claim.total_paid:
                db.add(PatientLedgerEntry(
                    id=uuid.uuid4(), practice_id=DEMO_PRACTICE_ID, patient_id=pid,
                    entry_type="payment", description=f"Insurance payment — {payer_name}",
                    amount=-claim.total_paid, running_balance=_d(billed - claim.total_paid),
                    cdt_code=cdt, payment_method="insurance",
                    posted_date=svc + timedelta(days=14),
                ))
                ledger_added += 1

        # Flush periodically to keep memory bounded.
        if added % 25 == 0:
            await db.flush()

    await db.flush()
    total = (await db.execute(
        select(func.count(Patient.id)).where(Patient.practice_id == DEMO_PRACTICE_ID)
    )).scalar()
    print(f"  ✅ Scale: +{added} patients (now {total}), +{subs_added} plans, "
          f"+{claims_added} claims, +{ledger_added} ledger entries")


async def main():
    async with SessionLocal() as db:
        await seed_scale_to_100(db)
        await db.commit()
    print("✅ Demo scale-to-100 complete!")


if __name__ == "__main__":
    asyncio.run(main())
