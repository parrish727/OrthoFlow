# Dental Monitoring (dentalmonitoring.com) — Competitor or Partner?

**Date:** 2026-11-20 · **Sources:** dentalmonitoring.com (home, security), integrations.dentalmonitoring.com, docs.partner.dental-monitoring.com (login required). Public pages only; no contract terms or API specifics were available.

## Verdict
**Complement, not competitor. Pursue an integration/partner conversation; do not build a competing product.**

## What Dental Monitoring (DM) is
- Remote orthodontic monitoring. Patients scan their teeth at home (smartphone, or the ScanBox pro device the practice sends home), and AI reviews the scans and flags findings such as an aligner not tracking, a wire issue or hygiene slipping.
- Positions itself as the first and only AI Software as a Medical Device in orthodontics (FDA De Novo and EU MDR, per DM). Of its 60+ tracked parameters, 21 fall under cleared indications.
- Products: Dental Monitoring (monitoring), DM Engage (lead assessment and treatment preview), DM Insights (practice analytics), SmartSTL (updated STL from scans).
- Scale claimed by DM: 2M+ patients monitored, 8,000+ dental professionals, 50 countries, 2B+ patient photos processed.

## Where it overlaps with OrthoFlow
| Area | DM | OrthoFlow | Overlap |
|---|---|---|---|
| Remote patient monitoring from home scans | Core product, regulated | Not built | None. We have no equivalent. |
| Practice analytics | DM Insights (monitoring-centred) | Reports, report builder, dashboard insights (financial and operational) | Light |
| Patient app | DM patient app | MyOrthoChart portal | Light (different purpose) |
| Practice management (scheduling, ledger, claims, charting, AR) | None | Core product | None |
| Cephalometrics | None | Ceph suite (2D live, 3D beta) | None |

DM does not do scheduling, billing, claims or charting. It relies on a PMS for those, which makes it a natural integration partner.

## Why not compete
- DM is a cleared medical device. Matching it means regulatory work (clearance, quality system) and a very large training image set. Neither is a fit for a practice-management product.
- Our strongest wedge (AR/collections long tail, AI revenue cycle) does not touch it.

## Integration route (how DM works with PMS vendors)
- DM runs a PMS integration program. Its integrations site lists about two dozen PMS integrations, including Greyfinch, Dolphin, Bonded, Sensei, OrthoBridge and Orthoadvance.
- Activation is simple: the practice generates a **DM API key** and pastes it into the PMS setup screen. Some PMSs also need extra setup or PMS support involvement.
- Typical integration behaviour on DM's pages: push a new patient from the PMS to DM with one click, pair existing patients without retyping, start/pause/stop monitoring from the patient screen, open the DM patient card from the treatment card, and pull DM scan summaries into the chart.
- DM's developer documentation sits behind a partner login (`docs.partner.dental-monitoring.com`). We need to request partner access to see the API surface, terms and fees.

## Competitive note
**Greyfinch is already on DM's integration list.** A DM integration is table stakes against Greyfinch for practices that use remote monitoring.

## Recommended path
1. Contact DM through its partner/contact channel and request integration partner access and docs. Ask about: API scope (patient create/pair, monitoring status, scan summaries, alerts), webhooks, cost and certification process, BAA, and timeline.
2. Scope a v1 around what practices actually use: pair a patient, show monitoring status and the latest scan finding on the patient chart, and link out to DM for the full scan. Do not copy DM's clinical findings into our own AI.
3. Build only after partner access and terms are confirmed. Until then, do not list DM as an integration anywhere.

## Data and compliance implications
- DM holds patient scan data on its own hosted platform (DM states it is HIPAA-compliant, signs BAAs on request, and hosts health data on third-party public-cloud infrastructure). Enabling DM for a practice means PHI is shared with a second business associate. A BAA between the practice and DM is needed, and our data-flow description must say so.
- This sits outside our self-hosted boundary described in `DATA_HOSTING_AND_LOCALITY.md`. Pitch material must not claim "all patient data stays on our infrastructure" once DM is enabled.

## Open questions
- DM partner terms and fees; whether DM requires a revenue share or certification.
- Whether practices want DM scan summaries inside OrthoFlow or are content with a deep link.
- Priority versus the OrthoFi meeting and first-client onboarding.
