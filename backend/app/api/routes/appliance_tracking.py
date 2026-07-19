"""
OrthoFlow AI — Lab Appliance Tracking API Routes (Sprint 4)
Full lifecycle management: labs, prescriptions, status updates, overdue alerts, quality metrics.
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.models import User
from app.models.appliance_tracking import (
    Lab,
    AppliancePrescription,
    ApplianceStatusHistory,
    EasyRxIntegration,
    ApplianceType,
    ApplianceStatus,
    Arch,
)

router = APIRouter(prefix="/api/appliances", tags=["appliance-tracking"])


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

# -- Lab schemas --

class LabCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    website: str | None = None
    account_number: str | None = None
    avg_turnaround_days: int = Field(default=10, ge=1, le=90)
    notes: str | None = None


class LabUpdate(BaseModel):
    name: str | None = None
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    website: str | None = None
    account_number: str | None = None
    avg_turnaround_days: int | None = Field(default=None, ge=1, le=90)
    notes: str | None = None
    is_active: bool | None = None


class LabResponse(BaseModel):
    id: str
    name: str
    contact_name: str | None
    phone: str | None
    email: str | None
    address: str | None
    website: str | None
    account_number: str | None
    avg_turnaround_days: int
    notes: str | None
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}


# -- Prescription schemas --

class PrescriptionCreate(BaseModel):
    patient_id: str
    lab_id: str
    appliance_type: str
    appliance_name: str = Field(..., min_length=1, max_length=255)
    arch: str
    teeth: str | None = None
    color: str | None = None
    material: str | None = None
    rx_notes: str | None = None
    special_instructions: str | None = None
    scan_file_url: str | None = None
    priority: str = "normal"
    lab_fee: float | None = None
    rush_fee: float | None = None


class StatusUpdate(BaseModel):
    status: str
    notes: str | None = None
    tracking_number: str | None = None
    lab_case_number: str | None = None


class PrescriptionResponse(BaseModel):
    id: str
    patient_id: str
    lab_id: str
    lab_name: str | None = None
    prescribed_by: str
    appliance_type: str
    appliance_name: str
    arch: str
    teeth: str | None
    color: str | None
    material: str | None
    rx_notes: str | None
    special_instructions: str | None
    scan_file_url: str | None
    status: str
    priority: str
    date_prescribed: str
    date_sent_to_lab: str | None
    date_received_by_lab: str | None
    date_shipped: str | None
    date_received: str | None
    date_placed: str | None
    expected_delivery_date: str | None
    tracking_number: str | None
    lab_case_number: str | None
    is_remake: bool
    remake_reason: str | None
    lab_fee: float | None
    rush_fee: float | None
    created_at: str

    model_config = {"from_attributes": True}


class QualityMetrics(BaseModel):
    lab_id: str
    lab_name: str
    total_orders: int
    completed_orders: int
    remake_count: int
    remake_rate: float
    avg_turnaround_actual: float | None
    on_time_rate: float
    total_spend: float


# ═══════════════════════════════════════════════════════════════════════════════
# LAB CRUD ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/labs", response_model=list[LabResponse])
async def list_labs(
    active_only: bool = Query(True),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LabResponse]:
    """List all labs for the practice."""
    query = select(Lab).where(Lab.practice_id == user.practice_id)
    if active_only:
        query = query.where(Lab.is_active.is_(True))
    query = query.order_by(Lab.name)

    result = await db.execute(query)
    labs = result.scalars().all()
    return [_lab_to_response(lab) for lab in labs]


@router.post("/labs", status_code=status.HTTP_201_CREATED, response_model=LabResponse)
async def create_lab(
    payload: LabCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LabResponse:
    """Add a new lab vendor."""
    lab = Lab(
        practice_id=user.practice_id,
        **payload.model_dump(),
    )
    db.add(lab)
    await db.commit()
    await db.refresh(lab)
    return _lab_to_response(lab)


@router.patch("/labs/{lab_id}", response_model=LabResponse)
async def update_lab(
    lab_id: str,
    payload: LabUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LabResponse:
    """Update a lab vendor."""
    lab = await _get_lab(db, lab_id, user.practice_id)
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(lab, key, value)
    await db.commit()
    await db.refresh(lab)
    return _lab_to_response(lab)


@router.get("/labs/{lab_id}/metrics", response_model=QualityMetrics)
async def get_lab_quality_metrics(
    lab_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QualityMetrics:
    """Get quality metrics for a specific lab."""
    lab = await _get_lab(db, lab_id, user.practice_id)
    return await _calculate_lab_metrics(db, lab)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

async def _get_lab(db: AsyncSession, lab_id: str, practice_id: uuid.UUID) -> Lab:
    """Fetch lab by ID with practice scoping."""
    result = await db.execute(
        select(Lab).where(Lab.id == uuid.UUID(lab_id), Lab.practice_id == practice_id)
    )
    lab = result.scalar_one_or_none()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")
    return lab


def _lab_to_response(lab: Lab) -> LabResponse:
    return LabResponse(
        id=str(lab.id),
        name=lab.name,
        contact_name=lab.contact_name,
        phone=lab.phone,
        email=lab.email,
        address=lab.address,
        website=lab.website,
        account_number=lab.account_number,
        avg_turnaround_days=lab.avg_turnaround_days,
        notes=lab.notes,
        is_active=lab.is_active,
        created_at=lab.created_at.isoformat() if lab.created_at else "",
    )


async def _calculate_lab_metrics(db: AsyncSession, lab: Lab) -> QualityMetrics:
    """Calculate quality metrics for a lab."""
    # Total orders
    total_q = await db.execute(
        select(func.count(AppliancePrescription.id)).where(
            AppliancePrescription.lab_id == lab.id
        )
    )
    total_orders = total_q.scalar() or 0

    # Completed (placed)
    completed_q = await db.execute(
        select(func.count(AppliancePrescription.id)).where(
            AppliancePrescription.lab_id == lab.id,
            AppliancePrescription.status == "placed",
        )
    )
    completed_orders = completed_q.scalar() or 0

    # Remakes
    remake_q = await db.execute(
        select(func.count(AppliancePrescription.id)).where(
            AppliancePrescription.lab_id == lab.id,
            AppliancePrescription.is_remake.is_(True),
        )
    )
    remake_count = remake_q.scalar() or 0
    remake_rate = (remake_count / total_orders * 100) if total_orders > 0 else 0.0

    # Average turnaround (sent to lab → received by practice)
    turnaround_q = await db.execute(
        select(
            func.avg(
                func.extract("epoch", AppliancePrescription.date_received)
                - func.extract("epoch", AppliancePrescription.date_sent_to_lab)
            ) / 86400  # Convert seconds to days
        ).where(
            AppliancePrescription.lab_id == lab.id,
            AppliancePrescription.date_sent_to_lab.isnot(None),
            AppliancePrescription.date_received.isnot(None),
        )
    )
    avg_turnaround_actual = turnaround_q.scalar()

    # On-time rate
    on_time_q = await db.execute(
        select(func.count(AppliancePrescription.id)).where(
            AppliancePrescription.lab_id == lab.id,
            AppliancePrescription.date_received.isnot(None),
            AppliancePrescription.expected_delivery_date.isnot(None),
            AppliancePrescription.date_received <= AppliancePrescription.expected_delivery_date,
        )
    )
    on_time_count = on_time_q.scalar() or 0

    delivered_q = await db.execute(
        select(func.count(AppliancePrescription.id)).where(
            AppliancePrescription.lab_id == lab.id,
            AppliancePrescription.date_received.isnot(None),
            AppliancePrescription.expected_delivery_date.isnot(None),
        )
    )
    delivered_count = delivered_q.scalar() or 0
    on_time_rate = (on_time_count / delivered_count * 100) if delivered_count > 0 else 100.0

    # Total spend
    spend_q = await db.execute(
        select(
            func.coalesce(func.sum(AppliancePrescription.lab_fee), 0)
            + func.coalesce(func.sum(AppliancePrescription.rush_fee), 0)
        ).where(AppliancePrescription.lab_id == lab.id)
    )
    total_spend = float(spend_q.scalar() or 0)

    return QualityMetrics(
        lab_id=str(lab.id),
        lab_name=lab.name,
        total_orders=total_orders,
        completed_orders=completed_orders,
        remake_count=remake_count,
        remake_rate=round(remake_rate, 1),
        avg_turnaround_actual=round(avg_turnaround_actual, 1) if avg_turnaround_actual else None,
        on_time_rate=round(on_time_rate, 1),
        total_spend=round(total_spend, 2),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PRESCRIPTION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/prescriptions", response_model=list[PrescriptionResponse])
async def list_prescriptions(
    status_filter: str | None = Query(None, alias="status"),
    patient_id: str | None = None,
    lab_id: str | None = None,
    appliance_type: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PrescriptionResponse]:
    """List appliance prescriptions with filters."""
    query = select(AppliancePrescription).where(
        AppliancePrescription.practice_id == user.practice_id
    )

    if status_filter:
        query = query.where(AppliancePrescription.status == status_filter)
    if patient_id:
        query = query.where(AppliancePrescription.patient_id == uuid.UUID(patient_id))
    if lab_id:
        query = query.where(AppliancePrescription.lab_id == uuid.UUID(lab_id))
    if appliance_type:
        query = query.where(AppliancePrescription.appliance_type == appliance_type)

    query = query.order_by(AppliancePrescription.created_at.desc())
    result = await db.execute(query)
    prescriptions = result.scalars().all()

    # Fetch lab names for display
    lab_ids = {p.lab_id for p in prescriptions}
    lab_names: dict[uuid.UUID, str] = {}
    if lab_ids:
        labs_result = await db.execute(select(Lab).where(Lab.id.in_(lab_ids)))
        for lab in labs_result.scalars().all():
            lab_names[lab.id] = lab.name

    return [_rx_to_response(p, lab_names.get(p.lab_id)) for p in prescriptions]


@router.post("/prescriptions", status_code=status.HTTP_201_CREATED, response_model=PrescriptionResponse)
async def create_prescription(
    payload: PrescriptionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PrescriptionResponse:
    """Create a new appliance prescription."""
    # Validate lab belongs to practice
    lab = await _get_lab(db, payload.lab_id, user.practice_id)

    # Calculate expected delivery date from lab avg turnaround
    today = date.today()
    expected = today + timedelta(days=lab.avg_turnaround_days)

    rx = AppliancePrescription(
        practice_id=user.practice_id,
        patient_id=uuid.UUID(payload.patient_id),
        lab_id=uuid.UUID(payload.lab_id),
        prescribed_by=user.id,
        appliance_type=payload.appliance_type,
        appliance_name=payload.appliance_name,
        arch=payload.arch,
        teeth=payload.teeth,
        color=payload.color,
        material=payload.material,
        rx_notes=payload.rx_notes,
        special_instructions=payload.special_instructions,
        scan_file_url=payload.scan_file_url,
        priority=payload.priority,
        lab_fee=payload.lab_fee,
        rush_fee=payload.rush_fee,
        date_prescribed=today,
        expected_delivery_date=expected,
        status="draft",
    )
    db.add(rx)
    await db.commit()
    await db.refresh(rx)

    # Log initial status
    history = ApplianceStatusHistory(
        prescription_id=rx.id,
        previous_status=None,
        new_status="draft",
        changed_by=user.id,
        notes="Prescription created",
    )
    db.add(history)
    await db.commit()

    return _rx_to_response(rx, lab.name)


@router.get("/prescriptions/{rx_id}", response_model=PrescriptionResponse)
async def get_prescription(
    rx_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PrescriptionResponse:
    """Get a single prescription by ID."""
    rx = await _get_prescription(db, rx_id, user.practice_id)
    lab_result = await db.execute(select(Lab.name).where(Lab.id == rx.lab_id))
    lab_name = lab_result.scalar_one_or_none()
    return _rx_to_response(rx, lab_name)


@router.patch("/prescriptions/{rx_id}/status", response_model=PrescriptionResponse)
async def update_prescription_status(
    rx_id: str,
    payload: StatusUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PrescriptionResponse:
    """Update the status of an appliance prescription."""
    rx = await _get_prescription(db, rx_id, user.practice_id)
    old_status = rx.status
    new_status = payload.status

    # Validate status transition
    if new_status not in [s.value for s in ApplianceStatus]:
        raise HTTPException(status_code=400, detail=f"Invalid status: {new_status}")

    # Update status and relevant date fields
    rx.status = new_status
    if payload.tracking_number:
        rx.tracking_number = payload.tracking_number
    if payload.lab_case_number:
        rx.lab_case_number = payload.lab_case_number

    # Auto-set date fields based on status
    today = date.today()
    if new_status == "submitted" and not rx.date_sent_to_lab:
        rx.date_sent_to_lab = today
    elif new_status == "received_by_lab" and not rx.date_received_by_lab:
        rx.date_received_by_lab = today
    elif new_status == "shipped" and not rx.date_shipped:
        rx.date_shipped = today
    elif new_status == "received" and not rx.date_received:
        rx.date_received = today
    elif new_status == "placed" and not rx.date_placed:
        rx.date_placed = today

    # Log status change
    history = ApplianceStatusHistory(
        prescription_id=rx.id,
        previous_status=old_status,
        new_status=new_status,
        changed_by=user.id,
        notes=payload.notes,
    )
    db.add(history)
    await db.commit()
    await db.refresh(rx)

    lab_result = await db.execute(select(Lab.name).where(Lab.id == rx.lab_id))
    lab_name = lab_result.scalar_one_or_none()
    return _rx_to_response(rx, lab_name)


@router.post("/prescriptions/{rx_id}/remake", status_code=status.HTTP_201_CREATED, response_model=PrescriptionResponse)
async def create_remake(
    rx_id: str,
    reason: str = Query(..., min_length=1),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PrescriptionResponse:
    """Create a remake order from a rejected prescription."""
    original = await _get_prescription(db, rx_id, user.practice_id)

    # Mark original as rejected
    original.status = "rejected"
    history = ApplianceStatusHistory(
        prescription_id=original.id,
        previous_status=original.status,
        new_status="rejected",
        changed_by=user.id,
        notes=f"Rejected — remake ordered: {reason}",
    )
    db.add(history)

    # Get lab for expected delivery calc
    lab = await _get_lab(db, str(original.lab_id), user.practice_id)
    today = date.today()

    # Create new prescription as remake
    remake = AppliancePrescription(
        practice_id=user.practice_id,
        patient_id=original.patient_id,
        lab_id=original.lab_id,
        prescribed_by=user.id,
        appliance_type=original.appliance_type,
        appliance_name=original.appliance_name,
        arch=original.arch,
        teeth=original.teeth,
        color=original.color,
        material=original.material,
        rx_notes=original.rx_notes,
        special_instructions=original.special_instructions,
        scan_file_url=original.scan_file_url,
        priority="rush",
        lab_fee=original.lab_fee,
        date_prescribed=today,
        expected_delivery_date=today + timedelta(days=lab.avg_turnaround_days),
        status="submitted",
        date_sent_to_lab=today,
        is_remake=True,
        remake_reason=reason,
        original_prescription_id=original.id,
    )
    db.add(remake)
    await db.commit()
    await db.refresh(remake)

    # Log remake creation
    remake_history = ApplianceStatusHistory(
        prescription_id=remake.id,
        previous_status=None,
        new_status="submitted",
        changed_by=user.id,
        notes=f"Remake of {str(original.id)[:8]}: {reason}",
    )
    db.add(remake_history)
    await db.commit()

    return _rx_to_response(remake, lab.name)


# ═══════════════════════════════════════════════════════════════════════════════
# OVERDUE ALERTS & DASHBOARD ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/overdue", response_model=list[PrescriptionResponse])
async def get_overdue_appliances(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PrescriptionResponse]:
    """Get all appliances past their expected delivery date that haven't been received."""
    today = date.today()
    query = select(AppliancePrescription).where(
        AppliancePrescription.practice_id == user.practice_id,
        AppliancePrescription.expected_delivery_date < today,
        AppliancePrescription.status.in_(["submitted", "received_by_lab", "in_fabrication", "shipped"]),
    ).order_by(AppliancePrescription.expected_delivery_date.asc())

    result = await db.execute(query)
    prescriptions = result.scalars().all()

    lab_ids = {p.lab_id for p in prescriptions}
    lab_names: dict[uuid.UUID, str] = {}
    if lab_ids:
        labs_result = await db.execute(select(Lab).where(Lab.id.in_(lab_ids)))
        for lab in labs_result.scalars().all():
            lab_names[lab.id] = lab.name

    return [_rx_to_response(p, lab_names.get(p.lab_id)) for p in prescriptions]


@router.get("/summary")
async def get_appliance_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Dashboard summary: counts by status, overdue count, etc."""
    # Counts by status
    status_q = await db.execute(
        select(
            AppliancePrescription.status,
            func.count(AppliancePrescription.id),
        ).where(
            AppliancePrescription.practice_id == user.practice_id
        ).group_by(AppliancePrescription.status)
    )
    status_counts = {row[0]: row[1] for row in status_q.all()}

    # Overdue count
    today = date.today()
    overdue_q = await db.execute(
        select(func.count(AppliancePrescription.id)).where(
            AppliancePrescription.practice_id == user.practice_id,
            AppliancePrescription.expected_delivery_date < today,
            AppliancePrescription.status.in_(["submitted", "received_by_lab", "in_fabrication", "shipped"]),
        )
    )
    overdue_count = overdue_q.scalar() or 0

    # Due this week
    week_end = today + timedelta(days=7)
    due_soon_q = await db.execute(
        select(func.count(AppliancePrescription.id)).where(
            AppliancePrescription.practice_id == user.practice_id,
            AppliancePrescription.expected_delivery_date.between(today, week_end),
            AppliancePrescription.status.in_(["submitted", "received_by_lab", "in_fabrication", "shipped"]),
        )
    )
    due_this_week = due_soon_q.scalar() or 0

    return {
        "status_counts": status_counts,
        "overdue_count": overdue_count,
        "due_this_week": due_this_week,
        "total_active": sum(
            v for k, v in status_counts.items()
            if k not in ("placed", "rejected", "cancelled")
        ),
    }


@router.get("/prescriptions/{rx_id}/history")
async def get_status_history(
    rx_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Get the full status change history for a prescription."""
    rx = await _get_prescription(db, rx_id, user.practice_id)
    result = await db.execute(
        select(ApplianceStatusHistory)
        .where(ApplianceStatusHistory.prescription_id == rx.id)
        .order_by(ApplianceStatusHistory.changed_at.asc())
    )
    history = result.scalars().all()
    return [
        {
            "id": str(h.id),
            "previous_status": h.previous_status,
            "new_status": h.new_status,
            "changed_by": str(h.changed_by),
            "notes": h.notes,
            "changed_at": h.changed_at.isoformat() if h.changed_at else None,
        }
        for h in history
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# EASYRX INTEGRATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

class EasyRxConfig(BaseModel):
    easyrx_practice_id: str | None = None
    easyrx_api_key: str | None = None
    launch_url: str | None = None
    sync_enabled: bool = False


@router.get("/easyrx/config")
async def get_easyrx_config(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get EasyRx integration settings."""
    result = await db.execute(
        select(EasyRxIntegration).where(EasyRxIntegration.practice_id == user.practice_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        return {"is_enabled": False, "easyrx_practice_id": None, "sync_enabled": False}

    return {
        "is_enabled": config.is_enabled,
        "easyrx_practice_id": config.easyrx_practice_id,
        "launch_url": config.launch_url,
        "sync_enabled": config.sync_enabled,
        "last_sync_at": config.last_sync_at.isoformat() if config.last_sync_at else None,
    }


@router.put("/easyrx/config")
async def update_easyrx_config(
    payload: EasyRxConfig,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Update EasyRx integration settings."""
    result = await db.execute(
        select(EasyRxIntegration).where(EasyRxIntegration.practice_id == user.practice_id)
    )
    config = result.scalar_one_or_none()

    if not config:
        config = EasyRxIntegration(practice_id=user.practice_id, is_enabled=True)
        db.add(config)

    if payload.easyrx_practice_id is not None:
        config.easyrx_practice_id = payload.easyrx_practice_id
    if payload.easyrx_api_key is not None:
        config.easyrx_api_key = payload.easyrx_api_key
    if payload.launch_url is not None:
        config.launch_url = payload.launch_url
    config.sync_enabled = payload.sync_enabled
    config.is_enabled = True

    await db.commit()
    return {"status": "updated"}


@router.get("/easyrx/launch-url/{patient_id}")
async def get_easyrx_launch_url(
    patient_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Generate EasyRx SSO launch URL for a specific patient."""
    result = await db.execute(
        select(EasyRxIntegration).where(
            EasyRxIntegration.practice_id == user.practice_id,
            EasyRxIntegration.is_enabled.is_(True),
        )
    )
    config = result.scalar_one_or_none()
    if not config or not config.launch_url:
        raise HTTPException(status_code=404, detail="EasyRx integration not configured")

    # Build launch URL with patient context
    # EasyRx uses URL params to pass patient info for SSO launch
    from app.models.clinical import Patient
    patient_result = await db.execute(
        select(Patient).where(
            Patient.id == uuid.UUID(patient_id),
            Patient.practice_id == user.practice_id,
        )
    )
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Construct launch URL (EasyRx pattern: base_url?first=X&last=Y&dob=Z&chart=ID)
    import urllib.parse
    params = {
        "first": patient.first_name,
        "last": patient.last_name,
        "chart_id": str(patient.id)[:8],
    }
    if patient.date_of_birth:
        params["dob"] = patient.date_of_birth.isoformat()

    launch = f"{config.launch_url}?{urllib.parse.urlencode(params)}"
    return {"launch_url": launch}


# ═══════════════════════════════════════════════════════════════════════════════
# SHARED HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

async def _get_prescription(db: AsyncSession, rx_id: str, practice_id: uuid.UUID) -> AppliancePrescription:
    """Fetch prescription by ID with practice scoping."""
    result = await db.execute(
        select(AppliancePrescription).where(
            AppliancePrescription.id == uuid.UUID(rx_id),
            AppliancePrescription.practice_id == practice_id,
        )
    )
    rx = result.scalar_one_or_none()
    if not rx:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return rx


def _rx_to_response(rx: AppliancePrescription, lab_name: str | None = None) -> PrescriptionResponse:
    return PrescriptionResponse(
        id=str(rx.id),
        patient_id=str(rx.patient_id),
        lab_id=str(rx.lab_id),
        lab_name=lab_name,
        prescribed_by=str(rx.prescribed_by),
        appliance_type=rx.appliance_type,
        appliance_name=rx.appliance_name,
        arch=rx.arch,
        teeth=rx.teeth,
        color=rx.color,
        material=rx.material,
        rx_notes=rx.rx_notes,
        special_instructions=rx.special_instructions,
        scan_file_url=rx.scan_file_url,
        status=rx.status,
        priority=rx.priority,
        date_prescribed=rx.date_prescribed.isoformat() if rx.date_prescribed else "",
        date_sent_to_lab=rx.date_sent_to_lab.isoformat() if rx.date_sent_to_lab else None,
        date_received_by_lab=rx.date_received_by_lab.isoformat() if rx.date_received_by_lab else None,
        date_shipped=rx.date_shipped.isoformat() if rx.date_shipped else None,
        date_received=rx.date_received.isoformat() if rx.date_received else None,
        date_placed=rx.date_placed.isoformat() if rx.date_placed else None,
        expected_delivery_date=rx.expected_delivery_date.isoformat() if rx.expected_delivery_date else None,
        tracking_number=rx.tracking_number,
        lab_case_number=rx.lab_case_number,
        is_remake=rx.is_remake,
        remake_reason=rx.remake_reason,
        lab_fee=float(rx.lab_fee) if rx.lab_fee else None,
        rush_fee=float(rx.rush_fee) if rx.rush_fee else None,
        created_at=rx.created_at.isoformat() if rx.created_at else "",
    )
