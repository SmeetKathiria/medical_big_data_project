from .schemas import HealthcareDocument


def parse_cms(row: dict) -> HealthcareDocument:
    doc = HealthcareDocument.from_row({**row, "source_type": "cms"})
    doc.metadata.setdefault("document_type", "CMS policy")
    return doc
