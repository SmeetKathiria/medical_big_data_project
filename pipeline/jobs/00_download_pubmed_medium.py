from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import struct
import urllib.request
from pathlib import Path
from typing import Any

from medintel.config import get_settings
from medintel.r2_storage import LocalLake, write_jsonl

PUBMED_BASELINE_URL = "https://ftp.ncbi.nlm.nih.gov/pubmed/baseline/"


def _pubmed_listing() -> list[dict[str, Any]]:
    html = urllib.request.urlopen(PUBMED_BASELINE_URL, timeout=60).read().decode("utf-8")
    pattern = re.compile(r'href="(?P<name>pubmed26n\d+\.xml\.gz)".*?(?P<size>[0-9.]+)(?P<unit>[KMG])', re.S)
    multiplier = {"K": 1024, "M": 1024**2, "G": 1024**3}
    rows = []
    for match in pattern.finditer(html):
        name = match.group("name")
        rows.append({
            "name": name,
            "url": f"{PUBMED_BASELINE_URL}{name}",
            "compressed_listing_bytes": int(float(match.group("size")) * multiplier[match.group("unit")]),
        })
    return rows


def _download(url: str, output: Path) -> dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    size = 0
    if not output.exists():
        request = urllib.request.Request(url, headers={"User-Agent": "MedIntel PubMed medium pipeline"})
        with urllib.request.urlopen(request, timeout=900) as response:
            with output.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
    else:
        with output.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                size += len(chunk)
    with output.open("rb") as handle:
        handle.seek(-4, 2)
        uncompressed_bytes = struct.unpack("<I", handle.read(4))[0]
    return {
        "path": str(output),
        "bytes": size,
        "uncompressed_bytes": uncompressed_bytes,
        "sha256": digest.hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="pubmed-medium-local")
    parser.add_argument("--target-gib", type=float, default=4.0)
    parser.add_argument("--max-files", type=int, default=24)
    args = parser.parse_args()

    lake = LocalLake(get_settings())
    output_dir = lake.path("raw", "pubmed_baseline_medium", args.run_id, ".keep").parent
    target_bytes = int(args.target_gib * 1024**3)
    total_uncompressed = 0
    total_compressed = 0
    records = []
    for row in _pubmed_listing()[: args.max_files]:
        output = output_dir / row["name"]
        record = {**row, **_download(row["url"], output)}
        records.append(record)
        total_compressed += int(record["bytes"])
        total_uncompressed += int(record["uncompressed_bytes"])
        if total_uncompressed >= target_bytes:
            break

    manifest = lake.path("raw", "pubmed_baseline_medium", f"{args.run_id}_manifest.jsonl")
    write_jsonl(manifest, records)
    summary = {
        "run_id": args.run_id,
        "files": len(records),
        "compressed_bytes": total_compressed,
        "uncompressed_bytes": total_uncompressed,
        "compressed_gib": round(total_compressed / 1024**3, 3),
        "uncompressed_gib": round(total_uncompressed / 1024**3, 3),
        "manifest": str(manifest),
        "archive_dir": str(output_dir),
    }
    summary_path = lake.path("reports", "pubmed_medium", f"{args.run_id}_download_summary.json")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
