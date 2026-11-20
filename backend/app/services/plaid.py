"""Plaid integration — bank account linking + ACH payment initiation."""
import httpx
from app.core.config import settings

_PLAID_BASE = {
    "sandbox": "https://sandbox.plaid.com",
    "production": "https://production.plaid.com",
}


async def create_link_token(user_id: str, practice_name: str) -> str:
    """Create a Plaid Link token for the frontend to open the bank connection UI."""
    base = _PLAID_BASE.get(settings.PLAID_ENVIRONMENT, _PLAID_BASE["sandbox"])
    
    payload = {
        "client_id": settings.PLAID_CLIENT_ID,
        "secret": settings.PLAID_SECRET,
        "user": {"client_user_id": user_id},
        "client_name": "OrthoFlow AI",
        "products": ["auth"],
        "country_codes": ["US"],
        "language": "en",
    }
    
    # Production requires redirect_uri for OAuth banks
    if settings.PLAID_ENVIRONMENT == "production":
        payload["redirect_uri"] = "https://app.orthoflowsolutions.com/plaid/callback"
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{base}/link/token/create",
            json=payload,
            timeout=15,
        )
        if resp.status_code >= 400:
            error_data = resp.json()
            raise Exception(f"Plaid error: {error_data.get('error_message', resp.text[:200])}")
        return resp.json()["link_token"]


async def exchange_public_token(public_token: str) -> dict:
    """Exchange Plaid public token for access token after user links bank."""
    base = _PLAID_BASE.get(settings.PLAID_ENVIRONMENT, _PLAID_BASE["sandbox"])
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{base}/item/public_token/exchange",
            json={
                "client_id": settings.PLAID_CLIENT_ID,
                "secret": settings.PLAID_SECRET,
                "public_token": public_token,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()  # {"access_token": "...", "item_id": "..."}


async def get_accounts(access_token: str) -> list[dict]:
    """Get linked bank accounts."""
    base = _PLAID_BASE.get(settings.PLAID_ENVIRONMENT, _PLAID_BASE["sandbox"])
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{base}/accounts/get",
            json={
                "client_id": settings.PLAID_CLIENT_ID,
                "secret": settings.PLAID_SECRET,
                "access_token": access_token,
            },
            timeout=15,
        )
        resp.raise_for_status()
        accounts = resp.json()["accounts"]
        return [{"id": a["account_id"], "name": a["name"], "mask": a["mask"]} for a in accounts]


async def initiate_ach_payment(access_token: str, account_id: str, amount: float, vendor_name: str) -> dict:
    """Initiate an ACH payment to a vendor."""
    base = _PLAID_BASE.get(settings.PLAID_ENVIRONMENT, _PLAID_BASE["sandbox"])
    async with httpx.AsyncClient() as client:
        # Create transfer authorization
        auth_resp = await client.post(
            f"{base}/transfer/authorization/create",
            json={
                "client_id": settings.PLAID_CLIENT_ID,
                "secret": settings.PLAID_SECRET,
                "access_token": access_token,
                "account_id": account_id,
                "type": "debit",
                "network": "ach",
                "amount": str(amount),
                "ach_class": "ppd",
                "user": {"legal_name": vendor_name},
            },
            timeout=15,
        )
        auth_resp.raise_for_status()
        authorization_id = auth_resp.json()["authorization"]["id"]

        # Create the transfer
        transfer_resp = await client.post(
            f"{base}/transfer/create",
            json={
                "client_id": settings.PLAID_CLIENT_ID,
                "secret": settings.PLAID_SECRET,
                "access_token": access_token,
                "account_id": account_id,
                "authorization_id": authorization_id,
                "amount": str(amount),
                "description": f"OrthoFlow payment to {vendor_name}",
            },
            timeout=15,
        )
        transfer_resp.raise_for_status()
        return transfer_resp.json()["transfer"]


# ── Patient payments (MyOrthoChart) ───────────────────────────────────────────
# Scaffolding for patient ACH payments. The call sequence follows Plaid's documented Link ->
# token exchange -> transfer authorization -> transfer flow. It stays OFF until
# PATIENT_PAYMENTS_ENABLED is set; production credentials and the Plaid Transfer setup are
# provided by the owner. Card data never touches OrthoFlow (bank-account ACH only).

def patient_payments_ready() -> dict:
    """Readiness for the portal and for logs. Never exposes secrets."""
    creds = bool(settings.PLAID_CLIENT_ID and settings.PLAID_SECRET)
    return {
        "enabled": bool(settings.PATIENT_PAYMENTS_ENABLED and creds),
        "flag_on": bool(settings.PATIENT_PAYMENTS_ENABLED),
        "credentials_present": creds,
        "environment": settings.PLAID_ENVIRONMENT,
    }


async def create_patient_link_token(patient_id: str) -> str:
    """Link token for a patient in MyOrthoChart (client_user_id is the patient id, never a name)."""
    base = _PLAID_BASE.get(settings.PLAID_ENVIRONMENT, _PLAID_BASE["sandbox"])
    payload = {
        "client_id": settings.PLAID_CLIENT_ID,
        "secret": settings.PLAID_SECRET,
        "user": {"client_user_id": patient_id},
        "client_name": "MyOrthoChart",
        "products": ["auth"],
        "country_codes": ["US"],
        "language": "en",
    }
    if settings.PLAID_ENVIRONMENT == "production":
        payload["redirect_uri"] = f"{settings.PORTAL_BASE_URL.rstrip('/')}/plaid/callback"
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{base}/link/token/create", json=payload, timeout=15)
        if resp.status_code >= 400:
            raise RuntimeError(f"Plaid error: {resp.json().get('error_message', resp.text[:200])}")
        return resp.json()["link_token"]


async def initiate_patient_debit(
    public_token: str, account_id: str, amount: str, legal_name: str, idempotency_key: str
) -> dict:
    """Exchange the Link public token, authorize a one-time ACH debit and create the transfer.

    Raises RuntimeError with a patient-safe message if Plaid declines. `idempotency_key`
    (max 50 chars) makes a retried request create at most one transfer.
    """
    base = _PLAID_BASE.get(settings.PLAID_ENVIRONMENT, _PLAID_BASE["sandbox"])
    auth = {"client_id": settings.PLAID_CLIENT_ID, "secret": settings.PLAID_SECRET}
    async with httpx.AsyncClient(timeout=20) as client:
        ex = await client.post(f"{base}/item/public_token/exchange", json={**auth, "public_token": public_token})
        ex.raise_for_status()
        access_token = ex.json()["access_token"]

        az = await client.post(f"{base}/transfer/authorization/create", json={
            **auth, "access_token": access_token, "account_id": account_id,
            "type": "debit", "network": "ach", "amount": amount, "ach_class": "web",
            "user": {"legal_name": legal_name},
        })
        az.raise_for_status()
        authorization = az.json()["authorization"]
        if authorization.get("decision") != "approved":
            raise RuntimeError("Your bank could not approve this payment. Please try another account or call the office.")

        tr = await client.post(f"{base}/transfer/create", json={
            **auth, "access_token": access_token, "account_id": account_id,
            "authorization_id": authorization["id"], "amount": amount,
            "description": "Ortho payment", "idempotency_key": idempotency_key[:50],
        })
        tr.raise_for_status()
        return tr.json()["transfer"]
