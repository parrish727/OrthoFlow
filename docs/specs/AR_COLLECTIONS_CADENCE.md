# OrthoFlow — AR Collections Cadence (30 / 60 / 90 / 120 / 180 days)

**Date:** 2026-11-20 · **Status:** Built on branch `feature/ar-cadence-stedi-plaid` (migration 034), pending PR approval.
**Scope:** Orthodontic patient-responsible balances only. Insurance claims age on their own lifecycle.
**Why it matters:** many billing tools stop tracking balances at 90 to 120 days. OrthoFlow keeps following up through 180, and links the patient straight to payment. This is a sales moat; see `GTM.md`.

## 1. What the cadence does

| Days past due | Reminder |
|---|---|
| 30 | Friendly: a payment is past due, pay in MyOrthoChart |
| 60 | Over 60 days, pay or call to set up a plan |
| 90 | Over 90 days, pay or call so we can help |
| 120 | Still a past-due balance, pay or talk through options |
| 180 | Final automatic reminder |

After 180 days (`AR_OUTREACH_CAP_DAYS`) OrthoFlow stops. The account needs a practice decision. The cap can be raised in config if it proves worthwhile. Days 120 to the cap are the "long tail".

**Automatic or manual is the doctor's choice.** Automatic sending is off until the owner or doctor turns it on, normally at initial setup (Setup Wizard, practice step) and any time in Settings. The Ledger long-tail view and the manual tools (AI collections letters, report-builder bulk text) work either way.

## 2. Due dates on the Ledger (answers "the Ledger needs due dates")

Each patient can have a payment-plan schedule (`payment_plan_installments`): monthly installments with a due date and amount.
- **Created automatically** when a contract is placed: the patient portion minus the down payment, split over the contract's estimated months, first due one month after placement. If the proposal has no patient portion or no estimated months, no schedule is created (nothing is guessed).
- **Set or replaced by staff:** `POST /api/v1/finance/payment-plan/{patient_id}` (first due date, months, total). Old installments are canceled, not deleted.
- **Shown** in the Ledger: next due date on each roster row, and an installment panel (paid, partial, due, overdue, upcoming) when a row is expanded.
- **Payments are applied first-in-first-out** to the oldest due installment at read time, so there is no second ledger to keep in sync. Patient payments exclude insurance payments (tied to a claim or ERA posting) and the contract's down payment.

## 3. How lateness is measured

1. **With a schedule (`due_source: schedule`):** days since the oldest installment that payments have not covered.
2. **Without a schedule (`due_source: estimated`):** days since the last patient payment, or the oldest charge if none. The Ledger labels these "est."
3. A patient with no positive balance is never late.

Only accounts with a schedule are texted automatically. Estimated accounts appear in the Ledger for staff but are never auto-texted, because the date is a guess.

### Why `/reports/ar-aging` could disagree with the Ledger (and the fix)
Before this change the two used different clocks. The Ledger roster aged the oldest *charge* (by service date). The report aged the oldest ledger *entry of any type* (by posted date), so a down payment or any early payment made a patient look as old as the contract. A patient paying monthly on a long contract could land in 120+ in one view and not the other. It was spotted in review and deliberately left unchanged at first: changing a shipped financial report's numbers needed your sign-off, and the real fix needed due dates, which did not exist. Both now call `services/ar_aging.py`, so they cannot differ. A test run against a throwaway database confirmed identical bucket totals.

## 4. Safety rules for automatic reminders (`services/ar_outreach.py`)

- Practice setting must be on (`practices.ar_auto_outreach_enabled`), set by owner or doctor, audit-logged.
- SMS consent (TCPA) required; opt-outs and the patient's quiet hours honored. No consent: nothing is sent or recorded, so it sends later if the patient opts in.
- Sent only 10:00 to 17:00 practice time (`AR_OUTREACH_TZ`, default America/New_York), once per day.
- Each milestone sent at most once per delinquency cycle (unique per patient, milestone and oldest uncovered due date). First seen at day 130: only the 120-day message goes; 30, 60 and 90 are recorded as superseded.
- Text includes first name, practice name and the MyOrthoChart link. No balance amount.
- A failed send is not recorded, so it retries on the next run.
- Every send is written to the message log and `ar_outreach_events`.

## 5. Pay link
The text links to `PORTAL_BASE_URL/portal?section=billing`. The patient signs in to MyOrthoChart (SMS code) and lands on Billing. Online payment there runs through Plaid; see `FINANCIAL_LAYER_STEDI_PLAID.md`. The link carries no token and no balance.

## 6. Not built (do not promise)
- Recurring auto-pay that charges on due dates. The "auto-pay" labels on ledger rows are display conventions from reference prefixes, not an engine.
- Automatic ACH return handling. A returned payment must be posted by staff until Plaid webhooks are wired.
- A 120/180-specific AI letter template (closest is `collections_90`).
- Email as a reminder channel.

## 7. Settings
`AR_OUTREACH_CAP_DAYS` (180), `AR_OUTREACH_TZ`, `AR_OUTREACH_START_HOUR` (10), `AR_OUTREACH_END_HOUR` (17), `PORTAL_BASE_URL`. Per practice: `ar_auto_outreach_enabled`.
