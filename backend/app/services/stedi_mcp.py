"""Stedi MCP (Model Context Protocol) integration — DORMANT until production.

Stedi's eligibility MCP server exposes AI-agent tools (`search_for_payer`, `eligibility_check`)
with built-in payer lookup, retry, and error-recovery logic — the same logic the Stedi Agent
uses. It is a Streamable HTTP MCP server at:

    https://mcp.us.stedi.com/2025-07-11/mcp   (API-key auth; raw key in Authorization header)

IMPORTANT — WHY THIS IS DORMANT
───────────────────────────────
The MCP server is only available for PRODUCTION Stedi accounts. OrthoFlow is currently on a
SANDBOX account, so this client is scaffolded but disabled (STEDI_MCP_ENABLED=false). It
raises StediMCPUnavailable if called while disabled — the eligibility route uses the direct
REST client (services/stedi.py) in the meantime.

TRANSITION TO PRODUCTION (single, well-defined switch)
──────────────────────────────────────────────────────
1. Upgrade the Stedi account to production (portal → "Upgrade account").
2. Set env: STEDI_MCP_ENABLED=true and STEDI_MCP_API_KEY=<prod-or-test key>.
   (Test keys work with the MCP server for PHI-free development once the account is production.)
3. Optionally route eligibility through the MCP agent (search_for_payer → eligibility_check
   with automatic retry/troubleshooting) instead of the direct REST client, by calling
   StediMCPClient.run_eligibility_check() from the eligibility route behind the flag.

This design keeps the production cutover to a config flip + a small routing change, with the
tool contract already modeled here so there are no surprises.

Docs: https://www.stedi.com/docs/healthcare/mcp-server
"""
from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class StediMCPUnavailable(RuntimeError):
    """Raised when the MCP server is called while dormant (sandbox / disabled)."""


class StediMCPClient:
    """Thin client for Stedi's Streamable HTTP MCP server.

    Dormant by default. When STEDI_MCP_ENABLED is true and a key is present, this issues
    JSON-RPC 2.0 tool calls over Streamable HTTP to the MCP endpoint. The tool surface mirrors
    Stedi's documented MCP tools so the production wiring is already correct.
    """

    #: Documented MCP tools (see Stedi docs → MCP server → Tools).
    TOOLS = ("search_for_payer", "eligibility_check")

    def __init__(self, url: str | None = None, api_key: str | None = None):
        self.url = url or settings.STEDI_MCP_URL
        self.api_key = api_key if api_key is not None else settings.STEDI_MCP_API_KEY
        self.enabled = settings.STEDI_MCP_ENABLED

    def _require_enabled(self) -> None:
        if not self.enabled:
            raise StediMCPUnavailable(
                "Stedi MCP is dormant. It requires a PRODUCTION Stedi account and "
                "STEDI_MCP_ENABLED=true. OrthoFlow is currently sandbox — use the direct REST "
                "eligibility client (services/stedi.py) instead."
            )
        if not self.api_key:
            raise StediMCPUnavailable("STEDI_MCP_API_KEY is not configured.")

    def _headers(self) -> dict[str, str]:
        # MCP API-key auth uses the raw key in the Authorization header (same as REST).
        return {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

    async def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict:
        """Invoke an MCP tool via JSON-RPC 2.0 over Streamable HTTP. Dormant until enabled."""
        self._require_enabled()
        if tool_name not in self.TOOLS:
            raise ValueError(f"Unknown MCP tool '{tool_name}'. Available: {self.TOOLS}")

        import httpx  # local import keeps this module import-safe while dormant

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(self.url, headers=self._headers(), json=payload)
            resp.raise_for_status()
            return resp.json()

    # ── Public tool wrappers (production surface) ───────────────────────────────

    async def search_for_payer(self, query: str) -> dict:
        """Find a Stedi payer by ID or (partial/typo) name. e.g. 'cig' → Cigna."""
        return await self._call_tool("search_for_payer", {"query": query})

    async def run_eligibility_check(self, patient: dict, provider: dict, payer: dict) -> dict:
        """Construct + submit an eligibility check with MCP retry/troubleshooting built in."""
        return await self._call_tool("eligibility_check", {
            "patient": patient, "provider": provider, "payer": payer,
        })

    def status(self) -> dict:
        """Report readiness — used by health/diagnostics without triggering a call."""
        return {
            "enabled": self.enabled,
            "configured": bool(self.api_key),
            "url": self.url,
            "reason": None if self.enabled else "Dormant — requires production Stedi account.",
        }
