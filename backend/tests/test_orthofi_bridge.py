"""Tests for the OrthoFi financial bridge (status + handoff schema).

CI-safe: covers the dormant-status contract and the handoff model validation. The full
create-patient + seed-ledger import_handoff round-trip is verified against the live DB during the
session (CI has no demo practice rows to match against).
"""
from decimal import Decimal

from app.services import orthofi


def test_status_dormant_by_default():
    s = orthofi.status()
    assert s["enabled"] is False
    assert s["configured"] is False
    assert s["mode"] == "import"
    assert "no public api" in s["message"].lower() or "no public API".lower() in s["message"].lower()


def test_handoff_model_minimal():
    h = orthofi.OrthoFiHandoff(
        external_id="OF-1", first_name="Ada", last_name="Owes",
        outstanding_balance=Decimal("1200.00"),
    )
    assert h.external_id == "OF-1"
    assert h.outstanding_balance == Decimal("1200.00")
    assert h.monthly_payment is None


def test_handoff_model_full():
    h = orthofi.OrthoFiHandoff(
        external_id="OF-2", first_name="Bo", last_name="Balance",
        outstanding_balance=Decimal("3000"), contract_total=Decimal("6000"),
        monthly_payment=Decimal("250"), plan_summary="Comprehensive Phase 1",
    )
    assert h.contract_total == Decimal("6000")
    assert h.plan_summary == "Comprehensive Phase 1"
