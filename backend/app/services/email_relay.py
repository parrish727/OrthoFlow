"""Built-in email relay — free SMTP (no paid provider).

Sends AI letters + referral letters to recipient emails using a practice-configured SMTP server
(env). No third-party paid email API. If SMTP isn't configured, send() returns a clear
'not configured' result so the UI can guide setup (and the demo degrades gracefully).

FUTURE HOOK: per-doctor business email (send AS the doctor's own address / OAuth) — this relay is
the abstraction that will grow that capability without changing callers.
"""
from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage


def _smtp_config() -> dict:
    return {
        "host": os.environ.get("SMTP_HOST", ""),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "user": os.environ.get("SMTP_USER", ""),
        "password": os.environ.get("SMTP_PASSWORD", ""),
        "from_addr": os.environ.get("SMTP_FROM", os.environ.get("SMTP_USER", "")),
        "use_tls": os.environ.get("SMTP_USE_TLS", "true").lower() == "true",
    }


def is_configured() -> bool:
    c = _smtp_config()
    return bool(c["host"] and c["from_addr"])


def relay_status() -> dict:
    c = _smtp_config()
    return {
        "configured": is_configured(),
        "host": c["host"] or None,
        "from_addr": c["from_addr"] or None,
        "message": ("Built-in email relay ready." if is_configured()
                    else "Email relay not configured — set SMTP_HOST/SMTP_FROM (+ SMTP_USER/PASSWORD) to send."),
    }


def send_email(*, to_addr: str, subject: str, body: str, from_name: str | None = None) -> dict:
    """Send a plain-text email via the configured SMTP relay. Returns a result dict (never raises
    to the caller for expected/config errors — surfaces status instead)."""
    c = _smtp_config()
    if not is_configured():
        return {"sent": False, "reason": "not_configured", "message": relay_status()["message"]}

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{c['from_addr']}>" if from_name else c["from_addr"]
    msg["To"] = to_addr
    msg.set_content(body)

    try:
        if c["use_tls"]:
            ctx = ssl.create_default_context()
            with smtplib.SMTP(c["host"], c["port"], timeout=30) as server:
                server.starttls(context=ctx)
                if c["user"]:
                    server.login(c["user"], c["password"])
                server.send_message(msg)
        else:
            with smtplib.SMTP(c["host"], c["port"], timeout=30) as server:
                if c["user"]:
                    server.login(c["user"], c["password"])
                server.send_message(msg)
        return {"sent": True, "to": to_addr}
    except Exception as e:  # noqa: BLE001 — surface SMTP errors as a result, don't 500
        return {"sent": False, "reason": "smtp_error", "message": str(e)[:200]}


def format_letter(*, practice: str, address: str, location: str, contact: str,
                  intro: str, body: str, thank_you: str, from_line: str) -> str:
    """Compose a letter in the standard format:
    Practice, Address, Location, Contact, Intro, Body, Thank you, From."""
    parts = [
        practice,
        address,
        location,
        contact,
        "",
        intro,
        "",
        body,
        "",
        thank_you,
        "",
        from_line,
    ]
    return "\n".join(p for p in parts if p is not None)
