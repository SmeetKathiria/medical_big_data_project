from __future__ import annotations

import argparse
import json
import os

from medintel.config import get_settings
from medintel.medical_codes import extract_entities
from medintel.metrics import stage
from medintel.r2_storage import LocalLake
from medintel.spark import get_spark
from medintel import db


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    lake = LocalLake(get_settings())
    stage(args.run_id, "extract_entities", "Extracting healthcare entities")
    input_path = lake.path("silver", "normalized_documents", f"{args.run_id}.jsonl")
    spark = get_spark("medintel-extract-entities")
    docs = spark.read.json(str(input_path))
    output_path = lake.path("gold", "medical_entities", f"{args.run_id}.jsonl")
    count = 0
    write_db_entities = os.getenv("MEDINTEL_DB_ENTITY_UPSERT", "").lower() in {"1", "true", "yes"}
    with output_path.open("w", encoding="utf-8") as handle:
        for row in docs.select("doc_id", "text").toJSON().toLocalIterator():
            doc = json.loads(row)
            for entity in extract_entities(doc.get("text") or ""):
                entity_row = {"doc_id": doc["doc_id"], **entity}
                handle.write(json.dumps(entity_row, sort_keys=True) + "\n")
                count += 1
                if write_db_entities:
                    db.execute(
                        """
                        INSERT INTO medical_entities (doc_id, entity_type, entity_value, normalized_value, context)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            entity_row["doc_id"],
                            entity_row["entity_type"],
                            entity_row["entity_value"],
                            entity_row["normalized_value"],
                            entity_row["context"],
                        ),
                    )
    spark.stop()
    db.update_run(args.run_id, entities_extracted=count)
    db.event(args.run_id, "extract_entities", f"Extracted {count} entities")


if __name__ == "__main__":
    main()
