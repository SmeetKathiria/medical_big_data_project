from __future__ import annotations

import argparse
import json
from collections import defaultdict

from medintel.config import get_settings
from medintel.metrics import stage
from medintel.retrieval_selection import select_chunks
from medintel.r2_storage import LocalLake, read_jsonl, write_jsonl
from medintel.spark import get_spark
from medintel import db


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    lake = LocalLake(get_settings())
    stage(args.run_id, "retrieval_selection", "Selecting citation-ready retrieval corpus")
    spark = get_spark("medintel-retrieval-selection")
    entities = defaultdict(list)
    for entity in read_jsonl(lake.path("gold", "medical_entities", f"{args.run_id}.jsonl")):
        entities[entity["doc_id"]].append(entity)
    entity_map = dict(entities)
    output_path = lake.path("retrieval", "corpus", f"{args.run_id}.jsonl")
    count = 0
    with output_path.open("w", encoding="utf-8") as handle:
        docs = spark.read.json(str(lake.path("gold", "healthcare_documents", f"{args.run_id}.jsonl")))
        for row in docs.toJSON().toLocalIterator():
            doc = json.loads(row)
            for chunk in select_chunks(doc, entity_map.get(doc["doc_id"], [])):
                handle.write(json.dumps(chunk, sort_keys=True) + "\n")
                count += 1
    spark.stop()
    db.update_run(args.run_id, chunks_selected=count)
    db.event(args.run_id, "retrieval_selection", f"Selected {count} retrieval chunks")


if __name__ == "__main__":
    main()
