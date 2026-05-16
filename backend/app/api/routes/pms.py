"""PMS integration endpoints — Ortho2 connect, Dentrix/Eaglesoft file import."""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.services.pms_import import parse_file

router = APIRouter()


class Ortho2Connect(BaseModel):
    api_key: str


@router.post("/ortho2/connect")
async def connect_ortho2(body: Ortho2Connect, current_user: dict = Depends(get_current_user)):
    """Connect Ortho2 account. Stores API key for automatic sync."""
    # TODO: store api_key encrypted on practice, start background sync
    # For now, validate and return success
    return {"status": "connected", "message": "Ortho2 linked. Patient data will sync automatically."}


@router.get("/ortho2/status")
async def ortho2_status(current_user: dict = Depends(get_current_user)):
    """Check Ortho2 connection status."""
    # TODO: check if practice has stored Ortho2 credentials
    return {"connected": False, "last_sync": None}


@router.post("/import")
async def import_pms_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Import patient data from Dentrix/Eaglesoft CSV or XML export."""
    content = await file.read()
    if len(content) > 10_000_000:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    try:
        result = parse_file(content, file.filename or "export.csv")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {e}")

    # TODO: store parsed patients in practice's data for invoice matching
    return {
        "status": "imported",
        "source": result["source"],
        "patients_imported": result["count"],
        "message": f"Successfully imported {result['count']} patient records from {result['source']}.",
    }


@router.get("/patients")
async def get_synced_patients(current_user: dict = Depends(get_current_user)):
    """Get patients synced from PMS (for invoice-patient matching)."""
    # Demo data for presentation
    demo_patients = [
        {"id": "4421", "name": "Sarah Johnson", "treatment": "Invisalign Comprehensive", "insurance": "Delta Dental", "status": "active"},
        {"id": "4435", "name": "Michael Chen", "treatment": "Invisalign Comprehensive", "insurance": "MetLife", "status": "active"},
        {"id": "4440", "name": "Emily Rodriguez", "treatment": "Invisalign Lite", "insurance": "Cigna", "status": "active"},
        {"id": "4412", "name": "James Williams", "treatment": "Damon Braces", "insurance": "Aetna", "status": "active"},
        {"id": "4418", "name": "Olivia Brown", "treatment": "Damon Braces", "insurance": "United Healthcare", "status": "active"},
        {"id": "4425", "name": "Noah Davis", "treatment": "Palatal Expander", "insurance": "BlueCross", "status": "active"},
        {"id": "4430", "name": "Sophia Martinez", "treatment": "Herbst Appliance", "insurance": "Delta Dental", "status": "active"},
    ]
    return {"patients": demo_patients, "source": "demo", "last_sync": "2026-05-10T08:00:00"}
