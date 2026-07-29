"""Scan outputs for PII before returning to the user."""

from __future__ import annotations

import re

PII_PATTERNS = {
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
}


def scan_for_pii(text: str) -> dict[str, int]:
    """Scan text for PII. Returns dict of PII type → count."""
    findings: dict[str, int] = {}
    for pii_type, pattern in PII_PATTERNS.items():
        matches = re.findall(pattern, text)
        if matches:
            findings[pii_type] = len(matches)
    return findings


def redact_pii(text: str) -> str:
    """Replace PII with [REDACTED]."""
    for pii_type, pattern in PII_PATTERNS.items():
        text = re.sub(pattern, f"[REDACTED_{pii_type.upper()}]", text)
    return text
