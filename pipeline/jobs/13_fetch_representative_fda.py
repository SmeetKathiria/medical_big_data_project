from __future__ import annotations

import argparse

from medintel.config import get_settings
from medintel.r2_storage import LocalLake
from medintel.source_fetchers import fetch_fda_representative_labels


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="local-representative")
    parser.add_argument("--per-query-limit", type=int, default=25)
    parser.add_argument("--total-limit", type=int, default=500)
    parser.add_argument("--max-text-chars", type=int, default=12000)
    args = parser.parse_args()

    settings = get_settings()
    lake = LocalLake(settings)
    output = lake.path("raw", "fda", f"{args.run_id}_fda.jsonl")
    count = fetch_fda_representative_labels(
        output,
        per_query_limit=args.per_query_limit,
        total_limit=args.total_limit,
        max_text_chars=args.max_text_chars,
    )
    print({
        "run_id": args.run_id,
        "fda_documents": count,
        "output": str(output),
        "per_query_limit": args.per_query_limit,
        "total_limit": args.total_limit,
    })


if __name__ == "__main__":
    main()
