from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://orthoflow:changeme@localhost:5433/orthoflow"

    # Redis
    REDIS_URL: str = "redis://localhost:6380/0"

    # Object Storage
    S3_ENDPOINT: str = "http://localhost:9100"
    S3_ACCESS_KEY: str = "orthoflow"
    S3_SECRET_KEY: str = "changeme123"
    S3_BUCKET: str = "invoices"

    # LLM
    LLM_PROVIDER: str = "ollama"  # ollama | litellm | bedrock
    OLLAMA_URL: str = "http://localhost:11435"
    OLLAMA_MODEL: str = "mistral"
    BEDROCK_MODEL: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"

    # Auth
    JWT_SECRET: str = "change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "https://app.orthoflowsolutions.com"]

    # HIPAA
    AUDIT_LOG_ENABLED: bool = True
    PHI_ENCRYPTION_KEY: str = ""  # AES-256 key for PHI at rest

    class Config:
        env_file = ".env"


settings = Settings()
