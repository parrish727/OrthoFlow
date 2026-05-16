"""Spend intelligence endpoints — vendor insights, forecasting, budgeting."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import Invoice
from app.services.spend_intelligence import analyze_vendor_pricing, forecast_spend, generate_budget_report

router = APIRouter()


@router.get("/vendor-insights")
async def vendor_insights(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get vendor pricing insights — shows where you're overpaying."""
    result = await db.execute(
        select(Invoice).where(Invoice.practice_id == current_user["practice_id"])
    )
    invoices = [{"vendor_name": i.vendor_name, "coded_json": i.coded_json, "total_amount": i.total_amount} for i in result.scalars().all()]
    insights = analyze_vendor_pricing(invoices)
    return {"insights": insights, "total_potential_savings": sum(i["potential_savings"] for i in insights)}


@router.get("/forecast")
async def spend_forecast(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get spend forecast for next 3 months based on historical data."""
    result = await db.execute(
        select(Invoice).where(Invoice.practice_id == current_user["practice_id"])
    )
    invoices = [{"total_amount": i.total_amount, "created_at": i.created_at.isoformat() if i.created_at else ""} for i in result.scalars().all()]
    return forecast_spend(invoices)


@router.get("/budget")
async def budget_report(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get budget vs actual spend report."""
    result = await db.execute(
        select(Invoice).where(Invoice.practice_id == current_user["practice_id"])
    )
    invoices = [{"coded_json": i.coded_json} for i in result.scalars().all()]
    return generate_budget_report(invoices)
