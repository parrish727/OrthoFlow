"""Medicaid State Rules Engine — configurable per-state orthodontic coverage rules.

RECORDS NOTE (verified 2026-10): Medicaid orthodontic medical-necessity is driven by the HLD index
score (from the clinical exam) + clinical photographs. A cephalometric radiograph is NOT universally
required and is increasingly state-dependent/supplemental — several states base approval on HLD +
photos alone, and some (e.g. WA) have removed "medically necessary" status from the ceph (CDT D0340)
so it needs its own prior auth as an extra. `records_required` below reflects the per-state baseline;
cephs are listed under `records_supplemental` where they are optional/not mandated. Confirm the
specific state program's current manual before submission.
"""
from decimal import Decimal

# State Medicaid rules — add states as needed
STATE_RULES: dict[str, dict] = {
    "NC": {
        "age_limit": 20,
        "requires_prior_auth": True,
        "handicapping_score_required": True,
        "min_hld_score": 26,
        "covered_codes": ["D8070", "D8080", "D8210", "D8220", "D8660", "D8670", "D8680", "D8695"],
        "max_treatment_months": 36,
        "records_required": ["HLD index score (>= 26)", "clinical photographs"],
        "records_supplemental": ["panoramic radiograph", "cephalometric radiograph/tracing (if requested)"],
        "fee_schedule": {
            "D8070": Decimal("4200.00"), "D8080": Decimal("4200.00"),
            "D8210": Decimal("1800.00"), "D8220": Decimal("2200.00"),
            "D8660": Decimal("75.00"), "D8670": Decimal("195.00"),
            "D8680": Decimal("450.00"), "D8695": Decimal("250.00"),
        },
        "billing_notes": "NC Medicaid requires an HLD Index score >= 26 plus clinical photographs for "
                         "comprehensive ortho prior auth. A cephalometric radiograph/tracing is "
                         "supplemental (not universally required) — include only if the plan requests it.",
    },
    "SC": {
        "age_limit": 20,
        "requires_prior_auth": True,
        "handicapping_score_required": True,
        "min_hld_score": 26,
        "covered_codes": ["D8070", "D8080", "D8210", "D8220", "D8660", "D8670", "D8680", "D8695"],
        "max_treatment_months": 30,
        "records_required": ["HLD index score (>= 26)", "panoramic radiograph"],
        "records_supplemental": ["clinical photographs", "cephalometric radiograph/tracing (if requested)"],
        "fee_schedule": {
            "D8070": Decimal("3800.00"), "D8080": Decimal("3800.00"),
            "D8210": Decimal("1600.00"), "D8220": Decimal("2000.00"),
            "D8660": Decimal("65.00"), "D8670": Decimal("175.00"),
            "D8680": Decimal("400.00"), "D8695": Decimal("225.00"),
        },
        "billing_notes": "SC Medicaid requires prior authorization with an HLD score and a panoramic "
                         "radiograph. A cephalometric film is supplemental, not a standard requirement.",
    },
}


class RuleValidationResult:
    def __init__(self, allowed: bool, errors: list[str] | None = None, warnings: list[str] | None = None, max_fee: Decimal | None = None):
        self.allowed = allowed
        self.errors = errors or []
        self.warnings = warnings or []
        self.max_fee = max_fee


def get_state_rules(state_code: str) -> dict | None:
    """Get Medicaid rules for a state."""
    return STATE_RULES.get(state_code.upper())


def validate_claim_against_state(state_code: str, cdt_code: str, patient_age: int | None = None, billed_amount: Decimal | None = None) -> RuleValidationResult:
    """Validate a claim line against state Medicaid rules."""
    rules = get_state_rules(state_code)
    if not rules:
        return RuleValidationResult(True, warnings=[f"No Medicaid rules configured for state {state_code}. Submitting without state validation."])

    errors = []
    warnings = []

    # Age check
    if patient_age is not None and patient_age > rules["age_limit"]:
        errors.append(f"Patient age {patient_age} exceeds {state_code} Medicaid age limit of {rules['age_limit']}")

    # Code coverage check
    if cdt_code not in rules["covered_codes"]:
        errors.append(f"CDT code {cdt_code} is not covered by {state_code} Medicaid")

    # Fee schedule enforcement
    max_fee = rules["fee_schedule"].get(cdt_code)
    if max_fee and billed_amount and billed_amount > max_fee:
        errors.append(f"Billed amount ${billed_amount} exceeds {state_code} Medicaid allowed amount of ${max_fee} for {cdt_code}")

    # Prior auth warning
    if rules["requires_prior_auth"]:
        warnings.append(f"{state_code} Medicaid requires prior authorization for orthodontic treatment")

    return RuleValidationResult(allowed=len(errors) == 0, errors=errors, warnings=warnings, max_fee=max_fee)


def get_max_allowed_fee(state_code: str, cdt_code: str) -> Decimal | None:
    """Get the maximum Medicaid allowed fee for a code in a state."""
    rules = get_state_rules(state_code)
    if not rules:
        return None
    return rules["fee_schedule"].get(cdt_code)


def get_supported_states() -> list[str]:
    """Get list of states with configured Medicaid rules."""
    return list(STATE_RULES.keys())
