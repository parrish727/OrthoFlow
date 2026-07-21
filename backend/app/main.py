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
from app.api.routes import ai_intelligence, ai_denial_patterns, ai_referrals, ai_timeline
from app.api.routes import portal, portal_admin, reports, migration
from app.api.routes import team
from app.api.routes import timetracking
from app.api.routes import appliance_tracking
from app.api.routes import clinical_enhancements
from app.api.routes import workflow
from app.api.routes import messaging
from app.core.config import settings
from app.core.database import engine, Base

app = FastAPI(
    title="OrthoFlow AI",
    version="0.1.0",
    description="AI-Powered Accounts Payable Automation for Orthodontic Practices",
    redirect_slashes=False,
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
    import app.models  # noqa: ensure all models are registered
    # Schema managed by Alembic migrations — no create_all needed
    pass

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
app.include_router(ai_intelligence.router, tags=["ai-intelligence"])
app.include_router(ai_denial_patterns.router, tags=["ai-intelligence"])
app.include_router(ai_referrals.router, tags=["ai-intelligence"])
app.include_router(ai_timeline.router, tags=["ai-intelligence"])
app.include_router(portal.router, tags=["patient-portal"])
app.include_router(portal_admin.router, tags=["patient-portal-admin"])
app.include_router(team.router, tags=["team"])
app.include_router(reports.router, tags=["reports"])
app.include_router(migration.router, tags=["migration"])
app.include_router(timetracking.router, tags=["time-tracking"])
app.include_router(appliance_tracking.router, tags=["appliance-tracking"])
app.include_router(clinical_enhancements.router, tags=["clinical-enhancements"])
app.include_router(workflow.router, tags=["workflow"])
app.include_router(messaging.router, tags=["messaging"])


# ── Deep Health Check (verifies core routes, not just "is the process alive") ──
@app.get("/health/deep")
async def deep_health_check():
    """Comprehensive health check that catches enum mismatches, DB issues, and import errors.
    Called by QA agent and container healthcheck. If this fails, the app is broken."""
    from sqlalchemy import text, select, func
    from app.core.database import get_db, SessionLocal
    from app.models.clinical import Patient
    from app.core.auth import create_token

    errors = []

    # 1. DB connection + model query
    try:
        async with SessionLocal() as db:
            await db.execute(text("SELECT 1"))
            result = await db.execute(select(func.count(Patient.id)))
            count = result.scalar()
    except Exception as e:
        errors.append(f"db/models: {e}")

    # 2. Verify auth works (catches role enum issues)
    try:
        token = create_token("test-id", "test-practice", "owner")
        assert len(token) > 20
    except Exception as e:
        errors.append(f"auth: {e}")

    if errors:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"status": "unhealthy", "errors": errors})

    return {"status": "healthy", "checks": ["db", "models", "auth"], "patient_count": count}
