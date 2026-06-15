from medintel.qdrant_index import payload_for_chunk


def test_qdrant_payload_contains_required_fields():
    payload = payload_for_chunk({
        "chunk_id": "c1",
        "doc_id": "d1",
        "source_type": "cms",
        "title": "Policy",
        "url": "https://example.test",
        "text_chunk": "Citation text",
        "entities": [],
        "source_authority_score": 1.0,
    })
    assert payload["chunk_id"] == "c1"
    assert payload["text_chunk"] == "Citation text"
