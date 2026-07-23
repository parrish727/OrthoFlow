"""OrthoFlow API — CDT Code Library + Appointment Type Templates.
Search/filter CDT codes, list appointment types by specialty.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.cdt_codes import CDTCode, AppointmentTypeTemplate

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])


@router.get("/cdt-codes")
async def search_cdt_codes(
    q: str = Query(None, min_length=1, description="Search by code or description"),
    category: str = Query(None, description="Filter by category"),
    specialty: str = Query(None, description="Filter by specialty"),
    common_only: bool = Query(False, description="Only return commonly used codes"),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Search and filter CDT codes."""
    query = select(CDTCode)

    if q:
        search = f"%{q}%"
        query = query.where(
            or_(
                CDTCode.code.ilike(search),
                CDTCode.description.ilike(search),
                CDTCode.short_description.ilike(search),
            )
        )
    if category:
        query = query.where(CDTCode.category == category)
    if specialty:
        query = query.where(CDTCode.specialty == specialty)
    if common_only:
        query = query.where(CDTCode.is_common.is_(True))

    query = query.order_by(CDTCode.code).limit(limit)
    result = await db.execute(query)
    codes = result.scalars().all()

    return {
        "codes": [
            {
                "code": c.code,
                "category": c.category,
                "subcategory": c.subcategory,
                "description": c.description,
                "short_description": c.short_description,
                "specialty": c.specialty,
                "is_common": c.is_common,
                "avg_fee": c.avg_fee,
                "tooth_specific": c.tooth_specific,
                "surface_specific": c.surface_specific,
            }
            for c in codes
        ],
        "total": len(codes),
    }


@router.get("/cdt-codes/categories")
async def get_cdt_categories(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get all CDT code categories with counts."""
    from sqlalchemy import func
    result = await db.execute(
        select(CDTCode.category, func.count(CDTCode.id))
        .group_by(CDTCode.category)
        .order_by(CDTCode.category)
    )
    categories = [{"name": row[0], "count": row[1]} for row in result.all()]
    return {"categories": categories}


@router.get("/appointment-types")
async def list_appointment_types(
    specialty: str = Query(None, description="Filter by specialty"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List appointment type templates, optionally filtered by specialty."""
    query = select(AppointmentTypeTemplate).where(AppointmentTypeTemplate.is_active.is_(True))

    if specialty:
        query = query.where(AppointmentTypeTemplate.specialty == specialty)

    query = query.order_by(AppointmentTypeTemplate.sort_order)
    result = await db.execute(query)
    types = result.scalars().all()

    return {
        "appointment_types": [
            {
                "id": str(t.id),
                "name": t.name,
                "specialty": t.specialty,
                "category": t.category,
                "default_duration_minutes": t.default_duration_minutes,
                "default_cdt_codes": t.default_cdt_codes,
                "color": t.color,
                "requires_chair": t.requires_chair,
                "requires_da": t.requires_da,
                "is_hygiene": t.is_hygiene,
            }
            for t in types
        ],
        "total": len(types),
    }


@router.get("/specialties")
async def list_specialties(
    user: dict = Depends(get_current_user),
) -> dict:
    """List available dental specialties."""
    return {
        "specialties": [
            {"id": "general", "name": "General Dentistry", "color": "#3B82F6"},
            {"id": "ortho", "name": "Orthodontics", "color": "#0D9488"},
            {"id": "perio", "name": "Periodontics", "color": "#F97316"},
            {"id": "cosmetic", "name": "Cosmetic Dentistry", "color": "#EC4899"},
            {"id": "surgery", "name": "Oral Surgery", "color": "#DC2626"},
            {"id": "endo", "name": "Endodontics", "color": "#6366F1"},
            {"id": "prosth", "name": "Prosthodontics", "color": "#8B5CF6"},
        ]
    }
