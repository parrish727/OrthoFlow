"""OrthoFlow — Novu Notification Integration.

All SMS and Email notifications route through self-hosted Novu.
Novu handles: delivery, retries, templates, subscriber preferences.
"""
import os
import logging
import httpx

logger = logging.getLogger(__name__)

NOVU_API_URL = os.environ.get("NOVU_API_URL", "http://localhost:3900")
NOVU_SECRET_KEY = os.environ.get("NOVU_SECRET_KEY", "")


async def novu_request(method: str, path: str, json_data: dict = None) -> dict:
    """Make a request to the self-hosted Novu API."""
    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method,
            f"{NOVU_API_URL}/v1{path}",
            headers={
                "Authorization": f"ApiKey {NOVU_SECRET_KEY}",
                "Content-Type": "application/json",
            },
            json=json_data,
            timeout=30.0,
        )
        if resp.status_code >= 400:
            logger.error(f"Novu API error: {resp.status_code} {resp.text[:200]}")
        return resp.json() if resp.status_code < 400 else {"error": resp.text[:200]}


async def create_subscriber(patient_id: str, email: str = None, phone: str = None, first_name: str = "", last_name: str = "") -> dict:
    """Register a patient as a Novu subscriber."""
    data = {
        "subscriberId": patient_id,
        "firstName": first_name,
        "lastName": last_name,
    }
    if email:
        data["email"] = email
    if phone:
        data["phone"] = phone
    return await novu_request("POST", "/subscribers", data)


async def update_subscriber(patient_id: str, email: str = None, phone: str = None) -> dict:
    """Update a subscriber's contact info."""
    data = {}
    if email:
        data["email"] = email
    if phone:
        data["phone"] = phone
    return await novu_request("PUT", f"/subscribers/{patient_id}", data)


async def send_notification(patient_id: str, workflow_id: str, payload: dict = None) -> dict:
    """Trigger a notification workflow for a patient.
    
    workflow_id examples: 'appointment-reminder', 'appointment-confirmation', 'custom-message'
    payload: template variables like {patient_name}, {appointment_date}, {appointment_time}
    """
    data = {
        "name": workflow_id,
        "to": {"subscriberId": patient_id},
        "payload": payload or {},
    }
    return await novu_request("POST", "/events/trigger", data)


async def send_sms(patient_id: str, message: str) -> dict:
    """Send a direct SMS to a patient via Novu."""
    return await send_notification(patient_id, "direct-sms", {"message": message})


async def send_email(patient_id: str, subject: str, body: str) -> dict:
    """Send a direct email to a patient via Novu."""
    return await send_notification(patient_id, "direct-email", {"subject": subject, "body": body})


async def send_appointment_reminder(patient_id: str, patient_name: str, appointment_date: str, appointment_time: str, office_name: str, office_phone: str) -> dict:
    """Send appointment reminder via Novu (SMS + Email based on subscriber preferences)."""
    return await send_notification(patient_id, "appointment-reminder", {
        "patient_name": patient_name,
        "appointment_date": appointment_date,
        "appointment_time": appointment_time,
        "office_name": office_name,
        "office_phone": office_phone,
    })


async def send_confirmation_request(patient_id: str, patient_name: str, appointment_date: str, appointment_time: str, office_name: str) -> dict:
    """Send appointment confirmation request (reply YES/CANCEL)."""
    return await send_notification(patient_id, "appointment-confirmation", {
        "patient_name": patient_name,
        "appointment_date": appointment_date,
        "appointment_time": appointment_time,
        "office_name": office_name,
    })
