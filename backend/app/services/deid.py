"""De-identification for AI prompts: swap identifiers for placeholders, restore them locally.

Why: we have no BAA with the AI provider, so nothing that identifies a patient may leave our
servers. Every prompt is scrubbed here before it is sent, and the model's answer is restored here
before anyone sees it. The model only ever sees placeholders such as [PATIENT_NAME] or [DATE_2];
the mapping lives in memory for the length of one request and is never logged or stored.

What is replaced
- Registered people (patient, guardian, family): full name, "Last, First", first, last.
- Registered values (claim number, member id, DOB, service date, ...).
- Pattern hits in any free text: SSN, email, phone, dates, long digit runs, honorific names
  ("Mrs. Smith"), and (aggressive mode) any proper noun mid-sentence.
- Dates can instead become relative text ("42 days ago") when the model needs timing but the
  answer does not need the real date.

Accuracy: restoration is an exact reverse, so letters and appeals come back with the real names,
dates and numbers. Clinical content (diagnoses, CDT codes, wire sizes, measurements, money) is not
an identifier and is sent as is.

Limits (do not oversell): this removes known identifiers and common patterns. Free text can hold a
name we were never told about. Aggressive mode covers staff-typed text; clinical notes rely on the
registered family names plus the honorific rule. Safe Harbor "no actual knowledge" for notes
needs an NER pass or expert determination. See docs/compliance/AI_DEIDENTIFICATION.md.
"""
from __future__ import annotations

import re
from datetime import date, datetime

_MONTHS = (r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
           r"Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)")

_RX = {
    "SSN": re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"),
    "EMAIL": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "PHONE": re.compile(r"(?<![\d$.])(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)"),
    "DATE": re.compile(
        r"(?<![\d-])(?:\d{4}-\d{2}-\d{2}|\d{4}-\d{2}(?!\d)|\d{1,2}/\d{1,2}/\d{2,4}|"
        + _MONTHS + r"\.? \d{1,2}(?:st|nd|rd|th)?(?:,? \d{4})?|" + _MONTHS + r",? \d{4})(?![\d-])"),
    "PERSON": re.compile(r"\b(?:Mr|Mrs|Ms|Miss|Mx|Dr)\.? [A-Z][a-zA-Z'-]+(?: [A-Z][a-zA-Z'-]+)?"),
    "ID": re.compile(r"(?<![\w$.])\d{7,}(?!\w|\.\d)"),
}

# Proper-noun words that are not names; used only by aggressive mode.
_ALLOW = {
    "Dear", "Sincerely", "Regards", "Thank", "Thanks", "Best", "Warmly", "Respectfully", "Hello", "Hi",
    "Please", "Your", "Our", "We", "The", "This", "That", "These", "Those", "If", "In", "On", "At",
    "For", "As", "It", "Is", "Are", "Was", "Were", "And", "But", "Or", "To", "Of", "By", "With",
    "From", "Re", "Attn", "Office", "Practice", "Orthodontics", "Orthodontic", "Orthodontist",
    "Doctor", "Parent", "Guardian", "Patient", "Account", "Balance", "Payment", "Payments",
    "Insurance", "Claims", "Claim", "Department", "Review", "Class", "Phase", "Invisalign",
    "MyOrthoChart", "OrthoFlow", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
    "Sunday", "January", "February", "March", "April", "May", "June", "July", "August", "September",
    "October", "November", "December", "Medicaid", "Medicare", "Reconsideration", "Re",
}
_PROPER = re.compile(r"(?<![.!?\n]\s)(?<!^)\b[A-Z][a-z]{2,}\b")
_TOKEN_RX = re.compile(r"\[[A-Z]+(?:_[A-Z]+)*(?:_\d+)?\]")


class DeidError(Exception):
    """Raised when a prompt still contains an identifier after scrubbing. The request must fail."""


def age_years(dob: date | None, today: date | None = None) -> str:
    """Age is allowed (under 90). Used instead of a date of birth."""
    if not dob:
        return "unknown"
    today = today or date.today()
    a = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return "90 or older" if a >= 90 else str(max(a, 0))


def relative_date(d: date, today: date | None = None) -> str:
    today = today or date.today()
    n = (d - today).days
    if n == 0:
        return "today"
    unit_n, unit = (abs(n), "day") if abs(n) < 60 else (round(abs(n) / 30.4), "month")
    s = f"{unit_n} {unit}{'' if unit_n == 1 else 's'}"
    return f"{s} from now" if n > 0 else f"{s} ago"


def _parse_iso(s: str) -> date | None:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


class DeidSession:
    """One request's placeholder map. Never persist or log this object."""

    def __init__(self, today: date | None = None):
        self.today = today or date.today()
        self._tok_to_orig: dict[str, str] = {}
        self._orig_to_tok: dict[str, str] = {}
        self._counters: dict[str, int] = {}
        self._names: list[tuple[str, str, bool]] = []   # (original, token, case_sensitive)

    # ── registration ──
    def _new(self, kind: str, original: str) -> str:
        key = original.strip().lower()
        if key in self._orig_to_tok:
            return self._orig_to_tok[key]
        n = self._counters.get(kind, 0) + 1
        self._counters[kind] = n
        tok = f"[{kind}_{n}]"
        self._tok_to_orig[tok] = original.strip()
        self._orig_to_tok[key] = tok
        return tok

    def add_person(self, kind: str, first: str | None, last: str | None = None, full: str | None = None) -> str:
        """Register a person. Returns the placeholder for the full name, e.g. [PATIENT_NAME]."""
        first = (first or "").strip()
        last = (last or "").strip()
        if full and not (first or last):
            parts = full.split()
            first, last = (parts[0], " ".join(parts[1:])) if parts else ("", "")
        full_name = f"{first} {last}".strip()
        tok_full = f"[{kind}_NAME]"
        if full_name:
            self._tok_to_orig[tok_full] = full_name
            self._names.append((full_name, tok_full, False))
            if last:
                self._names.append((f"{last}, {first}", tok_full, False))
        if first:
            self._tok_to_orig[f"[{kind}_FIRST]"] = first
            self._names.append((first, f"[{kind}_FIRST]", True))
        if last:
            self._tok_to_orig[f"[{kind}_LAST]"] = last
            self._names.append((last, f"[{kind}_LAST]", True))
        self._names.sort(key=lambda t: len(t[0]), reverse=True)
        return tok_full

    def add_value(self, kind: str, value) -> str:
        """Register an identifier value (claim number, member id, date...). Returns its token."""
        if value is None or str(value).strip() == "":
            return ""
        if isinstance(value, (date, datetime)):
            value = value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
        return self._new(kind, str(value))

    # ── scrub ──
    def scrub(self, text: str, dates: str = "token", aggressive: bool = False) -> str:
        """Replace identifiers in `text`. dates: "token" (restorable) or "relative" (not restored)."""
        if not text:
            return text or ""
        out = text
        for orig, tok, case_sensitive in self._names:
            flags = 0 if case_sensitive else re.IGNORECASE
            out = re.sub(rf"(?<![A-Za-z0-9_]){re.escape(orig)}(?![A-Za-z0-9_])", tok, out, flags=flags)
        for key, tok in sorted(self._orig_to_tok.items(), key=lambda kv: len(kv[0]), reverse=True):
            orig = self._tok_to_orig[tok]
            out = re.sub(rf"(?<![A-Za-z0-9_]){re.escape(orig)}(?![A-Za-z0-9_])", tok, out, flags=re.IGNORECASE)

        def sub_kind(kind):
            def f(m):
                return self._new(kind, m.group(0))
            return f

        for kind in ("SSN", "EMAIL", "PHONE"):
            out = _RX[kind].sub(sub_kind(kind), out)

        def date_sub(m):
            s = m.group(0)
            if dates == "relative":
                d = _parse_iso(s)
                if d:
                    return relative_date(d, self.today)
            return self._new("DATE", s)
        out = _RX["DATE"].sub(date_sub, out)
        out = _RX["PERSON"].sub(sub_kind("PERSON"), out)
        out = _RX["ID"].sub(sub_kind("ID"), out)

        if aggressive:
            def proper(m):
                w = m.group(0)
                return w if w in _ALLOW else self._new("NAME", w)
            segs = re.split(r"(\[[A-Z0-9_]+\])", out)       # leave existing tokens untouched
            out = "".join(s if s.startswith("[") and s.endswith("]") else _PROPER.sub(proper, s) for s in segs)
        return out

    def check(self, text: str) -> None:
        """Fail closed: raise if any registered identifier or pattern survived."""
        body = _TOKEN_RX.sub(" ", text)
        for orig, _tok, case_sensitive in self._names:
            if re.search(rf"(?<![A-Za-z0-9_]){re.escape(orig)}(?![A-Za-z0-9_])", body,
                         0 if case_sensitive else re.IGNORECASE):
                raise DeidError("identifier survived scrubbing")
        for key in self._orig_to_tok:
            if len(key) >= 3 and re.search(rf"(?<![A-Za-z0-9_]){re.escape(key)}(?![A-Za-z0-9_])", body.lower()):
                raise DeidError("identifier survived scrubbing")
        for kind in ("SSN", "EMAIL", "PHONE", "DATE", "PERSON", "ID"):
            if _RX[kind].search(body):
                raise DeidError(f"{kind.lower()} pattern survived scrubbing")

    # ── restore ──
    def restore(self, text: str) -> str:
        """Put the real values back into the model's answer (bracketed or bare placeholders)."""
        if not text:
            return text or ""
        out = text
        for tok in sorted(self._tok_to_orig, key=len, reverse=True):
            orig = self._tok_to_orig[tok]
            out = out.replace(tok, orig)
            bare = tok[1:-1]
            out = re.sub(rf"(?<![A-Za-z0-9_]){re.escape(bare)}(?![A-Za-z0-9_])", lambda _m, o=orig: o, out)
        return out

    def has_tokens(self) -> bool:
        return bool(self._tok_to_orig)


TOKEN_INSTRUCTION = (
    "Some details are replaced by placeholders in square brackets, for example [PATIENT_NAME], "
    "[DATE_1] or [CLAIM_1]. Reproduce each placeholder exactly as written wherever you would write "
    "that detail. Never guess or invent the real value behind a placeholder."
)


def claim_session(claim) -> DeidSession:
    """A session pre-loaded with a claim's identifiers (patient, subscriber id, claim number, prior
    auth, ERA reference, service and submission dates). Duck-typed so it works with the ORM model."""
    s = DeidSession()
    if getattr(claim, "patient_name", None):
        s.add_person("PATIENT", None, None, full=claim.patient_name)
    s.add_value("SUBSCRIBER_ID", getattr(claim, "subscriber_id", None))
    s.add_value("CLAIM_NO", getattr(claim, "claim_number", None))
    s.add_value("PRIOR_AUTH", getattr(claim, "prior_auth_number", None))
    s.add_value("ERA_REF", getattr(claim, "era_reference", None))
    s.add_value("SERVICE_DATE", getattr(claim, "service_date", None))
    sub = getattr(claim, "submission_date", None)
    if sub:
        s.add_value("SUBMISSION_DATE", sub.date() if isinstance(sub, datetime) else sub)
    return s


def days_between(a, b) -> int | None:
    """Whole days from a to b (dates or datetimes). None if either is missing."""
    if not a or not b:
        return None
    a = a.date() if isinstance(a, datetime) else a
    b = b.date() if isinstance(b, datetime) else b
    return (b - a).days
