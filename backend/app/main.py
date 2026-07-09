from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import invoices, auth, practices, health
from app.api.routes import quickbooks, notifications, payments, pms, spend
from app.api.routes import clinical
from app.api.routes import ai_assistant
from app.api.routes import finance as finance_routes
from app.api.routes import eligibility
from app.api.routes import claims_workflow
from app.api.routes import ai_claims
from app.api.routes import comm_preferences, comm_templates, comm_scheduler, comm_inbound, comm_dashboard
from app.api.routes import imaging, imaging_alerts, imaging_ingest
from app.core.config import settings
from app.core.database import engine, Base

app = FastAPI(
    title="OrthoFlow AI",
    version="0.1.0",
    description="AI-Powered Accounts Payable Automation for Orthodontic Practices",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    from app.models.models import Base  # noqa: ensure models are imported
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(health.router, tags=["health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(practices.router, prefix="/api/v1/practices", tags=["practices"])
app.include_router(invoices.router, prefix="/api/v1/invoices", tags=["invoices"])
app.include_router(quickbooks.router, prefix="/api/v1/integrations/quickbooks", tags=["quickbooks"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])
app.include_router(pms.router, prefix="/api/v1/pms", tags=["pms"])
app.include_router(spend.router, prefix="/api/v1/spend", tags=["spend"])
app.include_router(clinical.router, tags=["clinical"])
app.include_router(ai_assistant.router, tags=["ai-assistant"])
app.include_router(finance_routes.router, tags=["finance"])
app.include_router(eligibility.router, tags=["eligibility"])
app.include_router(claims_workflow.router, tags=["claims-workflow"])
app.include_router(ai_claims.router, tags=["ai-claims"])
app.include_router(comm_preferences.router, tags=["communications"])
app.include_router(comm_templates.router, tags=["communications"])
app.include_router(comm_scheduler.router, tags=["communications"])
app.include_router(comm_inbound.router, tags=["communications"])
app.include_router(comm_dashboard.router, tags=["communications"])
app.include_router(imaging.router, tags=["imaging"])
app.include_router(imaging_alerts.router, tags=["imaging"])
app.include_router(imaging_ingest.router, tags=["imaging"])
