# OrthoFlow AI

AI-powered practice management and accounts payable automation for orthodontic & dental practices.

## Modules

| Phase | Module | Key Features |
|-------|--------|--------------|
| — | AP Automation | Invoice OCR, AI classification (97%+ accuracy), approval workflow, QuickBooks sync, duplicate detection |
| 1 | Scheduling & Patient Charts | Multi-chair schedule, DA drag-and-drop, tooth chart, AI clinical notes |
| 2 | Finance & Insurance | Patient ledger, insurance plans, eligibility verification, claims workflow (HIPAA 837D), AI denial detection + appeal writing, payment posting + ERA |
| 3 | Patient Communications | Automated reminders (email active), two-way texting (SMS disabled pending legal review), TCPA consent management, message templates, delivery dashboard |
| 4a | Imaging Suite | Web upload, MinIO cloud storage, in-chart viewer, overdue imaging alerts, edge appliance architecture (for Phase 4b on-premise capture) |

## Quick Start

```bash
cp .env.example .env
docker compose up -d
curl http://localhost:8000/health
# → {"status": "healthy"}
cd frontend && npm install && npx vite --host 0.0.0.0
# → http://localhost:5173
```

## Services

| Service | Port | Purpose |
|---------|------|---------|
| Backend API | 8000 | FastAPI — auth, invoices, scheduling, claims, comms, imaging |
| Frontend | 5173 | React 19 + Vite — SPA dashboard |
| PostgreSQL | 5433 | Database (pgvector for semantic features) |
| Redis | 6380 | Job queue, caching, pub/sub |
| MinIO | 9100/9101 | Object storage (invoices, images, documents) |
| Ollama | 11435 | Local embeddings (nomic-embed-text), classification |
| Worker | internal | Async pipeline (OCR, AI classification, claim generation) |
| Watchtower | internal | Auto-deploy from GHCR on merge to main |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, TypeScript (strict), Vite, Tailwind CSS, Framer Motion, Lucide icons |
| Backend | Python 3.11+, FastAPI, SQLAlchemy, Pydantic, httpx |
| Database | PostgreSQL 16 + pgvector |
| AI (production) | Anthropic Claude (via Darius orchestration) |
| AI (local) | Ollama — nomic-embed-text (embeddings), custom classification models |
| Storage | MinIO (encryption at rest enabled) |
| Queue/Cache | Redis |
| CI/CD | GitHub Actions (lint → test → build → push to GHCR) |
| Deploy | Watchtower auto-pull from GHCR, Docker Compose |
| Container Scanning | Trivy (in CI pipeline) |

## Architecture

```
Frontend (React 19 + Vite + Tailwind)
    │
    ▼
Backend API (FastAPI)
    ├── Auth (JWT, practice-scoped, SMS OTP MFA for admin)
    ├── Scheduling (multi-chair, DA assignment)
    ├── Patient Charts (tooth chart, AI clinical notes)
    ├── Finance (ledger, insurance, claims, ERA)
    ├── Communications (reminders, templates, delivery tracking)
    ├── Imaging (upload, viewer, alerts)
    └── AP Automation (OCR, classification, approval, QuickBooks sync)
    │
    ├── PostgreSQL (relational data + pgvector)
    ├── Redis (job queue + cache)
    ├── MinIO (documents, images, invoices)
    └── Ollama / Claude (AI classification, denial detection, notes)
    │
    ▼
Worker (async pipelines)
    → OCR text extraction
    → LLM invoice classification
    → Claim generation (HIPAA 837D)
    → Denial detection + appeal drafting
    → Reminder scheduling + delivery
```

## Security & Compliance

| Control | Implementation |
|---------|----------------|
| Authentication | JWT (1hr expiry) + SMS OTP MFA, practice-scoped claims |
| Authorization | RBAC — Owner / Office Manager / Bookkeeper |
| Data Isolation | All queries filtered by practice_id from JWT |
| Encryption (transit) | TLS 1.2+ enforced, HSTS |
| Encryption (rest) | pgcrypto (DB), MinIO server-side encryption (objects) |
| Audit Trail | Every data access logged (who, what, when, IP) |
| File Scanning | ClamAV on all uploads |
| Container Scanning | Trivy in GitHub Actions CI |
| PHI Protection | No patient data in logs or error messages |
| HIPAA Compliance | Full §164.312 controls implemented |
| Network | nginx reverse proxy only, Cloudflare DDoS, fail2ban |

## Deployment

| Environment | Method |
|-------------|--------|
| Production | Merge to `main` → GitHub Actions → GHCR → Watchtower auto-deploy |
| Self-hosted | Docker Compose on Mac Pro, docker_agent-net bridge |
| Domain | app.orthoflowsolutions.com (frontend), api.orthoflowsolutions.com (backend) |

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection (asyncpg) |
| `REDIS_URL` | Redis connection |
| `MINIO_ENDPOINT` | MinIO host:port |
| `ANTHROPIC_API_KEY` | Claude API (production inference) |
| `OLLAMA_URL` | Local Ollama instance |
| `TWILIO_*` | SMS OTP + patient messaging credentials |
| `QUICKBOOKS_*` | QuickBooks OAuth + sync credentials |

All secrets via `.env` (gitignored). Never committed to source.

## Documentation

| Doc | Path |
|-----|------|
| Technical Spec | `docs/SPEC.md` |
| Medicare/Medicaid | `docs/MEDICARE_MEDICAID_SPEC.md` |
| TCPA Consent Workflow | `docs/TCPA_CONSENT_WORKFLOW.md` |
| Clearinghouse Guide | `docs/CLEARINGHOUSE_GUIDE.md` |

## Git Flow

- `main` — production (merges via PR only, no force push)
- Feature branches → PR → CI passes → merge → auto-deploy

## Built By

Melanin Technologies Inc. — Charlotte, NC
www.melanin-tech.com | info@melanin-tech.com
