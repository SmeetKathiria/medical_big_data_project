from __future__ import annotations

import argparse
import json
import os

from medintel.config import get_settings
from medintel.metrics import stage
from medintel.quality import score_document
from medintel.r2_storage import LocalLake, write_jsonl
from medintel.spark import get_spark
from medintel import db


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    lake = LocalLake(get_settings())
    stage(args.run_id, "quality_safety", "Scoring quality and healthcare safety constraints")
    input_path = lake.path("silver", "normalized_documents", f"{args.run_id}.jsonl")
    spark = get_spark("medintel-quality-safety")
    kept_count = 0
    rejected_count = 0
    write_db_docs = os.getenv("MEDINTEL_DB_DOCUMENT_UPSERT", "").lower() in {"1", "true", "yes"}
    kept_path = lake.path("gold", "healthcare_documents", f"{args.run_id}.jsonl")
    rejected_path = lake.path("gold", "quality_reports", f"{args.run_id}.jsonl")
    with kept_path.open("w", encoding="utf-8") as kept_out:
        with rejected_path.open("w", encoding="utf-8") as rejected_out:
            for row in spark.read.json(str(input_path)).toJSON().toLocalIterator():
                ok, scored = score_document(json.loads(row))
                if ok:
                    kept_out.write(json.dumps(scored, sort_keys=True) + "\n")
                    kept_count += 1
                    if write_db_docs:
                        db.execute(
                            """
                            INSERT INTO healthcare_documents (doc_id, source_id, source_type, title, url, publication_date, effective_date, version, text_uri, metadata)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                            ON CONFLICT (doc_id) DO UPDATE SET metadata = EXCLUDED.metadata
                            """,
                            (
                                scored["doc_id"],
                                scored["source_id"],
                                scored["source_type"],
                                scored["title"],
                                scored["url"],
                                scored.get("publication_date"),
                                scored.get("effective_date"),
                                scored.get("version"),
                                f"gold/healthcare_documents/{args.run_id}.jsonl",
                                db.json_param(scored["metadata"]),
                            ),
                        )
                else:
                    rejected_out.write(json.dumps(scored, sort_keys=True) + "\n")
                    rejected_count += 1
    spark.stop()
    db.update_run(args.run_id, documents_kept=kept_count, documents_rejected=rejected_count)
    db.event(args.run_id, "quality_safety", f"Kept {kept_count} documents and rejected {rejected_count}")


if __name__ == "__main__":
    main()
