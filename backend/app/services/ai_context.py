"""AI Context Detection — auto-determines specialty from appointment metadata."""

# Mapping of keywords/CDT code ranges to specialty context
SPECIALTY_KEYWORDS = {
    "ortho": ["adjustment", "bonding", "deband", "invisalign", "retainer", "wire", "bracket", "elastic", "aligner", "ortho"],
    "general": ["cleaning", "prophy", "filling", "composite", "amalgam", "exam", "x-ray", "extraction", "root canal"],
    "cosmetic": ["veneer", "whitening", "bleaching", "smile", "cosmetic", "bonding anterior"],
    "perio": ["srp", "scaling", "root planing", "perio", "deep cleaning", "debridement", "pocket"],
    "surgery": ["implant", "bone graft", "surgical", "impacted", "wisdom"],
}

CDT_SPECIALTY_RANGES = {
    "D0": "general",  # diagnostic
    "D1": "general",  # preventive
    "D2": "general",  # restorative (could be cosmetic for veneers)
    "D3": "general",  # endo
    "D4": "perio",
    "D5": "general",  # prostho
    "D6": "surgery",  # implants
    "D7": "surgery",  # oral surgery
    "D8": "ortho",
    "D9": "general",  # adjunctive
}

SPECIALTY_PROMPTS = {
    "ortho": "You are assisting with an orthodontic appointment. Use orthodontic terminology (brackets, wires, elastics, arch forms, treatment phases, torque, rotation, crowding, spacing). Focus on tooth movement, appliance adjustments, and treatment progress.",
    "general": "You are assisting with a general dentistry appointment. Use standard dental terminology (restoration, caries, prophylaxis, radiograph, occlusion). Focus on diagnosis, treatment planning, and preventive care.",
    "cosmetic": "You are assisting with a cosmetic dentistry appointment. Use aesthetic terminology (shade matching, smile design, veneer preparation, tissue contouring, gingival margin). Focus on appearance outcomes and patient expectations.",
    "perio": "You are assisting with a periodontal appointment. Use periodontal terminology (probing depths, clinical attachment level, bleeding on probing, scaling and root planing, pocket reduction). Focus on tissue health and disease management.",
    "surgery": "You are assisting with an oral surgery appointment. Use surgical terminology (flap elevation, osteotomy, implant placement, bone grafting, suturing, hemostasis). Focus on procedure steps and post-operative instructions.",
}


def detect_specialty(appointment_type: str | None = None, cdt_codes: str | None = None, note_text: str | None = None) -> str:
    """Auto-detect specialty from appointment metadata. Returns specialty string."""
    # Priority 1: CDT codes (most specific)
    if cdt_codes:
        for code in cdt_codes.split(","):
            code = code.strip().upper()
            prefix = code[:2]
            if prefix in CDT_SPECIALTY_RANGES:
                # Special cases
                if code == "D2962":  # veneer
                    return "cosmetic"
                return CDT_SPECIALTY_RANGES[prefix]

    # Priority 2: Appointment type keywords
    if appointment_type:
        appt_lower = appointment_type.lower()
        for specialty, keywords in SPECIALTY_KEYWORDS.items():
            if any(kw in appt_lower for kw in keywords):
                return specialty

    # Priority 3: Note text content (fallback)
    if note_text:
        note_lower = note_text.lower()
        scores = {}
        for specialty, keywords in SPECIALTY_KEYWORDS.items():
            scores[specialty] = sum(1 for kw in keywords if kw in note_lower)
        best = max(scores, key=scores.get)
        if scores[best] > 0:
            return best

    # Default: general
    return "general"


def get_specialty_system_prompt(specialty: str) -> str:
    """Get the AI system prompt addition for the detected specialty."""
    return SPECIALTY_PROMPTS.get(specialty, SPECIALTY_PROMPTS["general"])


def build_clinical_note_prompt(appointment_type: str | None = None, cdt_codes: str | None = None, note_text: str | None = None) -> str:
    """Build the full system prompt with auto-detected specialty context."""
    specialty = detect_specialty(appointment_type, cdt_codes, note_text)
    base_prompt = "You are an AI clinical note assistant for a dental practice. Help structure clinical observations into professional SOAP-format notes. Be concise, use bullet points, and include relevant clinical details."
    specialty_addition = get_specialty_system_prompt(specialty)
    return f"{base_prompt}\n\n{specialty_addition}\n\nDetected context: {specialty} appointment."
