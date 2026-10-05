# OrthoFi ↔ OrthoFlow Integration — Feasibility & Bridge Design

**Date:** 2026-10-04 · **Status:** Scaffolding shipped (dormant); live activation pending partnership.

## Why
OrthoFi is used by a large share of orthodontic practices for digital new-patient intake, insurance
verification, benefit calculation, and contract setup. Its key limitation: it **stops tracking at
~120 days**. OrthoFlow's AR aging + 90+/120+ delinquency tracking (shipped) is built to own exactly
that long tail. Doctors treat "do you integrate with OrthoFi?" as a standard due-diligence question,
so a credible bridge is strategically important for landing OrthoFi-using practices.

## Feasibility findings (discovery 2026-10-04)
- **No public OrthoFi developer API.** OrthoFi integrations are **partner-driven**, not self-serve.
  Documented integrations include **Gaidge** (analytics) and **Ortho2 Edge Cloud**, where the model
  is **PMS → OrthoFi import** ("OrthoFi can import patient, responsible party, and appointment
  information directly from Edge Cloud"). Direction is typically data flowing *into* OrthoFi from a
  PMS — not an outbound API we can freely consume.
- **Implication:** we cannot code against a real OrthoFi API today. A live integration requires a
  **partnership conversation** to obtain an API/endpoint or an agreed export format.
- **Relationship path:** OrthoFi CEO/co-founder is **Dave Ternan** (confirms the "David" Slalom
  connection). Action: reach out via LinkedIn referencing the Slalom overlap to open an integration
  discussion; follow OrthoFi + Dave's posts; monitor the Orthopreneurs podcast.

## What we shipped now (source-agnostic bridge scaffolding)
Rather than fabricate an integration, we built the OrthoFlow side so a real feed plugs in with no
rework — mirroring how Stedi/ADP connectors stay dormant until first-customer activation.
- `app/services/orthofi.py`: `status()` (configured/dormant + mode) and `import_handoff(...)` that
  takes a parsed `OrthoFiHandoff` (patient identity + outstanding balance + plan at the hand-off
  boundary), **creates/matches the patient**, and **seeds the outstanding balance into the OrthoFlow
  ledger** so AR tracking continues. Idempotent per `external_id` (tagged in `reference_number` as
  `ORTHOFI:<id>`); also writes a provenance AR note surfaced on the Ledger roster.
- `GET /api/v1/finance/orthofi/status`, `POST /api/v1/finance/orthofi/handoff`.
- Config (dormant): `ORTHOFI_ENABLED=False`, `ORTHOFI_API_KEY`, `ORTHOFI_BASE_URL`.

**Source-agnostic by design:** the importer works from an already-parsed record, so the handoff can
arrive from (a) a future OrthoFi API, or (b) a CSV/JSON export the practice/OrthoFi provides at the
120-day boundary. The latter is usable **immediately** for a practice that can export from OrthoFi,
with zero dependency on OrthoFi engineering.

## Activation paths (in order of likelihood)
1. **Export/import (available now):** practice exports 120-day+ balances from OrthoFi (CSV/JSON) →
   OrthoFlow ingests via the handoff endpoint. No OrthoFi partnership needed.
2. **Partner API (requires conversation):** if the Dave Ternan outreach yields API access, set
   `ORTHOFI_ENABLED/ORTHOFI_API_KEY/ORTHOFI_BASE_URL`, add a pull-sync in `orthofi.py` that maps
   OrthoFi records → `OrthoFiHandoff`, and the existing importer handles the rest.

## Risks / notes
- Patient matching is name + DOB (no external_id column on Patient). Low risk at import volume; if a
  practice needs exact external-id mapping, add a `patients.orthofi_external_id` column later.
- Keep the bridge dormant in prod until a real feed exists; the endpoints are safe (manual, audited,
  idempotent) but should not imply a live OrthoFi connection in the UI until configured.

## Next actions
- [ ] pktech_dev: LinkedIn outreach to Dave Ternan (Slalom overlap) re: integration.
- [ ] Confirm whether the first client can export 120-day+ balances from OrthoFi (enables path 1 now).
- [ ] If API granted: implement `orthofi.pull_sync()` mapping → `OrthoFiHandoff`; flip ORTHOFI_ENABLED.
