# OrthoFlow AI — Steering

## What This Is

Accounts payable automation + insurance claims platform for orthodontic practices.
Live at: https://app.orthoflowsolutions.com / https://api.orthoflowsolutions.com
Repo: github.com/parrish727/OrthoFlow (private, feature/orthoflow_v1 branch)

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
