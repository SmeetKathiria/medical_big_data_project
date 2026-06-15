from __future__ import annotations

from .chunking import chunk_text


def select_chunks(doc: dict, entities: list[dict]) -> list[dict]:
    source_score = doc.get("metadata", {}).get("source_authority_score", 0.5)
    chunks = []
    for index, text_chunk in enumerate(chunk_text(doc["text"])):
        chunks.append({
            "chunk_id": f"{doc['doc_id']}:{index}",
            "doc_id": doc["doc_id"],
            "source_type": doc["source_type"],
            "title": doc["title"],
            "url": doc["url"],
            "text_chunk": text_chunk,
            "publication_date": doc.get("publication_date"),
            "effective_date": doc.get("effective_date"),
            "version": doc.get("version"),
            "entities": entities,
            "source_authority_score": source_score,
            "metadata": doc.get("metadata", {}),
        })
    return chunks
