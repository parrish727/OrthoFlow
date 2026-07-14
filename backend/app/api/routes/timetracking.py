"""OrthoFlow — Time Tracking & Payroll API.

Clock in/out, time entry management, pay rates, and payroll summaries.
"""
import logging
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_role
from app.core.database import get_db
from app.core.audit import audit_log
from app.models.timetracking import TimeEntry, PayRate, PayrollPeriod
from app.models.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/time")


# ── Schemas ───────────────────────────────────────────────────────────────────

class ClockInResponse(BaseModel):
    id: str
    clock_in: datetime
    status: str


class ClockOutResponse(BaseModel):
    id: str
    clock_in: datetime
    clock_out: datetime
    total_hours: float
    status: str


class MyStatusResponse(BaseModel):
    is_clocked_in: bool
    clock_in_time: datetime | None = None
    today_hours: float
    current_entry_id: str | None = None


class TimeEntryResponse(BaseModel):
    id: str
    staff_id: str
    clock_in: datetime
    clock_out: datetime | None
    total_hours: float | None
    entry_type: str
    status: str
    notes: str | None
    edited_by: str | None
    edited_at: datetime | None


class EditTimeEntryRequest(BaseModel):
    clock_in: datetime | None = None
    clock_out: datetime | None = None
    entry_type: str | None = None
    notes: str | None = None


class PayRateRequest(BaseModel):
    staff_id: str
    hourly_rate: Decimal = Field(..., gt=0, le=Decimal("9999.99"))
    worker_type: str = Field(..., pattern=r"^(permanent|temporary)$")
    effective_date: date


class PayRateResponse(BaseModel):
    id: str
    staff_id: str
    staff_name: str | None = None
    hourly_rate: float
    worker_type: str
    effective_date: date
    end_date: date | None


class StaffHoursEntry(BaseModel):
    staff_id: str
    staff_name: str
    total_hours: float
    entries: list[TimeEntryResponse]


class PayrollSummaryEntry(BaseModel):
    staff_id: str
    staff_name: str
    hours: float
    rate: float
    pay: float
    worker_type: str


# ── Clock In / Out ────────────────────────────────────────────────────────────

@router.post("/clock-in", status_code=status.HTTP_201_CREATED)
async def clock_in(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClockInResponse:
    """Clock in. Creates a new time entry with status 'clocked_in'."""
    staff_id = UUID(user["user_id"])
    practice_id = UUID(user["practice_id"])

    # Check if already clocked in
    existing = await db.execute(
        select(TimeEntry).where(
            and_(
                TimeEntry.staff_id == staff_id,
                TimeEntry.practice_id == practice_id,
                TimeEntry.status == "clocked_in",
            )
        )
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already clocked in. Clock out before clocking in again.",
        )

    now = datetime.now(timezone.utc)
    entry = TimeEntry(
        practice_id=practice_id,
        staff_id=staff_id,
        clock_in=now,
        status="clocked_in",
        entry_type="regular",
    )
    db.add(entry)

    await audit_log(db, user["practice_id"], user["user_id"], "time_entry.clock_in", "time_entry")

    await db.commit()
    await db.refresh(entry)

    logger.info(f"Staff {staff_id} clocked in at {now}")
    return ClockInResponse(id=str(entry.id), clock_in=entry.clock_in, status=entry.status)


@router.post("/clock-out")
async def clock_out(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClockOutResponse:
    """Clock out the current open time entry."""
    staff_id = UUID(user["user_id"])
    practice_id = UUID(user["practice_id"])

    result = await db.execute(
        select(TimeEntry).where(
            and_(
                TimeEntry.staff_id == staff_id,
                TimeEntry.practice_id == practice_id,
                TimeEntry.status == "clocked_in",
            )
        )
    )
    entry = result.scalars().first()
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active clock-in found. Clock in first.",
        )

    now = datetime.now(timezone.utc)
    delta = now - entry.clock_in
    total_hours = Decimal(str(round(delta.total_seconds() / 3600, 2)))

    entry.clock_out = now
    entry.total_hours = total_hours
    entry.status = "complete"

    await audit_log(db, user["practice_id"], user["user_id"], "time_entry.clock_out", "time_entry", str(entry.id))

    await db.commit()
    await db.refresh(entry)

    logger.info(f"Staff {staff_id} clocked out. Total hours: {total_hours}")
    return ClockOutResponse(
        id=str(entry.id),
        clock_in=entry.clock_in,
        clock_out=entry.clock_out,
        total_hours=float(entry.total_hours),
        status=entry.status,
    )


# ── My Status & Hours ─────────────────────────────────────────────────────────

@router.get("/my-status")
async def my_status(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MyStatusResponse:
    """Get current clock-in status and today's hours."""
    staff_id = UUID(user["user_id"])
    practice_id = UUID(user["practice_id"])

    # Check for active clock-in
    result = await db.execute(
        select(TimeEntry).where(
            and_(
                TimeEntry.staff_id == staff_id,
                TimeEntry.practice_id == practice_id,
                TimeEntry.status == "clocked_in",
            )
        )
    )
    active_entry = result.scalars().first()

    # Calculate today's hours
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_result = await db.execute(
        select(func.coalesce(func.sum(TimeEntry.total_hours), 0)).where(
            and_(
                TimeEntry.staff_id == staff_id,
                TimeEntry.practice_id == practice_id,
                TimeEntry.clock_in >= today_start,
                TimeEntry.status == "complete",
            )
        )
    )
    today_hours = float(today_result.scalar() or 0)

    # If currently clocked in, add running time
    if active_entry:
        running_delta = datetime.now(timezone.utc) - active_entry.clock_in
        today_hours += round(running_delta.total_seconds() / 3600, 2)

    return MyStatusResponse(
        is_clocked_in=active_entry is not None,
        clock_in_time=active_entry.clock_in if active_entry else None,
        today_hours=round(today_hours, 2),
        current_entry_id=str(active_entry.id) if active_entry else None,
    )


@router.get("/my-hours")
async def my_hours(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TimeEntryResponse]:
    """Get current user's time entries for the current pay period (last 14 days)."""
    staff_id = UUID(user["user_id"])
    practice_id = UUID(user["practice_id"])

    period_start = datetime.now(timezone.utc) - timedelta(days=14)

    result = await db.execute(
        select(TimeEntry).where(
            and_(
                TimeEntry.staff_id == staff_id,
                TimeEntry.practice_id == practice_id,
                TimeEntry.clock_in >= period_start,
            )
        ).order_by(TimeEntry.clock_in.desc())
    )
    entries = result.scalars().all()

    return [
        TimeEntryResponse(
            id=str(e.id),
            staff_id=str(e.staff_id),
            clock_in=e.clock_in,
            clock_out=e.clock_out,
            total_hours=float(e.total_hours) if e.total_hours else None,
            entry_type=e.entry_type,
            status=e.status,
            notes=e.notes,
            edited_by=str(e.edited_by) if e.edited_by else None,
            edited_at=e.edited_at,
        )
        for e in entries
    ]


# ── Staff Hours (Doctor/Manager) ─────────────────────────────────────────────

@router.get("/staff-hours")
async def staff_hours(
    start_date: date = Query(...),
    end_date: date = Query(...),
    user: dict = Depends(require_role("owner", "doctor", "office_manager")),
    db: AsyncSession = Depends(get_db),
) -> list[StaffHoursEntry]:
    """Get all staff hours for a date range, grouped by staff member."""
    practice_id = UUID(user["practice_id"])
    start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)

    # Get all entries in range for this practice
    result = await db.execute(
        select(TimeEntry, User.full_name).join(
            User, TimeEntry.staff_id == User.id
        ).where(
            and_(
                TimeEntry.practice_id == practice_id,
                TimeEntry.clock_in >= start_dt,
                TimeEntry.clock_in <= end_dt,
            )
        ).order_by(User.full_name, TimeEntry.clock_in.desc())
    )
    rows = result.all()

    # Group by staff
    staff_map: dict[str, StaffHoursEntry] = {}
    for entry, staff_name in rows:
        sid = str(entry.staff_id)
        if sid not in staff_map:
            staff_map[sid] = StaffHoursEntry(
                staff_id=sid,
                staff_name=staff_name or "Unknown",
                total_hours=0,
                entries=[],
            )
        te = TimeEntryResponse(
            id=str(entry.id),
            staff_id=sid,
            clock_in=entry.clock_in,
            clock_out=entry.clock_out,
            total_hours=float(entry.total_hours) if entry.total_hours else None,
            entry_type=entry.entry_type,
            status=entry.status,
            notes=entry.notes,
            edited_by=str(entry.edited_by) if entry.edited_by else None,
            edited_at=entry.edited_at,
        )
        staff_map[sid].entries.append(te)
        if entry.total_hours:
            staff_map[sid].total_hours += float(entry.total_hours)

    # Round totals
    for item in staff_map.values():
        item.total_hours = round(item.total_hours, 2)

    return list(staff_map.values())


# ── Payroll Summary (Doctor/Manager) ──────────────────────────────────────────

@router.get("/payroll-summary")
async def payroll_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    user: dict = Depends(require_role("owner", "doctor", "office_manager")),
    db: AsyncSession = Depends(get_db),
) -> list[PayrollSummaryEntry]:
    """Calculate pay for each staff member: hours × rate."""
    practice_id = UUID(user["practice_id"])
    start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)

    # Get total hours per staff in period
    hours_result = await db.execute(
        select(
            TimeEntry.staff_id,
            func.coalesce(func.sum(TimeEntry.total_hours), 0).label("total_hours"),
        ).where(
            and_(
                TimeEntry.practice_id == practice_id,
                TimeEntry.clock_in >= start_dt,
                TimeEntry.clock_in <= end_dt,
                TimeEntry.status.in_(["complete", "edited"]),
            )
        ).group_by(TimeEntry.staff_id)
    )
    hours_by_staff = {row.staff_id: float(row.total_hours) for row in hours_result.all()}

    if not hours_by_staff:
        return []

    # Get current pay rates for each staff member
    staff_ids = list(hours_by_staff.keys())
    rates_result = await db.execute(
        select(PayRate, User.full_name).join(
            User, PayRate.staff_id == User.id
        ).where(
            and_(
                PayRate.practice_id == practice_id,
                PayRate.staff_id.in_(staff_ids),
                PayRate.effective_date <= end_date,
                (PayRate.end_date.is_(None) | (PayRate.end_date >= start_date)),
            )
        ).order_by(PayRate.effective_date.desc())
    )

    # Use the most recent rate per staff member
    rate_map: dict[UUID, tuple[float, str, str]] = {}
    for rate, staff_name in rates_result.all():
        if rate.staff_id not in rate_map:
            rate_map[rate.staff_id] = (float(rate.hourly_rate), rate.worker_type, staff_name or "Unknown")

    summary = []
    for staff_id, hours in hours_by_staff.items():
        if staff_id in rate_map:
            rate_val, worker_type, name = rate_map[staff_id]
        else:
            # No rate configured — show 0
            rate_val, worker_type, name = 0.0, "permanent", "Unknown"
            # Try to get the name at least
            user_result = await db.execute(select(User.full_name).where(User.id == staff_id))
            user_name = user_result.scalar()
            if user_name:
                name = user_name

        pay = round(hours * rate_val, 2)
        summary.append(PayrollSummaryEntry(
            staff_id=str(staff_id),
            staff_name=name,
            hours=round(hours, 2),
            rate=rate_val,
            pay=pay,
            worker_type=worker_type,
        ))

    return sorted(summary, key=lambda x: x.staff_name)


# ── Edit Time Entry (Doctor/Manager) ─────────────────────────────────────────

@router.patch("/time-entries/{entry_id}")
async def edit_time_entry(
    entry_id: str,
    payload: EditTimeEntryRequest,
    user: dict = Depends(require_role("owner", "doctor", "office_manager")),
    db: AsyncSession = Depends(get_db),
) -> TimeEntryResponse:
    """Edit a time entry (correct clock in/out times). Logs edited_by."""
    practice_id = UUID(user["practice_id"])

    result = await db.execute(
        select(TimeEntry).where(
            and_(
                TimeEntry.id == UUID(entry_id),
                TimeEntry.practice_id == practice_id,
            )
        )
    )
    entry = result.scalars().first()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Time entry not found")

    # Apply edits
    if payload.clock_in is not None:
        entry.clock_in = payload.clock_in
    if payload.clock_out is not None:
        entry.clock_out = payload.clock_out
    if payload.entry_type is not None:
        if payload.entry_type not in ("regular", "overtime", "pto"):
            raise HTTPException(status_code=422, detail="entry_type must be regular, overtime, or pto")
        entry.entry_type = payload.entry_type
    if payload.notes is not None:
        entry.notes = payload.notes

    # Recalculate total hours if both clock_in and clock_out are set
    if entry.clock_in and entry.clock_out:
        delta = entry.clock_out - entry.clock_in
        entry.total_hours = Decimal(str(round(delta.total_seconds() / 3600, 2)))
        entry.status = "edited"

    entry.edited_by = UUID(user["user_id"])
    entry.edited_at = datetime.now(timezone.utc)

    await audit_log(
        db, user["practice_id"], user["user_id"],
        "time_entry.edit", "time_entry", entry_id,
        details=f"Edited by {user['role']}",
    )

    await db.commit()
    await db.refresh(entry)

    return TimeEntryResponse(
        id=str(entry.id),
        staff_id=str(entry.staff_id),
        clock_in=entry.clock_in,
        clock_out=entry.clock_out,
        total_hours=float(entry.total_hours) if entry.total_hours else None,
        entry_type=entry.entry_type,
        status=entry.status,
        notes=entry.notes,
        edited_by=str(entry.edited_by) if entry.edited_by else None,
        edited_at=entry.edited_at,
    )


# ── Pay Rates (Doctor/Manager) ────────────────────────────────────────────────

@router.post("/pay-rates", status_code=status.HTTP_201_CREATED)
async def set_pay_rate(
    payload: PayRateRequest,
    user: dict = Depends(require_role("owner", "doctor", "office_manager")),
    db: AsyncSession = Depends(get_db),
) -> PayRateResponse:
    """Set pay rate for a staff member."""
    practice_id = UUID(user["practice_id"])
    staff_id = UUID(payload.staff_id)

    # Verify staff belongs to this practice
    staff_result = await db.execute(
        select(User).where(and_(User.id == staff_id, User.practice_id == practice_id))
    )
    staff_user = staff_result.scalars().first()
    if not staff_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found in this practice")

    # End any existing open rate for this staff member
    existing_result = await db.execute(
        select(PayRate).where(
            and_(
                PayRate.practice_id == practice_id,
                PayRate.staff_id == staff_id,
                PayRate.end_date.is_(None),
            )
        )
    )
    existing_rate = existing_result.scalars().first()
    if existing_rate:
        existing_rate.end_date = payload.effective_date - timedelta(days=1)

    rate = PayRate(
        practice_id=practice_id,
        staff_id=staff_id,
        hourly_rate=payload.hourly_rate,
        worker_type=payload.worker_type,
        effective_date=payload.effective_date,
    )
    db.add(rate)

    await audit_log(
        db, user["practice_id"], user["user_id"],
        "pay_rate.set", "pay_rate", str(staff_id),
        details=f"Rate: {payload.hourly_rate}/hr, Type: {payload.worker_type}",
    )

    await db.commit()
    await db.refresh(rate)

    return PayRateResponse(
        id=str(rate.id),
        staff_id=str(rate.staff_id),
        staff_name=staff_user.full_name,
        hourly_rate=float(rate.hourly_rate),
        worker_type=rate.worker_type,
        effective_date=rate.effective_date,
        end_date=rate.end_date,
    )


@router.get("/pay-rates")
async def list_pay_rates(
    user: dict = Depends(require_role("owner", "doctor", "office_manager")),
    db: AsyncSession = Depends(get_db),
) -> list[PayRateResponse]:
    """List all active pay rates for the practice."""
    practice_id = UUID(user["practice_id"])

    result = await db.execute(
        select(PayRate, User.full_name).join(
            User, PayRate.staff_id == User.id
        ).where(
            and_(
                PayRate.practice_id == practice_id,
                PayRate.end_date.is_(None),
            )
        ).order_by(User.full_name)
    )

    return [
        PayRateResponse(
            id=str(rate.id),
            staff_id=str(rate.staff_id),
            staff_name=name or "Unknown",
            hourly_rate=float(rate.hourly_rate),
            worker_type=rate.worker_type,
            effective_date=rate.effective_date,
            end_date=rate.end_date,
        )
        for rate, name in result.all()
    ]


# ── Missed Punch Check (Internal) ────────────────────────────────────────────

@router.post("/missed-punch-check")
async def missed_punch_check(
    user: dict = Depends(require_role("owner", "doctor", "office_manager")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Check for missed punches (clocked in > 12 hours) and send SMS reminders."""
    from app.api.routes.comm_novu import send_notification

    practice_id = UUID(user["practice_id"])
    threshold = datetime.now(timezone.utc) - timedelta(hours=12)

    result = await db.execute(
        select(TimeEntry, User.full_name, User.id).join(
            User, TimeEntry.staff_id == User.id
        ).where(
            and_(
                TimeEntry.practice_id == practice_id,
                TimeEntry.status == "clocked_in",
                TimeEntry.clock_in < threshold,
            )
        )
    )
    missed = result.all()

    notifications_sent = 0
    for entry, staff_name, staff_user_id in missed:
        entry.status = "missed"
        try:
            await send_notification(
                str(staff_user_id),
                "missed-punch-reminder",
                {
                    "staff_name": staff_name or "Team member",
                    "clock_in_time": entry.clock_in.strftime("%I:%M %p"),
                    "clock_in_date": entry.clock_in.strftime("%m/%d/%Y"),
                },
            )
            notifications_sent += 1
        except Exception as e:
            logger.error(f"Failed to send missed punch notification to {staff_user_id}: {e}")

    await db.commit()

    logger.info(f"Missed punch check: {len(missed)} found, {notifications_sent} notifications sent")
    return {
        "missed_entries": len(missed),
        "notifications_sent": notifications_sent,
    }
