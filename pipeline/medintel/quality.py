from __future__ import annotations

from .pii_phi import contains_phi

AUTHORITY = {"cms": 1.0, "fda": 1.0, "pubmed": 0.85}


def score_document(doc: dict) -> tuple[bool, dict]:
    text = (doc.get("text") or "").strip()
    reasons: list[str] = []
    if not text:
        reasons.append("empty_text")
    if contains_phi(text):
        reasons.append("possible_phi")
    source_type = doc.get("source_type", "")
    metadata = dict(doc.get("metadata") or {})
    metadata["source_authority_score"] = AUTHORITY.get(source_type, 0.5)
    metadata["safety_disclaimer_required"] = True
    return not reasons, {**doc, "text": text, "metadata": metadata, "quality_reasons": reasons}
