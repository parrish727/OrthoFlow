"""Shared document-exchange workflow used by BOTH the office (workflow.py) and the patient
portal (portal.py), so the two directions stay consistent and in sync.

A single uploaded file becomes:
  1. a ClamAV scan (fail-closed) + size/type validation,
  2. one object in the private 'orthoflow-documents' MinIO bucket,
  3. one PatientDocument row (the single source surfaced in OrthoFlow chart/Documents + MyOrthoChart),
  4. one DocumentNotification for the OTHER audience (synced in-app feed), and
  5. a confirmation email to the patient (OrthoFlow Patient.email = source of truth).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinical import Patient
from app.models.workflow import PatientDocument, DocumentNotification
from app.services import documents as doc_storage
from app.services import email_relay
from app.services.scanner import scan_file, MAX_FILE_SIZE


async def scan_store_and_record(
    *,
    db: AsyncSession,
    practice_id: uuid.UUID,
    patient_id: uuid.UUID,
    content: bytes,
    filename: str,
    content_type: str | None,
    document_type: str,
    title: str,
    direction: str,                 # office_to_patient | patient_to_office
    uploaded_by_type: str,          # staff | patient
    uploaded_by: uuid.UUID | None,  # staff user id, or None for patient uploads
    notes: str | None = None,
) -> PatientDocument:
    """Scan → store in MinIO → create the PatientDocument row → notify the other side → email the
    patient. Returns the committed PatientDocument. Raises HTTPException on validation/scan failure.
    """
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            f"File exceeds the {MAX_FILE_SIZE // (1024 * 1024)}MB limit")

    # Security scan (fail-closed: rejects if ClamAV is unavailable or type/magic bytes invalid).
    scan = await scan_file(content, filename or "upload")
    if not scan.get("clean"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"File rejected by security scan: {scan.get('reason', 'unknown')}")

    # Store in the private documents bucket.
    key = doc_storage.build_key(practice_id, patient_id, filename or "upload", content_type)
    await doc_storage.store_document(key, content, content_type or "application/octet-stream")

    now = datetime.now(timezone.utc)
    doc = PatientDocument(
        id=uuid.uuid4(),
        practice_id=practice_id,
        patient_id=patient_id,
        document_type=document_type,
        title=title,
        file_url=None,
        storage_key=key,
        original_filename=filename,
        file_size_bytes=len(content),
        mime_type=content_type,
        uploaded_by=uploaded_by,
        uploaded_by_type=uploaded_by_type,
        direction=direction,
        shared_with_patient=True,
        scan_status="clean",
        scanned_at=now,
        notes=notes,
    )
    db.add(doc)
    await db.flush()  # assign doc.id before building the notification

    # Notify the OTHER audience, in the same transaction (keeps both feeds in sync).
    if direction == "office_to_patient":
        audience, who = "patient", "your orthodontic office"
        action_url = "/documents"
    else:
        audience, who = "office", "a patient"
        action_url = f"/patients/{patient_id}"

    db.add(DocumentNotification(
        id=uuid.uuid4(),
        practice_id=practice_id,
        patient_id=patient_id,
        document_id=doc.id,
        audience=audience,
        kind="document_uploaded",
        title="New document",
        body=f"{title} was uploaded by {who}.",
        action_url=action_url,
        is_read=False,
    ))

    await db.commit()
    await db.refresh(doc)

    # Confirmation email to the patient (best-effort; never blocks the upload).
    await _email_patient_confirmation(db, practice_id, patient_id, title, direction)

    return doc


async def _email_patient_confirmation(db, practice_id, patient_id, title: str, direction: str) -> None:
    """Email the patient a confirmation. OrthoFlow Patient.email is the source of truth."""
    try:
        patient = (await db.execute(
            select(Patient).where(Patient.id == patient_id, Patient.practice_id == practice_id)
        )).scalar_one_or_none()
        if not patient or not patient.email:
            return
        if direction == "patient_to_office":
            subject = "We received your document"
            body = (f"Hi {patient.first_name},\n\n"
                    f"We've received your upload \"{title}\" and added it to your chart. "
                    f"No further action is needed.\n\nThank you,\nYour Orthodontic Office")
        else:
            subject = "A new document is available in MyOrthoChart"
            body = (f"Hi {patient.first_name},\n\n"
                    f"Your orthodontic office added a new document, \"{title}\", to your chart. "
                    f"You can view it securely by signing in to MyOrthoChart.\n\n— Your Orthodontic Office")
        email_relay.send_email(to_addr=patient.email, subject=subject, body=body, from_name="OrthoFlow")
    except Exception:
        # Email is a convenience; a relay/config error must not fail the upload.
        pass
