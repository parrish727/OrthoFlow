"""Ortho2 Edge Cloud API integration — patient data, scheduling, treatment plans."""
import httpx
from app.core.config import settings

ORTHO2_BASE = "https://api.ortho2.com/v1"  # Edge Cloud REST API


async def connect(api_key: str, practice_id: str) -> dict:
    """Verify Ortho2 credentials and return practice info."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{ORTHO2_BASE}/practice",
            headers={"Authorization": f"Bearer {api_key}", "X-Practice-ID": practice_id},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()


async def get_patients(api_key: str, limit: int = 50) -> list[dict]:
    """Get active patients with treatment plans."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{ORTHO2_BASE}/patients",
            headers={"Authorization": f"Bearer {api_key}"},
            params={"status": "active", "limit": limit},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("patients", [])


async def get_appointments(api_key: str, days_ahead: int = 14) -> list[dict]:
    """Get upcoming appointments for supply prediction."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{ORTHO2_BASE}/appointments",
            headers={"Authorization": f"Bearer {api_key}"},
            params={"days_ahead": days_ahead},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("appointments", [])


async def get_insurance_claims(api_key: str, status: str = "pending") -> list[dict]:
    """Get insurance claims for EOB matching."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{ORTHO2_BASE}/claims",
            headers={"Authorization": f"Bearer {api_key}"},
            params={"status": status},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("claims", [])


async def sync_practice_data(api_key: str) -> dict:
    """Full sync — pull patients, appointments, claims."""
    patients = await get_patients(api_key)
    appointments = await get_appointments(api_key)
    claims = await get_insurance_claims(api_key)
    return {
        "patients": len(patients),
        "appointments": len(appointments),
        "claims": len(claims),
        "data": {"patients": patients, "appointments": appointments, "claims": claims},
    }
