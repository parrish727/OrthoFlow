"""ADP Time Clock connector — hours/timecards ONLY (no payroll).

Abstraction so the sandbox/mock provider is used until the first customer, then the real
ADP API Central "Team Time Cards" provider (OAuth2 + mutual-TLS client cert) swaps in via
config with no changes to callers.

Provider is selected by ADP_PROVIDER env: "sandbox" (default) | "api_central".
Scope is strictly Time & Attendance — this module never touches pay rates or payroll amounts.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import date, timedelta


@dataclass
class TimeCard:
    """A worker's hours for a day. Hours only — no pay."""
    worker_id: str
    worker_name: str
    work_date: str          # ISO date
    hours: float
    status: str             # e.g. "approved" | "pending"

    def to_dict(self) -> dict:
        return asdict(self)


class ADPTimeProvider(ABC):
    """Interface every ADP time provider implements. Hours/timecards only."""

    name: str = "base"

    @abstractmethod
    async def health(self) -> dict:
        """Connection/health status for the Time Clock integration panel."""
        raise NotImplementedError

    @abstractmethod
    async def get_timecards(self, start: date, end: date) -> list[TimeCard]:
        """Return team time cards (hours) for the date range."""
        raise NotImplementedError


class SandboxADPProvider(ADPTimeProvider):
    """Deterministic mock — no external calls, no credentials. Used until first customer.

    Generates plausible daily hours for a small demo team so the Time Clock ADP panel is
    demonstrable end-to-end without a real ADP account.
    """

    name = "sandbox"
    _TEAM = [
        ("W-1001", "Jordan Blake"),
        ("W-1002", "Mia Chen"),
        ("W-1003", "Andre Willis"),
    ]

    async def health(self) -> dict:
        return {
            "provider": self.name,
            "connected": True,
            "mode": "sandbox",
            "message": "ADP sandbox connector active — hours/timecards only. Real ADP API Central "
                       "(Team Time Cards) will be configured at first customer.",
            "payroll": False,
        }

    async def get_timecards(self, start: date, end: date) -> list[TimeCard]:
        cards: list[TimeCard] = []
        day = start
        while day <= end:
            if day.weekday() < 5:  # weekdays only
                for i, (wid, wname) in enumerate(self._TEAM):
                    # Deterministic hours (7.5–8.5) so the demo is stable/idempotent.
                    hours = 8.0 + ((day.toordinal() + i) % 3 - 1) * 0.5
                    cards.append(TimeCard(
                        worker_id=wid, worker_name=wname, work_date=day.isoformat(),
                        hours=round(hours, 2), status="approved",
                    ))
            day += timedelta(days=1)
        return cards


class APICentralADPProvider(ADPTimeProvider):
    """Real ADP API Central "Team Time Cards" provider (OAuth2 + mutual-TLS).

    Placeholder wiring — activated at first customer once ADP marketplace app credentials +
    client certificate are provisioned. Requires: ADP_CLIENT_ID, ADP_CLIENT_SECRET,
    ADP_CERT_PATH, ADP_KEY_PATH. Scope: Time & Attendance only (no Payroll Input).
    """

    name = "api_central"

    def __init__(self) -> None:
        self.client_id = os.environ.get("ADP_CLIENT_ID", "")
        self.client_secret = os.environ.get("ADP_CLIENT_SECRET", "")
        self.cert_path = os.environ.get("ADP_CERT_PATH", "")
        self.key_path = os.environ.get("ADP_KEY_PATH", "")
        self.base_url = os.environ.get("ADP_BASE_URL", "https://api.adp.com")

    def _configured(self) -> bool:
        return all([self.client_id, self.client_secret, self.cert_path, self.key_path])

    async def health(self) -> dict:
        if not self._configured():
            return {
                "provider": self.name, "connected": False, "mode": "api_central",
                "message": "ADP API Central selected but credentials/cert not configured "
                           "(ADP_CLIENT_ID/SECRET, ADP_CERT_PATH/KEY_PATH).",
                "payroll": False,
            }
        # Real implementation (at first customer): OAuth2 client-credentials over mTLS,
        # then GET /time/v2/workers/{aoid}/team-time-cards.
        return {"provider": self.name, "connected": True, "mode": "api_central", "payroll": False,
                "message": "ADP API Central configured."}

    async def get_timecards(self, start: date, end: date) -> list[TimeCard]:
        if not self._configured():
            raise RuntimeError("ADP API Central not configured — set credentials + client cert.")
        # Real call goes here at first customer (mTLS session + Team Time Cards API).
        raise NotImplementedError("ADP API Central Team Time Cards call implemented at first customer.")


def get_adp_provider() -> ADPTimeProvider:
    """Select the active provider from env (defaults to sandbox until first customer)."""
    provider = os.environ.get("ADP_PROVIDER", "sandbox").lower()
    if provider == "api_central":
        return APICentralADPProvider()
    return SandboxADPProvider()
