# OrthoFlow — Cephalometric Suite COMPLETE (Phases A–F) + Session Pickup (2026-10-05)

All 6 Ceph phases + UI placement SHIPPED to production and durable. `main == production == ba76ee5`,
alembic **033 (head)**. Deploy model unchanged: feature → PR → main (tests) → FF push to production
(GHCR → Watchtower). Repo: github.com/parrish727/OrthoFlow.

## Cephalometric Tracing & Analysis Suite — what shipped
Modeled on Angel Aligner ICS; grounded in current AI-landmarking research. Clinical decision-support:
semi-automatic, doctor-finalized, **no AI auto-finalize**; everything labeled predicted/clinician-reviewed.

- **Phase A** (PR #36, migr 030): `models/ceph.py` CephTracing + CephAnalysisDefinition.
  `services/ceph_engine.py` PURE measurement engine — SNA/SNB/ANB(=SNA−SNB)/Wits/FMA/SN-MP/Jarabak/
  U1-SN/IMPA + norms±SD + status; analyses **ABO (default)/Steiner/Downs/McNamara/Wits/Jarabak**.
  `api/routes/ceph.py` tracing CRUD, live-recompute on edit (dynamic refinement), finalize.
  Frontend `CephTracingEditor.tsx`: SVG landmark placement + interactive calibration (auto-scale) +
  live measurement table + finalize. 6 built-in analyses seeded (`seed_ceph_analyses`).
- **Phase B** (PR #37): `services/ceph_ai.py` AI 2D auto-landmarking via Anthropic vision
  (`ANTHROPIC_MODEL`) → normalized coords + per-point confidence → pixels; robust JSON parse;
  fail-safe (RuntimeError→503→manual). `POST /ceph/tracings/auto-landmark` → DRAFT is_ai_assisted.
  Editor: 'AI Auto-Trace' + low-confidence landmarks shaded amber.
- **Phase C** (PR #38): `ceph_engine.polygons_for` (Jarabak/Ricketts/skeletal/plane/axis) +
  `services/ceph_report.py` multi-format **PDF/PNG/JSON/Medicaid** (Pillow only, no new deps) stored
  via the documents service → PatientDocument → chart + MyOrthoChart (share_with_patient). Endpoints
  `GET /ceph/tracings/{id}/polygons`, `POST /ceph/tracings/{id}/report`.
- **UI placement** (PR #40): efficient workflow — Imaging viewer shows **Trace & Analyze** on a ceph
  image (in-context overlay, no nav); patient clinical chart hosts CephProgress + CephVTO + CephCBCT
  beside tooth chart/treatment notes.
- **Phase D** (PR #39, migr 031): `ceph_engine.superimpose` — 2-point similarity transform on stable
  S–N refs → per-landmark deltas (mm/px) separating change from head position. `CephSuperimposition`
  model. `POST /ceph/superimpositions` (both tracings finalized + same patient), list. Frontend
  `CephProgress.tsx`. (The Angel Aligner ICS analog.)
- **Phase E** (PR #41, migr 032): `services/ceph_vto.py` VTO projection (Ricketts growth +
  U1/L1 retraction → target landmarks; Holdaway soft-tissue ratios → schematic profile) + **photo-
  morph SCAFFOLD** (`MorphProvider` interface + `morph_status` + model cols profile_photo_key/
  soft_tissue_landmarks/morph_provider/morph_result_key — 2D schematic ships now). `CephVTO` model.
  Endpoints `POST /ceph/vto` (finalized source), list, finalize, `GET /ceph/vto/morph-status`.
  Frontend `CephVTO.tsx`.
- **Phase F** (PR #42, migr 033): 3D CBCT [BETA]. **Approved-provider split**: self-hosted 3D model
  (nnU-Net/nnLandmark) does geometry — **dormant** (`CBCT_GEOMETRY_ENABLED`/`CBCT_GEOMETRY_URL`),
  manual 3D landmarks work now; **Anthropic Opus** (`ANTHROPIC_CBCT_MODEL=claude-opus-4-6`) does the
  interpretation/report. `services/ceph_cbct.py` (3D angle/dist, compute_3d incl 3D-only bigonial
  width, interpret via Opus). `CephCBCTScan` model. Endpoints: geometry-status, multipart DICOM
  **ingest**, set 3D landmarks (recompute), **interpret** (Opus, 503 fallback), list. **Romexis/
  Planmeca interop** = their DICOM export → our ingest. Frontend `CephCBCT.tsx`.

## Config added (env-swappable, no redeploy)
- `ANTHROPIC_MODEL` (Haiku 4.5) — 2D vision + general.
- `ANTHROPIC_CBCT_MODEL` (claude-opus-4-6) — 3D CBCT interpretation.
- `CBCT_GEOMETRY_URL` / `CBCT_GEOMETRY_ENABLED` — self-hosted 3D model (dormant until provisioned).

## Tests
backend/tests/: test_ceph_engine (11), test_ceph_ai (7), test_ceph_report (6),
test_ceph_superimposition (4), test_ceph_vto (7), test_ceph_cbct (6) → **91 total backend tests pass**.
Frontend `npm run build` green each phase.

## Clinical-safety invariants (all phases)
No AI auto-finalize (doctor sign-off required); AI = decision-support draft; confidence shown; VTO/
CBCT labeled "predicted — clinician-reviewed, not a guaranteed outcome"; CBCT beta/supervised; audit-
logged; practice-scoped.

## OUTSTANDING / FUTURE (not blockers)
- Self-hosted 3D CBCT geometry model (nnU-Net/nnLandmark) deployment — then set CBCT_GEOMETRY_* to
  activate auto 3D landmarking (interface already in place).
- Photo-realistic soft-tissue morph backend (MorphProvider impl) — scaffold ready.
- Align Technology (Invisalign) + OrthoFi live API integrations — await partnership credentials
  (bridges/scaffolds in place).
- Site/brochure SEO/marketing pass — owned by FRONTEND agent + QA review (pktech_dev); still deferred.
  Note docs/specs/DOC_MARKETING_AUDIT_2026-10-05.md; 'SOC 2 Ready' KEPT (accurate posture).
- Ceph CENTER-nav entry (optional): currently entered via Imaging viewer + patient chart; a top-level
  Imaging/Ceph tab could be added if desired.

## FILES (ceph suite)
backend/app/models/ceph.py, backend/app/services/{ceph_engine,ceph_ai,ceph_report,ceph_vto,ceph_cbct}.py,
backend/app/api/routes/ceph.py, backend/alembic/versions/030_ceph_tracing..033_ceph_cbct.py,
backend/app/seeds/__init__.py (seed_ceph_analyses), backend/app/core/config.py,
frontend/src/components/{CephTracingEditor,CephProgress,CephVTO,CephCBCT}.tsx,
frontend/src/pages/{Imaging,PatientDetail}.tsx, frontend/src/lib/api.ts, backend/tests/test_ceph_*.py.
