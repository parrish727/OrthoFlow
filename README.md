# OrthoFlow AI

AI-Powered Accounts Payable Automation for Orthodontic & Dental Practices.

## What It Does

OrthoFlow eliminates the manual invoice processing that costs orthodontic offices 12–16 hours per week in staff time. Upload a PDF → AI extracts and classifies → one-tap approve → syncs to QuickBooks.

```
Invoice arrives (email/PDF/scan)
    → AI extracts vendor, line items, amounts (OCR + LLM)
    → AI classifies against orthodontic expense categories (97%+ accuracy)
    → Push notification for one-tap approval
    → Syncs to QuickBooks automatically
    → Done in 2 minutes vs. 15+ minutes manually
```

## Key Features

- **Invoice OCR** — auto-extract from PDF, image, or email
- **AI Classification** — ortho-specific vendor catalog (Ormco, 3M, Henry Schein, Patterson)
- **Approval Workflow** — mobile push notifications, one-tap approve/reject, configurable thresholds
- **Insurance EOB Matching** — flags underpayments for appeal
- **Duplicate Detection** — catches double-payments before they happen
- **QuickBooks Sync** — approved invoices push with correct GL codes
- **HIPAA Compliant** — audit trail, encryption, role-based access

## Quick Start (Local Development)

```bash
# 1. Copy environment
cp .env.example .env

# 2. Start all services
docker compose up -d

# 3. Verify backend
curl http://localhost:8000/
# → {"status": "healthy", "service": "orthoflow-ai"}

# 4. Start frontend
cd frontend && npm install && npx vite --host 0.0.0.0
# → http://localhost:5173
```

## Services

| Service | Port | Purpose |
|---------|------|---------|
| Backend API | 8000 | FastAPI — auth, invoices, approval |
| Frontend | 5173 | React + Vite — dashboard UI |
| PostgreSQL | 5433 | Database (pgvector) |
| Redis | 6380 | Job queue for async processing |
| MinIO | 9100/9101 | S3-compatible invoice storage |
| Ollama | 11435 | Local LLM (Mistral) |
| Worker | internal | OCR + AI classification pipeline |
| Watchtower | internal | Auto-deploy from GHCR |

## Architecture

```
Frontend (React + Vite + Tailwind)
    │
    ▼
Backend API (FastAPI)
    ├── Auth (JWT, practice-scoped)
    ├── Invoice CRUD + Upload
    └── Approval Workflow
    │
    ├── PostgreSQL (data)
    ├── Redis (job queue)
    ├── MinIO/S3 (document storage)
    └── Ollama/Bedrock (AI classification)
    │
    ▼
Worker (async pipeline)
    → OCR extract text
    → LLM classify line items
    → Update DB with results
```

## Tech Stack

- **Frontend** — React 19, TypeScript, Vite, Tailwind CSS v4, Lucide icons
- **Backend** — Python, FastAPI, SQLAlchemy, Pydantic
- **Database** — PostgreSQL + pgvector
- **AI** — Ollama (local, open-source) → AWS Bedrock (production, HIPAA-eligible)
- **Storage** — MinIO (local) → AWS S3 (production)
- **Queue** — Redis
- **CI/CD** — GitHub Actions (test on PR, build+push on merge)
- **Deploy** — Watchtower (auto-pull from GHCR)
- **IaC** — Terraform (AWS migration scaffold)

## HIPAA Compliance

- Healthcare MCP (HMCP) extension for patient identity segregation
- AuditLog on every data access (who, what, when, from where)
- Field-level encryption for PHI
- Multi-tenant isolation at DB and API level
- Role-based access: Owner / Office Manager / Bookkeeper
- BAA available with all infrastructure providers

## Git Flow

- `main` — production-ready, merges via PR only
- `feature/orthoflow_v1` — active development

## AWS Migration

Zero application code changes. Only environment variables:

```bash
LLM_PROVIDER=bedrock          # swap from ollama
S3_ENDPOINT=                   # remove (uses real S3)
DATABASE_URL=<RDS endpoint>    # swap from local postgres
```

Terraform scaffold in `terraform/main.tf`.

## Documentation

- `docs/SPEC.md` — technical specification
- `docs/CLIENT_MANIFEST.md` — client-facing project overview
- `docs/PRODUCT_OVERVIEW.md` — product features + competitive comparison

## Built By

Melanin Technologies Inc. — Charlotte, NC
www.melanin-tech.com | info@melanin-tech.com
