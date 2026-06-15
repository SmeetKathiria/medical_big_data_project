from __future__ import annotations

import argparse
import json
from pathlib import Path

from medintel.config import get_settings
from medintel.r2_storage import LocalLake
from medintel.spark import get_spark


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="pubmed-medium-local")
    args = parser.parse_args()

    lake = LocalLake(get_settings())
    manifest_path = lake.path("raw", "pubmed_baseline_medium", f"{args.run_id}_manifest.jsonl")
    archives = []
    with manifest_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                archives.append(json.loads(line))
    if not archives:
        raise SystemExit(f"No PubMed archives found in {manifest_path}")

    paths = [record["path"] for record in archives]
    spark = get_spark("medintel-pubmed-medium")
    lines = spark.sparkContext.textFile(",".join(paths), minPartitions=max(len(paths) * 2, 8))
    non_empty = lines.filter(lambda line: bool(line.strip()))
    report = {
        "run_id": args.run_id,
        "input_files": len(paths),
        "compressed_bytes": sum(int(record["bytes"]) for record in archives),
        "uncompressed_bytes_manifest": sum(int(record["uncompressed_bytes"]) for record in archives),
        "spark_lines": non_empty.count(),
        "spark_text_bytes": lines.map(lambda line: len(line.encode("utf-8")) + 1).sum(),
        "pubmed_article_start_tags": lines.filter(lambda line: "<PubmedArticle>" in line).count(),
        "pmid_lines": lines.filter(lambda line: "<PMID" in line).count(),
    }
    report["compressed_gib"] = round(report["compressed_bytes"] / 1024**3, 3)
    report["uncompressed_gib_manifest"] = round(report["uncompressed_bytes_manifest"] / 1024**3, 3)
    report["spark_text_gib"] = round(report["spark_text_bytes"] / 1024**3, 3)
    spark.stop()

    out = lake.path("reports", "pubmed_medium", f"{args.run_id}_spark_report.json")
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
