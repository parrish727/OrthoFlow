"""Seed demo accounts per role for client demonstrations.
Run via: docker compose exec backend python -m app.seeds.demo_accounts
"""
import asyncio
from uuid import UUID
from sqlalchemy import select
from app.core.database import SessionLocal
from app.core.auth import hash_password
from app.models.models import User, Practice

# The demo practice ID (must match the existing demo practice)
DEMO_PRACTICE_ID = UUID("82fe9d87-6250-4b15-ac7d-26de094a4be8")
DEMO_PRACTICE_NAME = "Brightsmile Orthodontics"
DEMO_PASSWORD = "Demo2026!"

DEMO_ACCOUNTS = [
    {
        "email": "demo@orthoflowsolutions.com",
        "full_name": "Dr. Williams",
        "role": "owner",
    },
    {
        "email": "demo-doctor@orthoflowsolutions.com",
        "full_name": "Dr. Williams",
        "role": "doctor",
    },
    {
        "email": "demo-manager@orthoflowsolutions.com",
        "full_name": "Jessica (Office Manager)",
        "role": "office_manager",
    },
    {
        "email": "demo-da@orthoflowsolutions.com",
        "full_name": "Mike (Dental Assistant)",
        "role": "dental_assistant",
    },
    {
        "email": "demo-frontdesk@orthoflowsolutions.com",
        "full_name": "Sarah (Front Desk)",
        "role": "front_desk",
    },
]


async def seed_demo_accounts():
    """Create demo accounts (idempotent — skips existing)."""
    async with SessionLocal() as db:
        # Ensure demo practice exists
        result = await db.execute(select(Practice).where(Practice.id == DEMO_PRACTICE_ID))
        practice = result.scalar_one_or_none()
        if not practice:
            practice = Practice(id=DEMO_PRACTICE_ID, name=DEMO_PRACTICE_NAME)
            db.add(practice)
            await db.flush()

        created = 0
        for acct in DEMO_ACCOUNTS:
            existing = await db.execute(select(User).where(User.email == acct["email"]))
            if existing.scalar_one_or_none():
                continue
            user = User(
                practice_id=DEMO_PRACTICE_ID,
                email=acct["email"],
                hashed_password=hash_password(DEMO_PASSWORD),
                full_name=acct["full_name"],
                role=acct["role"],
                is_active=True,
            )
            db.add(user)
            created += 1

        await db.commit()
        print(f"✅ Demo accounts: {created} created, {len(DEMO_ACCOUNTS) - created} already existed")


if __name__ == "__main__":
    asyncio.run(seed_demo_accounts())
