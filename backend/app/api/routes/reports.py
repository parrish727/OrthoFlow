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
from app.models.finance import PatientLedgerEntry, PaymentPosting
from app.models.claims import InsuranceClaim
from app.models.clinical import Appointment, Patient
from app.models.portal import ReportSnapshot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


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
