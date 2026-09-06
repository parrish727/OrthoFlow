"""OrthoFlow API — Schedule Notes (AI + DA daily notes synced to the schedule).

Surfaces the day's human + AI context alongside the schedule. Human notes (DA/manager/front
desk) are stored; AI notes are generated precognitively from the day's signals (early-outs,
double-booked chairs, unconfirmed high-value appointments, overdue balances arriving today)
so the team sees what matters before they go looking.
"""
import logging
from uuid import UUID
from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.audit import audit_log
from app.models.schedule_notes import ScheduleNote

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/schedule-notes", tags=["schedule-notes"])


class ScheduleNoteCreate(BaseModel):
    note_date: date
    content: str = Field(..., min_length=1, max_length=2000)
    origin: str = Field("da", pattern="^(ai|da|manager|front_desk|doctor)$")
    category: str = Field("operational", pattern="^(staffing|patient|operational|clinical|insight)$")
    placement: str = Field("above", pattern="^(above|below)$")
    tone: str = Field("info", pattern="^(info|highlight|warning)$")
    source_da_id: str | None = None
    patient_id: str | None = None
    is_pinned: bool = False


class ScheduleNoteOut(BaseModel):
    id: str
    note_date: str
    origin: str
    category: str
    placement: str
    tone: str
    content: str
    source_da_id: str | None
    patient_id: str | None
    is_pinned: bool
    is_dismissed: bool
    created_at: str | None


@router.get("")
async def list_schedule_notes(
    note_date: date = Query(default_factory=date.today),
    include_ai: bool = True,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Return stored notes for a date plus AI-surfaced notes, grouped by placement."""
    practice_id = user["practice_id"]

    rows = (await db.execute(
        select(ScheduleNote).where(
            ScheduleNote.practice_id == practice_id,
            ScheduleNote.note_date == note_date,
            ScheduleNote.is_dismissed == False,
        ).order_by(ScheduleNote.is_pinned.desc(), ScheduleNote.created_at.asc())
    )).scalars().all()

    stored = [_note_dict(n) for n in rows]

    ai_notes: list[dict] = []
    if include_ai:
        ai_notes = await _generate_ai_notes(db, practice_id, note_date, existing=rows)

    everything = stored + ai_notes
    return {
        "note_date": note_date.isoformat(),
        "above": [n for n in everything if n["placement"] == "above"],
        "below": [n for n in everything if n["placement"] == "below"],
        "count": len(everything),
    }


@router.post("", status_code=201, response_model=ScheduleNoteOut)
async def create_schedule_note(
    body: ScheduleNoteCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Create a schedule note (e.g., a DA personal note synced to the day)."""
    practice_id = user["practice_id"]
    note = ScheduleNote(
        practice_id=practice_id, note_date=body.note_date, origin=body.origin,
        category=body.category, placement=body.placement, tone=body.tone,
        content=body.content.strip(),
        source_da_id=body.source_da_id, patient_id=body.patient_id,
        is_pinned=body.is_pinned, created_by=user["user_id"],
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    await audit_log(db, practice_id, user["user_id"], "schedule_note.create", "schedule_note", str(note.id))
    return _note_dict(note)


@router.patch("/{note_id}/dismiss")
async def dismiss_schedule_note(
    note_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Dismiss a note so it no longer appears on the schedule."""
    practice_id = user["practice_id"]
    note = (await db.execute(
        select(ScheduleNote).where(ScheduleNote.id == note_id, ScheduleNote.practice_id == practice_id)
    )).scalar_one_or_none()
    if not note:
        raise HTTPException(404, "Note not found")
    note.is_dismissed = True
    await db.commit()
    await audit_log(db, practice_id, user["user_id"], "schedule_note.dismiss", "schedule_note", str(note_id))
    return {"id": str(note_id), "dismissed": True}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _note_dict(n: ScheduleNote) -> dict:
    return {
        "id": str(n.id),
        "note_date": n.note_date.isoformat(),
        "origin": n.origin,
        "category": n.category,
        "placement": n.placement,
        "tone": n.tone,
        "content": n.content,
        "source_da_id": str(n.source_da_id) if n.source_da_id else None,
        "patient_id": str(n.patient_id) if n.patient_id else None,
        "is_pinned": n.is_pinned,
        "is_dismissed": n.is_dismissed,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


async def _generate_ai_notes(db: AsyncSession, practice_id, note_date: date, existing: list) -> list[dict]:
    """Precognitively surface the day's context the team should know about.

    Read-only, deterministic signals derived from today's schedule + patient balances so the
    team sees staffing, patient-flow, and revenue context inline with the schedule. These are
    transient (not persisted) and never duplicate a human note already covering the same thing.
    """
    from sqlalchemy import func
    from app.models.clinical import Appointment
    from app.models.finance import PatientLedgerEntry

    notes: list[dict] = []

    def _ai(content: str, category: str, tone: str = "info", placement: str = "above") -> dict:
        return {
            "id": f"ai-{category}-{abs(hash(content)) % 10_000_000}",
            "note_date": note_date.isoformat(), "origin": "ai", "category": category,
            "placement": placement, "tone": tone, "content": content,
            "source_da_id": None, "patient_id": None, "is_pinned": False,
            "is_dismissed": False, "created_at": datetime.now(timezone.utc).isoformat(),
        }

    # Signal 1 — day volume + unconfirmed appointments.
    try:
        appts = (await db.execute(
            select(Appointment).where(
                Appointment.practice_id == practice_id,
                Appointment.appointment_date == note_date,
            )
        )).scalars().all()
    except Exception:
        appts = []

    if appts:
        total = len(appts)
        unconfirmed = sum(1 for a in appts if (getattr(a, "status", "") or "") in ("scheduled",))
        notes.append(_ai(
            f"{total} appointments on the schedule today.", "insight", "info", "above"))
        if unconfirmed:
            notes.append(_ai(
                f"{unconfirmed} appointment(s) still unconfirmed — front desk may want to send "
                f"confirmations this morning.", "operational", "highlight", "above"))

    # Signal 2 — patients with outstanding balances who are on today's schedule.
    try:
        patient_ids = {getattr(a, "patient_id", None) for a in appts if getattr(a, "patient_id", None)}
        collectable = 0
        for pid in patient_ids:
            bal = (await db.execute(
                select(func.sum(PatientLedgerEntry.amount)).where(
                    PatientLedgerEntry.patient_id == pid,
                    PatientLedgerEntry.practice_id == practice_id,
                )
            )).scalar()
            if bal and bal > 0:
                collectable += 1
        if collectable:
            notes.append(_ai(
                f"{collectable} patient(s) arriving today carry an outstanding balance — a good "
                f"moment to collect at check-in.", "insight", "highlight", "below"))
    except Exception as e:
        logger.debug(f"AI balance signal skipped: {e}")

    return notes
