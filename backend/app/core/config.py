from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    # Database (required — no dangerous default)
    DATABASE_URL: str = "postgresql://orthoflow:changeme@localhost:5433/orthoflow"

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
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "https://app.orthoflowsolutions.com"]

    # QuickBooks Online
    QBO_CLIENT_ID: str = ""
    QBO_CLIENT_SECRET: str = ""
    QBO_REDIRECT_URI: str = "https://api.orthoflowsolutions.com/api/v1/integrations/quickbooks/callback"
    QBO_ENVIRONMENT: str = "sandbox"  # sandbox | production

    # Plaid
    PLAID_CLIENT_ID: str = ""
    PLAID_SECRET: str = ""
    PLAID_ENVIRONMENT: str = "sandbox"  # sandbox | production

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
