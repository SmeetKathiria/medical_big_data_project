from medintel.retrieval_selection import select_chunks


def test_select_chunks_preserves_citation_metadata():
    chunks = select_chunks(
        {"doc_id": "d1", "source_type": "cms", "title": "Policy", "url": "https://example.test", "text": "Coverage text", "version": "2025", "metadata": {"source_authority_score": 1.0}},
        [{"entity_type": "CPT", "normalized_value": "72148"}],
    )
    assert chunks[0]["url"] == "https://example.test"
    assert chunks[0]["source_authority_score"] == 1.0
