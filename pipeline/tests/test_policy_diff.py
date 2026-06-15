from medintel.policy_diff import diff_policies


def test_policy_diff_summarizes_added_language():
    diff = diff_policies(
        {"doc_id": "old", "title": "Old", "url": "u", "version": "2024", "text": "requires medical necessity documentation"},
        {"doc_id": "new", "title": "New", "url": "u", "version": "2025", "text": "requires medical necessity documentation and objective functional limitation"},
    )
    assert "objective" in diff["summary"]
    assert len(diff["diff_json"]["citations"]) == 2
