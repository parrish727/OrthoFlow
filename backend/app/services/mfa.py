"""MFA service — SMS OTP for login verification. Uses database storage (not in-memory)."""
import random
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import OtpCode
from app.services.notifications import send_sms

OTP_EXPIRY_MINUTES = 5


async def send_otp(db: AsyncSession, user_id: str, phone: str) -> None:
    """Generate and send OTP via SMS. Stores in database."""
    code = str(random.randint(100000, 999999))
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)

    otp = OtpCode(
        user_id=user_id,
        code=code,
        phone=phone,
        expires_at=expires_at,
    )
    db.add(otp)
    await db.commit()

    await send_sms(phone, f"Your OrthoFlow verification code is: {code}. Expires in {OTP_EXPIRY_MINUTES} minutes.")


async def verify_otp(db: AsyncSession, user_id: str, code: str) -> bool:
    """Verify an OTP code. Returns True if valid. Marks as used."""
    result = await db.execute(
        select(OtpCode).where(
            and_(
                OtpCode.user_id == user_id,
                OtpCode.code == code,
                OtpCode.used == False,
                OtpCode.expires_at > datetime.now(timezone.utc),
            )
        ).order_by(OtpCode.created_at.desc()).limit(1)
    )
    otp = result.scalar_one_or_none()
    if not otp:
        return False

    # Mark as used (one-time)
    otp.used = True
    await db.commit()
    return True
