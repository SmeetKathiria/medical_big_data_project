from __future__ import annotations

import re

PHI_PATTERNS = [
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b(?:patient|mrn|medical record number)\s*[:#]\s*\w+", re.I),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
]


def contains_phi(text: str) -> bool:
    return any(pattern.search(text) for pattern in PHI_PATTERNS)
