# OrthoFlow — Session Pickup Notes (2026-09-08)

Resume point after a long working session on OrthoFlow (AI-native orthodontic practice
management). This captures everything built, how to run/verify it, deploy model, and open items.

Repo: github.com/parrish727/OrthoFlow  ·  App: app.orthoflowsolutions.com / api.orthoflowsolutions.com
Codebase: LinesOfBusiness/Orthodontic_Dental/orthoflow-ai/OrthoFlow

---

## Branching & Deploy Model (Option A — implemented this session)

- **main = source of truth** (tests only; pushing to main does NOT deploy).
- **production = deploy branch** (CI build → GHCR → Watchtower triggers ONLY on push to production).
- Promote to prod: `git checkout production && git merge --ff-only main && git push origin production`.
- CI: `.github/workflows/ci.yml` — build job gated on `refs/heads/production`; tests run on main/develop/PRs.
- `.github/CODEOWNERS` added (@parrish727 backstop + domain sections). GitHub validated (0 errors).
- **Branch protection = STAGED, NOT ENFORCED** (per pktech_dev: need fast changes, no release schedule yet).
  Runbook at `docs/BRANCH_PROTECTION_RUNBOOK.md` — create ruleset in Disabled/Evaluate, flip to Active later.
- FUTURE projects use full GitFlow (feature→develop→main→production), agent-managed peer review
  (DevOps/Backend+DBA/Frontend), escalate to pktech_dev only for main/production. Codified in
  ~/.kiro/steering/melanin-tech-global.md + kiro-agents DevOps guardrails (both gitignored/local).

Latest production commit as of pickup: 93cc0b0 (financial-impact reframing).

---

## CRITICAL INFRA STATE (must know on resume)

- **DB routing fix (live):** backend/worker `DATABASE_URL` points DIRECTLY at `orthoflow-postgres-1:5432`
  (compose environment override), NOT pgbouncer. Reason: (a) a Docker network-alias collision made
  `postgres` resolve to another project's container (172.20.0.29) instead of orthoflow-postgres-1
  (172.23.0.7); (b) asyncpg + pgbouncer SCRAM incompatibility. The role password was set to `kiro_secret`
  on orthoflow-postgres-1 (ALTER ROLE). `.env` DATABASE_URL + POSTGRES_PASSWORD set to kiro_secret.
- **pgbouncer** config was corrected (scripts/pgbouncer/: auth_type scram-sha-256 + userlist verifier,
  host=orthoflow-postgres-1 password=kiro_secret) but is BYPASSED currently. To re-enable pooling
  cleanly the asyncpg quirk needs statement_cache_size=0 (already in database.py via DB_VIA_PGBOUNCER)
  OR switch to auth_type=md5.
- **Backend runs a BAKED image** (no volume mounts). During dev I `docker cp` files into
  orthoflow-backend-1 + `docker restart` to test; the production IMAGE gets the code via CI on
  production push. After a container restart, re-copy any locally-edited files if testing.
- DB migrations: **at 019** (alembic). Demo practice_id = 82fe9d87-6250-4b15-ac7d-26de094a4be8.
- Demo login: demo@orthoflowsolutions.com / Demo2026! (roles: owner/doctor/office_manager/
  dental_assistant/front_desk, all password Demo2026!). Prime demo patient: **Priscilla Knowles**
  (id 78c5125a-32a9-44b9-9ff0-a63931713bb0). 100 demo patients total.

---

## WHAT WAS BUILT THIS SESSION (all committed to main + promoted to production)

### 1. Stedi clearinghouse integration (sandbox)
- services/stedi.py — real Stedi API contract. Eligibility (270/271) LIVE in test mode
  (POST /change/medicalnetwork/eligibility/v3, raw Authorization header, tradingPartnerServiceId/
  encounter{serviceTypeCodes:['35' dental]}/provider/subscriber; parses planStatus[]+benefitsInformation[]).
  837D dental claims + 277CA + 835 ERA SIMULATED in sandbox (STEDI_LIVE_CLAIMS flag flips to real).
- services/stedi_payers.py — internal payer → Stedi test payer map + mock subscriber fixtures.
  NOTE: this account's mock dataset differs from public docs; exact mock creds must come from the
  account's Stedi portal "New eligibility check" test form. Fallback to stored benefits works.
- services/stedi_mcp.py — DORMANT (production account required; STEDI_MCP_ENABLED=false).
- eligibility.py — calls Stedi live w/ graceful fallback + precognitive BenefitAlerts
  (ortho max, deductible, plan termination, stale verification).
- claims_workflow.py — submit builds 837D + simulated 277CA; /adjudicate synthesizes 835 ERA →
  PaymentPosting + PatientLedgerEntry.
- config: STEDI_ENABLED, STEDI_BASE_URL=healthcare.us.stedi.com/2024-04-01, STEDI_LIVE_CLAIMS,
  STEDI_PROVIDER_NPI=1999999984, dormant STEDI_MCP_* + NCTRACKS_*.

### 2. Roster-first UX (Insurance/Claims/Ledger/Payments) — CONFIRMED WORKING by user
- All patients visible on arrival (no search gate), filter, click-expand, quick-link tabs
  (Patient Record/Insurance/Claims/Ledger/Payments) deep-linking ?patient_id.
- Backend rosters: finance insurance-roster/ledger-roster/payments-roster + claims/roster.
- Frontend: Insurance.tsx, Claims.tsx (rewritten), Ledger.tsx (N+1 → roster), Payments.tsx (rewritten).

### 3. AI Schedule Notes (Schedule page) — AI + DA daily notes above/below schedule (model schedule_notes, migration 017).

### 4. Ortho ops (migration 018) — models/ortho_ops.py + routes/ortho_ops.py (/api/v1/ortho):
- Custom CDT codes (doctor-defined) + standard ortho seed (D8091/D8020/D8080/D8670-MC/D8660, seeds/ortho_cdt_standard.py)
- Patient comments (info + clinical charts) + Chart charges (add + collect→ledger at checkout) — PatientOrthoPanel.tsx on PatientDetail
- Per-patient insurance contracts (from TC Proposal → Claims), cadence monthly/quarterly + manual/auto,
  send-initial-claim-once-then-auto, daily payment poll
- Schedule appointment payload: Medicaid purple + "MC" badge, $ owe / $! late indicator, is_consult, insurance_verified

### 5. Pre-consult insurance verification — consults show INS ✓ / VERIFY INS ⚠ (flag not block, verified=checked ≤30d & active);
  /ortho/consult-readiness worklist; "Consults Needing Insurance Verification" report category.

### 6. Reports by category — /reports/categories + /reports/category/{key} (10 categories: patients_owe, by_insurance,
  missing_appointments, treatment_overdue, treatment_bring_sooner [AI], scheduled_appointments, private_collections,
  insurance_collections, no_chart_notes_today, consults_need_verification). Reports.tsx "Report Categories" tab.

### 7. NCTracks (NC Medicaid) — services/nctracks.py DORMANT 837D destination scaffold (pktech_dev does enrollment/creds).

### 8. OrthoFlow AI layers (Dashboard):
- **Practice Impact** card (PracticeImpact.tsx) — quantifies benefit in $ ordered claims→savings→efficiency
  (/ortho/practice-impact). Recoverable = denied$*0.5. Verified: $64.5k claims at stake, $121.9k savings.
- **AI Assist** card (AIAssist.tsx) — role-aware next-best-actions, REVENUE-FIRST (leads with denied-claims $,
  unbilled claims $) (/ortho/ai-assist?role=).
- **Automation Activity** card (AutomationActivity.tsx) — "OrthoFlow handled this automatically" + Run-now.

### 9. Automation Engine (migration 019, services/automation.py) — daily runner in worker loop:
- recurring_claims (auto contracts due → generate + advance), payment_poll (paid/pending/failed),
  consult_verify (auto re-verify eligibility for consults in next 2 days → stamps last_eligibility_check
  so schedule shows INS ✓ pre-visit). Idempotent per practice/task/day (AutomationRun audit table).
  Judgment calls (first claim, appeals, collections) NOT automated — surfaced by AI Assist.
- Endpoints: /ortho/automation/activity + /automation/run. Worker: workers/main.py _run_daily_automations.

---

## AUTOMATED TESTING (now a permanent QA standard — codified)
- Docker Playwright runner: `./e2e/run-e2e.sh [filter]` (mcr.microsoft.com/playwright:v1.45.0-jammy on
  docker_agent-net, targets frontend container). global-setup.ts authenticates once → storage/owner.json.
- Config e2e/playwright.docker.config.ts: workers=1, expect timeout 15s, baseURL orthoflow-frontend-1:3000.
  Backend CORS allows that origin.
- Specs: insurance-roster.spec.ts (6), finance-rosters.spec.ts (8), ortho-session.spec.ts
  (reports categories, AI suggestions, consult verification, AI assist, automation activity, schedule cards,
  patient panel, practice impact). ALL PASS INDIVIDUALLY.
- KNOWN FLAKINESS: full-file/all-suite runs intermittently fail due to Cloudflare rate-limiting under load
  against the public API. Each test passes solo. Fix (future): point browser at internal API to bypass CDN.
- Standard codified in docs/specs/QA_PIPELINE.md v1.1 + kiro-agents SRE Guardrails.
- LEGACY specs (auth/communications/flow-board/patients/rbac) use outdated selectors — pre-existing, need cleanup.

---

## MARKETING (LOCAL ONLY — never committed, per pktech_dev)
- orthoflow-marketing/social-cards/: card-01-verify-before-consult.html + .png (1080×1080, on-brand,
  accurate to pre-consult verification), render-card.js (playwright PNG renderer), README.md (agent guide:
  brand tokens, 4 structural devices, NON-NEGOTIABLE accuracy rules incl sandbox caveat, render command).
- Brand tokens: radial navy gradient #0d2035→#0B1B2B→#081420, teal #00C2A8, muted #8CA0B5, headline white 900 -1.5px Inter.
- ACCURACY: only claim shipped features; do NOT claim live at-scale payer transmission (simulated in sandbox)
  or unprovable ROI $. Site/brochure must align with production.

---

## OPEN ITEMS / NEXT
1. **macOS duplicate files** (' 2.py' / ' 2.ts' iCloud artifacts) across backend/ + e2e/ — uncommitted,
   need cleanup: `find . -name '* 2.*' -delete` from repo root.
2. **pgbouncer** — re-enable pooling properly (asyncpg statement_cache_size=0 or auth_type=md5) + fix the
   `postgres` network-alias collision so backend routes to orthoflow-postgres-1 without the IP override.
3. **Branch protection** — flip ruleset to Active when a release schedule exists (runbook ready).
4. **E2E full-suite reliability** — point runner at internal API to bypass Cloudflare rate-limiting.
5. **Stedi dental mock creds** — pull exact fixtures from the account's portal test form for true live eligibility round-trip; NCTracks enrollment (pktech_dev).
6. **More social cards** — vary structural device per card (two-column "denied→recovered", hero-stat once a provable metric exists).
7. Nice-to-haves backend-ready but not surfaced: last-5-searched dropdown in global search bar; "create contract from this TC proposal" button on TCProposal page.

## HOW TO VERIFY QUICKLY ON RESUME
- App health: `docker ps | grep orthoflow-backend-1` (should be healthy).
- Login+data: POST /api/v1/auth/login demo@orthoflowsolutions.com/Demo2026! → GET /api/v1/finance/insurance-roster (100), /ortho/practice-impact, /ortho/ai-assist?role=doctor, /ortho/automation/activity.
- E2E: `./e2e/run-e2e.sh insurance-roster` (6/6).

---

## PART 2 INITIATIVE (in progress, started 2026-09-08 eve)

Plan + risk assessment: `docs/specs/PART2_PLAN.md`. 8 phases, each independently built + verified.
Confirmed decisions captured in the plan doc. KEY: strictly orthodontics (removed Perio); insurance
= lifetime benefit no copay (~$2500 default, accumulates across phases, resets=new benefit period
archived); Plaid only (skipped Apple Pay/Zelle/CashApp/Tap-to-pay); TimeTracking UNTOUCHED; staff-time
automation is an internal sales-moat concept, NOT an in-app feature; remove pre-consult/consult-readiness
(keep no_chart_notes tracking).

### Phase 1 progress
- DONE: **Perio feature fully removed** (strictly ortho). Deleted backend/app/api/routes/perio.py,
  backend/app/models/perio.py, frontend/src/components/PerioChartView.tsx (was already orphaned in FE).
  Removed model import (models/__init__.py), route import + router registration (main.py). Added
  migration `020_drop_perio.py` (drops perio_readings + perio_exams; downgrade recreates). VERIFIED:
  backend imports OK, boots healthy (patient_count 100), /api/v1/perio -> 404, insurance-roster still 100,
  frontend builds clean. NOTE: left ai_context.py perio specialty branch + recall perio_maintenance +
  CDT D4 catalog entries alone (shared/incidental, not the charting feature).
- NEXT: PatientDetail.tsx Clinical Chart vs Administrative two-tab split. Structure mapped:
  header (back/name/phase/edit) shared; current content is one 2-col grid — left: Patient Info,
  ClinicalEnhancements, ToothChart, WireTrackingSection; right: quick-links (Ledger/Insurance/Schedule),
  Images panel, Appointments, PatientOrthoPanel, Treatment Notes (NoteInput), NextVisitSection.
  Plan: Clinical tab = clinical content; Administrative tab = finance quick-links + Documents panel +
  (later) TC save-to-documents. Documents backend EXISTS: GET/POST /api/v1/patients/{id}/documents
  (fields: document_type, title, file_url, file_size_bytes, mime_type, notes, created_at). NO api.ts
  client method yet — must add. Also pending in Phase 1: Emergency Medical note in Clinical Overview,
  swap Treatment Notes <-> Appliance tracking prominence (Treatment Notes bolder/higher), Documents tab
  next to Patient Info.
