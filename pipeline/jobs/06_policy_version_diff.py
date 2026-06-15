from __future__ import annotations

import argparse
import json

from medintel.config import get_settings
from medintel.metrics import stage
from medintel.policy_diff import diff_policies
from medintel.r2_storage import LocalLake, read_jsonl, write_jsonl
from medintel.spark import get_spark
from medintel import db


def _version_group_key(doc: dict) -> str:
    metadata = doc.get("metadata") or {}
    return metadata.get("display_id") or doc.get("source_id") or doc.get("doc_id")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    lake = LocalLake(get_settings())
    stage(args.run_id, "policy_diff", "Computing CMS policy version differences")
    input_path = lake.path("gold", "healthcare_documents", f"{args.run_id}.jsonl")
    spark = get_spark("medintel-policy-diff")
    docs = [
        json.loads(row)
        for row in spark.read.json(str(input_path)).filter("source_type = 'cms'").toJSON().collect()
    ]
    spark.stop()
    diffs = []
    groups: dict[str, list[dict]] = {}
    for doc in docs:
        groups.setdefault(_version_group_key(doc), []).append(doc)
    for versioned_docs in groups.values():
        unique_versions = {doc.get("version") for doc in versioned_docs}
        if len(versioned_docs) < 2 or len(unique_versions) < 2:
            continue
        versioned_docs.sort(key=lambda d: (d.get("effective_date") or "", d.get("version") or ""))
        diff = diff_policies(versioned_docs[0], versioned_docs[-1])
        diffs.append(diff)
        db.execute(
            """
            INSERT INTO policy_diffs (diff_id, source_type, topic, old_version, new_version, summary, diff_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
            ON CONFLICT (diff_id) DO UPDATE SET summary = EXCLUDED.summary, diff_json = EXCLUDED.diff_json
            """,
            (diff["diff_id"], diff["source_type"], diff["topic"], diff["old_version"], diff["new_version"], diff["summary"], db.json_param(diff["diff_json"])),
        )
    write_jsonl(lake.path("gold", "policy_diffs", f"{args.run_id}.jsonl"), diffs)
    db.event(args.run_id, "policy_diff", f"Produced {len(diffs)} policy diffs")


if __name__ == "__main__":
    main()
