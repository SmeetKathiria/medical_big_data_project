from __future__ import annotations

import argparse
import json

from medintel.config import get_settings
from medintel.r2_storage import LocalLake, read_jsonl


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="local-real-small")
    args = parser.parse_args()
    lake = LocalLake(get_settings())
    profiles = []
    for source_type in ["cms", "fda", "pubmed"]:
        rows = []
        for path in lake.list_files(f"raw/{source_type}"):
            if args.run_id in path.name:
                rows.extend(read_jsonl(path))
        keys = sorted({key for row in rows for key in row.keys()})
        profiles.append({
            "source_type": source_type,
            "documents": len(rows),
            "keys": keys,
            "example_titles": [row.get("title") for row in rows[:3]],
            "metadata_keys": sorted({key for row in rows for key in (row.get("metadata") or {}).keys()}),
        })
    out = lake.path("reports", "source_profiles", f"{args.run_id}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(profiles, indent=2), encoding="utf-8")
    print(json.dumps(profiles, indent=2))


if __name__ == "__main__":
    main()
