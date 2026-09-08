"""Seed the standard orthodontic CDT set the practice uses day-to-day.

Ensures these exist and are flagged common (surfaced first in pickers):
  D8091 - Comprehensive orthodontic treatment / surgical (surgery)
  D8020 - Limited orthodontic treatment (Phase 1 / transitional)
  D8080 - Comprehensive orthodontic treatment of the adolescent dentition
  D8670 - Periodic orthodontic treatment visit (Adjustment) — Medicaid (MC) billing code
  D8660 - Pre-orthodontic treatment examination (Treatment exam)

Note: CDT codes are updated yearly by the ADA; re-run after the annual update to refresh
descriptions/fees. Run: docker compose exec backend python -m app.seeds.ortho_cdt_standard
"""
import asyncio
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.cdt_codes import CDTCode

STANDARD_ORTHO = [
    # code, subcategory, description, short, avg_fee(cents)
    ("D8091", "comprehensive treatment",
     "Comprehensive orthodontic treatment with surgical (orthognathic) component", "Ortho Surgery", 700000),
    ("D8020", "limited treatment",
     "Limited orthodontic treatment of the transitional dentition (Phase 1)", "Limited/Phase 1", 350000),
    ("D8080", "comprehensive treatment",
     "Comprehensive orthodontic treatment of the adolescent dentition", "Adolescent", 600000),
    ("D8670", "other services",
     "Periodic orthodontic treatment visit (adjustment)", "Adjustment (MC)", 18500),
    ("D8660", "other services",
     "Pre-orthodontic treatment examination to monitor growth and development", "Treatment Exam", 25000),
]


async def seed_standard_ortho_cdt():
    async with SessionLocal() as db:
        added = updated = 0
        for code, subcat, desc, short, fee in STANDARD_ORTHO:
            existing = (await db.execute(select(CDTCode).where(CDTCode.code == code))).scalar_one_or_none()
            if existing:
                existing.is_common = True
                existing.specialty = "ortho"
                if not existing.short_description:
                    existing.short_description = short
                updated += 1
            else:
                db.add(CDTCode(
                    code=code, category="orthodontics", subcategory=subcat,
                    description=desc, short_description=short, specialty="ortho",
                    is_common=True, avg_fee=fee, tooth_specific=False, surface_specific=False,
                ))
                added += 1
        await db.commit()
        print(f"✅ Standard ortho CDT: {added} added, {updated} updated (D8091/D8020/D8080/D8670/D8660)")


if __name__ == "__main__":
    asyncio.run(seed_standard_ortho_cdt())
