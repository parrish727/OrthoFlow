from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    # Runtime environment
    ENVIRONMENT: str = "development"  # development | staging | production

    # Database (required — no dangerous default)
    DATABASE_URL: str = "postgresql://orthoflow:changeme@localhost:5433/orthoflow"
    # OrthoFlow reaches Postgres through PgBouncer (transaction pooling). When true, the
    # asyncpg driver disables prepared-statement caching for pooling compatibility.
    DB_VIA_PGBOUNCER: bool = True

    # Redis
    REDIS_URL: str = "redis://localhost:6380/0"

    # Object Storage
    S3_ENDPOINT: str = "http://localhost:9100"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = "invoices"

    # LLM — Anthropic Claude only for production inference
    LLM_PROVIDER: str = "anthropic"  # anthropic | ollama (ollama for local dev/embeddings only)
    ANTHROPIC_API_KEY: str = ""
    OLLAMA_URL: str = "http://localhost:11435"
    OLLAMA_MODEL: str = "nomic-embed-text"  # embeddings only

    # Auth
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 1  # Short-lived access tokens

    # CORS
    # CORS. Includes the internal E2E test origin (docker hostname) so the Dockerized
    # Playwright QA harness can drive the app without depending on public DNS/CDN.
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "https://app.orthoflowsolutions.com",
        "http://orthoflow-frontend-1:3000",
    ]

    # QuickBooks Online
    QBO_CLIENT_ID: str = ""
    QBO_CLIENT_SECRET: str = ""
    QBO_REDIRECT_URI: str = "https://api.orthoflowsolutions.com/api/v1/integrations/quickbooks/callback"
    QBO_ENVIRONMENT: str = "sandbox"  # sandbox | production

    # Plaid
    PLAID_CLIENT_ID: str = ""
    PLAID_SECRET: str = ""
    PLAID_ENVIRONMENT: str = "sandbox"  # sandbox | production

    # ── Stedi Clearinghouse ───────────────────────────────────────────────────
    # Eligibility (270/271) runs LIVE against Stedi test mode. Claims (837D) and ERA
    # (835) are simulated in sandbox to Stedi's real contract; flip STEDI_LIVE_CLAIMS
    # to true with a production key to submit real claims.
    STEDI_ENABLED: bool = True
    STEDI_API_KEY: str = ""
    # Correct base host per Stedi docs (JSON eligibility + dental-claims endpoints).
    STEDI_BASE_URL: str = "https://healthcare.us.stedi.com/2024-04-01"
    STEDI_WEBHOOK_SECRET: str = ""
    STEDI_LIVE_CLAIMS: bool = False  # sandbox: simulate claims/ERA. prod: submit for real.
    # Provider identity used on eligibility + claim submissions. Any NPI passing the
    # CMS check-digit algorithm works for Stedi test mode.
    STEDI_PROVIDER_NPI: str = "1999999984"
    STEDI_PROVIDER_ORG_NAME: str = "OrthoFlow Orthodontics"
    STEDI_SUBMITTER_ID: str = ""

    # Dormant Stedi MCP (production only — requires account upgrade). Scaffolded now,
    # activated on production transition. See services/stedi_mcp.py.
    # Streamable HTTP MCP server (API-key auth). Works with test keys but requires a
    # production Stedi account to be reachable.
    STEDI_MCP_ENABLED: bool = False
    STEDI_MCP_URL: str = "https://mcp.us.stedi.com/2025-07-11/mcp"
    STEDI_MCP_API_KEY: str = ""

    # Dormant NCTracks (NC Medicaid) claim destination — requires provider enrollment (CEP)
    # + EDI trading-partner setup. Scaffolded; enable after pktech_dev completes enrollment.
    NCTRACKS_ENABLED: bool = False
    NCTRACKS_API_URL: str = ""

    # Twilio (SMS for MFA)
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # ClamAV
    CLAMAV_URL: str = "http://clamav:3310"

    # HIPAA
    AUDIT_LOG_ENABLED: bool = True
    PHI_ENCRYPTION_KEY: str = ""  # AES-256 key for PHI at rest

    @field_validator("JWT_SECRET")
    @classmethod
    def jwt_secret_must_be_set(cls, v: str) -> str:
        if not v or v in ("change-this-in-production", "changeme"):
            import os
            if os.environ.get("ENVIRONMENT", "development") == "production":
                raise ValueError("JWT_SECRET must be set in production")
        return v

    class Config:
        env_file = ".env"


settings = Settings()
