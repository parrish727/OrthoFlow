"""Stedi Clearinghouse Integration — 837D dental claims submission, eligibility, and status."""
import asyncio
import os
import logging
from datetime import date, datetime, timezone

import httpx

from app.services.clearinghouse import SubmissionResult, ClaimStatus, EligibilityResponse

logger = logging.getLogger(__name__)

STEDI_API_KEY = os.environ.get("STEDI_API_KEY", "")
STEDI_BASE_URL = os.environ.get("STEDI_BASE_URL", "https://healthcare.stedi.com/2024-04-01")
STEDI_TIMEOUT = 30.0
MAX_RETRIES = 3
BACKOFF_BASE = 1.0  # seconds


class StediError(Exception):
    """Raised when Stedi API returns a non-recoverable error."""

    def __init__(self, message: str, status_code: int | None = None, response_body: dict | None = None):
        self.message = message
        self.status_code = status_code
        self.response_body = response_body or {}
        super().__init__(self.message)


class StediClient:
    """Concrete implementation of ClearinghouseAdapter for Stedi Healthcare API."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key or STEDI_API_KEY
        self.base_url = base_url or STEDI_BASE_URL
        if not self.api_key:
            raise StediError("STEDI_API_KEY not configured — set it in environment variables")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _request(self, method: str, path: str, json_body: dict | None = None) -> dict:
        """Execute an HTTP request with retry + exponential backoff."""
        url = f"{self.base_url}{path}"
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=STEDI_TIMEOUT) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=self._headers(),
                        json=json_body,
                    )

                if response.status_code == 429:
                    # Rate limited — backoff and retry
                    wait = BACKOFF_BASE * (2 ** attempt)
                    logger.warning(f"Stedi rate limited (429), retrying in {wait}s (attempt {attempt + 1}/{MAX_RETRIES})")
                    await asyncio.sleep(wait)
                    continue

                if response.status_code >= 500:
                    # Server error — retry
                    wait = BACKOFF_BASE * (2 ** attempt)
                    logger.warning(f"Stedi server error ({response.status_code}), retrying in {wait}s")
                    await asyncio.sleep(wait)
                    continue

                if response.status_code >= 400:
                    body = response.json() if response.content else {}
                    raise StediError(
                        message=body.get("message", f"Stedi API error {response.status_code}"),
                        status_code=response.status_code,
                        response_body=body,
                    )

                return response.json() if response.content else {}

            except httpx.TimeoutException as e:
                last_error = e
                wait = BACKOFF_BASE * (2 ** attempt)
                logger.warning(f"Stedi request timeout, retrying in {wait}s (attempt {attempt + 1}/{MAX_RETRIES})")
                await asyncio.sleep(wait)
            except StediError:
                raise
            except httpx.HTTPError as e:
                last_error = e
                wait = BACKOFF_BASE * (2 ** attempt)
                logger.warning(f"Stedi HTTP error: {e}, retrying in {wait}s")
                await asyncio.sleep(wait)

        raise StediError(
            message=f"Stedi request failed after {MAX_RETRIES} attempts: {last_error}",
            status_code=None,
        )

    def _format_837d_claim(self, claim_data: dict) -> dict:
        """Format claim data into Stedi 837D dental JSON structure."""
        return {
            "transactionSetPurposeCode": "00",  # Original
            "claimInformation": {
                "claimFrequencyCode": "1",  # Original claim
                "patientControlNumber": claim_data.get("patient_control_number", ""),
                "totalClaimChargeAmount": str(claim_data.get("total_billed", "0.00")),
                "placeOfServiceCode": claim_data.get("place_of_service", "11"),  # Office
                "claimSupplementalInformation": {
                    "priorAuthorizationNumber": claim_data.get("prior_auth_number"),
                },
            },
            "subscriber": {
                "memberId": claim_data.get("subscriber_id", ""),
                "firstName": claim_data.get("subscriber_first_name", ""),
                "lastName": claim_data.get("subscriber_last_name", ""),
                "dateOfBirth": claim_data.get("subscriber_dob", ""),
                "gender": claim_data.get("subscriber_gender", ""),
            },
            "patient": {
                "firstName": claim_data.get("patient_first_name", ""),
                "lastName": claim_data.get("patient_last_name", ""),
                "dateOfBirth": claim_data.get("patient_dob", ""),
                "gender": claim_data.get("patient_gender", ""),
                "address": {
                    "address1": claim_data.get("patient_address", ""),
                    "city": claim_data.get("patient_city", ""),
                    "state": claim_data.get("patient_state", ""),
                    "postalCode": claim_data.get("patient_zip", ""),
                },
            },
            "billingProvider": {
                "npi": claim_data.get("billing_provider_npi", ""),
                "taxId": claim_data.get("billing_tax_id", ""),
                "name": claim_data.get("billing_provider_name", ""),
                "address": {
                    "address1": claim_data.get("billing_address", ""),
                    "city": claim_data.get("billing_city", ""),
                    "state": claim_data.get("billing_state", ""),
                    "postalCode": claim_data.get("billing_zip", ""),
                },
            },
            "renderingProvider": {
                "npi": claim_data.get("rendering_provider_npi", ""),
                "firstName": claim_data.get("rendering_first_name", ""),
                "lastName": claim_data.get("rendering_last_name", ""),
            },
            "receiver": {
                "organizationName": claim_data.get("payer_name", ""),
                "payerId": claim_data.get("payer_id", ""),
            },
            "serviceLines": [
                {
                    "serviceDate": line.get("service_date", ""),
                    "procedureCode": line.get("cdt_code", ""),
                    "chargeAmount": str(line.get("billed_amount", "0.00")),
                    "toothNumber": line.get("tooth_number"),
                    "toothSurface": line.get("tooth_surface"),
                    "diagnosisCodePointer": line.get("diagnosis_pointer", "1"),
                    "oralCavityDesignation": line.get("oral_cavity", ""),
                }
                for line in claim_data.get("service_lines", [])
            ],
            "diagnosisCodes": claim_data.get("diagnosis_codes", []),
        }

    async def submit_dental_claim(self, claim_data: dict) -> SubmissionResult:
        """Submit a dental claim (837D) to Stedi."""
        try:
            formatted = self._format_837d_claim(claim_data)
            response = await self._request("POST", "/claims/dental", json_body=formatted)

            return SubmissionResult(
                success=True,
                claim_id=response.get("claimId"),
                tracking_number=response.get("trackingNumber"),
                errors=None,
            )
        except StediError as e:
            logger.error(f"Stedi claim submission failed: {e.message}")
            return SubmissionResult(
                success=False,
                claim_id=None,
                tracking_number=None,
                errors=[e.message] + e.response_body.get("errors", []),
            )

    async def submit_attachment(
        self, claim_id: str, attachment_type: str, content: bytes, filename: str
    ) -> dict:
        """Submit a claim attachment (e.g., X-rays, narratives, EOBs)."""
        import base64

        payload = {
            "claimId": claim_id,
            "attachmentType": attachment_type,  # "narrative", "xray", "periodontal_chart", "eob"
            "fileName": filename,
            "contentBase64": base64.b64encode(content).decode("utf-8"),
        }
        return await self._request("POST", "/claims/attachments", json_body=payload)

    async def resubmit_claim(
        self, original_claim_id: str, corrected_data: dict, appeal_narrative: str
    ) -> SubmissionResult:
        """Resubmit a denied claim with corrections and appeal narrative."""
        try:
            formatted = self._format_837d_claim(corrected_data)
            formatted["claimInformation"]["claimFrequencyCode"] = "7"  # Replacement claim
            formatted["claimInformation"]["originalClaimReference"] = original_claim_id
            formatted["claimInformation"]["appealNarrative"] = appeal_narrative

            response = await self._request("POST", "/claims/dental", json_body=formatted)

            return SubmissionResult(
                success=True,
                claim_id=response.get("claimId"),
                tracking_number=response.get("trackingNumber"),
                errors=None,
            )
        except StediError as e:
            logger.error(f"Stedi claim resubmission failed: {e.message}")
            return SubmissionResult(
                success=False,
                claim_id=None,
                tracking_number=None,
                errors=[e.message] + e.response_body.get("errors", []),
            )

    async def check_status(self, claim_id: str) -> ClaimStatus:
        """Check claim adjudication status (276/277 transaction)."""
        try:
            response = await self._request("GET", f"/claims/{claim_id}/status")

            # Map Stedi status to our internal status
            stedi_status = response.get("status", "pending").lower()
            status_map = {
                "accepted": "accepted",
                "in_process": "pending",
                "pending": "pending",
                "finalized": "paid",
                "denied": "denied",
                "rejected": "rejected",
            }

            adjudication_date = None
            if response.get("adjudicationDate"):
                adjudication_date = date.fromisoformat(response["adjudicationDate"])

            return ClaimStatus(
                claim_id=claim_id,
                status=status_map.get(stedi_status, "pending"),
                payer_claim_number=response.get("payerClaimNumber"),
                adjudication_date=adjudication_date,
                paid_amount=response.get("paidAmount"),
                denial_codes=response.get("denialCodes"),
            )
        except StediError as e:
            logger.error(f"Stedi status check failed for {claim_id}: {e.message}")
            return ClaimStatus(
                claim_id=claim_id,
                status="pending",
                denial_codes=[f"Status check error: {e.message}"],
            )

    async def check_eligibility(self, subscriber: dict) -> EligibilityResponse:
        """Real-time eligibility verification (270/271 transaction)."""
        try:
            payload = {
                "subscriber": {
                    "memberId": subscriber.get("subscriber_id", ""),
                    "firstName": subscriber.get("first_name", ""),
                    "lastName": subscriber.get("last_name", ""),
                    "dateOfBirth": subscriber.get("date_of_birth", ""),
                },
                "provider": {
                    "npi": subscriber.get("provider_npi", ""),
                },
                "payer": {
                    "payerId": subscriber.get("payer_id", ""),
                },
                "serviceTypes": subscriber.get("service_types", ["35"]),  # 35 = Dental Care
                "dateOfService": subscriber.get("date_of_service", date.today().isoformat()),
            }
            response = await self._request("POST", "/eligibility/check", json_body=payload)

            return EligibilityResponse(
                eligible=response.get("eligible", False),
                subscriber_id=subscriber.get("subscriber_id", ""),
                coverage_active=response.get("coverageActive", False),
                plan_name=response.get("planName"),
                remaining_benefit=response.get("remainingBenefit"),
                copay=response.get("copay"),
                errors=None,
            )
        except StediError as e:
            logger.error(f"Stedi eligibility check failed: {e.message}")
            return EligibilityResponse(
                eligible=False,
                subscriber_id=subscriber.get("subscriber_id", ""),
                coverage_active=False,
                errors=[e.message],
            )
