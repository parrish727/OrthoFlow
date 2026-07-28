# Statement of Work: Stedi Clearinghouse Integration

**Project:** OrthoFlow AI — Stedi Electronic Claims & Appeal Automation  
**Company:** Melanin Technologies Inc.  
**Author:** pktech_dev  
**Date:** 2026-07-28  
**Status:** Draft  
**Duration:** 3 weeks  

---

## 1. Project Overview & Objectives

Integrate Stedi's API-first clearinghouse into OrthoFlow AI to enable electronic dental claim submission (837D), real-time status tracking, and same-day automated appeal on denial.

**Objectives:**

- Eliminate manual claim submission workflows for orthodontic practices
- Achieve sub-24-hour appeal turnaround on denied claims via AI-assisted review
- Provide full audit trail and HIPAA-compliant transaction logging
- Reduce claim rejection rate through pre-submission validation

---

## 2. Scope of Work

### Included

- Stedi API client module (authentication, rate limiting, error handling)
- 837D dental claim formatting and validation per X12 5010 spec
- Clinical attachment submission (NEA/DMS format via Stedi)
- Webhook receiver for 277 (status) and 835 (payment/remittance) responses
- Appeal automation pipeline: denial detection → AI review → appeal generation → staff approval → resubmission
- Staff notification system with approval gate (Slack + in-app)
- Comprehensive audit trail for all clearinghouse transactions
- End-to-end demo flow using Stedi sandbox environment
- Integration tests and load testing against sandbox

### Excluded

- See Section 9 (Out of Scope)

---

## 3. Deliverables

| # | Deliverable | Acceptance Criteria |
|---|------------|-------------------|
| 1 | **Stedi API Client Module** | Authenticated API calls succeed against sandbox. Handles rate limits, retries (3x exponential backoff), and timeout (30s). Returns typed Pydantic models. |
| 2 | **837D Claim Formatter** | Generates valid X12 5010 837D segments for orthodontic claims. Passes Stedi's pre-submission validation with zero errors on test dataset of 20 claims. |
| 3 | **Attachment Submission** | Uploads clinical evidence (X-rays, photos, narratives) linked to claim via NEA reference. Files stored in MinIO, metadata in PostgreSQL. |
| 4 | **Webhook Receiver (277/835)** | Receives and parses 277 status updates and 835 remittance advice. Updates claim status in real-time. Handles signature verification. Idempotent processing. |
| 5 | **Appeal Automation Pipeline** | On denial: AI reviews EOB reason codes → generates appeal letter with supporting clinical evidence → routes to staff for approval → resubmits on approval. Target: <4 hours denial-to-resubmit. |
| 6 | **Staff Notification + Approval Gate** | Slack notification on denial with one-click approve/reject. In-app dashboard showing pending appeals with context. 5-minute timeout escalation. |
| 7 | **Audit Trail** | Every transaction (submit, status change, denial, appeal, resubmit) logged with timestamp, user/system actor, payload hash, and outcome. Queryable via API. HIPAA-compliant retention (6 years). |
| 8 | **Demo End-to-End Flow** | Scripted demo: create patient → submit claim → receive denial webhook → auto-generate appeal → staff approves → resubmit → receive acceptance. Runs against Stedi sandbox. Documented with screenshots. |

---

## 4. Timeline

### Week 1 — Core Client + Claim Submission + Attachments

| Day | Focus |
|-----|-------|
| 1–2 | Stedi API client module (auth, connection pooling, error handling) |
| 3–4 | 837D claim formatter + pre-submission validation |
| 5 | Attachment submission (MinIO upload → Stedi link) |

**Exit Criteria:** Successfully submit a valid 837D claim with attachment to Stedi sandbox and receive acknowledgment.

### Week 2 — Webhooks + Appeal Automation + Status Sync

| Day | Focus |
|-----|-------|
| 1–2 | Webhook receiver (277/835 parsing, signature verification, idempotency) |
| 3–4 | Appeal automation pipeline (AI review, letter generation, resubmission) |
| 5 | Staff notification + approval gate (Slack integration, in-app UI) |

**Exit Criteria:** Full denial-to-resubmission cycle completes in sandbox with staff approval step.

### Week 3 — Testing, Demo, Documentation

| Day | Focus |
|-----|-------|
| 1–2 | Integration tests, edge cases, error scenarios, load testing |
| 3 | End-to-end demo flow scripting and validation |
| 4 | Documentation (API docs, runbook, architecture diagram) |
| 5 | Code review, security audit, final fixes |

**Exit Criteria:** All tests pass, demo runs cleanly, documentation complete, code review approved.

---

## 5. Technical Requirements

| Component | Technology |
|-----------|-----------|
| API Client | Python 3.11+, httpx (async), Pydantic v2 models |
| Claim Formatting | Custom X12 5010 837D serializer |
| Attachments | MinIO object storage, PostgreSQL metadata |
| Webhooks | FastAPI endpoint, HMAC signature verification |
| Appeal AI | Claude (Anthropic) for denial analysis + letter generation |
| Notifications | Slack Bot API + OrthoFlow in-app notifications |
| Audit Log | PostgreSQL with immutable append-only table |
| Queue | Redis for async job processing (appeal pipeline) |
| Testing | pytest, httpx mock, Stedi sandbox |

**Infrastructure:**
- Runs within existing OrthoFlow Docker Compose stack
- Internal service on agent-net bridge (no public port exposure for webhook processor)
- Webhook endpoint exposed via existing nginx reverse proxy at `api.orthoflowsolutions.com`
- All secrets stored in Vaultwarden, referenced by env var

---

## 6. Dependencies & Assumptions

### Dependencies

- Stedi sandbox account provisioned with API keys
- Stedi documentation for 837D dental claim formatting
- Existing OrthoFlow patient/insurance data models
- Slack bot already configured for OrthoFlow notifications
- MinIO instance available on agent-net

### Assumptions

- Stedi sandbox accurately reflects production behavior
- Practice NPI and taxonomy codes are already stored in OrthoFlow
- Insurance payer IDs are mapped in existing OrthoFlow payer table
- Claude API access available for appeal letter generation
- Staff will review and approve/reject appeals within business hours

---

## 7. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Stedi API changes during development | Low | High | Pin API version, abstract behind interface layer |
| X12 formatting edge cases for dental | Medium | Medium | Use Stedi's pre-submission validation; build test dataset from real claim examples |
| Appeal letter quality insufficient | Medium | Medium | Human approval gate ensures no bad appeals ship; iterate on prompts with real denials |
| Webhook delivery failures | Low | High | Implement polling fallback (check status every 15 min for claims without webhook response in 2 hours) |
| HIPAA compliance gap in audit trail | Low | Critical | Audit trail design reviewed against HIPAA transaction logging requirements before implementation |
| Rate limiting during high-volume submission | Low | Medium | Implement queue with configurable concurrency; respect Stedi rate limit headers |

---

## 8. Testing & Acceptance Criteria

### Unit Tests
- 837D segment generation for all orthodontic procedure codes
- Webhook payload parsing (277 and 835 variants)
- Appeal letter generation with various denial reason codes
- Audit log immutability verification

### Integration Tests
- Full claim lifecycle against Stedi sandbox (submit → ack → status → payment)
- Denial → appeal → resubmit cycle
- Webhook signature verification (valid + invalid)
- Attachment upload and linkage

### Load Tests
- 50 concurrent claim submissions without error
- Webhook receiver handles 100 events/minute without dropping

### Acceptance Criteria (Overall)
- [ ] Valid 837D claim submits and receives acknowledgment from Stedi sandbox
- [ ] Attachments linked correctly and accessible from claim record
- [ ] 277/835 webhooks received, parsed, and update claim status within 5 seconds
- [ ] Denial triggers appeal pipeline within 60 seconds of webhook receipt
- [ ] Appeal letter generated and routed to staff within 5 minutes of denial
- [ ] Staff approval triggers resubmission within 30 seconds
- [ ] All transactions have complete audit trail entries
- [ ] Demo flow runs end-to-end without manual intervention (except staff approval)
- [ ] Zero HIPAA compliance findings in security review

---

## 9. Out of Scope

- ERA (835) auto-posting to practice management billing system
- Real payer enrollment (Stedi production onboarding)
- Patient billing or statement generation
- Eligibility verification (270/271) — separate future SOW
- Prior authorization workflows
- Multi-practice tenant isolation (single-practice MVP)
- Mobile app notifications (Slack + web only)
- Historical claim migration from existing clearinghouse
- Payer-specific appeal templates (generic template with AI customization only)

---

## Approvals

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Project Lead | pktech_dev | | |
| Engineering | | | |

---

*This is an internal Statement of Work for project tracking purposes. Not a client-facing contract.*
