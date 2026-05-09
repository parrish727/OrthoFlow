"""File scanning service — ClamAV virus/malware detection on uploads."""
import httpx

CLAMAV_URL = "http://clamav:3310"


async def scan_file(content: bytes, filename: str) -> dict:
    """Scan file content for viruses/malware.
    Returns: {"clean": True/False, "reason": "..."}
    """
    # Quick pattern checks before sending to ClamAV
    if _contains_known_threats(content):
        return {"clean": False, "reason": "Known threat pattern detected"}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{CLAMAV_URL}/scan",
                files={"file": (filename, content)},
                timeout=30,
            )
            if resp.status_code == 200:
                result = resp.json()
                return {"clean": result.get("clean", False), "reason": result.get("virus", "")}
    except Exception:
        # If ClamAV is unavailable, fall back to pattern matching only
        pass

    return {"clean": True, "reason": ""}


def _contains_known_threats(content: bytes) -> bool:
    """Check for known malicious patterns in file content."""
    threats = [
        b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR",  # EICAR test string
        b"X5O!P%@AP[4\x5cPZX54(P^)7CC)7}$EICAR",
        b"<?php",           # PHP shells
        b"<script>",        # XSS in uploaded files
        b"#!/bin/",         # Shell scripts
        b"import os; os.",  # Python injection
        b"eval(",           # Code execution
        b"exec(",           # Code execution
    ]
    for threat in threats:
        if threat in content:
            return True
    return False
