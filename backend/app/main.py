from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import invoices, auth, practices, health
from app.core.config import settings

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

app.include_router(health.router, tags=["health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(practices.router, prefix="/api/v1/practices", tags=["practices"])
app.include_router(invoices.router, prefix="/api/v1/invoices", tags=["invoices"])
