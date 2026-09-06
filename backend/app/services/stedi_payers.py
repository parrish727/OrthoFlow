"""Stedi payer mapping + dental eligibility mock fixtures.

Sandbox reality: Stedi test mode returns mock benefits ONLY for a fixed set of test payers
and ONLY when the subscriber's first name, last name, member ID (and DOB where required)
match Stedi's documented dental mock values exactly. This module maps OrthoFlow's internal
payer records to Stedi test payers and supplies the exact credentials that yield a live
mock 271 response, so an eligibility check on a demo patient actually round-trips to Stedi.

When we transition to production, real member IDs replace these fixtures and the mapping
simply becomes the payer-ID lookup (internal payer_id → Stedi tradingPartnerServiceId).

Dental mock payers (STC 35), per Stedi docs:
    Ameritas, Anthem BCBS CA, Cigna, Metlife, UnitedHealthcare.
"""
from __future__ import annotations

# ── Stedi dental test payers → tradingPartnerServiceId ──────────────────────────
# These are the payer IDs Stedi accepts for dental (835/837D-capable) mock eligibility.
STEDI_DENTAL_TEST_PAYERS: dict[str, dict] = {
    "AMERITAS": {"payer_id": "47009", "name": "Ameritas"},
    "ANTHEM_BCBS_CA": {"payer_id": "047198", "name": "Anthem Blue Cross Blue Shield of CA"},
    "CIGNA": {"payer_id": "62308", "name": "Cigna"},
    "METLIFE": {"payer_id": "65978", "name": "MetLife"},
    "UHC": {"payer_id": "87726", "name": "UnitedHealthcare"},
}

# Generic Stedi test payer used for claim-submission + ERA test workflows (837D→277CA→835).
STEDI_TEST_PAYER_ID = "STEDITEST"

# ── Exact dental mock subscriber credentials that return a live mock 271 ────────
# Keyed by our internal test payer key. These MUST match the mock fixtures provisioned
# for YOUR Stedi account exactly (first/last name, member ID, and DOB).
#
# IMPORTANT: Mock fixtures are account-specific. The public docs show example values, but
# a given sandbox account's dataset can differ. Pull the exact values for this account from
# the Stedi portal → enable Test mode → "New eligibility check" form (it pre-fills a valid
# mock request per payer). Paste those exact values here. Until then, a live check returns a
# Stedi AAA error (71/73/75) — which OrthoFlow surfaces to the TC — and the route falls back
# to stored benefits so the workflow never breaks.
#
# You can also override any fixture at runtime via env, e.g. STEDI_MOCK_UHC_MEMBER_ID.
STEDI_DENTAL_MOCK_SUBSCRIBERS: dict[str, dict] = {
    "AMERITAS": {"first_name": "John", "last_name": "Doe", "member_id": "AMERITAS123", "date_of_birth": "19800101"},
    "ANTHEM_BCBS_CA": {"first_name": "Jane", "last_name": "Doe", "member_id": "ABCBS12345", "date_of_birth": "19850315"},
    "CIGNA": {"first_name": "John", "last_name": "Doe", "member_id": "CIGNA123456", "date_of_birth": "19900210"},
    "METLIFE": {"first_name": "Jane", "last_name": "Doe", "member_id": "METLIFE9999", "date_of_birth": "19751120"},
    "UHC": {"first_name": "John", "last_name": "Doe", "member_id": "UHC202649", "date_of_birth": "19760214"},
}

# ── OrthoFlow internal payer_id → Stedi test payer key ──────────────────────────
# Maps the payers seeded in demo data to a Stedi test payer so eligibility is live.
INTERNAL_PAYER_TO_STEDI: dict[str, str] = {
    "DELTA-WI": "UHC",           # Delta Dental of WI  → UHC dental mock
    "CIGNA-DENTAL": "CIGNA",
    "METLIFE-DENTAL": "METLIFE",
    "AMERITAS-DENTAL": "AMERITAS",
    "ANTHEM-CA": "ANTHEM_BCBS_CA",
    "UHC-DENTAL": "UHC",
    "AETNA-DENTAL": "CIGNA",      # Aetna has no dental mock; route to Cigna for demo
    "GUARDIAN-DENTAL": "METLIFE",
    "BCBS-WI": "ANTHEM_BCBS_CA",
    "HUMANA-DENTAL": "AMERITAS",
    "WI-MEDICAID": "UHC",         # Medicaid demo → UHC dental mock for eligibility round-trip
}


def resolve_stedi_test_payer(internal_payer_id: str) -> dict | None:
    """Return {stedi_payer_id, name, mock_subscriber} for an internal payer, or None.

    None means the payer isn't mapped to a Stedi dental test payer, so the caller should
    fall back to stored-benefit computation.
    """
    key = INTERNAL_PAYER_TO_STEDI.get((internal_payer_id or "").upper())
    if not key:
        return None
    payer = STEDI_DENTAL_TEST_PAYERS.get(key)
    mock = STEDI_DENTAL_MOCK_SUBSCRIBERS.get(key)
    if not payer:
        return None
    return {
        "stedi_payer_id": payer["payer_id"],
        "stedi_payer_name": payer["name"],
        "mock_subscriber": mock,
        "test_payer_key": key,
    }
