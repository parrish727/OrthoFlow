# OrthoFlow — Part 2 Initiative Plan & Risk Assessment

Date: 2026-09-08 · Owner: pktech_dev · Branch model: main = source of truth, production = deploy.
Guiding principle: **OrthoFlow is an ecosystem** — every feature should connect naturally and in
multiple ways where it improves efficiency (TC → Contracts → Ledger → Claims → Reports → Letters →
Dashboard/EOD). Each phase ships independently and is verified (build + E2E) before the next.

Confirmed decisions (from pktech_dev):
1. Patient record = ONE record, two top-level tabs (Clinical Chart / Administrative). **Remove Perio entirely — strictly orthodontics.**
2. Insurance = **lifetime benefit** (no co-pay). Ortho lifetime max accumulates across phases (does NOT reset annually); common range $1,000–$3,000, default ~$2,500, configurable per plan. "Reset" = new benefit period under a new job/insurer/plan level → archive prior period (audit history). Rename "Annual remaining" → "Remaining benefit."
3. TC → Contracts → lifecycle. **EOD report = everything that happened in the office that day, printable.**
4. Payments: **stay on Plaid.** Skip Apple Pay/Zelle/CashApp/Tap-to-Pay (no truthful merchant rails today).
5. Reports: flexible builder + ONE flagship action ("didn't pay → bundle message"); expand data sources over phases.
6. Checkout → Work Done → AI creates claim → assign to ledger.
7. Dashboard monthly calendar (AI-suggested, doctor-approved) + Patient Flow moved to its own tab.
8. Clinical polish + multi-type AI Letters + custom codes + AI usage learning (per-doctor style profile + few-shot; NO fine-tuning).
+ **TimeTracking untouched.** "Staff-time automation" is an internal Melanin Tech / OrthoFlow sales-moat concept — NOT an in-app feature to build or remove.
+ Removal: **pre-consult / consult-readiness verification** feature (keep "appointments missing chart notes").

---

## Phase order (each independently shippable + verified)

1. **Patient Clinical/Admin split + Documents; remove Perio.** Foundational — other phases hang off the tab structure and documents.
2. **Insurance lifetime-benefit rework.** Data-model change; do early so Contracts/Reports build on the right shape.
3. **TC → Contracts → lifecycle + printable EOD report.** The ecosystem spine.
4. **Checkout → Work Done → AI claim → ledger.**
5. **Dashboard monthly calendar + Patient Flow tab.**
6. **Reports builder + flagship bundle-message action.**
7. **Clinical polish + multi-type AI Letters + custom codes + AI usage learning.**
8. **Remove pre-consult verification** (small; can fold in early alongside Perio removal in Phase 1 if clean).
+ Schedule money-symbol balance popup + Ledger auto-pay green/red color coding (small, slots into Phase 3/5).
+ Final ecosystem wiring + full verification + cleanup (incl. 37 macOS `* 2.*` artifacts).

---

## Existing foundations (reduces risk — mostly extension, not greenfield)

- Contracts: `PatientInsuranceContract` (models/ortho_ops.py) + create/update/list in routes/ortho_ops.py.
- Custom codes: `CustomCDTCode`. Chart charges: `ChartCharge` (collect → ledger). Documents: `PatientDocument` (routes/workflow.py).
- Reports: routes/reports.py (categories, AR aging, collections, production, provider productivity) + ReportSnapshot.
- Claims: claims_workflow.py (create/submit/adjudicate), Stedi client, appeal_automation.
- Letters: ai_referrals.generate_referral_letter (extend to multi-type). Patient status: `PatientStatus` enum.
- Payments: PaymentPosting + Plaid. Automation engine: services/automation.py + worker loop.

---

## Risk assessment (most → least critical) with mitigations

1. **DB migrations on a live demo (baked image, alembic at 019).** New tables/columns for lifetime benefit, contracts extensions, letter style profiles, report definitions.
   → *Mitigation:* additive migrations only (new columns nullable + defaults; new tables). No destructive drops except Perio (Phase 1) which is isolated. Test each migration against a scratch copy before applying; keep downgrade().
2. **Removing Perio + pre-consult without breaking the ecosystem.** Both are referenced across routes/reports/frontend/seeds/router registration/ai_context.
   → *Mitigation:* removal lists below; grep-verify zero dangling imports; run build + full E2E after each removal; update seeds so daily reseed doesn't fail.
3. **Patient record restructure (Phase 1) is high-blast-radius** — PatientDetail is 43KB and many features render inside it.
   → *Mitigation:* pure IA reorg (tabs) — do NOT move backend data; preserve all existing testids; snapshot E2E before/after; keep components, only change their tab container.
4. **Insurance semantics change** could corrupt eligibility math / benefit alerts used by Claims + Reports.
   → *Mitigation:* keep co-pay column in DB (stop surfacing it) to avoid data loss; add lifetime fields alongside; adapt `eligibility._annual_remaining` → remaining-benefit without deleting; unit-test the alert builder.
5. **Reports builder scope creep.** "Report on every feature" is unbounded.
   → *Mitigation:* ship a generic engine over a FIXED first set of data sources + the one flagship action; expand sources in later phases (explicitly agreed).
6. **AI "learns doctor's wording/usage" over-promise.**
   → *Mitigation:* implement as stored per-doctor style profile + few-shot examples to Claude/Darius; label as "learns your style"; NO fine-tuning claims.
7. **EOD "everything that happened today" breadth.**
   → *Mitigation:* define EOD as an aggregation across existing dated events (appointments completed, contracts started, payments posted, claims submitted, charges added, notes) — one query per source, printable view.
8. **E2E full-suite Cloudflare flakiness (known).**
   → *Mitigation:* verify per-phase with isolated specs (no-retry) as evidence; full-suite flakiness is pre-existing and tracked separately.

---

## Removal manifests

### Perio (Phase 1)
- backend: `app/api/routes/perio.py`, `app/models/perio.py`, `alembic/versions/015_perio_charting.py` (add a new down-only migration to drop tables rather than editing 015), router registration in `app/main.py`, references in `reports.py`, `ai_context.py`, `seeds/__init__.py` + demo seeds, `catalog.py`.
- frontend: `components/PerioChartView.tsx`, references in `pages/PatientDetail.tsx`, `pages/Reports.tsx`, `pages/Patients.tsx`, `lib/api.ts`.
- NOTE: leave `timetracking`/`recall`/`portal` "period" matches alone — those are false-positive substring hits ("payroll **period**", "**period**ic"), not perio.

### Pre-consult / consult-readiness (Phase 8, may fold into Phase 1)
- backend: consult_verify task in `services/automation.py`; `consult_readiness` endpoint in `routes/ortho_ops.py`; `consults_need_verification` category in `routes/reports.py`; verified-badge logic in `clinical.py` schedule payload.
- frontend: INS✓/VERIFY INS badges in `pages/Schedule.tsx`; mention in `components/AutomationActivity.tsx`; method in `lib/api.ts`; assertions in `e2e/tests/ortho-session.spec.ts`.
- KEEP: "appointments missing chart notes" (no_chart_notes_today) tracking.

---

## Verification standard (every phase)
- `npm run build` (frontend) + backend import/migration check.
- Rebuild frontend dist → `docker cp` into orthoflow-frontend-1 for live check.
- Add/extend `e2e/tests/*.spec.ts` with data-testids; run the phase's spec in isolation with `--retries=0` as passing evidence.
- Clean up temp artifacts. Update SESSION_PICKUP notes at the end.
