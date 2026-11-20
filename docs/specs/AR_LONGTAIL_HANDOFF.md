# OrthoFlow — AR Long-Tail Handoff (post-OrthoFi, 120–180 days)

**Date:** 2026-11-20 · **Status:** Window logic + Ledger view shipped on branch `feature/ar-longtail-orthofi-handoff` (pending PR). OrthoFi live feed: not active (see §6).
**Scope:** Orthodontic patient-responsible balances only. Insurance claims age on their own lifecycle and are out of scope here.

## 1. The rule

> OrthoFlow never works an account while an upstream financial platform (OrthoFi) is still tracking it. Our follow-up window opens **strictly after** the upstream tracking limit and closes at a cap.

| Setting | Default | Env var | Meaning |
|---|---|---|---|
| Window start | 120 days | `AR_LONGTAIL_START_DAYS` | Upstream platform's tracking limit. We activate only when delinquency is **greater than** this. |
| Window cap | 180 days | `AR_LONGTAIL_CAP_DAYS` | OrthoFlow follow-up stops here. Raise only if practice data shows it pays. |

Both are config, not code. If `CAP < START`, the cap is clamped to the start.

**Why 120.** The only source for "OrthoFi stops tracking at about 120 days" is the Adele consultant call (secondhand). Our earlier discussion also referred to 90. **Validate the exact limit with OrthoFi at the partnership meeting**, then set `AR_LONGTAIL_START_DAYS` to match. Nothing else changes.

## 2. How the clock works

Days delinquent = days since the patient's **last payment**. If the patient never paid, days since the **oldest charge**.

- A patient paying monthly on a long contract stays near 30 days and never enters the window.
- An account imported through the OrthoFi handoff (`ORTHOFI:<id>` reference) is **released by OrthoFi**. It enters the window on the handoff date, with its clock set to the start limit and counting forward. A payment after the handoff returns it to the normal day-count rule.

## 3. Statuses (returned on `GET /api/v1/finance/ledger-roster`)

| `longtail_status` | When | What staff see |
|---|---|---|
| `not_delinquent` | No balance, or no usable date | Nothing |
| `upstream_window` | Delinquent ≤ start | OrthoFi / the practice's current process owns it. OrthoFlow does not act. |
| `active` | start < days ≤ cap (or released by OrthoFi) | In the **Long-tail follow-up** filter on the Ledger |
| `past_cap` | days > cap | Needs a practice decision. No OrthoFlow outreach. |

The response also carries `longtail_days` and `longtail_window {start_days, cap_days}`.

## 4. What exists today (verified in code)

| Capability | Status |
|---|---|
| Window logic, config, statuses (`services/ar_longtail.py`) | Shipped on branch; 16 unit tests; roster verified on real Postgres (7 scenarios) |
| Ledger "Long-tail follow-up" filter with count | Shipped on branch |
| 90+/120+ aging, 90+ filter, inline AR notes, ledger search | Shipped (PR #33) |
| OrthoFi handoff import (`POST /finance/orthofi/handoff`, idempotent, seeds balance + provenance note) | Shipped, dormant until a feed exists |
| Staff-triggered outreach: AI collections letters (`collections_30/60/90`), report-builder "owes" filter with bundle SMS | Shipped |

## 5. What does NOT exist (do not promise)

- **No automatic outreach.** Nothing sends texts, emails or letters on a schedule. Staff review the long-tail list and trigger outreach. Do not describe this as "automated collections".
- **No true past-due tracking.** The ledger has no due dates or installment schedule. The clock is last-payment based, which is a proxy.
- **No 120/180-specific letter template.** The closest is `collections_90` (final notice).
- **No live OrthoFi connection.** See §6.
- **Known inconsistency:** `GET /reports/ar-aging` buckets by the oldest ledger entry of any type, so it can disagree with the Ledger roster. Fix before using the report in OrthoFi-facing material.
- The earlier roadmap note "SMS payment-link automation (30–90 day touchpoints)" is not found in code and should not be repeated.

## 6. Working with OrthoFi (partnership framing)

- **Complementary, not competing.** OrthoFi owns intake, verification, benefit calculation, contract setup and early-stage tracking. OrthoFlow starts where its tracking ends. The practice never has two systems chasing the same patient.
- **No collision by design.** The window opens only after the configured upstream limit, and handed-off accounts carry an `ORTHOFI:` provenance marker.
- **Two activation paths:** (1) practice exports balances past the limit (CSV/JSON) and we import them now, no OrthoFi engineering needed; (2) partner API/feed if OrthoFi provides one. OrthoFi has no public developer API today.
- **Asks for the meeting:** the exact tracking limit and what "stops tracking" means operationally (does the patient go to collections, or is the account simply dropped?); a handoff export format or feed; a way to signal "released" per account; their view on a 180-day cap.
- Practice outreach must respect consent and state rules (SMS consent: `docs/legal/TCPA_CONSENT_WORKFLOW.md`). Have counsel review long-tail letter wording before first use.

## 7. Decisions needed

1. Confirm the start limit (120 vs 90) with OrthoFi.
2. Approve the last-payment clock (vs. oldest-charge age).
3. Decide whether to build scheduled, staff-approved outreach for `active` accounts (not built).
4. Align `/reports/ar-aging` with the roster logic.
