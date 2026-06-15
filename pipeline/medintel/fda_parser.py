from .schemas import HealthcareDocument


def parse_fda(row: dict) -> HealthcareDocument:
    doc = HealthcareDocument.from_row({**row, "source_type": "fda"})
    doc.metadata.setdefault("document_type", "FDA document")
    return doc
