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

## How the AI Learns Your Practice

OrthoFlow's AI isn't generic — it's trained on orthodontic-specific terminology and adapts to how your office works.

### Orthodontic Vocabulary Recognition

The AI understands that:
- "Damon Q2 .022 Upper 5-5" = brackets (supplies category)
- "NiTi .016 x .022 Lower" = archwire (supplies)
- "Essix ACE .040" = retainer material (lab)
- "CBCT scan fee" = imaging (equipment/services)
- "Clearinghouse monthly" = insurance-related fee

It recognizes invoice formats from the top orthodontic vendors (Ormco, 3M Unitek, Henry Schein, Patterson Dental, American Orthodontics, Rocky Mountain Orthodontics) and knows how to parse their specific line item structures.

### Practice-Specific Learning

Over time, OrthoFlow learns YOUR office's preferences:
- **Custom GL mappings** — if you code "lab retainers" to account 5200 instead of 5100, the AI remembers
- **Approval patterns** — learns which vendors the doctor always approves vs. which need review
- **Vendor nicknames** — if your team calls Henry Schein "HS" on internal notes, the AI maps it correctly
- **Seasonal patterns** — knows you order more brackets in September (back-to-school rush) and flags unusual volumes

### How It Gets Smarter

1. **Day 1** — AI uses the base orthodontic vendor catalog (200+ item taxonomy)
2. **Week 1–4** — every approve/reject/edit teaches the model your preferences
3. **Month 2+** — confidence scores rise above 95%, fewer items need manual review
4. **Month 6+** — the AI has a complete picture of your practice's spending patterns, vendor relationships, and coding preferences

This learned data is YOUR data — it stays in your isolated environment and never trains other clients' models.

---

## v2 Features

| Feature | Description |
|---------|-------------|
| **Push Notifications** | Web Push + mobile notifications for invoice approvals, payment confirmations, and system alerts |
| **SMS OTP MFA** | Multi-factor authentication via Twilio SMS one-time passwords for enhanced account security |
| **Plaid ACH Payments** | Direct bank-to-bank payments via Plaid — pay vendors without leaving OrthoFlow |
| **Custom LLM Fine-tuning** | Practice-specific model fine-tuning on your invoice history for 99%+ classification accuracy |
| **QuickBooks Integration** | Bi-directional sync — approved invoices push to QuickBooks, chart of accounts pulls in automatically |

---

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
