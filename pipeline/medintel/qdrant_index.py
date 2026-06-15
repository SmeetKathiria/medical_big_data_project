from __future__ import annotations

try:
    import requests
except ImportError:
    requests = None


def payload_for_chunk(chunk: dict) -> dict:
    return {
        "chunk_id": chunk["chunk_id"],
        "doc_id": chunk["doc_id"],
        "source_type": chunk["source_type"],
        "title": chunk["title"],
        "url": chunk["url"],
        "publication_date": chunk.get("publication_date"),
        "effective_date": chunk.get("effective_date"),
        "version": chunk.get("version"),
        "entities": chunk.get("entities", []),
        "metadata": chunk.get("metadata", {}),
        "source_authority_score": chunk.get("source_authority_score", 0.5),
        "text_chunk": chunk["text_chunk"],
    }


def recreate_collection(qdrant_url: str, collection: str, dim: int) -> bool:
    if requests is None:
        return False
    try:
        requests.delete(f"{qdrant_url}/collections/{collection}", timeout=10)
        requests.put(f"{qdrant_url}/collections/{collection}", json={"vectors": {"size": dim, "distance": "Cosine"}}, timeout=5)
        return True
    except requests.RequestException:
        return False


def upsert_qdrant(qdrant_url: str, collection: str, points: list[dict], dim: int) -> bool:
    if not recreate_collection(qdrant_url, collection, dim):
        return False
    return upsert_qdrant_points(qdrant_url, collection, points)


def upsert_qdrant_points(qdrant_url: str, collection: str, points: list[dict]) -> bool:
    if requests is None:
        return False
    try:
        response = requests.put(f"{qdrant_url}/collections/{collection}/points", json={"points": points}, timeout=20)
        return response.ok
    except requests.RequestException:
        return False
