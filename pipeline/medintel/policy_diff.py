from __future__ import annotations

import difflib


def diff_policies(old_doc: dict, new_doc: dict) -> dict:
    old_words = old_doc["text"].split()
    new_words = new_doc["text"].split()
    matcher = difflib.SequenceMatcher(a=old_words, b=new_words)
    added: list[str] = []
    removed: list[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in {"replace", "delete"}:
            removed.extend(old_words[i1:i2])
        if tag in {"replace", "insert"}:
            added.extend(new_words[j1:j2])
    summary_bits = []
    if added:
        summary_bits.append("Added language: " + " ".join(added[:40]))
    if removed:
        summary_bits.append("Removed language: " + " ".join(removed[:40]))
    summary = " ".join(summary_bits) or "No material text changes detected."
    return {
        "diff_id": f"{old_doc['doc_id']}__{new_doc['doc_id']}",
        "source_type": "cms",
        "topic": old_doc.get("metadata", {}).get("topic") or new_doc.get("metadata", {}).get("topic") or "CMS policy",
        "old_version": old_doc.get("version"),
        "new_version": new_doc.get("version"),
        "summary": summary,
        "diff_json": {
            "added_terms": added,
            "removed_terms": removed,
            "citations": [
                {"doc_id": old_doc["doc_id"], "title": old_doc["title"], "url": old_doc["url"], "version": old_doc.get("version")},
                {"doc_id": new_doc["doc_id"], "title": new_doc["title"], "url": new_doc["url"], "version": new_doc.get("version")},
            ],
        },
    }
