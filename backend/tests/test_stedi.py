"""Tests for the Stedi clearinghouse integration (sandbox behavior)."""
from decimal import Decimal

import pytest

from app.services.stedi import StediClient, _gen_pcn, _money
from app.services.stedi_payers import resolve_stedi_test_payer, STEDI_DENTAL_TEST_PAYERS


CLAIM_DATA = {
    "payer_id": "87726", "payer_name": "UnitedHealthcare", "subscriber_id": "UHC202649",
    "subscriber_first_name": "Priscilla", "subscriber_last_name": "Knowles",
    "subscriber_dob": "19920415", "group_number": "GRP1", "claim_filing_code": "CI",
    "total_billed": "600.00", "rendering_provider_npi": "1999999984",
    "billing_provider_npi": "1999999984",
    "service_lines": [
        {"service_date": "20260901", "cdt_code": "D8080", "billed_amount": "600.00",
         "quantity": 1, "tooth_number": None, "tooth_surface": None},
    ],
}


def _client() -> StediClient:
    # Provide a dummy key so construction doesn't require env.
    return StediClient(api_key="test_dummy_key")


def test_pcn_is_17_chars_basic_charset():
    pcn = _gen_pcn()
    assert len(pcn) == 17
    assert pcn.isalnum() and pcn.upper() == pcn


def test_money_quantizes():
    assert _money("12.345") == Decimal("12.35")
    assert _money(None) == Decimal("0.00")


def test_build_837d_matches_stedi_contract():
    payload, pcn = _client().build_837d(CLAIM_DATA)
    assert payload["usageIndicator"] == "T"                     # sandbox = test
    assert payload["tradingPartnerServiceId"] == "87726"
    assert payload["claimInformation"]["claimFilingCode"] == "CI"
    assert payload["claimInformation"]["patientControlNumber"] == pcn
    assert len(payload["claimInformation"]["serviceLines"]) == 1
    sl = payload["claimInformation"]["serviceLines"][0]
    assert sl["dentalService"]["procedureCode"] == "D8080"
    assert sl["dentalService"]["lineItemChargeAmount"] == "600.00"
    assert payload["billing"]["npi"] == "1999999984"


@pytest.mark.asyncio
async def test_submit_dental_claim_simulated_returns_277ca():
    result = await _client().submit_dental_claim(CLAIM_DATA)
    assert result.success is True
    assert result.tracking_number and len(result.tracking_number) == 17
    assert result.raw["status"] == "SUCCESS"
    assert result.raw["acknowledgment277ca"]["status"] == "A1"
    assert result.raw["meta"]["simulated"] is True


def test_simulate_era_split():
    era = _client().simulate_era(
        claim_data={"patient_control_number": "PCN", "payer_name": "UnitedHealthcare",
                    "total_billed": Decimal("600.00")},
        adjudication={"total_allowed": Decimal("552.00"), "total_paid": Decimal("276.00"),
                      "patient_responsibility": Decimal("324.00"), "service_lines": [],
                      "claim_adjustments": []},
    )
    assert era.total_paid == 276.0
    assert era.trace_number.startswith("ERA")
    assert era.claims[0]["patientControlNumber"] == "PCN"
    assert era.claims[0]["claimPaymentAmount"] == "276.00"


def test_resolve_stedi_test_payer_maps_known_payers():
    m = resolve_stedi_test_payer("UHC-DENTAL")
    assert m is not None
    assert m["stedi_payer_id"] == STEDI_DENTAL_TEST_PAYERS["UHC"]["payer_id"]
    assert m["mock_subscriber"]["member_id"]


def test_resolve_stedi_test_payer_unknown_returns_none():
    assert resolve_stedi_test_payer("NOT-A-PAYER") is None


def test_all_mapped_payers_resolve():
    from app.services.stedi_payers import INTERNAL_PAYER_TO_STEDI
    for internal in INTERNAL_PAYER_TO_STEDI:
        assert resolve_stedi_test_payer(internal) is not None, internal
