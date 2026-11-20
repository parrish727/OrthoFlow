# OrthoFlow Financial Layer: Stedi + Plaid (replaces the OrthoFi integration)

**Date:** 2026-11-20 · **Decision:** OrthoFi is not available as a partner right now, so the OrthoFi integration is removed. OrthoFlow covers the same job itself with its partners Stedi (clearinghouse) and Plaid (bank connections and payments).

## Why no integration is needed
OrthoFi sits next to a practice management system (Dolphin, Cloud 9, Ortho2) and imports from it. OrthoFlow *is* the practice management system and the financial layer in one database, so there is nothing to import between them. Practices moving from Dolphin or Cloud 9 use the migration import (`pms_import.py`, Migration page, CSV/XML exports, Ortho2 connector).

## What OrthoFi does and where it lives in OrthoFlow

| Job | OrthoFlow today | Partner | Gap |
|---|---|---|---|
| Digital new-patient paperwork | MyOrthoChart forms: intake, health history, consent, financial agreement | none | None for forms |
| Insurance verification | Eligibility 270/271 (`services/stedi.py`) and the contract "verify insurance" step | **Stedi** | Production key goes live with the partnership activation |
| Benefit calculation | Lifetime-benefit tracking; contract carries insurance estimate and patient portion | Stedi (271 data) | **Estimate is typed by staff, not computed from the 271.** Next build |
| Contract and payment plan | Contracts, plus **new** monthly installment schedule with due dates (migration 034) | none | None |
| Claims (837D) and ERA (835) | Claim drafting at checkout, clearinghouse workflow | **Stedi** | Live submission is a config switch (`STEDI_LIVE_CLAIMS`), turned on at go-live |
| Collect patient payments | **New** MyOrthoChart pay-by-bank (ACH), scaffolded and off by default | **Plaid** | See "Plaid" below |
| Early and late delinquency tracking | **New** cadence at 30/60/90/120/180 days with a pay link; opt-in automatic sending | Twilio (SMS) | See `AR_COLLECTIONS_CADENCE.md` |
| Recurring auto-pay on due dates | Not built | Plaid | Needs stored bank authorization, mandate language and ACH return handling |

## Plaid: what is built and what the owner provides
Built (scaffold, `PATIENT_PAYMENTS_ENABLED=False`): `POST /portal/billing/pay/link-token`, `POST /portal/billing/pay`, and `GET /portal/billing/pay/status`; Plaid Link in MyOrthoChart; link token, public-token exchange, transfer authorization (WEB debit) and transfer create, with an idempotency key so a retry cannot double-charge; a pending payment posted to the ledger; checks that the amount is positive and not above the balance. No card data is handled. The fake saved Visa 4242 that `/portal/billing/methods` returned has been removed.

**Contract finding (2026-11-20):** the draft Plaid reseller agreement in `BusinessDocs/Contracts` (dated 2026-10-23, countersignature not confirmed) covers Auth, Identity and Balance. It does not cover Plaid Transfer, and has no HIPAA or BAA language. The ACH debit path below therefore needs its own Plaid product approval and an originating-bank/processor arrangement, and Plaid's written HIPAA position should be obtained. See `docs/compliance/VENDOR_SECURITY_ARCHITECTURE_2026-11-20.md`.

Needed from the owner before turning it on:
1. **Plaid production credentials and API structure** (`PLAID_CLIENT_ID`, `PLAID_SECRET`, `PLAID_ENVIRONMENT=production`). Currently defaults to sandbox.
2. **Plaid Transfer approval and the funds flow.** In a Plaid debit, money lands with the party that originates the transfer. Decide how funds reach each practice (payout model, who is the originator of record, refunds, disputes). This needs Plaid and counsel, not code.
3. **Return handling.** Plaid transfer webhooks (failed, returned) so a returned ACH reverses the ledger payment. Until then returns are posted by staff and the pending ledger line says so.
4. **Patient authorization text** (NACHA web debit authorization) shown before the bank connection.

## Marketing rule
"Powered by Stedi and Plaid" is accurate as a partnership statement. Do not advertise pay-by-bank as available to patients until `PATIENT_PAYMENTS_ENABLED` is on in production. Do not advertise recurring auto-pay.

## Next builds, in order
1. Compute the benefit estimate from the Stedi 271 response and prefill the contract.
2. Plaid webhooks and ACH return handling.
3. Recurring pay-by-bank on due dates (after 2).
