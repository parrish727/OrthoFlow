"""OrthoFi financial bridge.

OrthoFi is a financial platform used by a large share of ortho practices for digital intake,
insurance verification, benefit calc, and contract setup — but it STOPS tracking at ~120 days.
OrthoFlow's AR aging + 90+/120+ delinquency tracking owns that long tail. This bridge ingests an
OrthoFi "financial handoff" for a patient (balance + plan at the hand-off boundary) and continues
AR tracking inside OrthoFlow.

STATUS: OrthoFi has NO public developer API today — integration is partner-driven (their documented
model is PMS → OrthoFi import, e.g. Ortho2 Edge Cloud). So this module is SOURCE-AGNOSTIC: the
importer works from an already-parsed handoff record, which can arrive via (a) a future OrthoFi API,
or (b) a CSV/JSON export the practice/OrthoFi provides. It stays DORMANT (ORTHOFI_ENABLED=False)
until a real API or an agreed export format is available. See
docs/specs/ORTHOFI_INTEGRATION_FEASIBILITY.md.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.clinical import Patient
from app.models.finance import PatientLedgerEntry


def status() -> dict:
    """Report bridge readiness so the UI can show configured/dormant without guessing."""
    configured = bool(settings.ORTHOFI_ENABLED and settings.ORTHOFI_API_KEY and settings.ORTHOFI_BASE_URL)
    return {
        "enabled": settings.ORTHOFI_ENABLED,
        "configured": configured,
        "mode": "api" if configured else "import",
        "message": (
            "OrthoFi API bridge active."
            if configured
            else "OrthoFi has no public API available to OrthoFlow yet — financial handoffs are "
                 "accepted via documented CSV/JSON import. Live API activates when a partnership "
                 "endpoint + key are provisioned (ORTHOFI_ENABLED/ORTHOFI_API_KEY/ORTHOFI_BASE_URL)."
        ),
    }


class OrthoFiHandoff(BaseModel):
    """A single patient's financial handoff from OrthoFi at the ~120-day boundary.

    Source-agnostic: whatever provides this (future API or an export) maps onto these fields.
    """
    external_id: str = Field(..., description="OrthoFi patient/account id for idempotency + audit")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: date | None = None
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=20)
    outstanding_balance: Decimal = Field(..., description="Patient-responsible balance OrthoFi hands off")
    contract_total: Decimal | None = None
    monthly_payment: Decimal | None = None
    last_payment_date: date | None = None
    handoff_date: date | None = None  # the boundary date OrthoFi stopped tracking
    plan_summary: str | None = Field(None, max_length=500)


async def import_handoff(
    db: AsyncSession,
    practice_id: uuid.UUID,
    handoff: OrthoFiHandoff,
    created_by: uuid.UUID | None,
) -> dict:
    """Create/match the patient and seed the outstanding balance into the OrthoFlow ledger so AR
    tracking continues. Idempotent on (practice_id, external_id via the AR note marker + name/dob
    match). Returns a summary. Does NOT duplicate a prior handoff charge for the same external_id.
    """
    # Match an existing patient by name + DOB (safe, no external_id column); else create.
    q = select(Patient).where(
        Patient.practice_id == practice_id,
        Patient.first_name == handoff.first_name,
        Patient.last_name == handoff.last_name,
    )
    if handoff.date_of_birth:
        q = q.where(Patient.date_of_birth == handoff.date_of_birth)
    patient = (await db.execute(q.limit(1))).scalar_one_or_none()

    created_patient = False
    if not patient:
        patient = Patient(
            id=uuid.uuid4(),
            practice_id=practice_id,
            first_name=handoff.first_name,
            last_name=handoff.last_name,
            date_of_birth=handoff.date_of_birth,
            email=handoff.email,
            phone=handoff.phone,
            status="active",
            treatment_phase="active",
        )
        db.add(patient)
        await db.flush()
        created_patient = True

    # Idempotency: a handoff charge for this external_id is tagged in reference_number.
    ref = f"ORTHOFI:{handoff.external_id}"
    existing = (await db.execute(
        select(PatientLedgerEntry).where(
            PatientLedgerEntry.practice_id == practice_id,
            PatientLedgerEntry.patient_id == patient.id,
            PatientLedgerEntry.reference_number == ref,
        ).limit(1)
    )).scalar_one_or_none()

    ledger_created = False
    if existing is None and handoff.outstanding_balance and handoff.outstanding_balance != 0:
        db.add(PatientLedgerEntry(
            id=uuid.uuid4(),
            practice_id=practice_id,
            patient_id=patient.id,
            entry_type="charge",
            description=f"OrthoFi handoff balance{(' — ' + handoff.plan_summary) if handoff.plan_summary else ''}",
            amount=Decimal(handoff.outstanding_balance),
            service_date=handoff.handoff_date or date.today(),
            posted_date=date.today(),
            reference_number=ref,
            notes="Imported from OrthoFi at the 120-day financial handoff boundary.",
            created_by=created_by,
        ))
        ledger_created = True

    # Carry a short AR note so the financial coordinator sees the provenance on the Ledger roster.
    patient.ar_note = (
        f"OrthoFi handoff {handoff.handoff_date or date.today()}: balance "
        f"{handoff.outstanding_balance}"
        + (f", {handoff.monthly_payment}/mo" if handoff.monthly_payment else "")
    )
    patient.ar_note_updated_at = datetime.now(timezone.utc)
    patient.ar_note_updated_by = created_by

    await db.commit()
    return {
        "patient_id": str(patient.id),
        "external_id": handoff.external_id,
        "created_patient": created_patient,
        "ledger_entry_created": ledger_created,
        "already_imported": existing is not None,
    }
