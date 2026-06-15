from __future__ import annotations

import argparse
from pathlib import Path

from medintel.config import get_settings
from medintel.metrics import stage
from medintel.r2_storage import LocalLake, read_jsonl
from medintel import db


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    settings = get_settings()
    lake = LocalLake(settings)
    stage(args.run_id, "bronze_ingest", "Copying raw JSONL into bronze layer")

    manifest = settings.local_data_root / "manifests" / f"{args.run_id}.jsonl"
    rows = read_jsonl(manifest)
    docs_read = 0
    processed_bytes = 0
    for entry in rows:
        source = Path(entry["file_uri"])
        out = lake.path("bronze", entry["source_type"], args.run_id, source.name)
        out.parent.mkdir(parents=True, exist_ok=True)
        with source.open("r", encoding="utf-8") as src:
            with out.open("w", encoding="utf-8") as dest:
                for line in src:
                    if line.strip():
                        docs_read += 1
                    dest.write(line)
        processed_bytes += entry["file_size"]
    db.update_run(args.run_id, documents_read=docs_read, processed_bytes=processed_bytes)
    db.event(args.run_id, "bronze_ingest", f"Read {docs_read} source records")


if __name__ == "__main__":
    main()
