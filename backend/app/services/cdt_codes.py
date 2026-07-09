"""CDT Code Validation Engine — Orthodontic subset (D8000-series)."""

ORTHO_CDT_CODES: dict[str, dict] = {
    "D8010": {"description": "Limited ortho treatment, transitional dentition", "category": "limited"},
    "D8020": {"description": "Limited ortho treatment, adolescent dentition", "category": "limited"},
    "D8030": {"description": "Limited ortho treatment, adult dentition", "category": "limited"},
    "D8040": {"description": "Limited ortho treatment, early intervention", "category": "limited"},
    "D8070": {"description": "Comprehensive ortho treatment, transitional dentition", "category": "comprehensive"},
    "D8080": {"description": "Comprehensive ortho treatment, adolescent dentition", "category": "comprehensive"},
    "D8090": {"description": "Comprehensive ortho treatment, adult dentition", "category": "comprehensive"},
    "D8210": {"description": "Removable appliance therapy", "category": "appliance"},
    "D8220": {"description": "Fixed appliance therapy", "category": "appliance"},
    "D8660": {"description": "Pre-orthodontic treatment visit", "category": "visit"},
    "D8670": {"description": "Periodic orthodontic treatment visit", "category": "visit"},
    "D8680": {"description": "Orthodontic retention", "category": "retention"},
    "D8681": {"description": "Removable orthodontic retainer adjustment", "category": "retention"},
    "D8695": {"description": "Removal of fixed orthodontic appliances", "category": "removal"},
    "D8696": {"description": "Repair of orthodontic appliance", "category": "repair"},
    "D8697": {"description": "Repair of fixed retainer", "category": "repair"},
    "D8698": {"description": "Re-cement or re-bond fixed retainer", "category": "repair"},
    "D8699": {"description": "Re-cement or re-bond fixed retainer", "category": "repair"},
    "D8701": {"description": "Repair of fixed retainer, includes reattachment", "category": "repair"},
    "D8702": {"description": "Replacement of lost/broken retainer", "category": "retention"},
    "D8703": {"description": "Replacement of lost/broken retainer", "category": "retention"},
    "D8999": {"description": "Unspecified orthodontic procedure, by report", "category": "other"},
}


class CDTValidationResult:
    def __init__(self, valid: bool, code: str, errors: list[str] | None = None):
        self.valid = valid
        self.code = code
        self.errors = errors or []


def validate_cdt_code(code: str) -> CDTValidationResult:
    """Validate a single CDT code."""
    code = code.upper().strip()
    if not code.startswith("D"):
        return CDTValidationResult(False, code, [f"Invalid format: CDT codes start with 'D', got '{code}'"])
    if code not in ORTHO_CDT_CODES:
        if code.startswith("D8"):
            return CDTValidationResult(False, code, [f"Unknown ortho CDT code: {code}"])
        return CDTValidationResult(False, code, [f"Code {code} is not an orthodontic CDT code (D8xxx series)"])
    return CDTValidationResult(True, code)


def validate_claim_codes(codes: list[dict]) -> list[CDTValidationResult]:
    """Validate all CDT codes on a claim. Each code dict has 'code', 'fee', 'units'."""
    results = []
    for item in codes:
        code = item.get("code", "")
        result = validate_cdt_code(code)
        if result.valid:
            if item.get("units", 1) < 1:
                result.valid = False
                result.errors.append("Units must be >= 1")
            if item.get("fee", 0) < 0:
                result.valid = False
                result.errors.append("Fee cannot be negative")
        results.append(result)
    return results


def get_code_info(code: str) -> dict | None:
    """Get CDT code description and category."""
    return ORTHO_CDT_CODES.get(code.upper().strip())


def get_codes_by_category(category: str) -> list[dict]:
    """Get all CDT codes in a category."""
    return [{"code": k, **v} for k, v in ORTHO_CDT_CODES.items() if v["category"] == category]
