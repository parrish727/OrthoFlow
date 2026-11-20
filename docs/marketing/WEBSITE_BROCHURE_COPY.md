# Website and brochure copy: Stedi, Plaid and the collections cadence

**Date:** 2026-11-20 · **For:** Frontend agent + QA review (per the 2026-10-05 routing directive).
The website (`orthoflow-marketing`) and brochure (`orthoflow-brochure`) live in the MelaninTech repo, on a branch with 48 uncommitted files from other work, so they were not edited here. Insert the copy below. Keep the benefit-first tone from `DOC_MARKETING_AUDIT_2026-10-05.md`.

## Where
- Website `components/Features.tsx`: add a "Collections that keep going" feature card; add a "Built with Stedi and Plaid" strip near the integrations or trust section.
- Website `orthoflow-vs-competition.html`: replace "Auto-maps Cloud9/Tops" and "Same-Day AI Denial Appeals via Stedi" (both flagged wrong in the audit) with the claims below.
- Brochure `AgenticBrochure.tsx` and `index.html` (meta, JSON-LD featureList): add the same card and partner line; drop perio, hygiene recall and multi-specialty items.

## Copy (all verified against code or docs; see `docs/marketing/README.md`)
**Feature card, "Collections that keep going":** Many billing tools stop tracking at 90 to 120 days. OrthoFlow follows up at 30, 60, 90, 120 and 180 days past due, tied to your patients' real payment due dates, with a secure pay link texted straight to MyOrthoChart. Choose automatic or manual follow-up when you set up your practice.

**Partner strip:** Built with Stedi and Plaid. Stedi powers insurance eligibility checks, claims and remittances. Plaid powers secure bank connections for patient payments.

**One-liner for meta description:** The orthodontic-only practice platform with insurance checks, claims and collections follow-up built in.

## Do not publish yet
- "Pay by bank in MyOrthoChart" as an available feature (off until `PATIENT_PAYMENTS_ENABLED`).
- Recurring auto-pay.
- Any vendor name other than Stedi and Plaid as a partner or integration.
- "Automatic" without "optional": reminders are opt-in per practice.
