from __future__ import annotations

import argparse
from pathlib import Path

from medintel.config import get_settings, require_r2
from medintel.metrics import stage
from medintel.r2_storage import write_jsonl
from medintel.source_registry import source_id_for
from medintel import db


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--source-type", choices=["cms", "fda", "pubmed", "all"], required=True)
    parser.add_argument("--input-uri", required=True)
    parser.add_argument("--storage-mode", choices=["local", "r2"], default="local")
    args = parser.parse_args()

    settings = get_settings()
    if args.storage_mode == "r2":
        require_r2(settings)
    db.upsert_run(args.run_id, "running", "manifest")
    stage(args.run_id, "manifest", "Creating source manifest")

    input_root = Path(args.input_uri)
    source_types = ["cms", "fda", "pubmed"] if args.source_type == "all" else [args.source_type]
    entries = []
    for source_type in source_types:
        candidates = sorted((input_root / source_type).glob("*.jsonl"))
        expected_stem = f"{args.run_id}_{source_type}"
        run_candidates = [path for path in candidates if path.stem == expected_stem]
        for file_path in run_candidates or candidates:
            stat = file_path.stat()
            entry = {
                "source_id": source_id_for(file_path, source_type),
                "source_type": source_type,
                "file_uri": str(file_path),
                "file_size": stat.st_size,
                "version": file_path.stem,
                "effective_date": None,
                "status": "pending",
            }
            entries.append(entry)
            db.execute(
                """
                INSERT INTO healthcare_sources (source_id, source_type, name, source_uri, version)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (source_id) DO UPDATE SET source_uri = EXCLUDED.source_uri, version = EXCLUDED.version
                """,
                (entry["source_id"], source_type, file_path.name, str(file_path), entry["version"]),
            )

    write_jsonl(settings.local_data_root / "manifests" / f"{args.run_id}.jsonl", entries)
    db.update_run(args.run_id, total_bytes=sum(e["file_size"] for e in entries))
    db.event(args.run_id, "manifest", f"Manifest contains {len(entries)} files")


if __name__ == "__main__":
    main()
