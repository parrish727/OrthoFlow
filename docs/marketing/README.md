# OrthoFlow marketing assets (2026-11-20)

- `ORTHOFLOW_PITCH_DECK.html`: 8-slide branded deck and practice-facing explainer. Open in a browser, then Print > Save as PDF (landscape, no margins).
- `social/`: AR/Collections cadence and Stedi/Plaid cards. `node build_cards.mjs` regenerates `social/out/*.svg` and `*.png` (square 1080x1080, landscape 1200x627). Needs macOS (QuickLook + sips). Edit `MILESTONES`/`CAP` at the top if the cadence changes.

Brand: teal `#00C2A8`, navy `#0B1B2B`, Inter (system fallback), logos in `frontend/public/brand/`.

## Claim evidence (every claim traces to code or a doc)
| Claim | Evidence |
|---|---|
| 30/60/90/120/180 cadence, due dates, opt-in automatic reminders | `backend/app/services/ar_aging.py`, `ar_outreach.py`, `Ledger.tsx`, `docs/specs/AR_COLLECTIONS_CADENCE.md` |
| Stedi eligibility and claims (partner) | `services/stedi.py`; live claim submission is the `STEDI_LIVE_CLAIMS` switch |
| Plaid bank connections (partner) | `services/plaid.py`. **Patient pay-by-bank is off until `PATIENT_PAYMENTS_ENABLED`; do not advertise it as available until then.** |
| Inline AR notes, aging, ledger search | PR #33, `finance.py` |
| Staff-triggered letters and bulk text | `routes/ai_letters.py`, `routes/reports.py` (report builder, bundle-message) |
| Claim drafted at checkout, never auto-submitted | `routes/ortho_ops.py` work-done |
| Ceph suite, 3D beta | `docs/specs/CEPH_SUITE_COMPLETE_2026-10-05.md` |
| Stedi built, live claims off until go-live | `core/config.py` (`STEDI_LIVE_CLAIMS=False`) |
| Hosting, isolation, encryption, BAA before go-live | `docs/specs/DATA_HOSTING_AND_LOCALITY.md`, governance data-protection and BAA policies |
| Onboarding steps, 1 to 2 weeks | `docs/onboarding/FIRST_CLIENT_ONBOARDING_GUIDE.md` |

Not claimed anywhere: recurring auto-pay, patient pay-by-bank as available (until enabled), any OrthoFi connection, telehealth, "HIPAA certified", "data never leaves our network". Do not name OrthoFi or other vendors in public material.
