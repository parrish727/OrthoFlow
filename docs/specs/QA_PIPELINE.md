# OrthoFlow QA Pipeline Specification

> **Version:** 1.0  
> **Date:** 2026-07-30  
> **Status:** Active  
> **Scope:** OrthoFlow (Staff App) + MyOrthoChart (Patient Portal)

## Overview

Six-phase quality pipeline that validates the entire OrthoFlow product from infrastructure through user experience. Designed to support onboarding from 10 to 1000+ practices with proper error handling, logging, and automated regression prevention.

## Self-Improving Loop Engineering

All phases use a **max 6-iteration** correction loop:

1. Run phase checks
2. If failures detected → diagnose root cause
3. Attempt automated fix (if reversible/safe)
4. Re-run checks
5. If still failing after 6 attempts → escalate to pktech_dev with full diagnostic context
6. If fundamentally wrong approach → step back, reanalyze, take different path

---

## Phase 1: Monitoring (SRE Agent)

**Trigger:** Before any deployment, on schedule (every 5 min), after every merge to main  
**Owner:** SRE Agent  
**Goal:** Confirm infrastructure health before any changes ship

### Checks

| Check | Target | Pass Criteria |
|-------|--------|---------------|
| Container health | orthoflow-backend, orthoflow-frontend, orthoflow-postgres, orthoflow-livekit, pgbouncer | All `running`, restart count < 3/5min |
| API health | `GET /health` and `GET /health/deep` | 200 OK, < 500ms |
| Database | PgBouncer stats | Connection utilization < 70%, avg_wait < 100ms |
| LiveKit | Port 7880 reachable | TCP connect succeeds |
| Disk | Host filesystem | Usage < 80% |
| Memory | Docker stats | No container > 80% of limit |
| Certificates | TLS on public endpoints | > 30 days to expiry |
| DNS | DDNS check | Resolves correctly |

### Escalation

- P1 (service down): Immediate alert → auto-restart → escalate if persists
- P2 (degraded): Auto-restart up to 6 attempts → backlog
- P3 (warning): Log and continue

---

## Phase 2: Web/Brochure (Marketing Agent)

**Trigger:** After marketing site changes, weekly audit  
**Owner:** Frontend Agent (marketing scope)  
**Goal:** Marketing claims match shipped product — never aspirational

### Checks

| Check | Pass Criteria |
|-------|---------------|
| Feature list accuracy | Every listed feature exists and works in the app today |
| Multi-specialty scope | Only Orthodontics + General Dentistry referenced |
| Pricing page | Reflects current tiers ($499/$899/$1499) |
| Screenshots | Match current UI (no outdated mockups) |
| SEO | sitemap.xml valid, robots.txt correct, JSON-LD structured data present |
| Links | No broken internal/external links |
| Container health | orthoflow-marketing container running, port responding |
| Performance | Lighthouse score > 90 (Performance), > 95 (SEO) |

### Fail Actions

- Feature mismatch → update marketing copy to match reality
- Aspirational content → remove immediately
- Broken links → fix or remove

---

## Phase 3: App E2E (QA Agent — OrthoFlow Staff)

**Trigger:** After every PR merge, nightly full suite  
**Owner:** QA Agent  
**Goal:** All staff workflows functional across all roles

### Test Suites

#### Auth & RBAC
- [ ] All 5 demo roles can log in
- [ ] Each role sees only their permitted nav items
- [ ] Staff Permissions page accessible by Owner/Doctor/Manager only
- [ ] Permission toggle changes take effect on next page load

#### Schedule
- [ ] View today's schedule
- [ ] Create appointment (select patient, chair, DA, time)
- [ ] Drag-and-drop appointment between chairs
- [ ] Start virtual visit from appointment card
- [ ] Schedule next visit from patient card

#### Patient Flow Board
- [ ] Board shows 5 columns: Scheduled → Lobby → Seated → Checked Out → Dismissed
- [ ] Check-in from Scheduled → moves to Lobby
- [ ] Drag from Lobby → Seated
- [ ] Drag from Seated → Checked Out
- [ ] Drag from Checked Out → Dismissed
- [ ] Invalid transitions blocked (can't go backwards)

#### Patients
- [ ] Search patients (debounced)
- [ ] Create patient with all fields (first, middle, last, DOB, gender, phone, email, responsible party)
- [ ] Expand patient info panel shows all fields
- [ ] Navigate to patient detail page
- [ ] Filter by status/treatment phase

#### Clinical
- [ ] View/create treatment notes
- [ ] Tooth chart loads and updates
- [ ] Imaging upload and view
- [ ] Appliance tracking
- [ ] CDT code browser (69 codes, 10 categories)

#### Finance
- [ ] View patient ledger
- [ ] Submit insurance claim
- [ ] AI denial review generates response
- [ ] Payment posting
- [ ] ERA import

#### Communications
- [ ] View message templates
- [ ] Send message to patient
- [ ] Active Virtual Visits card shows active calls
- [ ] Start video call from Patient Messages conversation header

#### Video Calling (Staff)
- [ ] Start virtual visit from appointment card
- [ ] VideoRoom opens with camera preview
- [ ] End call button works
- [ ] Visit appears in Active Virtual Visits

### Pass Criteria
- All critical paths pass (0 failures)
- Performance: page load < 3s, API responses < 2s

---

## Phase 4: MyOrthoChart E2E (QA Agent — Patient Portal)

**Trigger:** After every PR merge affecting portal  
**Owner:** QA Agent  
**Goal:** Complete patient journey functional

### Test Suites

#### Auth
- [ ] Patient login (priscilla.knowles@melanin-tech.com / Demo2026!)
- [ ] Invalid login rejected
- [ ] Token expiry handled gracefully

#### Dashboard
- [ ] Patient name displayed
- [ ] Treatment progress visualization
- [ ] Next appointment shown
- [ ] Unread messages count

#### Appointments
- [ ] View upcoming appointments
- [ ] Appointment details accurate

#### Messages
- [ ] View message threads
- [ ] Send message to office
- [ ] Receive replies

#### Forms
- [ ] View pending forms
- [ ] Fill and submit form
- [ ] Submitted forms show as completed

#### Virtual Visits
- [ ] Patient can request/join virtual visit
- [ ] Waiting room shows "Waiting for your doctor..."
- [ ] When doctor joins → transition to active video call
- [ ] Camera/mic controls work
- [ ] End call works

### Pass Criteria
- All patient-facing flows work
- No broken states or unhandled errors visible to patient
- Touch targets ≥ 44px (mobile-first)

---

## Phase 5: UX/UI Consistency Audit (UX/UI Agent)

**Trigger:** Before any release, after major UI changes  
**Owner:** UX/UI Agent  
**Goal:** Seamless transition for practices switching from topsOrtho/Cloud 9/Dolphin

### Consistency Checks

| Element | Standard |
|---------|----------|
| Border radius | `rounded-2xl` (cards), `rounded-xl` (inputs), `rounded-lg` (buttons) |
| Primary color | Teal-600 (actions), Teal-50 (active states) |
| Font sizes | Headers: text-2xl, Subheaders: text-sm font-semibold, Body: text-sm |
| Status badges | Active=emerald, Inactive=gray, Alert/Urgent=red, Warning=amber |
| Empty states | Icon + text + action suggestion (never blank/broken-looking) |
| Spacing | Section gaps: mb-6, Card padding: p-4/p-5/p-6, List item: py-3/py-4 |
| Icons | Lucide React only (no mixing icon sets) |
| Animations | Framer Motion, subtle (no jarring transitions) |

### Transition UX Checks

| Competitor Pattern | OrthoFlow Equivalent | Status |
|-------------------|---------------------|--------|
| topsOrtho: Practice Setup > Staff Permissions | Settings > Staff Permissions | ✅ |
| Cloud 9: Employee Types (templates) | Role Templates + Apply button | ✅ |
| Cloud 9: per-employee overrides | Per-user toggle grid | ✅ |
| Dolphin: CDT catalog by category | CDT Code Browser grouped | ✅ |
| All: patient search is instant | Debounced search (300ms) | ✅ |
| All: schedule = main entry point | Dashboard → Schedule as top nav item | ✅ |
| topsOrtho: visit tracker (check-in flow) | Patient Flow Board | ✅ |

### Accessibility
- [ ] All interactive elements have aria-labels
- [ ] Focus visible on keyboard navigation
- [ ] Color contrast ≥ 4.5:1 (WCAG AA)
- [ ] Touch targets ≥ 44px on portal (mobile patients)

---

## Phase 6: Automated Testing (CI Pipeline)

**Trigger:** Every push to feature branches, merge queue  
**Owner:** QA Agent + CI  
**Framework:** Playwright  
**Location:** `OrthoFlow/e2e/`

### Test Structure

```
e2e/
├── playwright.config.ts
├── fixtures/
│   └── auth.ts          # Login helpers for all roles
├── tests/
│   ├── auth.spec.ts
│   ├── schedule.spec.ts
│   ├── patients.spec.ts
│   ├── flow-board.spec.ts
│   ├── video-calls.spec.ts
│   ├── communications.spec.ts
│   ├── finance.spec.ts
│   ├── rbac.spec.ts
│   ├── portal.spec.ts
│   └── setup-wizard.spec.ts
└── helpers/
    └── api.ts           # Direct API calls for test setup
```

### CI Integration

```yaml
# .github/workflows/e2e.yml
on:
  pull_request:
  merge_group:

jobs:
  e2e:
    runs-on: ubuntu-latest
    services:
      postgres: ...
      redis: ...
    steps:
      - uses: actions/checkout@v4
      - name: Start backend
      - name: Start frontend
      - name: Seed demo data
      - name: Run Playwright
        run: npx playwright test
      - name: Upload artifacts on failure
        uses: actions/upload-artifact@v4
        if: failure()
        with:
          path: e2e/test-results/
```

### Pass/Fail Criteria

| Metric | Threshold |
|--------|-----------|
| Test pass rate | 100% (0 failures = green) |
| Flaky test rate | < 2% (auto-retry once) |
| Total suite time | < 5 minutes |
| Screenshot comparison | No unexpected visual diff |

---

## Error Handling & Logging Standards

All production code must implement:

1. **Structured JSON logging** — every log line parseable
2. **Request correlation IDs** — trace a request across services
3. **Context-rich errors** — what happened, what was expected, what to check
4. **No swallowed exceptions** — every catch block logs or re-raises
5. **Audit trail** — PHI access logged per HIPAA

### Log Format
```json
{
  "timestamp": "2026-07-30T04:55:18.004Z",
  "level": "ERROR",
  "correlation_id": "req-abc123",
  "service": "orthoflow-backend",
  "module": "api.routes.clinical",
  "message": "Patient creation failed",
  "context": {
    "practice_id": "82fe9d87-...",
    "user_id": "...",
    "error_type": "IntegrityError",
    "detail": "duplicate key value violates unique constraint"
  }
}
```

---

## Scaling Roadmap

| Milestone | Infrastructure | Process |
|-----------|---------------|---------|
| 1-10 practices | Current Mac Pro (16-core, 32GB) | Manual onboarding, setup wizard |
| 10-50 practices | Upgrade to 64GB, add SSD cache | Semi-automated, k6 load testing weekly |
| 50-200 practices | Dedicated server rack or colo | Automated onboarding, multi-tenant isolation |
| 200-1000+ | Kubernetes cluster (Kind → real K8s) | Full GitOps, per-practice namespace |

---

## Multi-Specialty Scope

**In Scope (Now):**
- Orthodontics (full treatment lifecycle)
- General Dentistry (hygiene, restorative, recall)

**Backlog Epics (Future Clients):**
- Periodontics (perio charting exists but not production-ready)
- Cosmetic Dentistry (veneer tracking, whitening)
- Implants (surgical planning, healing phases)
- Endodontics (root canal tracking)
- Oral Surgery (extraction planning)

Each backlog specialty will be its own Epic with dedicated onboarding flow when client demand warrants.
