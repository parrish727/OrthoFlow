# OrthoFlow — Documentation & Marketing Consistency Audit (2026-10-05)

Audit of ALL doc + marketing surfaces vs the current production feature baseline
(main==production==28541aa, alembic 029). Rule (steering): describe only what EXISTS and runs
today — no aspirational claims, no AWS references, Anthropic Claude only (Ollama = embeddings).
This file is the remediation tracker; check items off as fixed. Surfaces live in three repos:
OrthoFlow/docs + two parent docs; orthoflow-marketing; orthoflow-brochure.

## PRIORITY 0 — Ship-blocking FALSE/ASPIRATIONAL external marketing claims (fix first)
MARKETING (orthoflow-marketing/components/*.tsx + orthoflow-vs-competition.html):
- [ ] Features.tsx "Virtual Visits" card (LiveKit telehealth) — REMOVE (not shipped).
- [ ] Features.tsx "Column scheduling …start virtual visits" — remove virtual-visits phrase.
- [ ] Features.tsx "Invisalign Integration …connected to your Align Technology account / ClinChecks" — reword to internal tracking (no live Align integration).
- [ ] Features.tsx "Same-Day Denial Appeals …resubmits same day" — reword to AI denial ANALYSIS + recoverable-revenue (no auto-appeal/auto-resubmit).
- [ ] Features.tsx "Patient Messaging + AI Auto-Reply … AI auto-responds in demo mode" — remove demo-mode + AI auto-reply claim.
- [ ] Hero/Features accuracy stat "99%"/"97-99%"/"10hr" — remove/qualify unsubstantiated metrics.
- [ ] HowItWorks "AI handles the documentation" / "AI-written appeals" — soften (no AI clinical doc; analysis only).
- [ ] Pricing "Clinical note assist" / "Imaging integration" / "Custom form builder" — reword to shipped reality.
- [ ] Testimonial comparison rows: "CBCT 3D viewer", "AI clinical note dictation" (true→false/remove), SMS reminder qualifier, stale "July 2026" date.
- [ ] orthoflow-vs-competition.html: REMOVE entire Virtual Visits/Telehealth section + "Virtual Visits Included" stat; fix "Same-Day AI Denial Appeals via Stedi" (wrong), "AI Imaging Analysis" (not shipped), "AI Treatment Timeline Predictions" (not shipped), "Auto ERA 835 posting" (not shipped), "Auto-maps Cloud9/Tops" (TOPS has NO integration), unverified counts (19 perms), stale July-2026 dates, "99% accuracy".
BROCHURE (orthoflow-brochure/frontend/src/components/AgenticBrochure.tsx + index.html):
- [ ] "Predicts Your Schedule" (no-show/overbooking prediction) — reword to overdue-patients/recoverable-revenue (shipped).
- [ ] "Surfaces What Matters" treatment-timeline AI prediction — reword to imaging store + recall alerts.
- [ ] Hero "predicts your schedule" — reword.
- [ ] "SOC 2 Ready" trust badge — replace w/ true control (SSE-S3 / audit logging) or remove.
- [ ] index.html meta/keywords/OG/Twitter + JSON-LD: remove multi-specialty (GP/perio/cosmetic), perio charting, hygiene recall; scope to orthodontic. Fix JSON-LD highPrice 799→999 (mismatch w/ 299/599/999). Remove JSON-LD unshipped featureList items (perio, hygiene recall, AI timeline, multi-specialty); add shipped ones.

## PRIORITY 1 — Add MAJOR SHIPPED features missing from marketing (honest differentiators)
Add across marketing + brochure (and docs): Secure Document Exchange (office⇄patient, ClamAV
virus-scan, presigned, email confirm); AR aging 30/60/90/90-120/120+ + 90+ delinquency filter/card
+ inline AR/collections notes + ledger search; full-month calendar + Patient Flow lobby board;
MyOrthoChart secure doc upload/download; QuickBooks Online AP; Stedi eligibility; AI Letters
(writing-style aware); dashboard AI insights (recoverable revenue/unbilled/overdue).

## PRIORITY 2 — Stale internal docs (rewrite against baseline)
- [ ] docs/specs/SPEC.md — SEVERELY STALE: still an AP-invoice product; AWS Bedrock/Textract/
  SageMaker/ECS/RDS (violates no-AWS); LLM_PROVIDER=bedrock; Plaid; wrong architecture. Full rewrite
  to ortho PMS + Anthropic Claude direct + self-hosted. HIGHEST doc priority.
- [ ] OrthoFlow_Architecture_and_Roadmap.md (parent) — SEVERELY STALE/ASPIRATIONAL: CBCT 3D viewer/
  OHIF/Cornerstone/MPR, ceph tracing, DICOM device integration/Orthanc, Celery, Twilio/SendGrid
  two-way, Ollama-for-generation, stale ports, demo@marcallenortho.com. Fence roadmap vs shipped;
  purge AWS; fix AI provider. Regenerate the .pdf after.
- [ ] OrthoFlow_Product_Overview_Clinical.md (parent) — CBCT 3D viewer, DICOM device upload, "two-way
  texting", eligibility "every morning" overstatement; missing all NEW features. Separate shipped vs
  roadmap. Regenerate the .pdf after.
- [ ] docs/specs/PRD.md — MODERATE: remove LiveKit virtual-visits from "key additions"; remove §5.15
  Periodontal Charting/multi-specialty (PART2 removed perio); remove AI imaging-analysis claim; add
  AR aging/90+/AR note/search, Secure Document Exchange, dashboard AI insights; add integrations-
  reality subsection (QBO/Stedi live-ish, OrthoFi dormant, TOPS migration-only, Ortho2 connector);
  note ANTHROPIC_MODEL env-configurable.
- [ ] docs/specs/GTM.md — MODERATE: Starter tier still lists AP-invoice features; "99% classification
  accuracy" stale; soften §9 moat claims (no 6-yr data / trained denial model); add NEW features.
- [ ] docs/specs/MYORTHOCHART.md — MILD: expand doc-access item to two-way secure upload/download
  (virus-scan + email + notifications); add appt confirm; verify "Medication Tracking" shipped.
- [ ] docs/specs/PART2_PLAN.md — dated planning artifact; leave as-is (historical).

## CROSS-CUTTING
- Pricing inconsistency: parent docs show a 4th "Self-Hosted $2,500+$99/mo" tier; PRD/GTM use 3
  tiers (Starter/Clinical/Enterprise). Pick one source of truth.
- Purge ALL AWS refs (SPEC.md). AI generation = Anthropic Claude (ANTHROPIC_MODEL, Haiku 4.5), not
  Ollama/Mistral/Bedrock. Ollama = embeddings only.
- Regenerate the two parent .pdf siblings after their .md are fixed.
- VERIFY-then-state (don't assume shipped): bracket/archwire charting granularity, 26 appt types, 19
  permission keys, Consultant role/7 consultant reports, Medication Tracking, ERA auto-posting,
  treatment-timeline prediction. If not confirmed in code, mark roadmap or remove.

## CONFIRMED CURRENT (written/updated this session — no action)
docs/onboarding/{ONBOARDING_CHECKLIST, FIRST_CLIENT_ONBOARDING_GUIDE, STAFF_TRAINING_CHECKLIST},
docs/specs/{ORTHOFI_INTEGRATION_FEASIBILITY, TOPS_INTEGRATION_INVESTIGATION,
ROADMAP_CEPH_AND_FIRST_CLIENT_2026-10-04}.

## PROCESS GOING FORWARD (user directive: keep docs+site+brochure continuously consistent)
Every feature PR that changes user-facing capability must also update: the relevant docs/specs,
marketing (orthoflow-marketing), and brochure (orthoflow-brochure) in the same change set, verified
against the live feature. Treat drift as a release blocker for customer-facing surfaces.
