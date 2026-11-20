# Security and Compliance Ownership

**Date:** 2026-11-20 · **Owner of record:** Security & Compliance (reports to pktech_dev)
OrthoFlow must stay aligned with HIPAA, PHI/PII, PCI DSS (scope: none, no card data), SOC 2 and ISO/IEC 27001 at all times. Security owns this continuously. It is not a one-time project and it is not left to whoever writes the feature.

## What Security owns
1. **Vendor inventory and agreements.** `SUBPROCESSORS.md` is the single list. No vendor receives patient data until its agreement is signed and listed as such.
2. **The PHI gate on every change.** Any PR that touches patient data, AI prompts, messaging, payments, auth, logging or infrastructure needs a Security review (checklist below) before merge.
3. **Risk register and evidence.** Controls in `VENDOR_SECURITY_ARCHITECTURE_2026-11-20.md` §4, kept current and evidenced for SOC 2 and ISO 27001.
4. **Incident response and breach notification**, including the tabletop and backup restore tests.
5. **Practice-facing contracts**: BAA, MSA, security exhibit, subprocessor list.
6. **Standing rule:** a compliance claim in sales or marketing copy must match the code and a signed agreement. Security signs off on every such claim.

## Automated guards already in the code
- `tests/test_deid.py::test_only_the_gateway_calls_the_anthropic_api` fails the build if any module other than `services/anthropic_gateway.py` calls the AI provider.
- The gateway fails closed: if an identifier survives scrubbing, the request is refused.
- `test_no_managed_cloud_llm_path` fails if a managed-cloud LLM path returns.
- Audit logging on patient data access; no PHI in logs (`core/logging.py`).

## PR checklist (also in `.github/pull_request_template.md`)
- [ ] Does this send patient data to a new or existing third party? If yes: vendor is in `SUBPROCESSORS.md` with a signed agreement.
- [ ] Any AI prompt goes through `anthropic_gateway` with a `DeidSession`; new identifier types are registered.
- [ ] No PHI in URLs, query strings, logs, error messages or SMS text.
- [ ] No card numbers accepted or stored. Bank data stays out of clinical tables.
- [ ] New data is practice-scoped (`practice_id`) and audit-logged.
- [ ] Marketing or docs claims touched by this change are still true.

## Frameworks: where each lives
| Framework | Where we evidence it |
|---|---|
| HIPAA Security Rule | Risk analysis, BAAs, audit log, access control, encryption, backups, incident runbook |
| PHI/PII | De-identification layer (`AI_DEIDENTIFICATION.md`), minimum-necessary SMS, subprocessor list |
| PCI DSS | Out of card scope: ACH bank payments only. Never accept card numbers. If cards are added later, use a hosted payment page (SAQ A) |
| SOC 2 | "SOC 2 Ready" posture only; no attestation program yet. Do not claim certified |
| ISO/IEC 27001 | Not certified. Controls mapped in the vendor architecture report |
