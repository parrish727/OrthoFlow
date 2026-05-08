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
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{base}/link/token/create",
            json={
                "client_id": settings.PLAID_CLIENT_ID,
                "secret": settings.PLAID_SECRET,
                "user": {"client_user_id": user_id},
                "client_name": "OrthoFlow AI",
                "products": ["auth", "transfer"],
                "country_codes": ["US"],
                "language": "en",
                "account_filters": {
                    "depository": {"account_subtypes": ["checking"]},
                },
            },
            timeout=15,
        )
        resp.raise_for_status()
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
