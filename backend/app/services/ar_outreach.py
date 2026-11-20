"""Automatic collections reminders: SMS at 30, 60, 90, 120 and 180 days past due.

Runs only when the practice owner/doctor has turned it on (Practice.ar_auto_outreach_enabled).
Safety rules, all enforced here:

- Only patients with a payment-plan schedule are texted. Accounts aged by an estimate (no
  schedule) show up in the Ledger for staff but are never auto-texted.
- SMS consent (TCPA) is required, opt-outs are honored, and the patient's quiet hours are
  respected. No consent means no message, and nothing is recorded, so it sends later if the
  patient opts in.
- Messages go out only inside the practice send window (default 10:00 to 17:00 local).
- Each milestone is sent at most once per delinquency cycle (AROutreachEvent is unique per
  patient, milestone and the oldest uncovered due date). If an account is first seen late, only
  the highest due milestone is sent; lower ones are recorded as superseded.
- Nothing is sent past the cap (AR_OUTREACH_CAP_DAYS, default 180).
- The text is generic: no patient name, practice name, balance or day count. It only points to the signed-in MyOrthoChart page.
- A failed send is logged but not recorded as sent, so it retries on the next run.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services import ar_aging

logger = logging.getLogger(__name__)


def pay_url() -> str:
    return f"{settings.PORTAL_BASE_URL.rstrip('/')}/portal?section=billing"


def message_for(milestone: int) -> str:
    """Generic text on purpose: no name, no practice name, no amount, no day count. SMS is not
    encrypted, so the message only points the patient to the signed-in portal."""
    url = pay_url()
    stop = " Reply STOP to opt out."
    if milestone <= 30:
        return f"You have a billing notice from your orthodontic office. Review it in MyOrthoChart: {url}{stop}"
    if milestone <= 60:
        return f"Second notice: you have an unpaid billing notice from your orthodontic office. Sign in to MyOrthoChart: {url}{stop}"
    if milestone <= 90:
        return f"Important: please review your billing notice from your orthodontic office in MyOrthoChart: {url} or call the office.{stop}"
    if milestone <= 120:
        return f"Reminder: your billing notice is still open. Sign in to MyOrthoChart: {url} or call the office to talk through options.{stop}"
    return f"Final reminder about your open billing notice. Sign in to MyOrthoChart: {url} or call the office.{stop}"


def in_send_window(now_utc: datetime) -> bool:
    local = now_utc.astimezone(ZoneInfo(settings.AR_OUTREACH_TZ))
    return settings.AR_OUTREACH_START_HOUR <= local.hour < settings.AR_OUTREACH_END_HOUR


def in_quiet_hours(now_utc: datetime, quiet_start: time | None, quiet_end: time | None) -> bool:
    if not quiet_start or not quiet_end:
        return False
    t = now_utc.astimezone(ZoneInfo(settings.AR_OUTREACH_TZ)).time()
    if quiet_start <= quiet_end:
        return quiet_start <= t < quiet_end
    return t >= quiet_start or t < quiet_end   # overnight window


async def run_for_practice(
    db: AsyncSession,
    practice,
    today: date | None = None,
    now_utc: datetime | None = None,
    sender=None,
) -> dict:
    """Send due reminders for one practice. `sender(phone, text) -> bool` is injectable for tests."""
    from app.models.clinical import Patient
    from app.models.communications import CommunicationPreference, MessageLog
    from app.models.finance import AROutreachEvent
    if sender is None:
        from app.services.notifications import send_sms as sender

    now_utc = now_utc or datetime.now(timezone.utc)
    today = today or now_utc.astimezone(ZoneInfo(settings.AR_OUTREACH_TZ)).date()
    result = {"enabled": bool(practice.ar_auto_outreach_enabled), "sent": 0, "skipped_no_consent": 0,
              "skipped_quiet_hours": 0, "failed": 0, "superseded": 0}
    if not practice.ar_auto_outreach_enabled or not in_send_window(now_utc):
        return result

    rows = [r for r in await ar_aging.load_aging(db, practice.id, today)
            if r.aging.due_source == "schedule" and r.aging.days_past_due is not None
            and r.aging.oldest_uncovered_due is not None]
    if not rows:
        return result

    pids = [r.patient_id for r in rows]
    events = (await db.execute(
        select(AROutreachEvent).where(AROutreachEvent.practice_id == practice.id,
                                      AROutreachEvent.patient_id.in_(pids))
    )).scalars().all()
    sent_map: dict[tuple[str, date], set[int]] = {}
    for e in events:
        sent_map.setdefault((str(e.patient_id), e.anchor_due_date), set()).add(e.milestone_days)

    prefs = {str(p.patient_id): p for p in (await db.execute(
        select(CommunicationPreference).where(CommunicationPreference.practice_id == practice.id,
                                              CommunicationPreference.patient_id.in_(pids)))).scalars().all()}
    patients = {str(p.id): p for p in (await db.execute(
        select(Patient).where(Patient.practice_id == practice.id, Patient.id.in_(pids)))).scalars().all()}

    for r in rows:
        anchor = r.aging.oldest_uncovered_due
        send_m, superseded = ar_aging.milestones_to_send(
            r.aging.days_past_due, sent_map.get((r.patient_id, anchor), set()))
        if send_m is None:
            continue
        pat = patients.get(r.patient_id)
        pref = prefs.get(r.patient_id)
        phone = (pref.phone_number if pref and pref.phone_number else (pat.phone if pat else None))
        if not pat or not pref or not pref.tcpa_consent or not pref.sms_enabled \
                or pref.tcpa_opt_out_date is not None or not phone:
            result["skipped_no_consent"] += 1
            continue
        if in_quiet_hours(now_utc, pref.quiet_start, pref.quiet_end):
            result["skipped_quiet_hours"] += 1
            continue

        body = message_for(send_m)
        ok = await sender(phone, body)
        log = MessageLog(
            practice_id=practice.id, patient_id=pat.id, direction="outbound", channel="sms",
            to_address=phone, body=body, status="sent" if ok else "failed",
            metadata_={"type": "ar_cadence", "milestone": send_m},
        )
        db.add(log)
        await db.flush()
        if not ok:
            result["failed"] += 1
            continue
        db.add(AROutreachEvent(practice_id=practice.id, patient_id=pat.id, milestone_days=send_m,
                               anchor_due_date=anchor, channel="sms", status="sent", message_log_id=log.id))
        for m in superseded:
            db.add(AROutreachEvent(practice_id=practice.id, patient_id=pat.id, milestone_days=m,
                                   anchor_due_date=anchor, channel="sms", status="superseded"))
            result["superseded"] += 1
        result["sent"] += 1

    await db.commit()
    return result
