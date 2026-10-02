"""In-process status of the demo daily-reseed background task.

The daily reseed keeps the demo practice's schedule on today's date. For a long time its
failures were swallowed as a log warning with no externally visible signal, so a broken reseed
went unnoticed for days. This module records the last reseed outcome so the health endpoint can
expose it and an SRE monitor can alert when the reseed goes stale or starts failing.

State is intentionally process-local (single-worker demo backend). It is NOT a substitute for
real metrics in a multi-replica production service — it exists to make the demo reseed observable.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional

# A reseed is considered "stale" if it has not succeeded within this many hours. The task runs
# daily, so anything approaching ~26h without a success means the schedule has drifted.
STALE_AFTER_HOURS = 26


@dataclass
class ReseedStatus:
    last_run_at: Optional[str] = None          # ISO8601 UTC of the last attempt (success or fail)
    last_success_at: Optional[str] = None      # ISO8601 UTC of the last successful reseed
    last_target_date: Optional[str] = None     # the ET date the last successful reseed populated
    last_error: Optional[str] = None           # error message from the last failed attempt
    consecutive_failures: int = 0
    ok: bool = True                            # False once a run fails, until the next success


_status = ReseedStatus()


def record_success(target_date: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    _status.last_run_at = now
    _status.last_success_at = now
    _status.last_target_date = target_date
    _status.last_error = None
    _status.consecutive_failures = 0
    _status.ok = True


def record_failure(error: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    _status.last_run_at = now
    _status.last_error = error
    _status.consecutive_failures += 1
    _status.ok = False


def _is_stale() -> bool:
    if _status.last_success_at is None:
        return False  # never run yet (e.g. fresh boot before first reseed) — not "stale"
    last = datetime.fromisoformat(_status.last_success_at)
    age_hours = (datetime.now(timezone.utc) - last).total_seconds() / 3600.0
    return age_hours > STALE_AFTER_HOURS


def snapshot() -> dict:
    """Serializable status for the health endpoint, with a derived stale flag + overall health."""
    data = asdict(_status)
    stale = _is_stale()
    data["stale"] = stale
    # Healthy only if the last run succeeded AND it is not stale.
    data["healthy"] = bool(_status.ok and not stale)
    data["stale_after_hours"] = STALE_AFTER_HOURS
    return data
