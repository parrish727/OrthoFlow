"""MFA service — SMS OTP for login verification."""
import random
import time
from app.services.notifications import send_sms

# OTP store: {user_id: {"code": "123456", "expires": timestamp, "phone": "+1..."}}
_otp_store: dict[str, dict] = {}

OTP_EXPIRY_SECONDS = 300  # 5 minutes


def generate_otp(user_id: str, phone: str) -> str:
    """Generate a 6-digit OTP and store it."""
    code = str(random.randint(100000, 999999))
    _otp_store[user_id] = {
        "code": code,
        "expires": time.time() + OTP_EXPIRY_SECONDS,
        "phone": phone,
    }
    return code


async def send_otp(user_id: str, phone: str):
    """Generate and send OTP via SMS."""
    code = generate_otp(user_id, phone)
    await send_sms(phone, f"Your OrthoFlow verification code is: {code}. Expires in 5 minutes.")


def verify_otp(user_id: str, code: str) -> bool:
    """Verify an OTP code. Returns True if valid."""
    entry = _otp_store.get(user_id)
    if not entry:
        return False
    if time.time() > entry["expires"]:
        _otp_store.pop(user_id, None)
        return False
    if entry["code"] != code:
        return False
    _otp_store.pop(user_id, None)  # One-time use
    return True
