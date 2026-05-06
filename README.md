# OrthoFlow AI

AI-Powered Accounts Payable Automation for Orthodontic Practices.

## Quick Start (Local Development)

```bash
# 1. Copy environment
cp .env.example .env

# 2. Start all services
docker compose up -d

# 3. Verify
curl http://localhost:8000/
# → {"status": "healthy", "service": "orthoflow-ai"}
```

**Services:**
| Service | Port | URL |
|---------|------|-----|
| Backend API | 8000 | http://localhost:8000 |
| Frontend | 5173 | http://localhost:5173 |
| PostgreSQL | 5433 | localhost:5433 |
| Redis | 6380 | localhost:6380 |
| MinIO Console | 9101 | http://localhost:9101 |
| Ollama | 11435 | http://localhost:11435 |

## Architecture

Fully isolated from Melanin Technologies infrastructure. Own network, own namespace, own data.

- **Backend:** Python / FastAPI — multi-tenant, HIPAA-compliant
- **AI:** Ollama (local, open-source) → AWS Bedrock (prod, HIPAA-eligible)
- **Storage:** MinIO (local, S3-compatible) → AWS S3 (prod)
- **Queue:** Redis + ARQ for async invoice processing
- **Database:** PostgreSQL + pgvector

## HIPAA Compliance

- Healthcare MCP (HMCP) extension for patient identity segregation
- AuditLog on every data access
- Field-level encryption for PHI
- Multi-tenant isolation at DB and API level
- See `docs/SPEC.md` for full compliance matrix

## AWS Migration

Zero application code changes. Only environment variables:

```bash
LLM_PROVIDER=bedrock          # swap from ollama
S3_ENDPOINT=                   # remove (uses real S3)
DATABASE_URL=<RDS endpoint>    # swap from local postgres
```

Terraform in `terraform/main.tf` — uncomment modules when ready.

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`):
- **On PR:** run tests against Postgres + Redis
- **On merge to main:** build + push Docker images to GHCR

## K8s Deployment (Local)

```bash
kubectl apply -f k8s/orthoflow.yaml
```

Creates isolated `orthoflow` namespace with all services.
