"""OrthoFlow API — Financial Reporting Dashboard.

Production reports, collections analysis, AR aging, and provider productivity.
All data returned in chart-friendly formats.
"""
import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, case, extract, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.audit import audit_log
from app.models.finance import PatientLedgerEntry, PaymentPosting, InsuranceSubscriber
from app.models.claims import InsuranceClaim
from app.models.clinical import Appointment, Patient
from app.models.portal import ReportSnapshot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


class ReportFilters(BaseModel):
    # Patient dimensions
    gender: str | None = None
    min_age: int | None = None
    max_age: int | None = None
    treatment_status: str | None = None       # patients.status
    treatment_phase: str | None = None
    referral: str | None = None               # matches referring_doctor (contains)
    has_referral: bool | None = None
    # Insurance
    insurance: str | None = None              # "has" | "none" | payer name (contains)
    # Financial
    payment_status: str | None = None         # "owes" | "paid_up"
    min_balance: float | None = None
    # Appointment / procedure
    appointment_type: str | None = None       # appointments.appointment_type (contains)
    procedure_cdt: str | None = None          # ledger cdt_code
    # Time window (created / activity)
    start_date: date | None = None
    end_date: date | None = None


async def _run_patient_report(db: AsyncSession, practice_id, f: ReportFilters) -> list[dict]:
    """Resolve the patient-tab report: patients matching the filter set, with balance + payer."""
    q = select(Patient).where(Patient.practice_id == practice_id)
    if f.gender:
        q = q.where(Patient.gender == f.gender)
    if f.treatment_status:
        q = q.where(Patient.status == f.treatment_status)
    if f.treatment_phase:
        q = q.where(Patient.treatment_phase == f.treatment_phase)
    if f.referral:
        q = q.where(Patient.referring_doctor.ilike(f"%{f.referral}%"))
    if f.has_referral is True:
        q = q.where(Patient.referring_doctor.isnot(None))
    if f.has_referral is False:
        q = q.where(Patient.referring_doctor.is_(None))
    if f.start_date:
        q = q.where(func.date(Patient.created_at) >= f.start_date)
    if f.end_date:
        q = q.where(func.date(Patient.created_at) <= f.end_date)
    patients = (await db.execute(q)).scalars().all()

    # Age filter (computed from DOB).
    today = date.today()
    def age_of(p):
        if not p.date_of_birth:
            return None
        return today.year - p.date_of_birth.year - ((today.month, today.day) < (p.date_of_birth.month, p.date_of_birth.day))
    if f.min_age is not None:
        patients = [p for p in patients if (a := age_of(p)) is not None and a >= f.min_age]
    if f.max_age is not None:
        patients = [p for p in patients if (a := age_of(p)) is not None and a <= f.max_age]

    pids = [p.id for p in patients]
    if not pids:
        return []

    # Balances (single grouped query).
    bal_rows = (await db.execute(
        select(PatientLedgerEntry.patient_id, func.sum(PatientLedgerEntry.amount))
        .where(PatientLedgerEntry.practice_id == practice_id, PatientLedgerEntry.patient_id.in_(pids))
        .group_by(PatientLedgerEntry.patient_id)
    )).all()
    bal_by = {str(pid): float(total or 0) for pid, total in bal_rows}

    # Primary payer per patient.
    subs = (await db.execute(
        select(InsuranceSubscriber).where(
            InsuranceSubscriber.practice_id == practice_id,
            InsuranceSubscriber.patient_id.in_(pids),
            InsuranceSubscriber.coverage_type == "primary",
        )
    )).scalars().all()
    payer_by = {str(s.patient_id): s.payer_name for s in subs}

    # Patients who had a given procedure CDT (ledger) or appointment type.
    proc_pids = None
    if f.procedure_cdt:
        rows = (await db.execute(
            select(PatientLedgerEntry.patient_id).where(
                PatientLedgerEntry.practice_id == practice_id,
                PatientLedgerEntry.cdt_code == f.procedure_cdt,
            ).distinct()
        )).all()
        proc_pids = {str(r[0]) for r in rows}
    appt_pids = None
    if f.appointment_type:
        rows = (await db.execute(
            select(Appointment.patient_id).where(
                Appointment.practice_id == practice_id,
                Appointment.appointment_type.ilike(f"%{f.appointment_type}%"),
            ).distinct()
        )).all()
        appt_pids = {str(r[0]) for r in rows}

    result = []
    for p in patients:
        pid = str(p.id)
        bal = bal_by.get(pid, 0.0)
        payer = payer_by.get(pid)
        # Financial filters.
        if f.payment_status == "owes" and bal <= 0:
            continue
        if f.payment_status == "paid_up" and bal > 0:
            continue
        if f.min_balance is not None and bal < f.min_balance:
            continue
        # Insurance filters.
        if f.insurance == "has" and not payer:
            continue
        if f.insurance == "none" and payer:
            continue
        if f.insurance and f.insurance not in ("has", "none") and (not payer or f.insurance.lower() not in payer.lower()):
            continue
        # Procedure / appointment membership.
        if proc_pids is not None and pid not in proc_pids:
            continue
        if appt_pids is not None and pid not in appt_pids:
            continue
        result.append({
            "patient_id": pid,
            "first_name": p.first_name, "last_name": p.last_name,
            "gender": p.gender, "age": age_of(p),
            "status": p.status, "treatment_phase": p.treatment_phase,
            "referring_doctor": p.referring_doctor,
            "payer_name": payer, "balance": round(bal, 2),
            "email": p.email, "phone": p.phone,
        })
    return result


@router.post("/builder/patient")
async def report_builder_patient(
    filters: ReportFilters,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Customizable PATIENT report — filter by any combination of dimensions."""
    practice_id = UUID(user["practice_id"]) if isinstance(user["practice_id"], str) else user["practice_id"]
    rows = await _run_patient_report(db, practice_id, filters)
    return {"tab": "patient", "count": len(rows), "rows": rows}


@router.post("/builder/insurance")
async def report_builder_insurance(
    filters: ReportFilters,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Customizable INSURANCE report — insured patients + plan/benefit summary."""
    practice_id = UUID(user["practice_id"]) if isinstance(user["practice_id"], str) else user["practice_id"]
    # Reuse patient resolution, then attach insurance detail and drop the uninsured.
    base = await _run_patient_report(db, practice_id, filters)
    pids = [r["patient_id"] for r in base]
    subs = (await db.execute(
        select(InsuranceSubscriber).where(
            InsuranceSubscriber.practice_id == practice_id,
            InsuranceSubscriber.patient_id.in_([UUID(p) for p in pids]) if pids else False,
            InsuranceSubscriber.coverage_type == "primary",
        )
    )).scalars().all() if pids else []
    sub_by = {str(s.patient_id): s for s in subs}
    rows = []
    for r in base:
        s = sub_by.get(r["patient_id"])
        if not s:
            continue
        remaining = float((s.ortho_lifetime_max or 0) - (s.ortho_lifetime_used or 0)) if s.ortho_lifetime_max is not None else None
        rows.append({
            **r,
            "payer_name": s.payer_name, "plan_type": s.plan_type,
            "lifetime_max": float(s.ortho_lifetime_max) if s.ortho_lifetime_max is not None else None,
            "remaining_benefit": remaining,
            "eligibility_status": s.eligibility_status,
        })
    return {"tab": "insurance", "count": len(rows), "rows": rows}


class BundleMessageRequest(BaseModel):
    filters: ReportFilters
    channel: str = Field("sms", pattern="^(sms|email)$")
    subject: str | None = None
    body: str = Field(..., min_length=1, max_length=1600)


@router.post("/builder/bundle-message")
async def report_bundle_message(
    body: BundleMessageRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Flagship cross-feature action: message everyone in a report result set.

    Example: run the "patients who owe" report, then bundle-message them a balance reminder.
    Logs one MessageLog per recipient (queued) via the communications pipeline.
    """
    from app.models.communications import MessageLog
    practice_id = UUID(user["practice_id"]) if isinstance(user["practice_id"], str) else user["practice_id"]
    rows = await _run_patient_report(db, practice_id, body.filters)

    queued = 0
    for r in rows:
        # Only message patients with a usable contact for the channel.
        contact = r.get("email") if body.channel == "email" else r.get("phone")
        if not contact:
            continue
        db.add(MessageLog(
            practice_id=practice_id,
            patient_id=UUID(r["patient_id"]),
            direction="outbound",
            channel=body.channel,
            to_address=contact,
            subject=body.subject,
            body=body.body,
            status="queued",
            metadata_={"source": "report_bundle"},
        ))
        queued += 1
    await db.commit()
    await audit_log(db, practice_id, user["user_id"], "report.bundle_message", "message_log", f"queued={queued}")
    return {"recipients_matched": len(rows), "messages_queued": queued, "channel": body.channel}


@router.get("/eod")
async def end_of_day_report(
    for_date: date = Query(default_factory=date.today),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """End-of-Day report — everything that happened in the office on `for_date`.

    Aggregates the day's activity into a single printable summary: appointments (by status),
    payments collected, charges posted, insurance claims submitted, and contracts placed.
    Powers the printable EOD view the office runs at close.
    """
    from app.models.ortho_ops import PatientInsuranceContract
    practice_id = UUID(user["practice_id"]) if isinstance(user["practice_id"], str) else user["practice_id"]

    # Patient name lookup.
    patients = (await db.execute(select(Patient).where(Patient.practice_id == practice_id))).scalars().all()
    name_by_id = {str(p.id): f"{p.first_name} {p.last_name}" for p in patients}

    # Appointments today by status.
    appts = (await db.execute(
        select(Appointment).where(
            Appointment.practice_id == practice_id,
            Appointment.appointment_date == for_date,
        )
    )).scalars().all()
    appt_by_status: dict[str, int] = {}
    for a in appts:
        s = a.status.value if hasattr(a.status, "value") else str(a.status)
        appt_by_status[s] = appt_by_status.get(s, 0) + 1

    # Ledger activity today (payments + charges).
    entries = (await db.execute(
        select(PatientLedgerEntry).where(
            PatientLedgerEntry.practice_id == practice_id,
            PatientLedgerEntry.posted_date == for_date,
        )
    )).scalars().all()
    payments = [e for e in entries if e.entry_type == "payment"]
    charges = [e for e in entries if e.entry_type == "charge"]
    total_collected = float(sum(abs(e.amount) for e in payments)) if payments else 0.0
    total_charged = float(sum(e.amount for e in charges)) if charges else 0.0

    # Claims submitted today.
    claims = (await db.execute(
        select(InsuranceClaim).where(
            InsuranceClaim.practice_id == practice_id,
            func.date(InsuranceClaim.submission_date) == for_date,
        )
    )).scalars().all()

    # Contracts placed (activated) today.
    contracts = (await db.execute(
        select(PatientInsuranceContract).where(
            PatientInsuranceContract.practice_id == practice_id,
            func.date(PatientInsuranceContract.updated_at) == for_date,
            PatientInsuranceContract.status == "active",
        )
    )).scalars().all()

    return {
        "date": for_date.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "appointments": {
            "total": len(appts),
            "by_status": appt_by_status,
        },
        "financials": {
            "payments_collected_count": len(payments),
            "total_collected": total_collected,
            "charges_posted_count": len(charges),
            "total_charged": total_charged,
            "payments": [
                {"patient": name_by_id.get(str(e.patient_id), "Unknown"),
                 "amount": float(abs(e.amount)), "method": e.payment_method, "description": e.description}
                for e in payments
            ],
        },
        "claims_submitted": [
            {"id": str(c.id), "patient": name_by_id.get(str(c.patient_id), "Unknown"),
             "status": c.status.value if hasattr(c.status, "value") else str(c.status)}
            for c in claims
        ],
        "contracts_placed": [
            {"id": str(c.id), "patient": name_by_id.get(str(c.patient_id), "Unknown"),
             "total_fee": float(c.total_treatment_fee), "fee_type": c.fee_type}
            for c in contracts
        ],
    }


# ── Schemas ───────────────────────────────────────────────────────────────────


class ChartDataPoint(BaseModel):
    label: str
    value: float


class ProductionByProvider(BaseModel):
    provider_id: str | None
    provider_label: str
    total_charges: float
    procedure_count: int


class ProductionByCDT(BaseModel):
    cdt_category: str
    total_charges: float
    procedure_count: int


class CollectionMonth(BaseModel):
    month: str
    production: float
    collections: float
    collection_rate: float


class ARBucket(BaseModel):
    bucket: str
    total_amount: float
    patient_count: int


class ProviderProductivity(BaseModel):
    provider_id: str | None
    provider_name: str
    total_procedures: int
    working_days: int
    avg_per_day: float
    total_production: float


class SnapshotCreate(BaseModel):
    report_type: str = Field(..., pattern="^(production|collections|ar_aging|provider_productivity)$")
    period_start: date
    period_end: date


# ── Production Report ─────────────────────────────────────────────────────────


@router.get("/production")
async def production_report(
    start_date: date = Query(..., description="Report start date"),
    end_date: date = Query(..., description="Report end date"),
    provider_id: str | None = Query(None, description="Filter by provider UUID"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Production report: total charges by date range, grouped by provider and CDT code category."""
    practice_id = user["practice_id"]

    if start_date > end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_date must be before end_date")

    # Base filter for charges
    base_filter = and_(
        PatientLedgerEntry.practice_id == practice_id,
        PatientLedgerEntry.entry_type == "charge",
        PatientLedgerEntry.posted_date >= start_date,
        PatientLedgerEntry.posted_date <= end_date,
    )
    if provider_id:
        base_filter = and_(base_filter, PatientLedgerEntry.provider_id == provider_id)

    # By provider
    provider_result = await db.execute(
        select(
            PatientLedgerEntry.provider_id,
            func.sum(PatientLedgerEntry.amount).label("total"),
            func.count(PatientLedgerEntry.id).label("count"),
        )
        .where(base_filter)
        .group_by(PatientLedgerEntry.provider_id)
        .order_by(func.sum(PatientLedgerEntry.amount).desc())
    )
    by_provider = [
        ProductionByProvider(
            provider_id=str(row.provider_id) if row.provider_id else None,
            provider_label=str(row.provider_id) if row.provider_id else "Unassigned",
            total_charges=float(row.total or 0),
            procedure_count=row.count,
        )
        for row in provider_result.all()
    ]

    # By CDT code category (first 4 chars = category)
    by_cdt = []
    try:
        cdt_result = await db.execute(
            select(
                func.left(PatientLedgerEntry.cdt_code, 4).label("cdt_cat"),
                func.sum(PatientLedgerEntry.amount).label("total"),
                func.count(PatientLedgerEntry.id).label("count"),
            )
            .where(and_(base_filter, PatientLedgerEntry.cdt_code.isnot(None)))
            .group_by(text("1"))
            .order_by(func.sum(PatientLedgerEntry.amount).desc())
        )
        by_cdt = [
            ProductionByCDT(
                cdt_category=row.cdt_cat or "Unknown",
                total_charges=float(row.total or 0),
                procedure_count=row.count,
            )
            for row in cdt_result.all()
        ]
    except Exception:
        by_cdt = []

    # Totals
    total_result = await db.execute(
        select(
            func.sum(PatientLedgerEntry.amount).label("total"),
            func.count(PatientLedgerEntry.id).label("count"),
        ).where(base_filter)
    )
    totals = total_result.one()

    await audit_log(
        db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="report.production",
        resource_type="report",
        details=f"Production report: {start_date} to {end_date}",
    )

    return {
        "period": {"start_date": str(start_date), "end_date": str(end_date)},
        "total_production": float(totals.total or 0),
        "total_procedures": totals.count,
        "by_provider": [p.model_dump() for p in by_provider],
        "by_cdt_category": [c.model_dump() for c in by_cdt],
    }


# ── Collections vs Production ─────────────────────────────────────────────────


@router.get("/collections")
async def collections_report(
    start_date: date = Query(..., description="Report start date"),
    end_date: date = Query(..., description="Report end date"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Collections vs Production: payments received vs charges posted, grouped by month."""
    practice_id = user["practice_id"]

    if start_date > end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_date must be before end_date")

    # Monthly production (charges)
    production_result = await db.execute(
        select(
            func.to_char(PatientLedgerEntry.posted_date, text("'YYYY-MM'")).label("month"),
            func.sum(PatientLedgerEntry.amount).label("total"),
        )
        .where(
            PatientLedgerEntry.practice_id == practice_id,
            PatientLedgerEntry.entry_type == "charge",
            PatientLedgerEntry.posted_date >= start_date,
            PatientLedgerEntry.posted_date <= end_date,
        )
        .group_by(func.to_char(PatientLedgerEntry.posted_date, text("'YYYY-MM'")))
        .order_by(func.to_char(PatientLedgerEntry.posted_date, text("'YYYY-MM'")))
    )
    production_by_month = {row.month: float(row.total or 0) for row in production_result.all()}

    # Monthly collections (payments — stored as negative amounts)
    collections_result = await db.execute(
        select(
            func.to_char(PatientLedgerEntry.posted_date, text("'YYYY-MM'")).label("month"),
            func.sum(func.abs(PatientLedgerEntry.amount)).label("total"),
        )
        .where(
            PatientLedgerEntry.practice_id == practice_id,
            PatientLedgerEntry.entry_type == "payment",
            PatientLedgerEntry.posted_date >= start_date,
            PatientLedgerEntry.posted_date <= end_date,
        )
        .group_by(func.to_char(PatientLedgerEntry.posted_date, text("'YYYY-MM'")))
        .order_by(func.to_char(PatientLedgerEntry.posted_date, text("'YYYY-MM'")))
    )
    collections_by_month = {row.month: float(row.total or 0) for row in collections_result.all()}

    # Combine months
    all_months = sorted(set(list(production_by_month.keys()) + list(collections_by_month.keys())))
    monthly_data = []
    total_production = 0.0
    total_collections = 0.0

    for month in all_months:
        prod = production_by_month.get(month, 0.0)
        coll = collections_by_month.get(month, 0.0)
        rate = (coll / prod * 100) if prod > 0 else 0.0
        monthly_data.append(CollectionMonth(
            month=month,
            production=prod,
            collections=coll,
            collection_rate=round(rate, 1),
        ))
        total_production += prod
        total_collections += coll

    overall_rate = (total_collections / total_production * 100) if total_production > 0 else 0.0

    await audit_log(
        db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="report.collections",
        resource_type="report",
        details=f"Collections report: {start_date} to {end_date}",
    )

    return {
        "period": {"start_date": str(start_date), "end_date": str(end_date)},
        "total_production": total_production,
        "total_collections": total_collections,
        "overall_collection_rate": round(overall_rate, 1),
        "monthly": [m.model_dump() for m in monthly_data],
    }


# ── AR Aging ──────────────────────────────────────────────────────────────────


@router.get("/ar-aging")
async def ar_aging_report(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """AR Aging: outstanding patient balances in 30/60/90/120+ day buckets."""
    practice_id = user["practice_id"]
    today = date.today()

    # Get net balance per patient with their oldest outstanding charge date
    # We calculate balance per patient then bucket by age of oldest unpaid charge
    balance_query = (
        select(
            PatientLedgerEntry.patient_id,
            func.sum(PatientLedgerEntry.amount).label("balance"),
            func.min(PatientLedgerEntry.posted_date).label("oldest_date"),
        )
        .where(
            PatientLedgerEntry.practice_id == practice_id,
        )
        .group_by(PatientLedgerEntry.patient_id)
        .having(func.sum(PatientLedgerEntry.amount) > 0)
    )

    result = await db.execute(balance_query)
    rows = result.all()

    buckets = {
        "0-30": {"total": 0.0, "patients": set()},
        "31-60": {"total": 0.0, "patients": set()},
        "61-90": {"total": 0.0, "patients": set()},
        "91-120": {"total": 0.0, "patients": set()},
        "120+": {"total": 0.0, "patients": set()},
    }

    for row in rows:
        balance = float(row.balance)
        oldest = row.oldest_date
        if not oldest:
            continue
        days_old = (today - oldest).days

        if days_old <= 30:
            bucket_key = "0-30"
        elif days_old <= 60:
            bucket_key = "31-60"
        elif days_old <= 90:
            bucket_key = "61-90"
        elif days_old <= 120:
            bucket_key = "91-120"
        else:
            bucket_key = "120+"

        buckets[bucket_key]["total"] += balance
        buckets[bucket_key]["patients"].add(row.patient_id)

    total_outstanding = sum(b["total"] for b in buckets.values())

    await audit_log(
        db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="report.ar_aging",
        resource_type="report",
    )

    return {
        "total_outstanding": round(total_outstanding, 2),
        "buckets": [
            ARBucket(
                bucket=key,
                total_amount=round(data["total"], 2),
                patient_count=len(data["patients"]),
            ).model_dump()
            for key, data in buckets.items()
        ],
    }


# ── Provider Productivity ─────────────────────────────────────────────────────


@router.get("/provider-productivity")
async def provider_productivity_report(
    start_date: date = Query(..., description="Report start date"),
    end_date: date = Query(..., description="Report end date"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Provider productivity: procedures per provider per day in date range."""
    practice_id = user["practice_id"]

    if start_date > end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_date must be before end_date")

    # Count completed appointments per provider
    appt_result = await db.execute(
        select(
            Appointment.created_by.label("provider_id"),
            func.count(Appointment.id).label("total_procedures"),
            func.count(func.distinct(Appointment.appointment_date)).label("working_days"),
        )
        .where(
            Appointment.practice_id == practice_id,
            Appointment.appointment_date >= start_date,
            Appointment.appointment_date <= end_date,
            Appointment.status == "completed",
        )
        .group_by(Appointment.created_by)
    )
    appt_data = {str(row.provider_id): {"procedures": row.total_procedures, "days": row.working_days} for row in appt_result.all()}

    # Get production per provider (charges)
    prod_result = await db.execute(
        select(
            PatientLedgerEntry.provider_id,
            func.sum(PatientLedgerEntry.amount).label("total"),
        )
        .where(
            PatientLedgerEntry.practice_id == practice_id,
            PatientLedgerEntry.entry_type == "charge",
            PatientLedgerEntry.posted_date >= start_date,
            PatientLedgerEntry.posted_date <= end_date,
        )
        .group_by(PatientLedgerEntry.provider_id)
    )
    prod_data = {str(row.provider_id): float(row.total or 0) for row in prod_result.all()}

    # Combine
    all_providers = set(list(appt_data.keys()) + list(prod_data.keys()))
    providers = []
    for pid in all_providers:
        appt_info = appt_data.get(pid, {"procedures": 0, "days": 0})
        production = prod_data.get(pid, 0.0)
        working_days = appt_info["days"] or 1
        providers.append(ProviderProductivity(
            provider_id=pid if pid != "None" else None,
            provider_name=pid if pid != "None" else "Unassigned",
            total_procedures=appt_info["procedures"],
            working_days=working_days,
            avg_per_day=round(appt_info["procedures"] / working_days, 1),
            total_production=round(production, 2),
        ))

    providers.sort(key=lambda p: p.total_production, reverse=True)

    await audit_log(
        db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="report.provider_productivity",
        resource_type="report",
        details=f"Provider productivity: {start_date} to {end_date}",
    )

    return {
        "period": {"start_date": str(start_date), "end_date": str(end_date)},
        "providers": [p.model_dump() for p in providers],
    }


# ── Report Snapshots ──────────────────────────────────────────────────────────


@router.post("/generate-snapshot", status_code=status.HTTP_201_CREATED)
async def generate_snapshot(
    payload: SnapshotCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate and cache a monthly report snapshot."""
    practice_id = user["practice_id"]

    # Generate report data based on type
    if payload.report_type == "production":
        # Re-use production logic inline to capture data
        result = await db.execute(
            select(
                func.sum(PatientLedgerEntry.amount).label("total"),
                func.count(PatientLedgerEntry.id).label("count"),
            ).where(
                PatientLedgerEntry.practice_id == practice_id,
                PatientLedgerEntry.entry_type == "charge",
                PatientLedgerEntry.posted_date >= payload.period_start,
                PatientLedgerEntry.posted_date <= payload.period_end,
            )
        )
        totals = result.one()
        snapshot_data = {
            "total_production": float(totals.total or 0),
            "total_procedures": totals.count,
        }
    elif payload.report_type == "collections":
        prod_result = await db.execute(
            select(func.sum(PatientLedgerEntry.amount)).where(
                PatientLedgerEntry.practice_id == practice_id,
                PatientLedgerEntry.entry_type == "charge",
                PatientLedgerEntry.posted_date >= payload.period_start,
                PatientLedgerEntry.posted_date <= payload.period_end,
            )
        )
        coll_result = await db.execute(
            select(func.sum(func.abs(PatientLedgerEntry.amount))).where(
                PatientLedgerEntry.practice_id == practice_id,
                PatientLedgerEntry.entry_type == "payment",
                PatientLedgerEntry.posted_date >= payload.period_start,
                PatientLedgerEntry.posted_date <= payload.period_end,
            )
        )
        prod_total = float(prod_result.scalar() or 0)
        coll_total = float(coll_result.scalar() or 0)
        rate = (coll_total / prod_total * 100) if prod_total > 0 else 0.0
        snapshot_data = {
            "total_production": prod_total,
            "total_collections": coll_total,
            "collection_rate": round(rate, 1),
        }
    else:
        snapshot_data = {"generated": True}

    snapshot = ReportSnapshot(
        practice_id=practice_id,
        report_type=payload.report_type,
        period_start=payload.period_start,
        period_end=payload.period_end,
        data=snapshot_data,
        generated_by=user["user_id"],
    )
    db.add(snapshot)
    await db.commit()
    await db.refresh(snapshot)

    await audit_log(
        db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="report.snapshot_generated",
        resource_type="report_snapshot",
        resource_id=str(snapshot.id),
        details=f"Generated {payload.report_type} snapshot: {payload.period_start} to {payload.period_end}",
    )

    logger.info("Report snapshot generated: %s for practice %s", payload.report_type, practice_id)
    return {
        "id": str(snapshot.id),
        "report_type": snapshot.report_type,
        "period_start": str(snapshot.period_start),
        "period_end": str(snapshot.period_end),
        "data": snapshot.data,
        "generated_at": snapshot.generated_at.isoformat(),
    }


@router.get("/snapshots")
async def list_snapshots(
    report_type: str | None = Query(None, description="Filter by report type"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List cached report snapshots."""
    practice_id = user["practice_id"]

    query = select(ReportSnapshot).where(
        ReportSnapshot.practice_id == practice_id,
    )
    if report_type:
        query = query.where(ReportSnapshot.report_type == report_type)

    query = query.order_by(ReportSnapshot.generated_at.desc()).limit(50)
    result = await db.execute(query)
    snapshots = result.scalars().all()

    return {
        "snapshots": [
            {
                "id": str(s.id),
                "report_type": s.report_type,
                "period_start": str(s.period_start),
                "period_end": str(s.period_end),
                "data": s.data,
                "generated_at": s.generated_at.isoformat(),
            }
            for s in snapshots
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Reports by Category (Frontdesk / Doctor / TC)
# Cloud9-informed category set. Each returns rows + a summary for the Reports UI.
# ═══════════════════════════════════════════════════════════════════════════════

REPORT_CATEGORIES = [
    {"key": "patients_owe", "label": "Patients Who Owe Money", "group": "financial"},
    {"key": "by_insurance", "label": "By Insurance (Payer Book)", "group": "financial"},
    {"key": "missing_appointments", "label": "Missing / Broken Appointments", "group": "scheduling"},
    {"key": "treatment_overdue", "label": "Treatment Status — Overdue", "group": "clinical"},
    {"key": "treatment_bring_sooner", "label": "Treatment Status — Bring In Sooner", "group": "clinical"},
    {"key": "scheduled_appointments", "label": "Scheduled Specific Appointments", "group": "scheduling"},
    {"key": "private_collections", "label": "Private Collections", "group": "financial"},
    {"key": "insurance_collections", "label": "Insurance Collections", "group": "financial"},
    {"key": "no_chart_notes_today", "label": "Appointments With No Chart Notes (Today)", "group": "clinical"},
]


@router.get("/categories")
async def list_report_categories(user: dict = Depends(get_current_user)):
    """List the available report categories for the Reports UI."""
    return {"categories": REPORT_CATEGORIES}


@router.get("/category/{key}")
async def report_by_category(
    key: str,
    report_date: date = Query(default_factory=date.today),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run a categorized report. Returns {key, label, rows, summary, ai_suggestions?}."""
    practice_id = UUID(user["practice_id"]) if isinstance(user["practice_id"], str) else user["practice_id"]
    cat = next((c for c in REPORT_CATEGORIES if c["key"] == key), None)
    if not cat:
        raise HTTPException(404, f"Unknown report category '{key}'")

    from app.models.finance import InsuranceSubscriber
    from app.models.ortho_ops import PatientInsuranceContract

    rows: list[dict] = []
    summary: dict = {}
    ai_suggestions: list[str] = []

    # ── Patients who owe money (balance > 0) ───────────────────────────────────
    if key in ("patients_owe", "private_collections", "insurance_collections"):
        bal_rows = (await db.execute(
            select(PatientLedgerEntry.patient_id, func.sum(PatientLedgerEntry.amount))
            .where(PatientLedgerEntry.practice_id == practice_id)
            .group_by(PatientLedgerEntry.patient_id)
        )).all()
        patients = {str(p.id): p for p in (await db.execute(
            select(Patient).where(Patient.practice_id == practice_id))).scalars().all()}
        subs = {str(s.patient_id): s for s in (await db.execute(
            select(InsuranceSubscriber).where(InsuranceSubscriber.practice_id == practice_id,
                                              InsuranceSubscriber.coverage_type == "primary"))).scalars().all()}
        for pid, bal in bal_rows:
            b = float(bal or 0)
            if b <= 0:
                continue
            p = patients.get(str(pid))
            if not p:
                continue
            has_ins = str(pid) in subs
            is_medicaid = has_ins and (subs[str(pid)].plan_type or "").lower() == "medicaid"
            # private_collections = self-pay balance; insurance_collections = has insurance
            if key == "private_collections" and has_ins:
                continue
            if key == "insurance_collections" and not has_ins:
                continue
            rows.append({
                "patient_id": str(pid), "patient_name": f"{p.first_name} {p.last_name}",
                "balance": round(b, 2), "has_insurance": has_ins,
                "payer_name": subs[str(pid)].payer_name if has_ins else None,
                "medicaid": is_medicaid,
            })
        rows.sort(key=lambda r: r["balance"], reverse=True)
        summary = {"patient_count": len(rows), "total_outstanding": round(sum(r["balance"] for r in rows), 2)}

    # ── By insurance (payer book) ───────────────────────────────────────────────
    elif key == "by_insurance":
        subs = (await db.execute(
            select(InsuranceSubscriber).where(InsuranceSubscriber.practice_id == practice_id))).scalars().all()
        by_payer: dict = {}
        for s in subs:
            g = by_payer.setdefault(s.payer_name, {"payer_name": s.payer_name, "plan_type": s.plan_type,
                                                   "patient_count": 0})
            g["patient_count"] += 1
        rows = sorted(by_payer.values(), key=lambda r: r["patient_count"], reverse=True)
        summary = {"payer_count": len(rows), "patients_with_insurance": sum(r["patient_count"] for r in rows)}

    # ── Missing / broken appointments ───────────────────────────────────────────
    elif key == "missing_appointments":
        appts = (await db.execute(
            select(Appointment).where(
                Appointment.practice_id == practice_id,
                Appointment.status.in_(["no_show", "cancelled", "broken"]),
            ).order_by(Appointment.appointment_date.desc()).limit(500)
        )).scalars().all()
        pmap = {str(p.id): p for p in (await db.execute(
            select(Patient).where(Patient.practice_id == practice_id))).scalars().all()}
        for a in appts:
            p = pmap.get(str(a.patient_id))
            rows.append({
                "appointment_id": str(a.id), "patient_id": str(a.patient_id),
                "patient_name": f"{p.first_name} {p.last_name}" if p else "—",
                "date": a.appointment_date.isoformat(), "status": a.status,
                "type": a.appointment_type,
            })
        summary = {"count": len(rows)}
        ai_suggestions = ["Prioritize re-booking no-shows in active treatment to avoid extending total treatment time."]

    # ── Treatment status: overdue / bring in sooner (AI-assisted) ───────────────
    elif key in ("treatment_overdue", "treatment_bring_sooner"):
        # Overdue = in active/finishing phase with last appointment > 45 days ago.
        # Bring sooner = active patients whose next appointment is far out but treatment is progressing.
        patients = (await db.execute(
            select(Patient).where(
                Patient.practice_id == practice_id,
                Patient.treatment_phase.in_(["active", "bonding", "finishing", "retention"]),
            )
        )).scalars().all()
        today = report_date
        for p in patients:
            last_appt = (await db.execute(
                select(func.max(Appointment.appointment_date)).where(
                    Appointment.practice_id == practice_id, Appointment.patient_id == p.id,
                    Appointment.appointment_date <= today)
            )).scalar()
            next_appt = (await db.execute(
                select(func.min(Appointment.appointment_date)).where(
                    Appointment.practice_id == practice_id, Appointment.patient_id == p.id,
                    Appointment.appointment_date > today)
            )).scalar()
            days_since = (today - last_appt).days if last_appt else None
            days_until = (next_appt - today).days if next_appt else None

            if key == "treatment_overdue":
                if (days_since is not None and days_since > 45) or (next_appt is None):
                    rows.append({
                        "patient_id": str(p.id), "patient_name": f"{p.first_name} {p.last_name}",
                        "phase": p.treatment_phase, "days_since_last": days_since,
                        "has_next_appointment": next_appt is not None,
                    })
            else:  # bring_sooner
                if days_until is not None and days_until > 42 and p.treatment_phase in ("finishing", "active"):
                    rows.append({
                        "patient_id": str(p.id), "patient_name": f"{p.first_name} {p.last_name}",
                        "phase": p.treatment_phase, "days_until_next": days_until,
                    })
        if key == "treatment_overdue":
            rows.sort(key=lambda r: (r["days_since_last"] or 9999), reverse=True)
            summary = {"count": len(rows)}
            ai_suggestions = [
                "Patients overdue >45 days risk treatment stagnation — schedule a visit to keep progress on track.",
                "Those with no next appointment should be contacted first to prevent drop-off.",
            ]
        else:
            rows.sort(key=lambda r: (r["days_until_next"] or 0), reverse=True)
            summary = {"count": len(rows)}
            ai_suggestions = [
                "Finishing-phase patients booked far out can often be brought in sooner to complete and deband earlier.",
                "Pulling these forward frees chair time and improves case-completion metrics.",
            ]

    # ── Scheduled specific appointments (for the date) ──────────────────────────
    elif key == "scheduled_appointments":
        appts = (await db.execute(
            select(Appointment).where(
                Appointment.practice_id == practice_id,
                Appointment.appointment_date == report_date,
            ).order_by(Appointment.start_time)
        )).scalars().all()
        pmap = {str(p.id): p for p in (await db.execute(
            select(Patient).where(Patient.practice_id == practice_id))).scalars().all()}
        for a in appts:
            p = pmap.get(str(a.patient_id))
            rows.append({
                "appointment_id": str(a.id), "patient_id": str(a.patient_id),
                "patient_name": f"{p.first_name} {p.last_name}" if p else "—",
                "start_time": a.start_time.isoformat() if a.start_time else None,
                "type": a.appointment_type, "status": a.status,
            })
        summary = {"count": len(rows), "date": report_date.isoformat()}

    # ── Appointments with no chart notes for the day ────────────────────────────
    elif key == "no_chart_notes_today":
        from app.models.clinical import TreatmentNote
        appts = (await db.execute(
            select(Appointment).where(
                Appointment.practice_id == practice_id,
                Appointment.appointment_date == report_date,
            )
        )).scalars().all()
        pmap = {str(p.id): p for p in (await db.execute(
            select(Patient).where(Patient.practice_id == practice_id))).scalars().all()}
        for a in appts:
            note = (await db.execute(
                select(func.count(TreatmentNote.id)).where(TreatmentNote.appointment_id == a.id)
            )).scalar() or 0
            if note == 0:
                p = pmap.get(str(a.patient_id))
                rows.append({
                    "appointment_id": str(a.id), "patient_id": str(a.patient_id),
                    "patient_name": f"{p.first_name} {p.last_name}" if p else "—",
                    "type": a.appointment_type, "status": a.status,
                })
        summary = {"count": len(rows), "date": report_date.isoformat()}
        ai_suggestions = ["Charts without notes should be documented before end of day for compliance and continuity."]

    return {
        "key": key, "label": cat["label"], "group": cat["group"],
        "rows": rows, "summary": summary, "ai_suggestions": ai_suggestions,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
