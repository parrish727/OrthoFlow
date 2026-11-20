# Demo vs Production Behavior

**Date:** 2026-11-20 · The demo practice (DEMO — Brightsmile Orthodontics, id in `app/core/demo.py`) and the practices that customers have onboarded run on the same stack. Seeding and the demo setup are unchanged. What changed is that simulated behavior is limited to the demo practice.

| Behavior | Demo practice | Onboarded practice |
|---|---|---|
| Daily payer payment poll (`automation.run_payment_poll`, `POST /ortho/contracts/run-payment-poll`) | Simulated paid/pending/failed rows, as before | Skipped / 409. No fabricated results |
| Claim submission (`POST /claims/{id}/submit`) | Simulated acknowledgment, always, even after Stedi goes live (fake patients never reach a real payer) | Real submission only. If live submission is off or the clearinghouse fails, the claim stays a draft and the user sees why |
| Simulated adjudication / ERA (`POST /claims/{id}/adjudicate`) | Allowed | 403. Real payments post from the payer's 835 |
| Eligibility check once `STEDI_LIVE_CLAIMS` is on | Uses stored benefits, never calls a production payer with fake subscribers | Real Stedi call with the patient's subscriber data |
| Demo auto-reply to portal messages | As before (already limited to the demo practice id) | None |

Tests: `tests/test_demo_gating.py`, `tests/test_stedi.py`. Verified against a throwaway database: real practice poll 0 rows and 409, claim stays draft, adjudicate 403; demo practice unchanged.

## Found, not changed
- Appeal submission to the payer (`ai_claims.submit_appeal_to_payer`, `appeal_automation`) calls `StediClient.resubmit_claim`, which does not exist. For a real practice that path errors. Needs to be built before appeals can be sent electronically.
- Demo seed files still contain simulated data by design; they only populate the demo practice.
