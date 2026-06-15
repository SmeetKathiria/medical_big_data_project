from .schemas import HealthcareDocument


def parse_pubmed(row: dict) -> HealthcareDocument:
    doc = HealthcareDocument.from_row({**row, "source_type": "pubmed"})
    doc.metadata.setdefault("document_type", "PubMed abstract")
    return doc
