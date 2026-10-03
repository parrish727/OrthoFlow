"""Shared time utilities.

Centralizes the Eastern-time source used by the demo seed and the daily reseed scheduler.
The demo practice (DEMO — Brightsmile Orthodontics) is in US Eastern, so "today" for the demo
schedule must track the Eastern *calendar date*. We use the IANA zone America/New_York rather
than a hardcoded UTC offset so the date is correct year-round (EDT and EST), not just in summer.
"""
from __future__ import annotations

from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

# Single source of truth for the demo practice's timezone.
EASTERN = ZoneInfo("America/New_York")


def eastern_now() -> datetime:
    """Current time in US Eastern (timezone-aware)."""
    return datetime.now(EASTERN)


def eastern_today() -> date:
    """Current calendar date in US Eastern."""
    return eastern_now().date()


def seconds_until_next_eastern_midnight(margin_minutes: int = 10) -> float:
    """Seconds to wait until just AFTER the next Eastern midnight.

    A small positive margin ensures the reseed fires on the new ET day (never a second before
    midnight, which would compute the previous day's date). Returns a float suitable for
    asyncio.sleep().
    """
    now = eastern_now()
    # Next ET midnight = tomorrow at 00:00 ET, plus margin.
    next_midnight = datetime.combine(
        now.date() + timedelta(days=1),
        datetime.min.time(),
        tzinfo=EASTERN,
    ) + timedelta(minutes=margin_minutes)
    return max(1.0, (next_midnight - now).total_seconds())
