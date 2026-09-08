# OrthoFlow AI — Steering

## What This Is

Accounts payable automation + insurance claims platform for orthodontic practices.
Live at: https://app.orthoflowsolutions.com / https://api.orthoflowsolutions.com
Repo: github.com/parrish727/OrthoFlow (private, feature/orthoflow_v1 branch)

## North Star — Precognitive by Design (READ FIRST)

OrthoFlow AI must be intuitive and **precognitive** — it should know what each member of
the ortho team wants and needs to do *before they know it themselves*. This applies to
EVERY role and EVERY surface:

- **Doctor** — next clinical action, patients needing attention, treatment-plan nudges
- **Dental Assistant (DA)** — chair readiness, prep needs, personal-day/shift context
- **Front Desk** — arrivals, forms outstanding, balances to collect, callbacks due
- **Office Manager** — bottlenecks, staffing, revenue/collections at a glance
- **Treatment Coordinator (Insurance, Claims, Ledgers, Reports)** — eligibility gaps,
  likely denials before submission, patient-responsibility surprises, appeal opportunities

### How this shapes every build (backend → frontend)

1. **Anticipate, don't just react.** Surface the next best action proactively. Pre-flag
   risk (denial likelihood, benefit exhaustion, overdue balances) before the user hunts.
2. **Sync context across roles.** Notes, statuses, and signals flow between DA, front desk,
   TC, and provider views so nobody re-enters or re-discovers what another already knows.
3. **Make small things unforgettable.** Micro-interactions, defaults, empty states, and
   copy all reflect deep ortho-workflow understanding. Details are the product.
4. **Everything matters end-to-end.** Backend, frontend, security, stability,
   sustainability, observability, and the seams between them are all held to this bar.
5. **Build on what exists with this instinct.** Every new feature or update must extend the
   current system while advancing this vision — not bolt on in isolation.

Every PR should be answerable: *"How does this make OrthoFlow feel like it read the team's
mind?"* If the answer is "it doesn't," reconsider the design.

## Stack

- **Backend:** FastAPI (Python), PostgreSQL, Redis, MinIO, Ollama
- **Frontend:** React + Vite + TypeScript, Tailwind CSS
- **AI/ML:** Custom orthoflow-classify model, OCR, LLM invoice classification
- **Infra:** Docker Compose, Watchtower (auto-deploy from GHCR)

## Architecture

```
backend/
  app/
    api/          # Route handlers
    models/       # SQLAlchemy models
    core/         # Config, security, deps
  alembic/        # DB migrations
  tests/
frontend/
  src/
    pages/        # Route views
    components/   # Reusable UI
  dist/           # Production build
ml/
  finetune.py     # Model training
  training_data/
k8s/
  orthoflow.yaml  # K8s deployment manifest
terraform/        # AWS migration scaffold
docs/
  SPEC.md                  # Core product spec
  MEDICARE_MEDICAID_SPEC.md # v2.1 insurance claims
```

## Integrations

- QuickBooks (OAuth) — invoice sync
- Plaid (ACH) — payment processing
- Ortho2 (API) — practice management
- Dentrix/Eaglesoft (file import)
- ClamAV — virus scanning on uploads

## Security

- JWT practice-scoped auth
- SMS OTP MFA
- HIPAA audit logs
- ClamAV file scanning
- Tier system: Standard (multi-tenant) / Enterprise (single-tenant K8s namespace)

## Rules

- All routes require Pydantic input validation
- HIPAA: audit log every data access, encrypt PII at rest
- No OpenAI models — Anthropic Claude or local Ollama only
- Tests required for auth and payment code paths
- Alembic for all schema changes (no raw DDL)

## Branching & Deploy Model (Option A)

OrthoFlow uses a two-branch model:

- **`main` = source of truth.** Always-releasable integration branch. Feature branches merge
  here via PR. Pushing to `main` runs **tests only** — it does NOT deploy.
- **`production` = deploy branch.** The CI build/publish job triggers **only** on pushes to
  `production` (image → GHCR → Watchtower deploys). This keeps "what is live" cleanly separate
  from "our source of truth."

**Promote to production** by merging `main → production` (fast-forward or PR). That push is what
ships to prod. Never build/deploy straight from `main`.

CI wiring (`.github/workflows/ci.yml`): test job runs on `main`, `develop`, and PRs; build job
gated on `refs/heads/production`. Recommended GitHub branch protection: PR-only on `main` and
`production`, required status checks (test job) before merge.
