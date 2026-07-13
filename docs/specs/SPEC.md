# OrthoFlow AI — Technical Specification

## Overview
AI-powered accounts payable automation for orthodontic practices. Processes vendor invoices through OCR + LLM classification, routes for approval, syncs to QuickBooks.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Client Browser / Mobile PWA                                     │
└──────────────────────┬──────────────────────────────────────────┘
                       │ HTTPS
┌──────────────────────▼──────────────────────────────────────────┐
│  FastAPI Backend (app/main.py)                                   │
│  ├── /api/v1/auth       — JWT authentication + SMS OTP MFA       │
│  ├── /api/v1/practices  — multi-tenant practice management      │
│  ├── /api/v1/invoices   — upload, list, approve, reject         │
│  ├── /api/v1/notifications — web push subscription & delivery   │
│  ├── /api/v1/payments   — Plaid ACH bank payments               │
│  ├── /api/v1/integrations — QuickBooks OAuth + sync             │
│  └── /health            — readiness/liveness probes             │
└──────┬──────────┬──────────┬──────────┬─────────────────────────┘
       │          │          │          │
  ┌────▼───┐ ┌───▼────┐ ┌───▼───┐ ┌───▼────┐
  │Postgres│ │ Redis  │ │ MinIO │ │ Ollama │
  │(pgvec) │ │(queue) │ │ (S3)  │ │ (LLM)  │
  └────────┘ └───┬────┘ └───────┘ └────────┘
                 │
          ┌──────▼──────┐
          │   Worker    │
          │ (ARQ async) │
          │ OCR → LLM → │
          │ classify    │
          └─────────────┘
```

## HIPAA Compliance Strategy

### MCP Server: Healthcare MCP (HMCP) Extension
Selected for:
- **Patient identity segregation** — each practice's data is isolated at the application and database level
- **Field-level permissions** — PHI fields encrypted at rest, access logged
- **Cross-organization protection** — prevents data leakage between practices

### Compliance Controls
| Control | Implementation |
|---------|---------------|
| Access Control (§164.312(a)) | JWT + RBAC (owner/manager/bookkeeper) |
| Audit Controls (§164.312(b)) | AuditLog table — every access logged with user, IP, timestamp |
| Integrity (§164.312(c)) | Immutable invoice records, versioned S3 objects |
| Transmission Security (§164.312(e)) | TLS 1.2+ everywhere, encrypted Redis connections |
| Encryption at Rest | AES-256 for PHI fields, S3 server-side encryption |
| Minimum Necessary | Field-level permissions — bookkeepers see amounts, not patient data |
| BAA | Required with AWS (available), QuickBooks (available) |

### Data Classification
| Field | PHI? | Encryption | Access Level |
|-------|------|-----------|-------------|
| Practice name | No | Standard | All roles |
| Vendor name | No | Standard | All roles |
| Invoice amounts | No | Standard | All roles |
| Patient names (if on invoice) | **Yes** | AES-256 | Owner + Manager only |
| NPI numbers | Sensitive | AES-256 | Owner only |
| Payment details | Sensitive | AES-256 | Owner + Manager |

## LLM Abstraction Layer

```python
# app/services/llm.py — single interface, multiple backends
async def complete(prompt, system, max_tokens) -> str:
    if settings.LLM_PROVIDER == "ollama":    # local dev
        return await _ollama(...)
    elif settings.LLM_PROVIDER == "bedrock": # AWS prod
        return await _bedrock(...)
```

### Local (open-source, no API keys):
- **Mistral 7B** via Ollama — invoice classification
- **nomic-embed-text** — semantic search for duplicate detection

### Production (HIPAA-eligible):
- **AWS Bedrock Claude** — BAA available, data stays in-region
- **AWS Textract** — OCR, HIPAA-eligible service

### Custom Model Path:
If compliance requires a fully private model:
1. Fine-tune Mistral/Llama on orthodontic invoice data
2. Host on Ollama (local) or SageMaker (AWS)
3. No data leaves the network

## Multi-Tenancy Model
- Every DB table has `practice_id` foreign key
- API middleware enforces tenant isolation via JWT claims
- No cross-practice queries possible at the ORM level
- K8s namespace provides network-level isolation

## AWS Migration Path

| Local | AWS Equivalent | Change Required |
|-------|---------------|-----------------|
| Docker Compose | ECS Fargate | Terraform `modules/ecs` |
| PostgreSQL container | RDS PostgreSQL | Connection string only |
| MinIO | S3 | Endpoint URL only |
| Redis container | ElastiCache | Connection string only |
| Ollama | Bedrock | `LLM_PROVIDER=bedrock` |
| Local filesystem | S3 | Already using S3 interface |

**Zero application code changes** — only environment variables and infrastructure.

## API Endpoints (MVP)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| POST | `/api/v1/auth/login` | JWT login |
| POST | `/api/v1/auth/register` | Create account |
| GET | `/api/v1/practices` | List practices |
| POST | `/api/v1/practices` | Create practice |
| POST | `/api/v1/invoices/upload` | Upload invoice PDF |
| GET | `/api/v1/invoices` | List invoices (practice-scoped) |
| GET | `/api/v1/invoices/{id}` | Get invoice detail |
| POST | `/api/v1/invoices/{id}/approve` | Approve invoice |
| POST | `/api/v1/invoices/{id}/reject` | Reject invoice |

## API Endpoints (v2)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/verify-otp` | Verify SMS OTP code for MFA |
| POST | `/api/v1/notifications/subscribe` | Register device for push notifications |
| DELETE | `/api/v1/notifications/subscribe` | Unsubscribe from push notifications |
| GET | `/api/v1/notifications` | List notifications for current user |
| PUT | `/api/v1/notifications/{id}/read` | Mark notification as read |
| POST | `/api/v1/notifications/send` | Send push notification (internal/admin) |
| POST | `/api/v1/payments/link-account` | Link bank account via Plaid |
| GET | `/api/v1/payments/accounts` | List linked payment accounts |
| POST | `/api/v1/payments/initiate` | Initiate ACH payment to vendor |
| GET | `/api/v1/payments/{id}/status` | Check payment status |
| GET | `/api/v1/payments` | List payment history |
| POST | `/api/v1/integrations/quickbooks/connect` | OAuth connect to QuickBooks |
| GET | `/api/v1/integrations/quickbooks/status` | Check QuickBooks connection status |
| POST | `/api/v1/integrations/quickbooks/sync` | Trigger manual sync to QuickBooks |
| GET | `/api/v1/integrations/quickbooks/accounts` | Pull chart of accounts from QuickBooks |

## File Structure
```
orthoflow-ai/
├── .github/workflows/ci.yml    # GitHub Actions CI/CD
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py             # FastAPI entry point
│       ├── core/
│       │   ├── config.py       # Pydantic settings
│       │   └── database.py     # SQLAlchemy async engine
│       ├── models/
│       │   └── models.py       # Practice, User, Invoice, LineItem, AuditLog
│       ├── api/routes/
│       │   ├── health.py
│       │   ├── auth.py
│       │   ├── practices.py
│       │   └── invoices.py
│       ├── services/
│       │   └── llm.py          # LLM abstraction (ollama/bedrock)
│       └── workers/
│           └── main.py         # ARQ async invoice processor
├── frontend/
│   ├── Dockerfile
│   └── package.json
├── k8s/
│   └── orthoflow.yaml          # Full namespace manifest
├── terraform/
│   └── main.tf                 # AWS infrastructure (commented, ready)
├── docker-compose.yml           # Local dev stack
├── .env.example
└── .gitignore
```

---

## AI Architecture — LLM Routing (Updated 2026-07-13)

### Client-Facing (OrthoFlow App)

```
OrthoFlow Backend → Anthropic Claude API (direct httpx call)
```

- Model: claude-haiku-4-5 (fast, reliable, <10s responses)
- No intermediary (no Darius, no litellm, no smolagents)
- HIPAA: PHI in transit over TLS, not stored by Anthropic (BAA required)
- Future: swap to Mistral Small 24B local (one URL change)

### Internal Operations (Darius Agent System)

```
Slack/Orchestrator → Darius → litellm → Anthropic Claude
```

- Used for: multi-step infrastructure tasks, code generation, planning
- Has: session memory, tool calling, evaluation loops, DAG execution
- Known issue: litellm cache_control_injection_points bug (non-blocking for internal use)
- Future: upgrade Darius runtime to eliminate Anthropic dependency

### Migration Path to Fully Local

| Phase | Target | Stack |
|-------|--------|-------|
| Current | Anthropic Haiku (client) + Sonnet (Darius) | httpx → Anthropic API |
| 07/20/2026 | Mistral Small 24B local (client) | httpx → Ollama endpoint |
| Future | Mistral Small local (client + Darius) | All local, zero API cost |

### What NOT to do
- Do not route client-facing AI through Darius/litellm (reliability risk)
- Do not use litellm for OrthoFlow features until the harness bug is resolved
- Do not expose internal agent errors to end users
