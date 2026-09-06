"""Stedi Healthcare Clearinghouse Integration.

Implements the ClearinghouseAdapter protocol against Stedi's real API contract:

    • Eligibility (270/271):  POST {base}/change/medicalnetwork/eligibility/v3   [LIVE in test mode]
    • Dental claims (837D):   POST {base}/dental-claims/submission              [PROD only — simulated in sandbox]
    • Claim status (276/277): retrieved from 277CA acknowledgments               [PROD only — simulated in sandbox]
    • Remittance (835 ERA):   GET  {base}/reports/835                            [PROD only — simulated in sandbox]

SANDBOX BEHAVIOR
────────────────
Stedi sandbox / test-mode accounts support ONLY mock eligibility checks against a fixed
set of test payers (Ameritas, Anthem BCBSCA, Cigna, Metlife, UnitedHealthcare, and the
generic STEDITEST payer). Test *claim* submission and ERA retrieval require a production
account. To keep the full Claims → Payments → Ledger workflow demonstrable end-to-end
without a production account, this client:

    1. Sends REAL eligibility checks to Stedi test mode (when the payer maps to a Stedi
       test payer and STEDI_ENABLED is true), and
    2. SIMULATES claim submission, 277CA acknowledgment, and 835 ERA generation using the
       exact request/response shapes documented by Stedi, so the workflow is production-
       faithful. Flip STEDI_LIVE_CLAIMS=true (with a production key) to submit for real.

Auth: Stedi uses a raw API key in the Authorization header (NOT a Bearer token).

Docs: https://www.stedi.com/docs/healthcare
"""
from __future__ import annotations

import asyncio
import logging
import random
import secrets
import string
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

import httpx

from app.core.config import settings
from app.services.clearinghouse import (
    ClaimStatus,
    EligibilityResponse,
    ERA835,
    SubmissionResult,
)

logger = logging.getLogger(__name__)

STEDI_TIMEOUT = 120.0  # Stedi holds real-time eligibility open up to 120s
MAX_RETRIES = 3
BACKOFF_BASE = 1.0  # seconds

# Basic-character-set alphabet for Patient Control Numbers (PCN) — Stedi recommends
# a hard-to-guess random string ≤ 17 chars using only the X12 basic character set.
_PCN_ALPHABET = string.ascii_uppercase + string.digits


class StediError(Exception):
    """Raised when Stedi API returns a non-recoverable error."""

    def __init__(self, message: str, status_code: int | None = None, response_body: dict | None = None):
        self.message = message
        self.status_code = status_code
        self.response_body = response_body or {}
        super().__init__(self.message)


def _gen_pcn() -> str:
    """Generate a strong, unique 17-char Patient Control Number (basic charset)."""
    return "".join(secrets.choice(_PCN_ALPHABET) for _ in range(17))


def _gen_control_number(width: int = 9) -> str:
    return "".join(secrets.choice(string.digits) for _ in range(width))


def _money(value) -> Decimal:
    return Decimal(str(value or "0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class StediClient:
    """Stedi Healthcare API adapter.

    Eligibility is genuinely live against Stedi test mode. Claims/ERA are simulated to
    Stedi's real contract while the account is sandbox (STEDI_LIVE_CLAIMS=false).
    """

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key if api_key is not None else settings.STEDI_API_KEY
        self.base_url = (base_url or settings.STEDI_BASE_URL).rstrip("/")
        self.provider_npi = settings.STEDI_PROVIDER_NPI
        self.provider_org = settings.STEDI_PROVIDER_ORG_NAME
        self.live_claims = settings.STEDI_LIVE_CLAIMS
        if not self.api_key:
            raise StediError("STEDI_API_KEY not configured — set it in environment variables")

    # ── HTTP plumbing ──────────────────────────────────────────────────────────

    def _headers(self, idempotency_key: str | None = None) -> dict[str, str]:
        # Stedi authenticates with the raw API key (no "Bearer " prefix).
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        json_body: dict | None = None,
        idempotency_key: str | None = None,
    ) -> dict:
        """Execute an HTTP request with retry + exponential backoff on 429/5xx/timeouts."""
        url = f"{self.base_url}{path}"
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=STEDI_TIMEOUT) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=self._headers(idempotency_key),
                        json=json_body,
                    )

                if response.status_code == 429:
                    wait = BACKOFF_BASE * (2 ** attempt)
                    logger.warning(f"Stedi rate limited (429), retry in {wait}s ({attempt + 1}/{MAX_RETRIES})")
                    await asyncio.sleep(wait)
                    continue

                if response.status_code >= 500:
                    wait = BACKOFF_BASE * (2 ** attempt)
                    logger.warning(f"Stedi server error ({response.status_code}), retry in {wait}s")
                    await asyncio.sleep(wait)
                    continue

                if response.status_code >= 400:
                    body = response.json() if response.content else {}
                    raise StediError(
                        message=body.get("message") or body.get("error") or f"Stedi API error {response.status_code}",
                        status_code=response.status_code,
                        response_body=body,
                    )

                return response.json() if response.content else {}

            except httpx.TimeoutException as e:
                last_error = e
                wait = BACKOFF_BASE * (2 ** attempt)
                logger.warning(f"Stedi timeout, retry in {wait}s ({attempt + 1}/{MAX_RETRIES})")
                await asyncio.sleep(wait)
            except StediError:
                raise
            except httpx.HTTPError as e:
                last_error = e
                wait = BACKOFF_BASE * (2 ** attempt)
                logger.warning(f"Stedi HTTP error: {e}, retry in {wait}s")
                await asyncio.sleep(wait)

        raise StediError(f"Stedi request failed after {MAX_RETRIES} attempts: {last_error}")

    # ── Eligibility (270/271) — LIVE in test mode ───────────────────────────────

    async def check_eligibility(self, subscriber: dict) -> EligibilityResponse:
        """Real-time dental eligibility verification (270/271).

        Expects a dict with keys: trading_partner_service_id (payer ID), first_name,
        last_name, member_id, date_of_birth (YYYYMMDD), and optionally provider_npi,
        provider_org, service_type_codes, date_of_service (YYYYMMDD).

        Returns a parsed EligibilityResponse extracting active-coverage status, plan name,
        remaining benefit, deductible, and co-pay from Stedi's benefitsInformation[] array.
        """
        payer_id = subscriber.get("trading_partner_service_id") or subscriber.get("payer_id", "")
        member_id = subscriber.get("member_id") or subscriber.get("subscriber_id", "")

        payload: dict = {
            "tradingPartnerServiceId": payer_id,
            "encounter": {
                # Dental care STC is "35"; Stedi dental mocks require exactly "35".
                "serviceTypeCodes": subscriber.get("service_type_codes", ["35"]),
            },
            "provider": {
                "organizationName": subscriber.get("provider_org") or self.provider_org,
                "npi": subscriber.get("provider_npi") or self.provider_npi,
            },
            "subscriber": {
                "firstName": subscriber.get("first_name", ""),
                "lastName": subscriber.get("last_name", ""),
                "memberId": member_id,
            },
        }
        # dateOfBirth and dateOfService are optional; include when provided.
        if subscriber.get("date_of_birth"):
            payload["subscriber"]["dateOfBirth"] = subscriber["date_of_birth"]
        if subscriber.get("date_of_service"):
            payload["encounter"]["dateOfService"] = subscriber["date_of_service"]

        try:
            response = await self._request(
                "POST", "/change/medicalnetwork/eligibility/v3", json_body=payload
            )
            return self._parse_eligibility(response, member_id)
        except StediError as e:
            logger.error(f"Stedi eligibility check failed: {e.message}")
            return EligibilityResponse(
                eligible=False,
                subscriber_id=member_id,
                coverage_active=False,
                errors=[e.message] + (e.response_body.get("errors") or []),
            )

    def _parse_eligibility(self, response: dict, member_id: str) -> EligibilityResponse:
        """Parse a Stedi 271 JSON response into our EligibilityResponse.

        Stedi returns coverage in planStatus[] and financial responsibility in
        benefitsInformation[] where code: 1=Active Coverage, B=Co-Payment, C=Deductible,
        F=Limitations, A=Co-Insurance, G=Out of Pocket.
        """
        errors = [e.get("description", str(e)) if isinstance(e, dict) else str(e)
                  for e in (response.get("errors") or [])]

        plan_status = response.get("planStatus") or []
        benefits = response.get("benefitsInformation") or []

        coverage_active = any(ps.get("statusCode") == "1" for ps in plan_status) or any(
            b.get("code") == "1" for b in benefits
        )

        plan_name = None
        for ps in plan_status:
            if ps.get("planDetails"):
                plan_name = ps["planDetails"]
                break
        if not plan_name:
            for b in benefits:
                if b.get("code") == "1" and b.get("planCoverage"):
                    plan_name = b["planCoverage"]
                    break

        copay = self._first_benefit_amount(benefits, "B")            # Co-Payment
        deductible_remaining = self._first_benefit_amount(
            benefits, "C", time_qualifier_code="29"                  # Deductible, Remaining
        )
        remaining_benefit = self._first_benefit_amount(
            benefits, "F"                                            # Limitations (often the plan max)
        )

        return EligibilityResponse(
            eligible=coverage_active and not errors,
            subscriber_id=member_id,
            coverage_active=coverage_active,
            plan_name=plan_name,
            remaining_benefit=remaining_benefit,
            copay=copay,
            errors=errors or None,
            raw=response,
            deductible_remaining=deductible_remaining,
            application_mode=(response.get("meta") or {}).get("applicationMode"),
            trace_id=(response.get("meta") or {}).get("traceId"),
            eligibility_check_id=response.get("id"),
        )

    @staticmethod
    def _first_benefit_amount(
        benefits: list[dict], code: str, time_qualifier_code: str | None = None
    ) -> float | None:
        """Return the first benefitAmount matching a benefit code (and optional time qualifier)."""
        for b in benefits:
            if b.get("code") != code:
                continue
            if time_qualifier_code and b.get("timeQualifierCode") != time_qualifier_code:
                continue
            amt = b.get("benefitAmount")
            if amt is not None:
                try:
                    return float(amt)
                except (TypeError, ValueError):
                    return None
        return None

    # ── Dental claim (837D) — PROD only; simulated in sandbox ───────────────────

    def build_837d(self, claim_data: dict) -> dict:
        """Build a Stedi 837D dental-claim JSON payload from OrthoFlow claim data.

        This matches Stedi's Dental Claims JSON endpoint contract exactly, so switching to
        live submission is a config flag (STEDI_LIVE_CLAIMS) rather than a rewrite.
        """
        pcn = claim_data.get("patient_control_number") or _gen_pcn()
        usage_indicator = "P" if self.live_claims and settings.ENVIRONMENT == "production" else "T"

        service_lines = []
        for i, line in enumerate(claim_data.get("service_lines", []), 1):
            sl: dict = {
                "serviceDate": line.get("service_date", ""),
                "providerControlNumber": line.get("provider_control_number") or f"{pcn}-{i:02d}",
                "dentalService": {
                    "procedureCode": line.get("cdt_code", ""),
                    "lineItemChargeAmount": str(line.get("billed_amount", "0.00")),
                    "procedureCount": line.get("quantity", 1),
                },
            }
            if line.get("tooth_number"):
                sl["dentalService"]["oralCavityDesignation"] = [str(line["tooth_number"])]
                sl["teethInformation"] = [{
                    "toothCode": str(line["tooth_number"]),
                    "toothSurfaceCodes": list(line.get("tooth_surface", "")) or None,
                }]
            service_lines.append(sl)

        payload: dict = {
            "usageIndicator": usage_indicator,
            "tradingPartnerServiceId": claim_data.get("payer_id", ""),
            "tradingPartnerName": claim_data.get("payer_name", ""),
            "submitter": {
                "organizationName": claim_data.get("billing_provider_name") or self.provider_org,
                "submitterIdentification": settings.STEDI_SUBMITTER_ID or claim_data.get("billing_tax_id", ""),
                "contactInformation": {
                    "name": "BILLING DEPARTMENT",
                    "phoneNumber": claim_data.get("billing_phone", ""),
                },
            },
            "receiver": {
                "organizationName": claim_data.get("payer_name", ""),
            },
            "subscriber": {
                "paymentResponsibilityLevelCode": "P",
                "memberId": claim_data.get("subscriber_id", ""),
                "firstName": claim_data.get("subscriber_first_name", ""),
                "lastName": claim_data.get("subscriber_last_name", ""),
                "groupNumber": claim_data.get("group_number", ""),
                "dateOfBirth": claim_data.get("subscriber_dob", ""),
            },
            "rendering": {
                "providerType": "RenderingProvider",
                "npi": claim_data.get("rendering_provider_npi", ""),
                "firstName": claim_data.get("rendering_first_name", ""),
                "lastName": claim_data.get("rendering_last_name", ""),
            },
            "claimInformation": {
                "claimFilingCode": claim_data.get("claim_filing_code", "CI"),  # CI=Commercial, MC=Medicaid
                "patientControlNumber": pcn,
                "claimChargeAmount": str(claim_data.get("total_billed", "0.00")),
                "placeOfServiceCode": claim_data.get("place_of_service", "11"),  # 11=Office
                "claimFrequencyCode": claim_data.get("claim_frequency_code", "1"),
                "signatureIndicator": "Y",
                "planParticipationCode": "A",
                "benefitsAssignmentCertificationIndicator": "Y",
                "releaseInformationCode": "Y",
                "serviceLines": service_lines,
            },
            "billing": {
                "providerType": "BillingProvider",
                "organizationName": claim_data.get("billing_provider_name") or self.provider_org,
                "npi": claim_data.get("billing_provider_npi", ""),
                "employerId": claim_data.get("billing_tax_id", ""),
            },
        }
        if claim_data.get("prior_auth_number"):
            payload["claimInformation"]["claimSupplementalInformation"] = {
                "priorAuthorizationNumber": claim_data["prior_auth_number"],
            }
        return payload, pcn

    async def submit_dental_claim(self, claim_data: dict) -> SubmissionResult:
        """Submit a dental claim (837D).

        In sandbox (STEDI_LIVE_CLAIMS=false) this simulates Stedi's synchronous response
        + 277CA acknowledgment. With a production key and STEDI_LIVE_CLAIMS=true it POSTs
        to the real Dental Claims endpoint.
        """
        payload, pcn = self.build_837d(claim_data)

        if not self.live_claims:
            return self._simulate_submission(payload, pcn)

        try:
            response = await self._request(
                "POST", "/dental-claims/submission",
                json_body=payload, idempotency_key=pcn,
            )
            ref = response.get("claimReference", {})
            return SubmissionResult(
                success=response.get("status") == "SUCCESS",
                claim_id=ref.get("correlationId") or ref.get("rhclaimNumber"),
                tracking_number=ref.get("patientControlNumber", pcn),
                errors=None,
                raw=response,
            )
        except StediError as e:
            logger.error(f"Stedi dental claim submission failed: {e.message}")
            return SubmissionResult(success=False, errors=[e.message] + (e.response_body.get("errors") or []))

    def _simulate_submission(self, payload: dict, pcn: str) -> SubmissionResult:
        """Produce a Stedi-faithful synchronous claim response + 277CA acknowledgment (sandbox)."""
        correlation_id = "01" + "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(24))
        service_lines = payload["claimInformation"]["serviceLines"]
        simulated_response = {
            "status": "SUCCESS",
            "controlNumber": _gen_control_number(1),
            "tradingPartnerServiceId": payload["tradingPartnerServiceId"],
            "claimReference": {
                "correlationId": correlation_id,
                "patientControlNumber": pcn,
                "timeOfResponse": datetime.now(timezone.utc).isoformat(),
                "payerId": payload["tradingPartnerServiceId"],
                "formatVersion": "5010",
                "rhclaimNumber": correlation_id,
                "serviceLines": [
                    {"lineItemControlNumber": sl["providerControlNumber"]} for sl in service_lines
                ],
            },
            "meta": {"traceId": correlation_id, "applicationMode": "test", "simulated": True},
            "payer": {
                "payerName": payload["tradingPartnerName"],
                "payerId": payload["tradingPartnerServiceId"],
            },
            "acknowledgment277ca": {
                "status": "A1",  # A1 = acknowledged / accepted for processing
                "statusDescription": "Acknowledgement/Receipt - claim received (simulated 277CA)",
                "patientControlNumber": pcn,
            },
            "httpStatusCode": "200 OK",
        }
        return SubmissionResult(
            success=True,
            claim_id=correlation_id,
            tracking_number=pcn,
            errors=None,
            raw=simulated_response,
        )

    # ── Remittance (835 ERA) — PROD only; simulated in sandbox ──────────────────

    def simulate_era(self, claim_data: dict, adjudication: dict) -> ERA835:
        """Synthesize an 835 ERA remittance from a claim + adjudication decision (sandbox).

        `adjudication` provides total_allowed, total_paid, patient_responsibility, and an
        optional per-line breakdown. Mirrors the shape of Stedi's 835 ERA report so Payments
        and Ledger posting logic is identical to production.
        """
        trace_number = "ERA" + _gen_control_number(9)
        payment_date = date.today()
        total_paid = _money(adjudication.get("total_paid", 0))

        era_claim = {
            "patientControlNumber": claim_data.get("patient_control_number", ""),
            "claimStatusCode": adjudication.get("claim_status_code", "1"),  # 1 = Processed as Primary
            "totalClaimChargeAmount": str(_money(claim_data.get("total_billed", 0))),
            "claimPaymentAmount": str(total_paid),
            "patientResponsibilityAmount": str(_money(adjudication.get("patient_responsibility", 0))),
            "serviceLines": adjudication.get("service_lines", []),
            "claimAdjustments": adjudication.get("claim_adjustments", []),
        }

        return ERA835(
            trace_number=trace_number,
            payer_name=claim_data.get("payer_name", ""),
            payment_date=payment_date,
            total_paid=float(total_paid),
            claims=[era_claim],
        )

    # ── Claim status (276/277) — PROD only; simulated in sandbox ────────────────

    async def check_status(self, claim_id: str, simulated_status: str | None = None) -> ClaimStatus:
        """Check claim adjudication status. Simulated in sandbox (no 276/277 in test mode)."""
        if not self.live_claims:
            return ClaimStatus(
                claim_id=claim_id,
                status=simulated_status or "accepted",
                payer_claim_number=None,
            )
        try:
            response = await self._request("GET", f"/claims/{claim_id}/status")
            stedi_status = (response.get("status") or "pending").lower()
            status_map = {
                "accepted": "accepted", "in_process": "pending", "pending": "pending",
                "finalized": "paid", "denied": "denied", "rejected": "rejected",
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
            return ClaimStatus(claim_id=claim_id, status="pending", denial_codes=[f"Status check error: {e.message}"])
