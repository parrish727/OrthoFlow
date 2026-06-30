# OrthoFlow v2.1 — Medicare/Medicaid Insurance Claims Processing

## Feature Summary

Add full Medicare and Medicaid claims lifecycle management to OrthoFlow, enabling orthodontic practices to submit, track, and reconcile government insurance claims while maintaining compliance with CMS guidelines and state-specific Medicaid rules.

---

## Problem Statement

Orthodontic practices accepting Medicare/Medicaid must:
1. Verify patient eligibility before treatment
2. Submit prior authorizations (required for most ortho under Medicaid)
3. Generate compliant electronic claims (837D format)
4. Process remittance advice (835 ERA) and auto-post payments
5. Follow state-specific Medicaid fee schedules and age/coverage limits
6. Maintain audit trails for CMS compliance

OrthoFlow currently stores insurance carrier names as text fields and pulls claims from Ortho2 for EOB matching — but has no native claims submission, eligibility verification, or government payer compliance logic.

---

## Scope

### In Scope (v2.1)
- Eligibility verification (270/271 HIPAA transactions)
- Prior authorization workflow (submission + status tracking)
- Claims submission (837D dental electronic claims)
- ERA/remittance processing (835 parsing + auto-posting)
- Medicaid fee schedule enforcement (state-configurable)
- CDT code validation (D8000-series orthodontic codes)
- Coordination of Benefits (COB) for dual-eligible patients
- NPI/provider enrollment status tracking
- Claim status inquiry (276/277 transactions)
- Denial management + resubmission workflow

### Out of Scope (future)
- Direct Medicare Part A/B medical claims (OrthoFlow is dental-focused)
- Clearinghouse partnership negotiation (use existing: Tesia, DentalXChange, or NEA)
- State Medicaid enrollment application assistance
- Real-time adjudication

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  OrthoFlow Frontend                                              │
│  ├── /claims           — Claims dashboard (submit, track, deny) │
│  ├── /eligibility      — Real-time eligibility check            │
│  └── /settings/payers  — Payer config, fee schedules, NPI       │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│  FastAPI Backend                                                  │
│  ├── /api/v1/claims         — CRUD + submission + status         │
│  ├── /api/v1/eligibility    — 270/271 verification               │
│  ├── /api/v1/prior-auth     — authorization requests             │
│  ├── /api/v1/remittance     — 835 ERA import + auto-post         │
│  └── /api/v1/payers        — payer config + fee schedules        │
└──────┬──────────────────────────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────────────────┐
│  Claims Engine (app/services/claims/)                             │
│  ├── eligibility.py    — 270/271 transaction builder/parser      │
│  ├── submission.py     — 837D claim generation + validation      │
│  ├── remittance.py     — 835 ERA parser + payment posting        │
│  ├── prior_auth.py     — authorization request management        │
│  ├── denial.py         — denial reason mapping + resubmission    │
│  ├── fee_schedule.py   — state Medicaid fee schedule engine      │
│  ├── cdt_codes.py      — CDT code validation + ortho subset      │
│  └── clearinghouse.py  — adapter interface (Tesia/DentalXChange) │
└──────┬──────────────────────────────────────────────────────────┘
       │
┌──────▼──────┐
│Clearinghouse│ ← SFTP/API (837D out, 835/277 in)
│  (External) │
└─────────────┘
```

---

## Data Models

### InsuranceClaim
```python
class InsuranceClaim(Base):
    __tablename__ = "insurance_claims"

    id: Mapped[uuid] = mapped_column(primary_key=True)
    practice_id: Mapped[uuid] = mapped_column(ForeignKey("practices.id"))
    patient_id: Mapped[str]                    # PMS patient ID
    patient_name: Mapped[str]
    subscriber_id: Mapped[str]                 # Medicare/Medicaid member ID
    payer_id: Mapped[str]                      # Payer identifier
    payer_type: Mapped[str]                    # "medicare" | "medicaid" | "commercial"
    state_code: Mapped[str | None]            # For Medicaid state rules
    claim_number: Mapped[str | None]          # Assigned after submission
    status: Mapped[str]                        # draft|submitted|accepted|rejected|paid|denied|appealed
    cdt_codes: Mapped[list] = mapped_column(JSONB)  # [{code, description, fee, units}]
    total_billed: Mapped[Decimal]
    total_allowed: Mapped[Decimal | None]
    total_paid: Mapped[Decimal | None]
    patient_responsibility: Mapped[Decimal | None]
    prior_auth_number: Mapped[str | None]
    rendering_provider_npi: Mapped[str]
    billing_provider_npi: Mapped[str]
    service_date: Mapped[date]
    submission_date: Mapped[datetime | None]
    adjudication_date: Mapped[datetime | None]
    denial_codes: Mapped[list | None] = mapped_column(JSONB)
    denial_reason: Mapped[str | None]
    era_reference: Mapped[str | None]         # 835 trace number
    coordination_of_benefits: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

### PriorAuthorization
```python
class PriorAuthorization(Base):
    __tablename__ = "prior_authorizations"

    id: Mapped[uuid] = mapped_column(primary_key=True)
    practice_id: Mapped[uuid]
    patient_id: Mapped[str]
    payer_id: Mapped[str]
    auth_number: Mapped[str | None]           # Assigned by payer
    status: Mapped[str]                        # pending|approved|denied|expired
    treatment_type: Mapped[str]               # comprehensive|phase_i|phase_ii|limited
    cdt_codes: Mapped[list] = mapped_column(JSONB)
    clinical_notes: Mapped[str]               # Required for Medicaid ortho
    diagnostic_codes: Mapped[list] = mapped_column(JSONB)  # ICD-10 (malocclusion)
    requested_date: Mapped[date]
    approved_date: Mapped[date | None]
    expiration_date: Mapped[date | None]
    approved_amount: Mapped[Decimal | None]
    denial_reason: Mapped[str | None]
```

### PracticePayerConfig
```python
class PracticePayerConfig(Base):
    __tablename__ = "practice_payer_configs"

    id: Mapped[uuid] = mapped_column(primary_key=True)
    practice_id: Mapped[uuid]
    payer_id: Mapped[str]
    payer_name: Mapped[str]
    payer_type: Mapped[str]                    # medicare|medicaid|commercial
    state_code: Mapped[str | None]
    enrolled: Mapped[bool] = mapped_column(default=False)
    npi: Mapped[str]
    tax_id: Mapped[str]
    clearinghouse: Mapped[str]                 # tesia|dentalxchange|nea
    clearinghouse_id: Mapped[str]             # Practice's clearinghouse account
    fee_schedule: Mapped[dict | None] = mapped_column(JSONB)
    submission_method: Mapped[str]            # electronic|portal
    notes: Mapped[str | None]
```

---

## CDT Codes (Orthodontic Subset)

Key codes OrthoFlow must validate:
| Code | Description | Typical Medicaid Coverage |
|------|-------------|--------------------------|
| D8010 | Limited ortho treatment (transitional dentition) | Varies by state |
| D8020 | Limited ortho treatment (adolescent dentition) | Varies by state |
| D8030 | Limited ortho treatment (adult dentition) | Rarely covered |
| D8040 | Limited ortho treatment (early intervention) | Most states |
| D8070 | Comprehensive ortho (transitional dentition) | With prior auth |
| D8080 | Comprehensive ortho (adolescent dentition) | With prior auth |
| D8090 | Comprehensive ortho (adult dentition) | Rarely covered |
| D8210 | Removable appliance therapy | Most states |
| D8220 | Fixed appliance therapy | Most states |
| D8660 | Pre-ortho treatment visit | Most states |
| D8670 | Periodic ortho treatment visit | Most states |
| D8680 | Ortho retention | Varies |
| D8681 | Removable retainer adjustment | Varies |
| D8695 | Removal of fixed ortho appliances | Most states |
| D8999 | Unspecified ortho procedure (by report) | Requires documentation |

---

## Medicaid State Rules Engine

Each state has different orthodontic Medicaid rules. The system stores these as configurable JSON:

```json
{
  "NC": {
    "age_limit": 20,
    "requires_prior_auth": true,
    "handicapping_score_required": true,
    "min_hld_score": 26,
    "covered_codes": ["D8070", "D8080", "D8210", "D8220", "D8660", "D8670", "D8680", "D8695"],
    "max_treatment_months": 36,
    "fee_schedule": {
      "D8080": 4200.00,
      "D8670": 195.00,
      "D8695": 250.00
    },
    "billing_notes": "NC Medicaid requires HLD Index score ≥26 for comprehensive ortho. Submit with clinical photos and ceph tracing."
  }
}
```

---

## Clearinghouse Integration

Abstract interface supporting multiple clearinghouses:

```python
class ClearinghouseAdapter(Protocol):
    async def submit_claim(self, claim_837d: str) -> SubmissionResult: ...
    async def check_status(self, claim_id: str) -> ClaimStatus: ...
    async def fetch_remittance(self, since: date) -> list[ERA835]: ...
    async def verify_eligibility(self, request_270: str) -> EligibilityResponse: ...
```

Initial implementation targets **Tesia** (widely used in dental) with DentalXChange as secondary.

---

## Compliance Requirements

| Requirement | Implementation |
|-------------|---------------|
| HIPAA 837D format | X12 5010 compliant claim generation |
| NPI validation | Luhn check + NPPES lookup on enrollment |
| Fee schedule enforcement | Block billing above Medicaid allowed amount |
| Prior auth tracking | Expiration alerts, auto-attach to claims |
| Audit trail | All claim actions logged (AuditLog table) |
| PHI encryption | Subscriber IDs, patient names encrypted at rest |
| Timely filing | Configurable deadline alerts per payer |
| Dual eligibility | COB logic: Medicare primary → Medicaid secondary |

---

## Frontend Pages

### /claims (Claims Dashboard)
- Filterable list: status, payer, date range, patient
- Bulk submission for draft claims
- Denial queue with one-click resubmission
- Revenue summary: billed vs. paid vs. outstanding

### /eligibility
- Patient lookup → real-time 270/271 check
- Coverage details: active dates, remaining benefits, copay
- Batch eligibility check (upcoming appointments)

### /settings/payers
- Add/configure payers (Medicare, state Medicaid, commercial)
- Upload/configure fee schedules
- NPI and enrollment status per payer
- Clearinghouse connection settings

---

## Implementation Phases

### Phase 1 (v2.1.0) — Foundation
- Data models + migrations
- CDT code validation engine
- Payer configuration UI
- Manual claim creation (draft → review → submit)
- Fee schedule enforcement

### Phase 2 (v2.1.1) — Electronic Submission
- Clearinghouse adapter (Tesia)
- 837D claim generation
- 835 ERA parsing + auto-posting
- Eligibility verification (270/271)

### Phase 3 (v2.1.2) — Intelligence
- Prior authorization workflow
- Denial management + appeal tracking
- Claim status polling (276/277)
- AI-assisted denial reason analysis + resubmission suggestions
- Batch operations (bulk submit, bulk eligibility)

---

## Dependencies

- Clearinghouse account (Tesia or DentalXChange) — practice must enroll
- Practice must be enrolled with Medicare/Medicaid as a provider
- NPI numbers for rendering and billing providers
- State Medicaid fee schedule data (publicly available per state)

---

## Success Metrics

- Claims submitted electronically vs. manual portal entry
- Average days to payment (target: <30 days)
- Denial rate reduction (AI-assisted resubmission)
- Eligibility check coverage (% of patients verified before treatment)
- Revenue captured from previously missed Medicaid-eligible patients

---

*Scoped: May 28, 2026*
*Target: OrthoFlow v2.1 (Insurance Claims Processing)*
*Priority: High — enables practices to accept government insurance patients*
