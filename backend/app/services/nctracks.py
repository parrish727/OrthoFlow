"""NCTracks (North Carolina Medicaid) claim destination — DORMANT until enrolled.

NCTracks is NC's Medicaid Management Information System (NC MMIS). Providers submit dental/
orthodontic claims to NCTracks electronically as ASC X12 837D, either through the NCTracks
Provider Portal or via EDI. Orthodontic services also typically require a prior approval (PA)
entered in NCTracks before claims are paid.

STATUS: SCAFFOLDED / DORMANT
────────────────────────────
Going live requires NCTracks provider enrollment (CEP registration), an NPI enrolled with NC
Medicaid, EFT setup, and an EDI trading-partner agreement / portal credentials — all completed
by pktech_dev. Until then this client is disabled (NCTRACKS_ENABLED=false) and
submit_claim() raises NCTracksUnavailable. The 837D it builds reuses OrthoFlow's existing
Stedi 837D builder shape, so wiring it live is a credential + endpoint change, not a rewrite.

Flow: Appointment → CDT → Claims → destination router → (clearinghouse | private | direct |
NCTracks). For Medicaid patients the destination is 'nctracks'.

Docs: https://www.nctracks.nc.gov (Submitting a Dental Claim; Dental/Ortho Prior Approval)
"""
from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class NCTracksUnavailable(RuntimeError):
    """Raised when NCTracks is invoked while dormant (not yet enrolled/enabled)."""


class NCTracksClient:
    """Thin NC Medicaid (NCTracks) 837D claim submission client. Dormant by default."""

    CLAIM_FILING_CODE = "MC"  # Medicaid
    TRANSACTION = "837D"      # dental claim

    def __init__(self, api_url: str | None = None, credentials: dict | None = None):
        self.enabled = getattr(settings, "NCTRACKS_ENABLED", False)
        self.api_url = api_url or getattr(settings, "NCTRACKS_API_URL", "")
        self.provider_npi = getattr(settings, "STEDI_PROVIDER_NPI", "")
        self.credentials = credentials or {}

    def _require_enabled(self) -> None:
        if not self.enabled:
            raise NCTracksUnavailable(
                "NCTracks is dormant. It requires NC Medicaid provider enrollment (CEP) + EDI "
                "trading-partner setup and NCTRACKS_ENABLED=true. Configure creds/enrollment first "
                "(pktech_dev). Until then, Medicaid claims are prepared but not transmitted."
            )

    def build_837d(self, claim_data: dict) -> dict:
        """Build a Medicaid 837D payload (claimFilingCode=MC). Reuses the Stedi builder shape."""
        from app.services.stedi import StediClient
        data = {**claim_data, "claim_filing_code": self.CLAIM_FILING_CODE}
        payload, pcn = StediClient(api_key="scaffold").build_837d(data)
        payload["_destination"] = "nctracks"
        return payload, pcn

    async def submit_claim(self, claim_data: dict) -> dict:
        """Submit an 837D Medicaid claim to NCTracks. Dormant until enrolled/enabled."""
        payload, pcn = self.build_837d(claim_data)
        if not self.enabled:
            # Prepared-but-not-transmitted: return a scaffold receipt so the workflow can
            # record the claim as "queued for NCTracks" without pretending it was sent.
            logger.info("NCTracks dormant — Medicaid claim prepared but not transmitted (PCN %s)", pcn)
            return {
                "status": "PREPARED_NOT_SENT",
                "destination": "nctracks",
                "patient_control_number": pcn,
                "reason": "NCTracks not enrolled/enabled — configure credentials to transmit.",
                "payload_ready": True,
            }
        # Live path (future): transmit 837D to NCTracks EDI endpoint.
        raise NCTracksUnavailable("Live NCTracks transmission not yet implemented — enrollment pending.")

    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "transaction": self.TRANSACTION,
            "claim_filing_code": self.CLAIM_FILING_CODE,
            "reason": None if self.enabled else "Dormant — requires NC Medicaid enrollment + EDI setup.",
        }
