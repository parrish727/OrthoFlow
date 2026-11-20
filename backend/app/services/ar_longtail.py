"""AR long-tail policy: when OrthoFlow's follow-up window opens and closes.

Design rule (partnership-safe): OrthoFlow never works an account while an upstream financial
platform (e.g. OrthoFi) is still tracking it. The window opens STRICTLY AFTER the upstream
tracking limit (AR_LONGTAIL_START_DAYS) and closes at AR_LONGTAIL_CAP_DAYS. Accounts that arrive
through the OrthoFi handoff import are released explicitly by the upstream system, so they open
at the handoff date instead of waiting for the day count.

Scope: orthodontic patient-responsible balances on the patient ledger. Insurance claims age on
their own claim lifecycle and are not part of this window.

Pure functions only (no DB, no I/O) so the policy is unit-testable.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.core.config import settings

# Status values returned to the UI / API.
NOT_DELINQUENT = "not_delinquent"   # no balance, or no usable date
UPSTREAM = "upstream_window"        # inside the upstream platform's tracking window: hands off
ACTIVE = "active"                   # OrthoFlow long-tail follow-up is open
PAST_CAP = "past_cap"               # beyond the cap: needs a practice decision, no OrthoFlow outreach


@dataclass(frozen=True)
class Window:
    start_days: int
    cap_days: int


def window() -> Window:
    """Configured window. The cap can never be below the start (misconfiguration guard)."""
    start = max(int(settings.AR_LONGTAIL_START_DAYS), 0)
    cap = max(int(settings.AR_LONGTAIL_CAP_DAYS), start)
    return Window(start_days=start, cap_days=cap)


def released_by_upstream(last_payment: date | None, handoff_date: date | None) -> bool:
    """True while an OrthoFi-handed-off account has had no payment since the handoff.

    Once the patient pays after the handoff, the normal day-count rule applies again.
    """
    return handoff_date is not None and (last_payment is None or last_payment <= handoff_date)


def delinquent_days(
    today: date,
    last_payment: date | None,
    oldest_charge: date | None,
    handoff_date: date | None = None,
    start_days: int | None = None,
) -> int | None:
    """Days the balance has been delinquent.

    - Clock = days since the last payment; with no payment, days since the oldest charge.
    - An OrthoFi-handed-off account that has had no payment since the handoff starts its clock at
      the upstream limit on the handoff date (it was already that delinquent when released) and
      counts forward from there.
    """
    if start_days is None:
        start_days = window().start_days
    if released_by_upstream(last_payment, handoff_date):
        return start_days + max((today - handoff_date).days, 0)
    anchor = last_payment or oldest_charge
    if anchor is None:
        return None
    return max((today - anchor).days, 0)


def classify(balance: float, days: int | None, handed_off: bool = False) -> str:
    """Return the long-tail status for an account."""
    if balance <= 0 or days is None:
        return NOT_DELINQUENT
    w = window()
    if days > w.cap_days:
        return PAST_CAP
    if handed_off or days > w.start_days:
        return ACTIVE
    return UPSTREAM
