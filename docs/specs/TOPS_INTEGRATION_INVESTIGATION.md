# TOPS (topsortho.com) Integration Investigation

**Date:** 2026-10-04 · **Status:** Investigation complete — no live integration path; migration-only.

## Context
The first-client prospect (5-location TX practice, consultant Adele) runs **TOPS**, a legacy ortho
PMS. Adele contacted TOPS about integration and was told TOPS does **not** integrate with any
third-party software because they offer their own product (**TopsPay / TopsPay Premier**). TopsPay
Premier only supports 30/60/90-day delinquency windows and then defaults accounts to collections —
the exact gap driving interest in OrthoFlow (the practice's delinquency sits mostly beyond 90 days).

## Findings
- **Closed ecosystem (confirmed).** TOPS positions itself as a centralized, single-vendor stack
  ("Tops centralizes more of your workflow so your team calls one place") and markets its own
  payments (TopsPay/TopsPay Premier), lab management, imaging, and scheduling. No public third-party
  API or developer portal is advertised. This matches TOPS's direct statement to the practice.
- **The only vendor-supported data path is MIGRATION, not integration.** TOPS's own "Switch Your
  Ortho PMS" guidance describes an implementation team that **assists with transferring practice
  data** when a practice moves TO TOPS. The inverse (exporting out of TOPS) would rely on the
  practice obtaining their own data export from TOPS during an offboarding.
- Contrast with ortho PMSs that DO expose integration: Ortho2 Edge Cloud (developer portal),
  Dentrix API Exchange, Greyfinch Connect. TOPS is not among these.

## Conclusion for OrthoFlow
- A **live, bidirectional TOPS↔OrthoFlow integration is not feasible** from TOPS's side (no API).
- The realistic path is **migration**: if the TX practice decides to switch, obtain a TOPS data
  export (patients, responsible parties, ledgers/balances, appointments, images) and import via
  OrthoFlow's existing migration pipeline (`services/pms_import.py`, `migration.py`), mapping their
  export format to OrthoFlow entities. Historical balances feed straight into the ledger + AR aging.
- For the delinquency pain specifically, OrthoFlow does NOT need TOPS integration to deliver value —
  the practice can run OrthoFlow's AR/90+/notes workflow on migrated or re-keyed balances, which is
  precisely what TopsPay Premier cannot do beyond 90 days.

## Recommendation
- Do not invest in a TOPS API integration (none exists to build against).
- If/when the practice commits to switching: scope a TOPS-export → OrthoFlow migration mapping as a
  one-time onboarding task (reuse the existing migration pipeline).
- Keep positioning OrthoFlow's 90+/120+ delinquency tracking + inline AR notes as the direct answer
  to the TopsPay Premier limitation.

## Related
- `docs/onboarding/ONBOARDING_CHECKLIST.md` §6 Data Migration (current PMS export intake).
- `docs/specs/ORTHOFI_INTEGRATION_FEASIBILITY.md` (the other integration track).
