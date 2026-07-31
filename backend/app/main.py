from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
from app.api.routes import portal, portal_admin, patient_messages, reports, migration
from app.api.routes import team
from app.api.routes import timetracking
from app.api.routes import appliance_tracking
from app.api.routes import clinical_enhancements
from app.api.routes import catalog
from app.api.routes import restorative
from app.api.routes import workflow
from app.api.routes import messaging
from app.api.routes import perio
from app.api.routes import recall
from app.api.routes import stedi_webhook
from app.api.routes import virtual_visits
from app.api.routes import staff_permissions
from app.api.routes import onboarding
from app.core.config import settings
from app.core.database import engine, Base
from app.core.logging import (
    setup_logging,
    get_logger,
    CorrelationIDMiddleware,
    RequestLoggingMiddleware,
    build_error_context,
    correlation_id_var,
)

# ── Initialize structured logging before anything else ────────────────────────
setup_logging(level="INFO")
logger = get_logger(__name__)

app = FastAPI(
    title="OrthoFlow AI",
    version="0.1.0",
    description="AI-Powered Accounts Payable Automation for Orthodontic Practices",
)

# ── Middleware (order matters: first added = outermost) ───────────────────────
# CORS must be outermost to handle preflight requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Request logging wraps the route handlers
app.add_middleware(RequestLoggingMiddleware)
# Correlation ID is innermost — sets context for everything above
app.add_middleware(CorrelationIDMiddleware)


# ── Global Exception Handler ─────────────────────────────────────────────────

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch all unhandled exceptions, log with full context, return safe 500."""
    error_context = build_error_context(exc, request=request, max_frames=5)
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {exc}",
        extra={"context": error_context},
    )

    # Return correlation ID so the client can reference it in support requests
    cid = correlation_id_var.get("none")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "correlation_id": cid,
            "error_type": type(exc).__name__,
        },
    )


@app.on_event("startup")
async def startup():
    import app.models  # noqa: ensure all models are registered
    # Schema managed by Alembic migrations — no create_all needed

    logger.info("OrthoFlow backend starting up", extra={"context": {"event": "startup"}})

    # Auto-seed demo data on startup (idempotent, ensures today's schedule/flow board populated)
    import os
    if os.environ.get("AUTO_SEED_DEMO", "true").lower() == "true":
        try:
            from app.seeds.demo_flow import seed_demo_flow
            await seed_demo_flow()
            logger.info("Demo seed completed", extra={"context": {"event": "seed_complete"}})
        except Exception as e:
            logger.warning(
                f"Demo seed on startup skipped: {e}",
                extra={"context": {"event": "seed_skipped", "reason": str(e)}},
            )

        # Background task: re-seed at midnight to keep today's schedule fresh
        import asyncio
        from datetime import datetime, timezone, timedelta

        async def daily_reseed():
            """Re-run seed at midnight each day so demo data stays current."""
            while True:
                now = datetime.now(timezone.utc)
                tomorrow = (now + timedelta(days=1)).replace(hour=4, minute=0, second=0, microsecond=0)  # 4 AM UTC = midnight ET
                wait_seconds = (tomorrow - now).total_seconds()
                await asyncio.sleep(wait_seconds)
                try:
                    from app.seeds.demo_flow import seed_demo_flow
                    await seed_demo_flow()
                    logger.info("Daily reseed completed", extra={"context": {"event": "daily_reseed"}})
                except Exception as e:
                    logger.warning(f"Daily reseed failed: {e}", extra={"context": {"event": "reseed_failed", "reason": str(e)}})

        asyncio.create_task(daily_reseed())

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
app.include_router(patient_messages.router, tags=["patient-messages"])
app.include_router(team.router, tags=["team"])
app.include_router(reports.router, tags=["reports"])
app.include_router(migration.router, tags=["migration"])
app.include_router(timetracking.router, tags=["time-tracking"])
app.include_router(appliance_tracking.router, tags=["appliance-tracking"])
app.include_router(clinical_enhancements.router, tags=["clinical-enhancements"])
app.include_router(catalog.router, tags=["catalog"])
app.include_router(restorative.router, tags=["restorative-charting"])
app.include_router(workflow.router, tags=["workflow"])
app.include_router(messaging.router, tags=["messaging"])
app.include_router(perio.router, tags=["perio-charting"])
app.include_router(recall.router, tags=["hygiene-recall"])
app.include_router(stedi_webhook.router, tags=["webhooks"])
app.include_router(virtual_visits.router, tags=["virtual-visits"])
app.include_router(staff_permissions.router, tags=["staff-permissions"])
app.include_router(onboarding.router, tags=["onboarding"])


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
