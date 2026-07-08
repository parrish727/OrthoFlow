"""File scanning service — ClamAV virus/malware detection on uploads.

Uses the ClamAV INSTREAM protocol over TCP socket (not HTTP REST).
FAILS CLOSED: if ClamAV is unavailable, the file is REJECTED (not silently passed).
"""
import struct
import asyncio

from app.core.config import settings

# Parse host:port from config
_clamav_url = settings.CLAMAV_URL.replace("http://", "").replace("https://", "")
CLAMAV_HOST = _clamav_url.split(":")[0] if ":" in _clamav_url else _clamav_url
CLAMAV_PORT = int(_clamav_url.split(":")[1]) if ":" in _clamav_url else 3310

# File validation
ALLOWED_MIME_PREFIXES = [b"%PDF", b"\xff\xd8\xff", b"\x89PNG"]  # PDF, JPEG, PNG
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


async def scan_file(content: bytes, filename: str) -> dict:
    """Scan file content for viruses/malware.

    Returns: {"clean": True/False, "reason": "..."}
    FAILS CLOSED: returns clean=False if ClamAV is unavailable.
    """
    # Size check
    if len(content) > MAX_FILE_SIZE:
        return {"clean": False, "reason": f"File too large ({len(content)} bytes, max {MAX_FILE_SIZE})"}

    # File type validation (magic bytes)
    if not _validate_file_type(content, filename):
        return {"clean": False, "reason": f"File type not allowed for: {filename}"}

    # Quick pattern checks
    if _contains_known_threats(content):
        return {"clean": False, "reason": "Known threat pattern detected"}

    # ClamAV INSTREAM scan
    try:
        result = await _clamav_instream(content)
        return result
    except Exception as e:
        # FAIL CLOSED: if ClamAV is unavailable, reject the file
        return {"clean": False, "reason": f"Security scanner unavailable: {e}. File rejected."}


async def _clamav_instream(content: bytes) -> dict:
    """Send file to ClamAV using the INSTREAM protocol over TCP."""
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(CLAMAV_HOST, CLAMAV_PORT),
        timeout=10,
    )

    try:
        # Send INSTREAM command
        writer.write(b"zINSTREAM\0")

        # Send file in chunks (ClamAV expects: 4-byte big-endian length + data)
        chunk_size = 2048
        for i in range(0, len(content), chunk_size):
            chunk = content[i:i + chunk_size]
            writer.write(struct.pack(">I", len(chunk)) + chunk)

        # Send zero-length chunk to signal end
        writer.write(struct.pack(">I", 0))
        await writer.drain()

        # Read response
        response = await asyncio.wait_for(reader.read(1024), timeout=30)
        response_str = response.decode("utf-8", errors="ignore").strip("\0").strip()

        if "OK" in response_str:
            return {"clean": True, "reason": ""}
        elif "FOUND" in response_str:
            virus_name = response_str.split("FOUND")[0].split(":")[-1].strip()
            return {"clean": False, "reason": f"Malware detected: {virus_name}"}
        else:
            return {"clean": False, "reason": f"Unexpected scanner response: {response_str}"}
    finally:
        writer.close()
        await writer.wait_closed()


def _validate_file_type(content: bytes, filename: str) -> bool:
    """Validate file type by magic bytes and extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    allowed_extensions = {"pdf", "png", "jpg", "jpeg", "tiff", "tif"}

    if ext not in allowed_extensions:
        return False

    # Check magic bytes
    if ext == "pdf" and not content[:4] == b"%PDF":
        return False
    if ext in ("jpg", "jpeg") and not content[:3] == b"\xff\xd8\xff":
        return False
    if ext == "png" and not content[:4] == b"\x89PNG":
        return False

    return True


def _contains_known_threats(content: bytes) -> bool:
    """Check for known malicious patterns in file content."""
    threats = [
        b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR",  # EICAR test string
        b"X5O!P%@AP[4\x5cPZX54(P^)7CC)7}$EICAR",
        b"<?php",           # PHP shells
        b"<script>",        # XSS in uploaded files
        b"#!/bin/",         # Shell scripts
    ]
    for threat in threats:
        if threat in content:
            return True
    return False
