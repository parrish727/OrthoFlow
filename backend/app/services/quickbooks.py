"""QuickBooks Online integration — OAuth2 + Bill creation."""
import httpx
import json
from urllib.parse import urlencode
from app.core.config import settings

_BASE_URL = {
    "sandbox": "https://sandbox-quickbooks.api.intuit.com",
    "production": "https://quickbooks.api.intuit.com",
}

_AUTH_URL = "https://appcenter.intuit.com/connect/oauth2"
_TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"


def get_auth_url(state: str) -> str:
    """Generate OAuth2 authorization URL for QuickBooks."""
    params = {
        "client_id": settings.QBO_CLIENT_ID,
        "redirect_uri": settings.QBO_REDIRECT_URI,
        "response_type": "code",
        "scope": "com.intuit.quickbooks.accounting",
        "state": state,
    }
    return f"{_AUTH_URL}?{urlencode(params)}"


async def exchange_code(code: str) -> dict:
    """Exchange authorization code for access + refresh tokens."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.QBO_REDIRECT_URI,
            },
            auth=(settings.QBO_CLIENT_ID, settings.QBO_CLIENT_SECRET),
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()


async def refresh_token(refresh_token: str) -> dict:
    """Refresh an expired access token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            auth=(settings.QBO_CLIENT_ID, settings.QBO_CLIENT_SECRET),
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()


async def create_bill(access_token: str, realm_id: str, invoice_data: dict) -> dict:
    """Create a Bill in QuickBooks from an approved OrthoFlow invoice."""
    base = _BASE_URL[settings.QBO_ENVIRONMENT]
    url = f"{base}/v3/company/{realm_id}/bill"

    # Map OrthoFlow line items to QBO Bill format
    lines = []
    for item in invoice_data.get("line_items", []):
        lines.append({
            "DetailType": "AccountBasedExpenseLineDetail",
            "Amount": item["total"],
            "Description": item["description"],
            "AccountBasedExpenseLineDetail": {
                "AccountRef": {"value": _map_category_to_account(item.get("category", "other"))},
            },
        })

    bill = {
        "VendorRef": {"name": invoice_data.get("vendor_name", "Unknown Vendor")},
        "TxnDate": invoice_data.get("invoice_date"),
        "DueDate": invoice_data.get("due_date"),
        "DocNumber": invoice_data.get("invoice_number"),
        "Line": lines,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            json=bill,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        return resp.json()


def _map_category_to_account(category: str) -> str:
    """Map OrthoFlow expense categories to QBO account IDs.
    These are defaults — practices can customize in Settings.
    """
    # Default QBO account mappings (will be configurable per practice)
    mapping = {
        "supplies": "1",      # Dental Supplies
        "lab": "2",           # Lab Expenses
        "equipment": "3",     # Equipment
        "services": "4",      # Professional Services
        "insurance": "5",     # Insurance & Clearinghouse
        "software": "6",      # Software & Technology
        "rent": "7",          # Rent & Occupancy
        "utilities": "8",     # Utilities
        "other": "9",         # Miscellaneous
    }
    return mapping.get(category, "9")
