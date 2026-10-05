# OrthoFlow — Roadmap & Decisions: Ceph Suite + First-Client Readiness (2026-10-04)

Captures everything discussed this session: the full Cephalometric Tracing & Analysis Suite plan,
the CBCT model decision, AND the commercial/first-client action items from the Adele (consultant)
call. Baseline: `main == production == 340a7f1`, alembic 028 (head). Deploy model: feature → PR →
main (tests) → FF to production (pktech_dev-approved). Model config: `ANTHROPIC_MODEL` env-swappable
(default Haiku 4.5); will add `ANTHROPIC_CBCT_MODEL` (default Opus) for the CBCT interpretation layer.

## TWO WORKSTREAMS — RECOMMENDED ORDER: B (commercial) FIRST, THEN A (clinical)
Rationale: Workstream B items are small, high-certainty, and directly enable landing the first
paying client (committed to a real prospect on the Adele call). Workstream A is a large clinical
module. Do the revenue-enabling quick wins + onboarding readiness first, then build the ceph suite.

────────────────────────────────────────────────────────────────────────
## WORKSTREAM A — CEPHALOMETRIC TRACING & ANALYSIS SUITE ("OrthoFlow Ceph")
Modeled on Angel Aligner's Intelligent Ceph System (ICS). Research-grounded (see citations below).

### Core design
- ONE shared primitive: landmark coordinates stored once per tracing. Every feature is (a) a
  computation over landmarks, (b) a visualization of them, or (c) a projection of them forward.
- SEMI-AUTOMATIC is the clinical standard: AI pre-places landmarks → DOCTOR reviews/adjusts →
  measurements compute. Never auto-finalize. Research: AI landmarking is highly reproducible
  (ICC~1.0) but accuracy still needs supervision (2D MRE ~0.5–0.65mm; CBCT weaker, ~59% within ±2mm/°).
- Measurements DERIVED from landmarks (not stored raw) → McNamara/Steiner/Downs/Wits/Jarabak/ABO +
  CUSTOM analyses are just different formulas over the same points. ABO = default shown.
- Superimposition aligns on STABLE reference points (SN / structural Björk) to separate treatment
  change from growth (the ICS mechanic).

### Builds on existing foundation (verified in code)
- `models/imaging.py`: PatientImage already has image_type='ceph'/'cbct', DICOM metadata (JSONB),
  SHA checksums, series grouping, MinIO storage (bucket orthoflow-imaging). Ceph tracing attaches
  ON TOP of these rows (FK to patient_images).
- Secure documents service (shipped 2026-10-04): private orthoflow-documents bucket + presigned +
  office⇄patient sync → used to deliver traced-report PDFs to chart/patient/Medicaid.
- medicaid_rules.py already references "ceph tracing" as an NC Medicaid HLD submission requirement.

### CBCT MODEL DECISION (answer to "most capable model")
State of the art for 3D CBCT landmarking is NOT a general LLM. It's specialized 3D medical-imaging
models: nnU-Net heatmap regression (nnLandmark, ~1.2–1.5mm = human inter-rater variability) and
attention/LSTM 3D nets (SA-LSTM). Architecture:
- 2D lateral ceph → Claude vision model (ANTHROPIC_MODEL) for landmark suggestion + interpretation.
- 3D CBCT → SELF-HOSTED 3D model (nnU-Net/nnLandmark family) for actual coordinates; Claude OPUS
  (ANTHROPIC_CBCT_MODEL) for the diagnostic INTERPRETATION/report-writing layer on top of computed
  measurements — NOT for geometry. Keeps us on approved providers (self-hosted open model + Anthropic
  language), per Melanin Tech rules. Default ANTHROPIC_CBCT_MODEL = Opus (max capability, user choice).

### PHASES (each independent: feature → PR → main → production)
- Phase A — Tracing core + Interactive Calibration. Models CephTracing (FK patient_images;
  analysis_type, landmarks JSONB {name:{x,y}}, measurements JSONB, calibration px/mm, status
  draft|finalized, traced_by, is_ai_assisted) + CephAnalysisDefinition (built-in + custom:
  landmarks list + measurement formulas). Manual landmark editor (canvas); AUTO-SCALING (detect
  known-distance/ruler/fiducial → px/mm) + DYNAMIC REFINEMENT (drag to recalibrate, live recompute);
  measurement engine (McNamara/Steiner/Downs/Wits/Jarabak/ABO + custom) w/ age/sex norms.
- Phase B — Automated Tracing (AI 2D). Vision model pre-places landmarks + per-point confidence →
  draft for mandatory doctor review. Manual mode fully works if AI down (fail-safe).
- Phase C — Visual Polygons + Multi-Format Diagnostic Reporting. Jarabak/Ricketts polygon overlays;
  report generator → PDF / PNG / structured JSON / Medicaid-formatted → stored via documents service
  → chart + MyOrthoChart + Medicaid submission.
- Phase D — Superimposition & Automated Progress Tracking (ICS analog). CephSuperimposition model
  (2+ tracing ids, registration method, deltas JSONB). Register on stable points, growth-vs-treatment
  deltas, overlay viewer + progress timeline.
- Phase E — VTO + Soft-Tissue Morphing. Landmark-projection engine (Ricketts growth + Holdaway soft
  tissue, custom allowed) → target tracing; soft-tissue morph. START 2D schematic profile-line morph
  + SCAFFOLD for full photo-realistic morph (see below). Labeled clinician-reviewed PREDICTION.
- Phase F — 3D CBCT (self-hosted 3D model + Opus interpretation). 3D landmarking/analysis +
  synthesized 2D ceph from volume. Ships last (least mature, highest cost), beta-labeled, supervised.

### PHOTO-REALISTIC SOFT-TISSUE MORPH — what it specifically requires (user wants full version)
Decision: ship 2D schematic profile morph first + build scaffolding for full photo-morph. Full
photo-realistic morph needs: (1) a calibrated lateral PROFILE PHOTO co-registered to the ceph;
(2) soft-tissue landmark correspondence between photo and ceph tracing; (3) a warp/displacement
field driven by predicted hard-tissue movement × soft-tissue response ratios (Holdaway/Ricketts),
or a generative model (GAN/diffusion, per literature — e.g. cGAN vs Dolphin VTO studies); (4)
image-warping pipeline (thin-plate-spline or ML) to render the morphed profile; (5) strong
"predicted, not guaranteed" labeling + clinician finalize gate. Scaffolding in Phase E = store the
profile photo + soft-tissue landmark set + a morph-provider interface so the generative backend can
be dropped in later without changing callers.

### RISKS (most→least critical)
1. VTO/soft-tissue morph are PREDICTIONS not outcomes — highest liability. Hard "predicted — planning/
   communication only" labeling, clinician-review-required, no patient view without finalize, audit-logged.
2. Auto-tracing clinical accuracy — semi-automatic, confidence-shaded, no auto-finalize.
3. Measurement/formula correctness — pure engine, unit-tested vs published reference cases per analysis, cited norms.
4. Soft-tissue warp realism — label schematic vs photo clearly; don't over-promise.
5. 3D CBCT accuracy + cost — separate tier/model, ships last, beta.
6. Scope — 6 independent shippable phases; Phase A delivers value with zero AI.

### RESEARCH CITATIONS (gathered this session)
- Angel Aligner ICS: algorithm-based landmark ID + superimposition on stable reference points,
  visualizes skeletal/dental change from treatment + growth, longitudinal (angelaligner.com ICS/iOrtho).
- 2D AI landmarking reproducible ICC~1.0, MRE 0.5–0.65mm, supervision still required (Springer
  s40510-026-00628-z, s13005-026-00608-y; semi-auto > auto accuracy, BMC Oral Health 2024).
- 3D CBCT: nnLandmark/nnU-Net ~1.2–1.5mm (arXiv 2504.06742); SA-LSTM 3D (arXiv 2107.09899); CBCT
  clinical ~59% within ±2mm/° (Nature s41598-026-41408-3).
- VTO: Ricketts/Holdaway predict growth + ideal soft-tissue profile; computer image prediction for
  patient education; Dolphin VTO benchmark; cGAN soft-tissue prediction (ResearchSquare rs-9252452).

### OPEN CONFIRMS (user already answered): photo-morph=full w/ 2D-first scaffold ✓; VTO Ricketts+Holdaway ✓;
ABO default ✓; CBCT model = self-hosted 3D + Opus interpretation (decided). CBCT = GREENFIELD
(confirmed 2026-10-04) — Phase F builds full DICOM volume ingest from scratch (DICOM metadata fields
already exist on PatientImage as a 4b hook). INTEROP TARGET: Romexis (Planmeca) is a common in-office
imaging/CBCT software — design CBCT ingest + imaging interop with Romexis export/DICOM in mind
(alongside the existing imaging_ingest.py edge-appliance path). Likely also relevant as a migration/
image source for onboarding.

────────────────────────────────────────────────────────────────────────
## WORKSTREAM B — FIRST-CLIENT / COMMERCIAL READINESS (from Adele consultant call)
Context: Adele consults for a 5-location (opening 6th) TX ortho practice on legacy PMS "TOPS"
(closed ecosystem, TOPS Pay Premier only does 30/60/90 then dumps to collections). Doctor carries
>$500K patient delinquency, rate 14%→16% (healthy = 3–5%). Weekly rebuilt Excel sheet, manual notes.
Strong product-market fit for OrthoFlow AR/automation/reporting.

### ACTION ITEMS (code-scoped against current repo)
1. LEDGER INLINE NOTES (committed to prospect). GAP: no inline notes column in the ledger VIEW.
   FINDING: PatientLedgerEntry ALREADY has a `notes` Text column — so this is mostly FRONTEND
   (expandable note button per ledger row, like the claim-status popup pattern) + a small save
   endpoint. Use case: "mom will pay Friday" logged in-context so staff don't re-contact next day.
   For financial/insurance coordinators — single place for financial notes, no screen cross-ref.
2. 90-DAY-PLUS DELINQUENCY BUCKET. FINDING: reports.py already has /ar-aging with 30/60/90/120+
   buckets (line 689). Need to (a) surface a 90+/120+ delinquency view in the LEDGER UI (not just
   the report), and (b) support structured tracking + notes for 90+ accounts instead of defaulting
   to collections (TOPS's failure). Likely small — extend existing aging logic + expose in ledger.
3. LEDGER PATIENT SEARCH BAR. Add search to the ledger view to jump to a patient (reduce nav friction).
4. ORTHOFI INTEGRATION (strategic priority). OrthoFi = financial platform used in ~85% of ortho
   practices (NOT a PMS): digital new-patient paperwork, insurance verification, benefit calc,
   contract setup. KEY GAP OrthoFlow fills: OrthoFi stops tracking at 120 days; OrthoFlow handles
   the long tail. Doctors will ask "do you integrate with OrthoFi?" as due-diligence. ACTION:
   investigate OrthoFi API/integration feasibility; design OrthoFi ↔ OrthoFlow financial bridge.
   Current OrthoFlow external insurance integration = Stedi (clearinghouse, background). Relationship
   angle: OrthoFi co-founder David may be a former Slalom colleague of Parrish (LinkedIn outreach).
5. TOPS INTEGRATION INVESTIGATION. TOPS claims closed ecosystem (no third-party integration, pushes
   own TOPS Pay Premier). Investigate whether ANY integration/data-export path exists for migration.
6. ONBOARDING + TRAINING DOCS (explicit deliverable). Create/update OrthoFlow + MyOrthoChart docs:
   a DETAILED first-client onboarding understanding doc answering likely client questions, an
   ONBOARDING CHECKLIST, and a STAFF TRAINING CHECKLIST — so we're production-ready for the first client.

### EXISTING AR/FINANCE FEATURES CONFIRMED (don't rebuild)
- 30/60/90 reporting structure exists; patient ledger tracks down payments, insurance payments,
  contractual insurance adjustments, monthly auto-charges, declined-payment flags.
- "Patients Who Owe Money" view (balance + insurance y/n) exists (reports.py payment_status owes/paid_up).
- SMS payment-link automation already in place (30–90 day touchpoints).
- Dashboard AI insights: recoverable revenue from denied claims, unbilled claim totals, patients
  overdue for next visit (currently high-level/demo-level indicators).
- AI letter generation learns practice writing style; tracks most-used letter types (school notes,
  referral thank-yous, collections) as quick-access. Sends via email_relay from the platform.
- "Today's Notes" (renamed from morning huddle) daily huddle view; daily schedule shows confirmation
  status + balance + owes + patient-card link. Monthly calendar needs click-in for counts (report
  builder can address month-level volume — ties to the full-month seed work shipped 2026-10-02).

### NON-ENGINEERING / FOLLOW-UPS (tracked, not build tasks)
- Secure a DOCTOR to review before launch (front-desk/clinical/consultant feedback gathered; doctor
  is the missing input). Candidates: new Charlotte ortho doctor; Adele network intro.
- Conferences: AAO Winter 2027 San Antonio (near-term), AAO Annual (June, Canada, largest), WIO
  (Courtney Dunn, intimate), Orthopreneurs Summit. Adele mapping 2027 schedule.
- Follow OrthoFi + co-founder on LinkedIn; Orthopreneurs podcast for industry context.

## IMMEDIATE BUILD ORDER (status)
B1 ledger notes ✅ → B2 90+ bucket ✅ → B3 ledger search ✅ (PR #33, alembic 029, SHIPPED) →
B6 onboarding/training docs ✅ → B4 OrthoFi bridge scaffolding ✅ → B5 TOPS investigation ✅
(PR #34, SHIPPED). WORKSTREAM B COMPLETE: main==production==28541aa.
NEXT: Ceph Suite Phase A…F (Workstream A above).
