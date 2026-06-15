from __future__ import annotations

import argparse
import json

from medintel.cms_parser import parse_cms
from medintel.config import get_settings
from medintel.fda_parser import parse_fda
from medintel.metrics import stage
from medintel.pubmed_parser import parse_pubmed
from medintel.r2_storage import LocalLake, write_jsonl
from medintel.spark import get_spark
from medintel import db

PARSERS = {"cms": parse_cms, "fda": parse_fda, "pubmed": parse_pubmed}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    lake = LocalLake(get_settings())
    stage(args.run_id, "normalize_sources", "Normalizing CMS, FDA, and PubMed records")
    spark = get_spark("medintel-normalize-sources")
    normalized_count = 0
    rejected_count = 0
    normalized_path = lake.path("silver", "normalized_documents", f"{args.run_id}.jsonl")
    rejected_path = lake.path("silver", "rejected_documents", f"{args.run_id}.jsonl")
    with normalized_path.open("w", encoding="utf-8") as normalized_out:
        with rejected_path.open("w", encoding="utf-8") as rejected_out:
            for source_type, parse in PARSERS.items():
                paths = [str(path) for path in lake.list_files(f"bronze/{source_type}/{args.run_id}")]
                if not paths:
                    continue
                for item in spark.read.json(paths).toJSON().toLocalIterator():
                    row = json.loads(item)
                    try:
                        normalized_out.write(json.dumps(parse(row).to_dict(), sort_keys=True) + "\n")
                        normalized_count += 1
                    except Exception as exc:
                        rejected_out.write(json.dumps({"source_type": source_type, "row": row, "error": str(exc)}, sort_keys=True) + "\n")
                        rejected_count += 1
    spark.stop()
    db.update_run(args.run_id, documents_read=normalized_count, documents_rejected=rejected_count)
    db.event(args.run_id, "normalize_sources", f"Normalized {normalized_count} documents")


if __name__ == "__main__":
    main()
