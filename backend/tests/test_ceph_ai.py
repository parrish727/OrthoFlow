"""Tests for Ceph Phase B AI auto-landmarking helpers (CI-safe — no live model call).

Covers JSON extraction robustness and media-type inference. The live vision round-trip + pixel
conversion is verified against the real model during the session (CI has no ANTHROPIC key).
"""
from app.services import ceph_ai as A


def test_extract_json_bare():
    assert A._extract_json('{"landmarks": {"S": {"x": 0.5, "y": 0.5}}}') == {"landmarks": {"S": {"x": 0.5, "y": 0.5}}}


def test_extract_json_fenced():
    text = "Sure:\n```json\n{\"landmarks\": {\"N\": {\"x\": 0.6, \"y\": 0.3}}}\n```"
    assert A._extract_json(text) == {"landmarks": {"N": {"x": 0.6, "y": 0.3}}}


def test_extract_json_with_prose_prefix_suffix():
    text = 'Here are the points {"landmarks": {"A": {"x": 0.7, "y": 0.5}}} hope this helps'
    assert A._extract_json(text) == {"landmarks": {"A": {"x": 0.7, "y": 0.5}}}


def test_extract_json_garbage_returns_none():
    assert A._extract_json("no json at all") is None
    assert A._extract_json("") is None


def test_media_type_from_content_type():
    assert A._media_type("image/jpeg", None) == "image/jpeg"
    assert A._media_type("image/png", None) == "image/png"


def test_media_type_from_filename_fallback():
    assert A._media_type(None, "ceph.JPG") == "image/jpeg"
    assert A._media_type("application/octet-stream", "ceph.png") == "image/png"
    assert A._media_type(None, "unknown.tiff") == "image/png"  # safe default


def test_glossary_covers_abo_landmarks():
    from app.services import ceph_engine as E
    for k in E.analysis_landmarks("abo"):
        assert k in A._LANDMARK_GLOSSARY, f"missing glossary entry for {k}"
