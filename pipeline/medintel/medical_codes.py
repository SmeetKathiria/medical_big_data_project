from __future__ import annotations

import re

PATTERNS = {
    "CPT": re.compile(r"\b\d{5}\b"),
    "HCPCS": re.compile(r"\b[A-Z]\d{4}\b"),
    "ICD10": re.compile(r"\b[A-Z]\d{2}(?:\.\d{1,4})?\b"),
    "NDC": re.compile(r"\b\d{4,5}-\d{3,4}-\d{1,2}\b"),
    "FDA_APPLICATION": re.compile(r"\b(?:NDA|BLA|ANDA)\s?\d{3,6}\b", re.I),
    "PMID": re.compile(r"\bPMID:?\s?(\d{6,9})\b", re.I),
}

DRUG_TERMS = ["semaglutide", "GLP-1", "GLP-1 receptor agonist"]
CONDITION_TERMS = ["obesity", "overweight", "pancreatitis", "kidney injury"]
PROCEDURE_TERMS = ["MRI lumbar spine", "lumbar spine MRI"]


def _context(text: str, start: int, end: int, window: int = 80) -> str:
    return text[max(0, start - window) : min(len(text), end + window)]


def extract_entities(text: str) -> list[dict]:
    entities: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for entity_type, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            value = match.group(1) if entity_type == "PMID" and match.groups() else match.group(0)
            key = (entity_type, value.upper())
            if key not in seen:
                seen.add(key)
                entities.append({
                    "entity_type": entity_type,
                    "entity_value": value,
                    "normalized_value": value.upper(),
                    "context": _context(text, match.start(), match.end()),
                })
    for entity_type, terms in {
        "DRUG": DRUG_TERMS,
        "CONDITION": CONDITION_TERMS,
        "PROCEDURE": PROCEDURE_TERMS,
    }.items():
        for term in terms:
            match = re.search(re.escape(term), text, re.I)
            if match:
                entities.append({
                    "entity_type": entity_type,
                    "entity_value": term,
                    "normalized_value": term.lower(),
                    "context": _context(text, match.start(), match.end()),
                })
    return entities
