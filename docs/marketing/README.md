# OrthoFlow marketing assets (2026-11-20)

- `ORTHOFLOW_PITCH_DECK.html`: 8-slide branded deck and practice-facing explainer. Open in a browser, then Print > Save as PDF (landscape, no margins).
- `social/`: AR/Collections long-tail cards. `node build_cards.mjs` regenerates `social/out/*.svg` and `*.png` (square 1080x1080, landscape 1200x627). Needs macOS (QuickLook + sips). Edit `START`/`CAP` at the top if OrthoFi confirms a different limit.

Brand: teal `#00C2A8`, navy `#0B1B2B`, Inter (system fallback), logos in `frontend/public/brand/`.

## Claim evidence (every claim traces to code or a doc)
| Claim | Evidence |
|---|---|
| Long-tail window, statuses, filter | `backend/app/services/ar_longtail.py`, `Ledger.tsx`, `docs/specs/AR_LONGTAIL_HANDOFF.md` |
| Inline AR notes, aging, ledger search | PR #33, `finance.py` |
| Staff-triggered letters and bulk text | `routes/ai_letters.py`, `routes/reports.py` (report builder, bundle-message) |
| Claim drafted at checkout, never auto-submitted | `routes/ortho_ops.py` work-done |
| Ceph suite, 3D beta | `docs/specs/CEPH_SUITE_COMPLETE_2026-10-05.md` |
| Stedi built, live claims off until go-live | `core/config.py` (`STEDI_LIVE_CLAIMS=False`) |
| Hosting, isolation, encryption, BAA before go-live | `docs/specs/DATA_HOSTING_AND_LOCALITY.md`, governance data-protection and BAA policies |
| Onboarding steps, 1 to 2 weeks | `docs/onboarding/FIRST_CLIENT_ONBOARDING_GUIDE.md` |

Not claimed anywhere: automatic collections outreach, a live OrthoFi connection, telehealth, "HIPAA certified", "data never leaves our network". Do not name OrthoFi in public material until the partnership is agreed.
