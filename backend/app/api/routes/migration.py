"""OrthoFlow API — Patient Migration Tool.

Import patient data from other practice management systems (Dolphin, Ortho2, Eaglesoft)
or generic CSV files. Handles upload, validation, mapping, and background import.
"""
import csv
import io
import logging
import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, File, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, SessionLocal
from app.core.auth import get_current_user
from app.core.audit import audit_log
from app.core.config import settings
from app.models.portal import MigrationJob
from app.models.clinical import Patient
from app.services.storage import upload_file, download_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/migration", tags=["migration"])


# ── Constants ─────────────────────────────────────────────────────────────────

SUPPORTED_SYSTEMS: dict[str, dict] = {
    "dolphin": {
        "name": "Dolphin Imaging & Management",
        "file_format": "CSV export from Dolphin",
        "default_mapping": {
            "patient_id": "patient_id",
            "first_name": "first_name",
            "last_name": "last_name",
            "dob": "dob",
            "phone": "phone",
            "email": "email",
            "status": "status",
            "referring_doctor": "referring_dr",
        },
        "expected_columns": ["patient_id", "first_name", "last_name", "dob", "phone", "email", "status", "referring_dr"],
    },
    "ortho2": {
        "name": "Ortho2 Edge",
        "file_format": "CSV export from Ortho2",
        "default_mapping": {
            "patient_id": "PatNo",
            "first_name": "FName",
            "last_name": "LName",
            "dob": "BDate",
            "phone": "Phone1",
            "email": "Email",
            "status": "Status",
            "referring_doctor": "RefDoc",
        },
        "expected_columns": ["PatNo", "FName", "LName", "BDate", "Phone1", "Email", "Status", "RefDoc"],
    },
    "eaglesoft": {
        "name": "Patterson Eaglesoft",
        "file_format": "CSV export from Eaglesoft",
        "default_mapping": {
            "patient_id": "PatNum",
            "first_name": "FirstName",
            "last_name": "LastName",
            "dob": "Birthdate",
            "phone": "HmPhone",
            "email": "Email",
            "status": "PatStatus",
            "referring_doctor": None,
        },
        "expected_columns": ["PatNum", "FirstName", "LastName", "Birthdate", "HmPhone", "Email", "PatStatus"],
    },
    "csv": {
        "name": "Generic CSV",
        "file_format": "Any CSV file — user maps columns manually",
        "default_mapping": {},
        "expected_columns": [],
    },
}

# Standard OrthoFlow patient fields for mapping target
ORTHOFLOW_FIELDS = [
    "first_name", "last_name", "dob", "email", "phone",
    "phone_secondary", "address", "status", "referring_doctor",
]


# ── Schemas ───────────────────────────────────────────────────────────────────


class MappingUpdate(BaseModel):
    field_mapping: dict[str, str | None] = Field(
        ..., description="Maps OrthoFlow field names to source column names"
    )


class JobResponse(BaseModel):
    id: str
    source_system: str
    status: str
    total_records: int
    imported_records: int
    failed_records: int
    skipped_records: int
    field_mapping: dict | None
    validation_errors: dict | None
    created_at: str


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/systems")
async def list_supported_systems(
    user: dict = Depends(get_current_user),
) -> dict:
    """List supported source systems with their expected file formats and field mappings."""
    systems = []
    for key, info in SUPPORTED_SYSTEMS.items():
        systems.append({
            "id": key,
            "name": info["name"],
            "file_format": info["file_format"],
            "expected_columns": info["expected_columns"],
            "default_mapping": info["default_mapping"],
        })
    return {"systems": systems, "orthoflow_fields": ORTHOFLOW_FIELDS}


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_migration_file(
    source_system: str = Query(..., description="Source system ID: dolphin, ortho2, eaglesoft, csv"),
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload a CSV/export file for migration. Stores in MinIO, creates a MigrationJob."""
    practice_id = user["practice_id"]

    if source_system not in SUPPORTED_SYSTEMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported system: {source_system}. Supported: {list(SUPPORTED_SYSTEMS.keys())}",
        )

    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported",
        )

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:  # 50MB limit for migration files
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large (max 50MB)",
        )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty",
        )

    # Store in MinIO
    job_id = uuid.uuid4()
    storage_key = f"migrations/{practice_id}/{job_id}/{file.filename}"
    await upload_file(storage_key, content, "text/csv")

    # Create MigrationJob
    job = MigrationJob(
        id=job_id,
        practice_id=practice_id,
        source_system=source_system,
        status="pending",
        source_file_path=storage_key,
        field_mapping=SUPPORTED_SYSTEMS[source_system]["default_mapping"] or None,
        created_by=user["user_id"],
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    await audit_log(
        db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="migration.upload",
        resource_type="migration_job",
        resource_id=str(job.id),
        details=f"Uploaded {file.filename} from {source_system}",
    )

    logger.info("Migration file uploaded: job=%s system=%s", str(job.id), source_system)
    return {
        "id": str(job.id),
        "source_system": source_system,
        "status": "pending",
        "file_name": file.filename,
        "default_mapping": job.field_mapping,
    }


@router.post("/validate/{job_id}")
async def validate_migration_file(
    job_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Parse uploaded file, detect columns, suggest field mapping, report validation errors."""
    practice_id = user["practice_id"]

    result = await db.execute(
        select(MigrationJob).where(
            MigrationJob.id == job_id,
            MigrationJob.practice_id == practice_id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Migration job not found")

    if job.status not in ("pending", "validating"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is in '{job.status}' state and cannot be validated",
        )

    # Download and parse file
    try:
        file_content = await download_file(job.source_file_path)
    except Exception as e:
        logger.error("Failed to download migration file: %s", str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to read uploaded file")

    text_content = file_content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text_content))
    detected_columns = reader.fieldnames or []

    # Parse rows for validation
    errors: list[dict] = []
    row_count = 0
    sample_rows: list[dict] = []

    for i, row in enumerate(reader):
        row_count += 1
        if i < 5:
            sample_rows.append(dict(row))

        # Basic validation
        mapping = job.field_mapping or {}
        first_name_col = mapping.get("first_name")
        last_name_col = mapping.get("last_name")

        if first_name_col and not row.get(first_name_col, "").strip():
            errors.append({"row": i + 2, "field": "first_name", "error": "Missing first name"})
        if last_name_col and not row.get(last_name_col, "").strip():
            errors.append({"row": i + 2, "field": "last_name", "error": "Missing last name"})

        # Limit errors to first 100
        if len(errors) >= 100:
            errors.append({"row": 0, "field": "_", "error": f"Truncated: showing first 100 of more errors"})
            break

    # Suggest mapping if generic CSV
    suggested_mapping: dict[str, str | None] = {}
    if job.source_system == "csv":
        col_lower = {c.lower().replace(" ", "_"): c for c in detected_columns}
        for field in ORTHOFLOW_FIELDS:
            if field in col_lower:
                suggested_mapping[field] = col_lower[field]
            else:
                suggested_mapping[field] = None
    else:
        suggested_mapping = job.field_mapping or {}

    # Update job
    job.status = "validating"
    job.total_records = row_count
    job.validation_errors = {"errors": errors[:100], "error_count": len(errors)}
    if job.source_system == "csv" and not job.field_mapping:
        job.field_mapping = suggested_mapping
    await db.commit()

    await audit_log(
        db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="migration.validate",
        resource_type="migration_job",
        resource_id=str(job.id),
        details=f"Validated {row_count} rows, {len(errors)} errors",
    )

    return {
        "id": str(job.id),
        "status": "validating",
        "total_records": row_count,
        "detected_columns": list(detected_columns),
        "suggested_mapping": suggested_mapping,
        "validation_errors": errors[:100],
        "error_count": len(errors),
        "sample_rows": sample_rows,
    }


@router.patch("/mapping/{job_id}")
async def update_field_mapping(
    job_id: str,
    payload: MappingUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Confirm or update field mapping before import execution."""
    practice_id = user["practice_id"]

    result = await db.execute(
        select(MigrationJob).where(
            MigrationJob.id == job_id,
            MigrationJob.practice_id == practice_id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Migration job not found")

    if job.status not in ("pending", "validating"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update mapping for job in '{job.status}' state",
        )

    job.field_mapping = payload.field_mapping
    await db.commit()

    await audit_log(
        db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="migration.mapping_updated",
        resource_type="migration_job",
        resource_id=str(job.id),
    )

    return {"id": str(job.id), "field_mapping": job.field_mapping, "status": job.status}


@router.post("/execute/{job_id}")
async def execute_migration(
    job_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Start the import as a background task. Creates patients from mapped data."""
    practice_id = user["practice_id"]

    result = await db.execute(
        select(MigrationJob).where(
            MigrationJob.id == job_id,
            MigrationJob.practice_id == practice_id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Migration job not found")

    if job.status not in ("pending", "validating"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot execute job in '{job.status}' state. Must be pending or validating.",
        )

    if not job.field_mapping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Field mapping must be set before execution. Call PATCH /mapping/{job_id} first.",
        )

    # Mark as importing
    job.status = "importing"
    job.started_at = datetime.now(timezone.utc)
    await db.commit()

    await audit_log(
        db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="migration.execute",
        resource_type="migration_job",
        resource_id=str(job.id),
    )

    # Launch background import
    background_tasks.add_task(
        _run_import,
        job_id=str(job.id),
        practice_id=practice_id,
        source_file_path=job.source_file_path,
        field_mapping=job.field_mapping,
    )

    logger.info("Migration import started: job=%s", str(job.id))
    return {"id": str(job.id), "status": "importing", "message": "Import started in background"}


async def _run_import(
    job_id: str,
    practice_id: str,
    source_file_path: str,
    field_mapping: dict,
) -> None:
    """Background task: import patient records from CSV using field mapping."""
    async with SessionLocal() as db:
        try:
            # Download file
            file_content = await download_file(source_file_path)
            text_content = file_content.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text_content))

            imported = 0
            failed = 0
            skipped = 0
            log_lines: list[str] = []

            for i, row in enumerate(reader):
                try:
                    # Extract mapped fields
                    first_name_col = field_mapping.get("first_name")
                    last_name_col = field_mapping.get("last_name")

                    first_name = row.get(first_name_col, "").strip() if first_name_col else ""
                    last_name = row.get(last_name_col, "").strip() if last_name_col else ""

                    if not first_name or not last_name:
                        skipped += 1
                        log_lines.append(f"Row {i + 2}: Skipped — missing name")
                        continue

                    # Build patient record
                    dob_col = field_mapping.get("dob")
                    email_col = field_mapping.get("email")
                    phone_col = field_mapping.get("phone")
                    status_col = field_mapping.get("status")
                    ref_dr_col = field_mapping.get("referring_doctor")

                    dob_str = row.get(dob_col, "").strip() if dob_col else ""
                    patient_dob = _parse_date(dob_str) if dob_str else None

                    patient = Patient(
                        practice_id=practice_id,
                        first_name=first_name,
                        last_name=last_name,
                        date_of_birth=patient_dob,
                        email=row.get(email_col, "").strip() if email_col else None,
                        phone=row.get(phone_col, "").strip() if phone_col else None,
                        status="active",
                        referring_doctor=row.get(ref_dr_col, "").strip() if ref_dr_col else None,
                    )
                    db.add(patient)
                    imported += 1

                except Exception as e:
                    failed += 1
                    log_lines.append(f"Row {i + 2}: Error — {str(e)[:200]}")

                # Batch commit every 100 records
                if (i + 1) % 100 == 0:
                    await db.commit()

            await db.commit()

            # Update job status
            job_result = await db.execute(select(MigrationJob).where(MigrationJob.id == job_id))
            job = job_result.scalar_one()
            job.status = "complete" if failed == 0 else "complete"
            job.imported_records = imported
            job.failed_records = failed
            job.skipped_records = skipped
            job.completed_at = datetime.now(timezone.utc)
            job.import_log = "\n".join(log_lines[-500:])  # Keep last 500 lines
            await db.commit()

            logger.info(
                "Migration complete: job=%s imported=%d failed=%d skipped=%d",
                job_id, imported, failed, skipped,
            )

        except Exception as e:
            logger.error("Migration failed: job=%s error=%s", job_id, str(e))
            try:
                job_result = await db.execute(select(MigrationJob).where(MigrationJob.id == job_id))
                job = job_result.scalar_one()
                job.status = "failed"
                job.completed_at = datetime.now(timezone.utc)
                job.import_log = f"Fatal error: {str(e)[:1000]}"
                await db.commit()
            except Exception:
                pass


def _parse_date(date_str: str) -> date | None:
    """Attempt to parse common date formats from various PMS exports."""
    formats = ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%d/%m/%Y", "%Y%m%d", "%m/%d/%y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


# ── Job Listing ───────────────────────────────────────────────────────────────


@router.get("/jobs")
async def list_migration_jobs(
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all migration jobs for the practice."""
    practice_id = user["practice_id"]

    query = select(MigrationJob).where(MigrationJob.practice_id == practice_id)
    if status_filter:
        query = query.where(MigrationJob.status == status_filter)
    query = query.order_by(MigrationJob.created_at.desc())

    result = await db.execute(query)
    jobs = result.scalars().all()

    return {
        "jobs": [
            {
                "id": str(j.id),
                "source_system": j.source_system,
                "status": j.status,
                "total_records": j.total_records,
                "imported_records": j.imported_records,
                "failed_records": j.failed_records,
                "skipped_records": j.skipped_records,
                "created_at": j.created_at.isoformat(),
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
            }
            for j in jobs
        ],
    }


@router.get("/jobs/{job_id}")
async def get_migration_job(
    job_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get migration job detail with progress, errors, and log."""
    practice_id = user["practice_id"]

    result = await db.execute(
        select(MigrationJob).where(
            MigrationJob.id == job_id,
            MigrationJob.practice_id == practice_id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Migration job not found")

    return {
        "id": str(job.id),
        "source_system": job.source_system,
        "status": job.status,
        "total_records": job.total_records,
        "imported_records": job.imported_records,
        "failed_records": job.failed_records,
        "skipped_records": job.skipped_records,
        "field_mapping": job.field_mapping,
        "validation_errors": job.validation_errors,
        "import_log": job.import_log,
        "source_file_path": job.source_file_path,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "created_at": job.created_at.isoformat(),
    }
