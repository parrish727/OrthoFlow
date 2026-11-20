"""De-identification layer: nothing identifying reaches the AI provider, and answers come back whole."""
import io
import pathlib
import re
from datetime import date

import pytest

from app.core.config import settings
from app.services import anthropic_gateway as gw
from app.services import deid as d

TODAY = date(2026, 11, 20)


def sess():
    s = d.DeidSession(today=TODAY)
    s.add_person("PATIENT", "Ada", "Lovelace")
    s.add_person("GUARDIAN", None, None, full="Byron Lovelace")
    return s


# ── scrub / restore ──
def test_names_become_placeholders_and_round_trip():
    s = sess()
    out = s.scrub("Ada Lovelace (Lovelace, Ada) saw Dr. Chen. Ada's mother is Byron Lovelace.")
    assert "Ada" not in out and "Lovelace" not in out and "Byron" not in out
    assert "[PATIENT_NAME]" in out and "[GUARDIAN_NAME]" in out
    restored = s.restore(out)
    assert "Ada Lovelace" in restored and "Byron Lovelace" in restored


def test_patterns_ssn_email_phone_date_id():
    s = sess()
    text = "SSN 123-45-6789, email ada@example.com, call (704) 555-0142, seen 2026-10-05 and 10/05/2026, member 98765432."
    out = s.scrub(text)
    for bad in ("123-45-6789", "ada@example.com", "555-0142", "2026-10-05", "10/05/2026", "98765432"):
        assert bad not in out
    s.check(out)
    assert s.restore(out) == text


def test_clinical_content_is_left_alone():
    s = sess()
    text = "Upper 19x25 SS wire, D8080 billed $1500.00, elastics 3/16, Class II, tooth #8, 18 months."
    assert s.scrub(text) == text


def test_relative_dates_for_notes():
    s = sess()
    out = s.scrub("Bonded 2026-10-05; wire change 2025-11-20", dates="relative")
    assert "2026" not in out and "2025" not in out
    assert "46 days ago" in out and "12 months ago" in out


def test_age_instead_of_dob():
    assert d.age_years(date(2012, 5, 4), TODAY) == "14"
    assert d.age_years(date(1920, 1, 1), TODAY) == "90 or older"
    assert d.age_years(None) == "unknown"


def test_honorific_names_in_free_text():
    s = sess()
    out = s.scrub("Mrs. Okafor called about the bill; Ms. Jane Doe will pay Friday.")
    assert "Okafor" not in out and "Jane" not in out
    assert s.restore(out).startswith("Mrs. Okafor")


def test_aggressive_mode_tokenizes_unknown_proper_nouns_and_restores():
    s = sess()
    text = "Dear Priya, thank you for visiting Smile Brothers in Charlotte. We will see you soon."
    out = s.scrub(text, aggressive=True)
    for name in ("Priya", "Smile", "Brothers", "Charlotte"):
        assert name not in out
    assert out.startswith("Dear ") and "thank you" in out
    assert s.restore(out) == text


def test_check_fails_closed_when_identifier_survives():
    s = sess()
    with pytest.raises(d.DeidError):
        s.check("Please call Ada Lovelace")
    with pytest.raises(d.DeidError):
        s.check("reach me at ada@example.com")


def test_restore_handles_bare_and_bracketed_placeholders():
    s = sess()
    tok = s.add_value("CLAIM_NO", "CLM-7788")
    assert tok == "[CLAIM_NO_1]"
    assert s.restore("Re: [CLAIM_NO_1] and CLAIM_NO_1 for [PATIENT_NAME]'s file") == "Re: CLM-7788 and CLM-7788 for Ada Lovelace's file"


def test_claim_session_registers_claim_identifiers():
    class C:
        patient_name = "Ada Lovelace"; subscriber_id = "SUB123456"; claim_number = "CLM-7788"
        prior_auth_number = "PA-991"; era_reference = None
        service_date = date(2026, 9, 1); submission_date = None
    s = d.claim_session(C())
    out = s.scrub("Ada Lovelace SUB123456 claim CLM-7788 auth PA-991 service 2026-09-01")
    for bad in ("Ada", "SUB123456", "CLM-7788", "PA-991", "2026-09-01"):
        assert bad not in out
    assert d.days_between(date(2026, 9, 1), date(2026, 9, 20)) == 19


# ── gateway ──
class _Resp:
    def __init__(self, text): self._t = text
    def raise_for_status(self): pass
    def json(self): return {"content": [{"text": self._t}]}


def _fake_client(sent: list, answer: str):
    class C:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, headers=None, json=None, timeout=None):
            sent.append(json); return _Resp(answer)
    return C


@pytest.mark.asyncio
async def test_gateway_sends_only_placeholders_and_restores_answer(monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key")
    sent: list = []
    monkeypatch.setattr(gw.httpx, "AsyncClient", _fake_client(sent, "Dear [GUARDIAN_NAME], [PATIENT_NAME] is doing well. Seen [DATE_1]."))
    s = sess()
    prompt = "Write to Byron Lovelace about Ada Lovelace (DOB 2012-05-04, ada@example.com). Bonded 2026-10-05."
    out = await gw.complete(prompt, s)
    payload = repr(sent[0])
    for bad in ("Ada", "Lovelace", "Byron", "2012-05-04", "ada@example.com", "2026-10-05"):
        assert bad not in payload
    assert "[PATIENT_NAME]" in payload and "Reproduce each placeholder" in sent[0]["system"]
    assert out.startswith("Dear Byron Lovelace, Ada Lovelace is doing well. Seen 2026-10-05") or "Ada Lovelace" in out


@pytest.mark.asyncio
async def test_gateway_requires_key(monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")
    with pytest.raises(gw.GatewayError):
        await gw.complete("hi", d.DeidSession())


def test_strip_image_metadata_removes_exif_and_text_chunks():
    from PIL import Image, PngImagePlugin
    im = Image.new("RGB", (8, 8), "white")
    info = PngImagePlugin.PngInfo(); info.add_text("PatientName", "Ada Lovelace")
    buf = io.BytesIO(); im.save(buf, "PNG", pnginfo=info)
    assert b"Ada Lovelace" in buf.getvalue()
    clean, media = gw.strip_image_metadata(buf.getvalue())
    assert b"Ada Lovelace" not in clean and media == "image/png"


@pytest.mark.asyncio
async def test_image_analysis_can_be_switched_off(monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "k")
    monkeypatch.setattr(settings, "CEPH_AI_CLOUD_ENABLED", False)
    with pytest.raises(gw.GatewayError) as e:
        await gw.complete_image("landmarks", b"x")
    assert e.value.kind == "disabled"


# ── structural guard ──
def test_only_the_gateway_calls_the_anthropic_api():
    root = pathlib.Path(__file__).resolve().parents[1] / "app"
    offenders = [
        str(p.relative_to(root)) for p in root.rglob("*.py")
        if p.name != "anthropic_gateway.py" and "api.anthropic.com" in p.read_text()
    ]
    assert offenders == [], f"Call Claude only through app/services/anthropic_gateway.py: {offenders}"


def test_no_managed_cloud_llm_path():
    root = pathlib.Path(__file__).resolve().parents[1] / "app"
    assert not re.search(r"bedrock", (root / "services" / "llm.py").read_text(), re.I)
