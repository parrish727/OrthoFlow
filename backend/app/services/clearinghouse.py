"""Clearinghouse Adapter Interface — abstract protocol for claim submission."""
from typing import Protocol
from dataclasses import dataclass
from datetime import date


@dataclass
class SubmissionResult:
    success: bool
    claim_id: str | None = None
    tracking_number: str | None = None
    errors: list[str] | None = None


@dataclass
class ClaimStatus:
    claim_id: str
    status: str  # accepted, rejected, pending, paid
    payer_claim_number: str | None = None
    adjudication_date: date | None = None
    paid_amount: float | None = None
    denial_codes: list[str] | None = None


@dataclass
class EligibilityResponse:
    eligible: bool
    subscriber_id: str
    coverage_active: bool
    plan_name: str | None = None
    remaining_benefit: float | None = None
    copay: float | None = None
    errors: list[str] | None = None


@dataclass
class ERA835:
    trace_number: str
    payer_name: str
    payment_date: date
    total_paid: float
    claims: list[dict]  # [{claim_id, paid, allowed, patient_resp, adjustments}]


class ClearinghouseAdapter(Protocol):
    """Protocol for clearinghouse integrations. Implement per vendor."""

    async def submit_claim(self, claim_837d: str) -> SubmissionResult:
        """Submit an 837D claim to the clearinghouse."""
        ...

    async def check_status(self, claim_id: str) -> ClaimStatus:
        """Check claim adjudication status (276/277)."""
        ...

    async def fetch_remittance(self, since: date) -> list[ERA835]:
        """Fetch ERA/835 remittance advice since a date."""
        ...

    async def verify_eligibility(self, subscriber_id: str, payer_id: str, provider_npi: str) -> EligibilityResponse:
        """Real-time eligibility verification (270/271)."""
        ...


class TesiaClearinghouse:
    """Tesia clearinghouse adapter — placeholder for implementation."""

    def __init__(self, api_key: str, practice_id: str):
        self.api_key = api_key
        self.practice_id = practice_id
        self.base_url = "https://api.tesia.com/v1"

    async def submit_claim(self, claim_837d: str) -> SubmissionResult:
        # TODO: Implement SFTP/API submission to Tesia
        return SubmissionResult(success=False, errors=["Tesia integration not yet configured. Enroll at tesia.com."])

    async def check_status(self, claim_id: str) -> ClaimStatus:
        return ClaimStatus(claim_id=claim_id, status="pending")

    async def fetch_remittance(self, since: date) -> list[ERA835]:
        return []

    async def verify_eligibility(self, subscriber_id: str, payer_id: str, provider_npi: str) -> EligibilityResponse:
        return EligibilityResponse(eligible=False, subscriber_id=subscriber_id, coverage_active=False, errors=["Eligibility check not yet configured."])


class DentalXChangeClearinghouse:
    """DentalXChange adapter — placeholder for implementation."""

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.base_url = "https://api.dentalxchange.com"

    async def submit_claim(self, claim_837d: str) -> SubmissionResult:
        return SubmissionResult(success=False, errors=["DentalXChange integration not yet configured."])

    async def check_status(self, claim_id: str) -> ClaimStatus:
        return ClaimStatus(claim_id=claim_id, status="pending")

    async def fetch_remittance(self, since: date) -> list[ERA835]:
        return []

    async def verify_eligibility(self, subscriber_id: str, payer_id: str, provider_npi: str) -> EligibilityResponse:
        return EligibilityResponse(eligible=False, subscriber_id=subscriber_id, coverage_active=False, errors=["DentalXChange eligibility not yet configured."])
