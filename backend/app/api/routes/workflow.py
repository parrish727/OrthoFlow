"""OrthoFlow API — Sprint 2 Workflow Routes.

Visit tracker, recent patient searches, patient documents,
schedule popup, and appointment compliance endpoints.
All endpoints are practice-scoped via JWT.
"""
import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.audit import audit_log
from app.core.database import get_db
from app.models.clinical import Patient, Appointment, AppointmentStatus
from app.models.workflow import PatientVisitStatus, RecentPatientSearch, PatientDocument, DocumentNotification
from app.services import documents as doc_storage
from app.services.document_exchange import scan_store_and_record

router = APIRouter(prefix="/api/v1", tags=["workflow"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class VisitStatusResponse(BaseModel):
    id: str
    patient_id: str
    appointment_id: str
    status: str
    chair_id: str | None = None
    checked_in_at: str | None = None
    seated_at: str | None = None
    checked_out_at: str | None = None
    created_at: str
    patient_name: str | None = None


class VisitStatusCreate(BaseModel):
    patient_id: str = Field(..., description="Patient UUID")
    appointment_id: str = Field(..., description="Appointment UUID")
    chair_id: str | None = None


class VisitStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(lobby|seated|checked_out|dismissed)$")
    chair_id: str | None = None


class RecentSearchResponse(BaseModel):
    patient_id: str
    first_name: str
    last_name: str
    searched_at: str


class RecentSearchCreate(BaseModel):
    patient_id: str = Field(..., description="Patient UUID")


class DocumentResponse(BaseModel):
    id: str
    patient_id: str
    document_type: str
    title: str
    file_url: str | None = None
    original_filename: str | None = None
    file_size_bytes: int | None = None
    mime_type: str | None = None
    uploaded_by: str | None = None
    uploaded_by_type: str = "staff"
    direction: str = "office_to_patient"
    notes: str | None = None
    created_at: str


def _document_response(doc: PatientDocument) -> "DocumentResponse":
    return DocumentResponse(
        id=str(doc.id),
        patient_id=str(doc.patient_id),
        document_type=doc.document_type,
        title=doc.title,
        file_url=doc.file_url,
        original_filename=doc.original_filename,
        file_size_bytes=doc.file_size_bytes,
        mime_type=doc.mime_type,
        uploaded_by=str(doc.uploaded_by) if doc.uploaded_by else None,
        uploaded_by_type=doc.uploaded_by_type,
        direction=doc.direction,
        notes=doc.notes,
        created_at=_ts(doc.created_at),
    )


class DocumentCreate(BaseModel):
    document_type: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=255)
    file_url: str | None = Field(None, max_length=512)
    file_size_bytes: int | None = None
    mime_type: str | None = Field(None, max_length=100)
    notes: str | None = None


class PatientPopupResponse(BaseModel):
    patient_id: str
    first_name: str
    last_name: str
    date_of_birth: str | None = None
    status: str
    chart_number: str
    treatment_phase: str


class AppointmentComplianceResponse(BaseModel):
    patient_id: str
    total_scheduled: int
    completed: int
    no_shows: int
    cancelled: int
    compliance_rate: float


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ts(dt: datetime | None) -> str | None:
    """Convert datetime to ISO string or None."""
    return dt.isoformat() if dt else None


VALID_STATUS_TRANSITIONS = {
    "lobby": ["seated", "checked_out", "dismissed"],
    "seated": ["lobby", "checked_out", "dismissed"],
    "checked_out": ["seated", "lobby", "dismissed"],
    "dismissed": ["lobby", "seated", "checked_out"],
}


# ── Visit Tracker ─────────────────────────────────────────────────────────────

@router.get("/visit-tracker", response_model=list[VisitStatusResponse])
async def list_visit_statuses(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List today's patient visit statuses for the practice."""
    today_start = datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc)
    today_end = datetime.combine(date.today(), datetime.max.time(), tzinfo=timezone.utc)

    query = (
        select(PatientVisitStatus, Patient.first_name, Patient.last_name)
        .join(Patient, Patient.id == PatientVisitStatus.patient_id)
        .where(
            and_(
                PatientVisitStatus.practice_id == user["practice_id"],
                PatientVisitStatus.created_at >= today_start,
                PatientVisitStatus.created_at <= today_end,
            )
        )
        .order_by(PatientVisitStatus.created_at.desc())
    )
    result = await db.execute(query)
    rows = result.all()

    return [
        VisitStatusResponse(
            id=str(row.PatientVisitStatus.id),
            patient_id=str(row.PatientVisitStatus.patient_id),
            appointment_id=str(row.PatientVisitStatus.appointment_id),
            status=row.PatientVisitStatus.status,
            chair_id=str(row.PatientVisitStatus.chair_id) if row.PatientVisitStatus.chair_id else None,
            checked_in_at=_ts(row.PatientVisitStatus.checked_in_at),
            seated_at=_ts(row.PatientVisitStatus.seated_at),
            checked_out_at=_ts(row.PatientVisitStatus.checked_out_at),
            created_at=_ts(row.PatientVisitStatus.created_at),
            patient_name=f"{row.first_name} {row.last_name}",
        )
        for row in rows
    ]


@router.post("/visit-tracker", response_model=VisitStatusResponse, status_code=status.HTTP_201_CREATED)
async def create_visit_status(
    payload: VisitStatusCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check in a patient — creates a visit status record."""
    now = datetime.now(timezone.utc)
    visit = PatientVisitStatus(
        id=uuid.uuid4(),
        practice_id=uuid.UUID(user["practice_id"]),
        patient_id=uuid.UUID(payload.patient_id),
        appointment_id=uuid.UUID(payload.appointment_id),
        status="lobby",
        chair_id=uuid.UUID(payload.chair_id) if payload.chair_id else None,
        checked_in_at=now,
        created_at=now,
    )
    db.add(visit)
    await db.commit()
    await db.refresh(visit)

    await audit_log(db, user["practice_id"], user["user_id"], "patient_check_in", "patient_visit_status", str(visit.id))

    return VisitStatusResponse(
        id=str(visit.id),
        patient_id=str(visit.patient_id),
        appointment_id=str(visit.appointment_id),
        status=visit.status,
        chair_id=str(visit.chair_id) if visit.chair_id else None,
        checked_in_at=_ts(visit.checked_in_at),
        seated_at=_ts(visit.seated_at),
        checked_out_at=_ts(visit.checked_out_at),
        created_at=_ts(visit.created_at),
    )


@router.patch("/visit-tracker/{visit_id}/status", response_model=VisitStatusResponse)
async def update_visit_status(
    visit_id: str,
    payload: VisitStatusUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update visit status with automatic timestamp management."""
    result = await db.execute(
        select(PatientVisitStatus).where(
            and_(
                PatientVisitStatus.id == uuid.UUID(visit_id),
                PatientVisitStatus.practice_id == user["practice_id"],
            )
        )
    )
    visit = result.scalar_one_or_none()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit status not found")

    # Validate transition
    allowed = VALID_STATUS_TRANSITIONS.get(visit.status, [])
    if payload.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from '{visit.status}' to '{payload.status}'. Allowed: {allowed}",
        )

    now = datetime.now(timezone.utc)
    visit.status = payload.status

    # Set timestamps based on new status
    if payload.status == "seated":
        visit.seated_at = now
        if payload.chair_id:
            visit.chair_id = uuid.UUID(payload.chair_id)
    elif payload.status == "checked_out":
        visit.checked_out_at = now
    elif payload.status == "dismissed":
        if not visit.checked_out_at:
            visit.checked_out_at = now

    # Allow chair assignment on any transition
    if payload.chair_id and payload.status != "seated":
        visit.chair_id = uuid.UUID(payload.chair_id)

    await db.commit()
    await db.refresh(visit)

    await audit_log(db, user["practice_id"], user["user_id"], "visit_status_update", "patient_visit_status", str(visit.id))

    return VisitStatusResponse(
        id=str(visit.id),
        patient_id=str(visit.patient_id),
        appointment_id=str(visit.appointment_id),
        status=visit.status,
        chair_id=str(visit.chair_id) if visit.chair_id else None,
        checked_in_at=_ts(visit.checked_in_at),
        seated_at=_ts(visit.seated_at),
        checked_out_at=_ts(visit.checked_out_at),
        created_at=_ts(visit.created_at),
    )


# ── Recent Patient Searches ───────────────────────────────────────────────────

@router.get("/recent-searches", response_model=list[RecentSearchResponse])
async def list_recent_searches(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's last 10 recently searched patients."""
    query = (
        select(RecentPatientSearch, Patient.first_name, Patient.last_name)
        .join(Patient, Patient.id == RecentPatientSearch.patient_id)
        .where(RecentPatientSearch.user_id == user["user_id"])
        .order_by(RecentPatientSearch.searched_at.desc())
        .limit(10)
    )
    result = await db.execute(query)
    rows = result.all()

    return [
        RecentSearchResponse(
            patient_id=str(row.RecentPatientSearch.patient_id),
            first_name=row.first_name,
            last_name=row.last_name,
            searched_at=_ts(row.RecentPatientSearch.searched_at),
        )
        for row in rows
    ]


@router.post("/recent-searches", status_code=status.HTTP_201_CREATED)
async def log_recent_search(
    payload: RecentSearchCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Log a patient search. Upserts — updates searched_at if already exists."""
    patient_uuid = uuid.UUID(payload.patient_id)

    # Check if entry already exists for this user+patient
    existing = await db.execute(
        select(RecentPatientSearch).where(
            and_(
                RecentPatientSearch.user_id == user["user_id"],
                RecentPatientSearch.patient_id == patient_uuid,
            )
        )
    )
    record = existing.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if record:
        record.searched_at = now
    else:
        record = RecentPatientSearch(
            id=uuid.uuid4(),
            practice_id=uuid.UUID(user["practice_id"]),
            user_id=uuid.UUID(user["user_id"]),
            patient_id=patient_uuid,
            searched_at=now,
        )
        db.add(record)

    await db.commit()
    return {"status": "ok"}


# ── Patient Documents ─────────────────────────────────────────────────────────

@router.get("/patients/{patient_id}/documents", response_model=list[DocumentResponse])
async def list_patient_documents(
    patient_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all documents for a patient (both office-uploaded and patient-uploaded)."""
    query = (
        select(PatientDocument)
        .where(
            and_(
                PatientDocument.patient_id == uuid.UUID(patient_id),
                PatientDocument.practice_id == user["practice_id"],
            )
        )
        .order_by(PatientDocument.created_at.desc())
    )
    result = await db.execute(query)
    docs = result.scalars().all()
    return [_document_response(doc) for doc in docs]


@router.post("/patients/{patient_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_patient_document(
    patient_id: str,
    file: UploadFile = File(...),
    document_type: str = Form(...),
    title: str = Form(...),
    notes: str | None = Form(None),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Office uploads a real file for a patient (office → patient).

    Flow: ClamAV scan (fail-closed) → store in the private MinIO documents bucket → create the
    single PatientDocument row → notify the patient (MyOrthoChart feed) → email the patient.
    """
    practice_uuid = uuid.UUID(user["practice_id"])
    patient_uuid = uuid.UUID(patient_id)

    # Patient must belong to this practice.
    patient = (await db.execute(
        select(Patient).where(Patient.id == patient_uuid, Patient.practice_id == practice_uuid)
    )).scalar_one_or_none()
    if not patient:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")

    # Idempotency guard: block an accidental double-submit (same patient + type + title in 60s).
    from datetime import timedelta as _td
    recent = (await db.execute(
        select(PatientDocument).where(
            PatientDocument.practice_id == practice_uuid,
            PatientDocument.patient_id == patient_uuid,
            PatientDocument.document_type == document_type,
            PatientDocument.title == title,
            PatientDocument.created_at >= datetime.now(timezone.utc) - _td(seconds=60),
        ).limit(1)
    )).scalar_one_or_none()
    if recent is not None:
        return _document_response(recent)

    content = await file.read()
    doc = await scan_store_and_record(
        db=db,
        practice_id=practice_uuid,
        patient_id=patient_uuid,
        content=content,
        filename=file.filename or "upload",
        content_type=file.content_type,
        document_type=document_type,
        title=title,
        direction="office_to_patient",
        uploaded_by_type="staff",
        uploaded_by=uuid.UUID(user["user_id"]),
        notes=notes,
    )

    await audit_log(db, user["practice_id"], user["user_id"], "document_upload", "patient_documents", str(doc.id))
    return _document_response(doc)


@router.get("/patients/{patient_id}/documents/{document_id}/download")
async def download_patient_document(
    patient_id: str,
    document_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return a short-lived presigned URL for a document (staff, scoped to their practice)."""
    doc = (await db.execute(
        select(PatientDocument).where(
            PatientDocument.id == uuid.UUID(document_id),
            PatientDocument.patient_id == uuid.UUID(patient_id),
            PatientDocument.practice_id == uuid.UUID(user["practice_id"]),
        )
    )).scalar_one_or_none()
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    if not doc.storage_key:
        # Legacy row with only an external file_url.
        return {"url": doc.file_url}

    url = await doc_storage.issue_download_url(doc.storage_key, download_name=doc.original_filename or doc.title)
    await audit_log(db, user["practice_id"], user["user_id"], "document_download", "patient_documents", str(doc.id))
    return {"url": url, "expires_in": doc_storage.PRESIGN_EXPIRY_SECONDS}


@router.post("/patients/{patient_id}/documents/reference", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document_reference(
    patient_id: str,
    payload: DocumentCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a metadata-only / reference document record (NO file upload).

    For INTERNAL, server-originated records such as archived TC proposals, where the "document" is
    a reference/summary rather than a user-uploaded file. Real file uploads use the multipart
    POST .../documents endpoint (scan + MinIO). Keeps the 60s idempotency guard; shared with the
    patient by default so it appears in MyOrthoChart like other chart documents.
    """
    practice_uuid = uuid.UUID(user["practice_id"])
    patient_uuid = uuid.UUID(patient_id)
    from datetime import timedelta as _td
    recent = (await db.execute(
        select(PatientDocument).where(
            PatientDocument.practice_id == practice_uuid,
            PatientDocument.patient_id == patient_uuid,
            PatientDocument.document_type == payload.document_type,
            PatientDocument.title == payload.title,
            PatientDocument.created_at >= datetime.now(timezone.utc) - _td(seconds=60),
        ).limit(1)
    )).scalar_one_or_none()
    if recent is not None:
        return _document_response(recent)

    doc = PatientDocument(
        id=uuid.uuid4(),
        practice_id=practice_uuid,
        patient_id=patient_uuid,
        document_type=payload.document_type,
        title=payload.title,
        file_url=payload.file_url,
        file_size_bytes=payload.file_size_bytes,
        mime_type=payload.mime_type,
        uploaded_by=uuid.UUID(user["user_id"]),
        uploaded_by_type="staff",
        direction="office_to_patient",
        shared_with_patient=True,
        scan_status="clean",
        notes=payload.notes,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    await audit_log(db, user["practice_id"], user["user_id"], "document_reference", "patient_documents", str(doc.id))
    return _document_response(doc)


@router.get("/document-notifications")
async def list_office_document_notifications(
    patient_id: str | None = Query(None),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Office-audience document notifications (patient → office uploads) + unread count.

    Optionally filter to a single patient (used on the patient detail page).
    """
    conditions = [
        DocumentNotification.practice_id == uuid.UUID(user["practice_id"]),
        DocumentNotification.audience == "office",
    ]
    if patient_id:
        conditions.append(DocumentNotification.patient_id == uuid.UUID(patient_id))
    rows = (await db.execute(
        select(DocumentNotification).where(and_(*conditions))
        .order_by(DocumentNotification.created_at.desc()).limit(50)
    )).scalars().all()
    return {
        "unread": sum(1 for n in rows if not n.is_read),
        "notifications": [
            {
                "id": str(n.id),
                "patient_id": str(n.patient_id),
                "document_id": str(n.document_id),
                "title": n.title,
                "body": n.body,
                "action_url": n.action_url,
                "is_read": n.is_read,
                "created_at": _ts(n.created_at),
            }
            for n in rows
        ],
    }


@router.patch("/document-notifications/{notification_id}/read")
async def mark_office_document_notification_read(
    notification_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    n = (await db.execute(
        select(DocumentNotification).where(
            DocumentNotification.id == uuid.UUID(notification_id),
            DocumentNotification.practice_id == uuid.UUID(user["practice_id"]),
            DocumentNotification.audience == "office",
        )
    )).scalar_one_or_none()
    if not n:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
    n.is_read = True
    await db.commit()
    return {"status": "ok"}


# ── Schedule Patient Popup ────────────────────────────────────────────────────

@router.get("/schedule/patient-popup/{patient_id}", response_model=PatientPopupResponse)
async def get_patient_popup(
    patient_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Quick-view patient info for the schedule popup card."""
    result = await db.execute(
        select(Patient).where(
            and_(
                Patient.id == uuid.UUID(patient_id),
                Patient.practice_id == user["practice_id"],
            )
        )
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    return PatientPopupResponse(
        patient_id=str(patient.id),
        first_name=patient.first_name,
        last_name=patient.last_name,
        date_of_birth=patient.date_of_birth.isoformat() if patient.date_of_birth else None,
        status=patient.status,
        chart_number=str(patient.id)[:8].upper(),
        treatment_phase=patient.treatment_phase,
    )


# ── Appointment Compliance ────────────────────────────────────────────────────

@router.get("/patients/{patient_id}/appointment-compliance", response_model=AppointmentComplianceResponse)
async def get_appointment_compliance(
    patient_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return appointment keeping statistics for a patient."""
    patient_uuid = uuid.UUID(patient_id)

    result = await db.execute(
        select(
            func.count(Appointment.id).label("total"),
            func.count(case((Appointment.status == AppointmentStatus.completed, 1))).label("completed"),
            func.count(case((Appointment.status == AppointmentStatus.no_show, 1))).label("no_shows"),
            func.count(case((Appointment.status == AppointmentStatus.cancelled, 1))).label("cancelled"),
        ).where(
            and_(
                Appointment.patient_id == patient_uuid,
                Appointment.practice_id == user["practice_id"],
            )
        )
    )
    row = result.one()
    total = row.total or 0
    completed = row.completed or 0
    no_shows = row.no_shows or 0
    cancelled = row.cancelled or 0

    # Compliance = completed / (total - cancelled) if any non-cancelled exist
    denominator = total - cancelled
    compliance_rate = round((completed / denominator * 100), 1) if denominator > 0 else 0.0

    return AppointmentComplianceResponse(
        patient_id=patient_id,
        total_scheduled=total,
        completed=completed,
        no_shows=no_shows,
        cancelled=cancelled,
        compliance_rate=compliance_rate,
    )
