"""Tests for the secure document-exchange upload layer.

Focus on the deterministic, CI-safe pieces that run WITHOUT a live ClamAV or MinIO:
  • scanner type/size validation (magic bytes for PDF/PNG/JPEG/TIFF/HEIC/HEIF/WebP, 50MB cap,
    known-threat rejection) — these run BEFORE the ClamAV INSTREAM call.
  • documents storage key/extension helpers.

The full ClamAV + MinIO round-trip is verified against the live stack during the session, not in
unit tests (CI has no ClamAV; the scanner fails closed there by design).
"""
from app.services.scanner import (
    _validate_file_type,
    _contains_known_threats,
    MAX_FILE_SIZE,
)
from app.services import documents as ds


# ── Size cap ──────────────────────────────────────────────────────────────────

def test_max_file_size_is_50mb():
    assert MAX_FILE_SIZE == 50 * 1024 * 1024


# ── Type validation: accepted formats ──────────────────────────────────────────

def test_accept_pdf():
    assert _validate_file_type(b"%PDF-1.7 ...", "doc.pdf") is True

def test_accept_png():
    assert _validate_file_type(b"\x89PNG\r\n\x1a\n", "img.png") is True

def test_accept_jpeg():
    assert _validate_file_type(b"\xff\xd8\xff\xe0", "photo.jpg") is True
    assert _validate_file_type(b"\xff\xd8\xff\xe1", "photo.jpeg") is True

def test_accept_tiff():
    assert _validate_file_type(b"II*\x00rest", "scan.tiff") is True
    assert _validate_file_type(b"MM\x00*rest", "scan.tif") is True

def test_accept_heic_iphone():
    # ISO-BMFF: 4-byte box size, 'ftyp', brand 'heic'
    heic = b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00heicmif1"
    assert _validate_file_type(heic, "IMG_0001.heic") is True

def test_accept_heif_brands():
    for brand in (b"heix", b"hevc", b"heif", b"mif1", b"msf1"):
        data = b"\x00\x00\x00\x18ftyp" + brand + b"\x00\x00\x00\x00"
        assert _validate_file_type(data, "photo.heif") is True, brand

def test_accept_webp():
    webp = b"RIFF\x00\x00\x00\x00WEBPVP8 "
    assert _validate_file_type(webp, "img.webp") is True


# ── Type validation: rejected formats ───────────────────────────────────────────

def test_reject_unknown_extension():
    assert _validate_file_type(b"MZ\x90\x00", "malware.exe") is False

def test_reject_pdf_with_wrong_magic():
    assert _validate_file_type(b"not a pdf", "fake.pdf") is False

def test_reject_png_with_wrong_magic():
    assert _validate_file_type(b"\xff\xd8\xff", "fake.png") is False

def test_reject_heic_without_ftyp():
    # Right extension, but not an ISO-BMFF container.
    assert _validate_file_type(b"\x00\x00\x00\x18XXXXheic", "fake.heic") is False

def test_reject_webp_without_webp_marker():
    assert _validate_file_type(b"RIFF\x00\x00\x00\x00XXXX", "fake.webp") is False

def test_reject_no_extension():
    assert _validate_file_type(b"%PDF", "noext") is False


# ── Known-threat patterns ───────────────────────────────────────────────────────

def test_known_threats_block_php_and_script():
    assert _contains_known_threats(b"<?php system($_GET[x]); ?>") is True
    assert _contains_known_threats(b"<script>evil()</script>") is True
    assert _contains_known_threats(b"#!/bin/sh\nrm -rf /") is True

def test_clean_content_not_flagged():
    assert _contains_known_threats(b"%PDF-1.7 a perfectly normal consent form") is False


# ── Documents storage helper: keying + extension ───────────────────────────────

def test_ext_for_prefers_filename():
    assert ds.ext_for("IMG_1234.HEIC", "image/heic") == "heic"
    assert ds.ext_for("scan.PDF", "application/pdf") == "pdf"
    assert ds.ext_for("photo.jpeg", "image/jpeg") == "jpg"  # normalized

def test_ext_for_falls_back_to_mime():
    assert ds.ext_for("noext", "image/png") == "png"
    assert ds.ext_for("", "application/pdf") == "pdf"
    assert ds.ext_for("weird.xyz", "image/webp") == "webp"

def test_build_key_scopes_by_practice_and_patient():
    import uuid
    p, pat = uuid.uuid4(), uuid.uuid4()
    key = ds.build_key(p, pat, "consent.pdf", "application/pdf")
    assert key.startswith(f"{p}/{pat}/")
    assert key.endswith(".pdf")

def test_documents_bucket_and_expiry_constants():
    assert ds.DOCUMENTS_BUCKET == "orthoflow-documents"
    assert ds.PRESIGN_EXPIRY_SECONDS == 300
