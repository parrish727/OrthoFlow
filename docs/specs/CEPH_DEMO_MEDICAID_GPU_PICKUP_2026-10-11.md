# OrthoFlow — Ceph Demo-Readiness + Medicaid Accuracy + GPU/Morph Findings (2026-10-11)

Pickup doc for the arc after the Ceph Suite A–F completion. All SHIPPED + durable.
`main == production == 9c00d03`, alembic **033 (head)**, 0 diff. Deploy model unchanged
(feature → PR → main → FF production → GHCR → Watchtower). 91 backend tests pass.

## What shipped in this arc (PRs #40–#46)
- **#40** Ceph UI placement — efficient workflow: Imaging viewer shows **Trace & Analyze** on a ceph
  image (in-context overlay); patient clinical chart hosts CephProgress + CephVTO + CephCBCT.
- **#41/#42** Phases E (VTO + soft-tissue scaffold) and F (3D CBCT) — see CEPH_SUITE_COMPLETE doc.
- **#43** Ceph suite A–F architecture/pickup doc.
- **#44** Ceph DEMO DATA + UI polish: removed the raw model name from the CBCT panel; added
  `app/seeds/demo_ceph.py` (idempotent) seeding the flagship demo patient **Priscilla Knowles**
  (id 78c5125a-32a9-44b9-9ff0-a63931713bb0) with a ceph image + 2 finalized ABO tracings
  (initial+progress, ANB 6.1°→5.0°) + superimposition + VTO + CBCT scan w/ interpretation. Wired into
  seed_demo_flow (own session, fail-safe). CONVENTION: new clinical features ship with demo mock data.
- **#45** Licensed-sample ceph image support: `demo_ceph._load_ceph_image()` prefers
  `backend/app/seeds/assets/sample_ceph.(png|jpg)` (records source on image desc), else labeled
  synthetic placeholder. `seeds/assets/README.md` has drop-in steps + approved CC-BY sources.
- **#46** Medicaid ceph-requirement correction + VTO before/after morph overlay (details below).

## WHY the ceph panels looked empty before (root cause, fixed)
Components were deployed, but the demo had ZERO tracings/VTOs/CBCT and only a bogus ceph image, so
every panel showed its empty-state and 'Trace & Analyze' (ceph-only) had no real ceph to attach to.
Now the demo is fully populated for Priscilla. To view: open Priscilla → her ceph in Imaging →
Trace & Analyze; her clinical chart shows Cephalometric Progress + VTO (with morph) + 3D CBCT.

## MEDICAID + CEPH — VERIFIED (your contact was right)
Confirmed against current state Medicaid manuals (Oct 2026): orthodontic medical-necessity is driven
by the **HLD index score + clinical photographs**; a **cephalometric radiograph is NOT universally
required** — it's state-dependent/supplemental. Washington explicitly REMOVED 'medically necessary'
from ceph CDT D0340; CA/IL/Utah gate on HLD. Corrected in code:
- `services/medicaid_rules.py`: NC/SC billing_notes fixed (HLD+photos core; ceph supplemental/
  if-requested); added `records_required` / `records_supplemental` fields + module RECORDS NOTE.
- `services/ceph_report.py`: Medicaid note reframed — ceph = OPTIONAL supporting evidence, not required.

## VTO SOFT-TISSUE MORPH (in-house, CPU-only — SHIPPED)
Before→after soft-tissue profile overlay on the VTO (current dashed gray vs predicted violet),
driven by the Ricketts/Holdaway projection. `api/routes/ceph.py` VTO stores
`soft_tissue.source_profile` alongside the predicted `profile`; frontend `CephVTO.tsx` ProfileMorph
SVG renders both. Demo tracings gained soft-tissue landmarks (Sn/UL/LL/Pog_soft) → 5 before + 5 after
points on the demo VTO. This is the schematic (non-generative) morph — the real CPU-only deliverable.

## GPU FINDING (answering "can we use the Radeon Pro Vega 56 8GB?")
NO — not practically. The blocker is the ML software stack, not raw power:
- 3D/generative models need PyTorch/TF + **CUDA (NVIDIA)**. AMD needs **ROCm = Linux-only, not on
  macOS**. On Mac, GPU ML needs **Apple Silicon (Metal/MPS)**; a discrete AMD Vega has no usable
  PyTorch backend → CPU fallback (impractically slow for 3D volumetric inference). 8GB also under
  nnU-Net 3D's typical 11–24GB.
- Path forward: a small **NVIDIA/Linux GPU host** (or hosted endpoint). OrthoFlow already calls it
  via `CBCT_GEOMETRY_URL` / `CBCT_GEOMETRY_ENABLED` (dormant) — zero code change to activate.

## COME BACK TO (open items, prioritized)
1. **Licensed sample ceph image** — mechanism live; needs EITHER a licensed image you own (drop at
   backend/app/seeds/assets/sample_ceph.png + SAMPLE_CEPH_LICENSE.txt, re-seed) OR go-ahead on the
   Aariz CC-BY dataset request (github.com/manwaarkhd/aariz-cephalometric-dataset) with attribution.
   Until then the demo uses the labeled synthetic placeholder.
2. **GPU inference host** (NVIDIA/Linux or hosted) to activate: (a) full 3D CBCT auto-landmarking
   (self-hosted nnU-Net/nnLandmark → set CBCT_GEOMETRY_URL/ENABLED), and (b) generative
   photo-realistic soft-tissue morph. Also needs DICOM libs (pydicom/SimpleITK/numpy — intentionally
   NOT in the lean image yet) + a trained/licensed 3D model + annotated CBCT dataset.
3. **Full TPS photo-warp** (classical, non-generative, CPU) — buildable in-house but needs a captured
   calibrated PROFILE PHOTO co-registered to the ceph (a capture-workflow step we don't collect yet)
   + numpy. Deferred; schematic morph covers the demo need for now.
4. **Align Technology (Invisalign) + OrthoFi live API** integrations — await partnership credentials
   (bridges/scaffolds already in place).
5. **Site/brochure SEO/marketing pass** — owned by FRONTEND agent + QA review (pktech_dev directive);
   still deferred. See docs/specs/DOC_MARKETING_AUDIT_2026-10-05.md ('SOC 2 Ready' KEPT as accurate).

## KEY FACTS
- Ceph config (env-swappable): `ANTHROPIC_MODEL` (Haiku 4.5, 2D vision+general), `ANTHROPIC_CBCT_MODEL`
  (claude-opus-4-6, 3D interpretation only), `CBCT_GEOMETRY_URL`/`CBCT_GEOMETRY_ENABLED` (dormant).
- Clinical-safety invariants hold everywhere: no AI auto-finalize, doctor sign-off, predicted/
  clinician-reviewed labels, CBCT beta/supervised, audit-logged, practice-scoped.
- Full ceph architecture: docs/specs/CEPH_SUITE_COMPLETE_2026-10-05.md.
- Demo re-seed (if needed): `docker exec orthoflow-backend-1 python -c "import asyncio; from
  app.seeds.demo_ceph import seed_ceph_demo; asyncio.run(seed_ceph_demo())"` (idempotent; clear
  Priscilla's ceph rows first to force a re-seed with new landmarks).
