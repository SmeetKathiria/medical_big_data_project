from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class HealthcareDocument:
    doc_id: str
    source_id: str
    source_type: str
    title: str
    url: str
    publication_date: str | None
    effective_date: str | None
    version: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "HealthcareDocument":
        return cls(
            doc_id=str(row["doc_id"]),
            source_id=str(row.get("source_id") or row.get("source_type")),
            source_type=str(row["source_type"]).lower(),
            title=str(row.get("title") or "Untitled"),
            url=str(row.get("url") or ""),
            publication_date=row.get("publication_date"),
            effective_date=row.get("effective_date"),
            version=str(row.get("version") or ""),
            text=str(row.get("text") or ""),
            metadata=dict(row.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "title": self.title,
            "url": self.url,
            "publication_date": self.publication_date,
            "effective_date": self.effective_date,
            "version": self.version,
            "text": self.text,
            "metadata": self.metadata,
        }
