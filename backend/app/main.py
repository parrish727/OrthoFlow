from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import invoices, auth, practices, health
from app.api.routes import quickbooks, notifications, payments, pms
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
