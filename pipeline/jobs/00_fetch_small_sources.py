from __future__ import annotations

import argparse
import json

from medintel.config import get_settings, require_cms_mcd_license
from medintel.r2_storage import LocalLake
from medintel.source_fetchers import fetch_cms_mcd_articles, fetch_fda_labels, fetch_pubmed_abstracts


def _jsonl_count(path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                json.loads(line)
                count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="local-real-small")
    parser.add_argument("--cms-code", default="72148")
    parser.add_argument("--cms-limit", type=int, default=5)
    parser.add_argument("--fda-limit", type=int, default=3)
    parser.add_argument("--pubmed-limit", type=int, default=5)
    parser.add_argument("--cms-license-accepted", action="store_true")
    parser.add_argument("--force-refresh", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    require_cms_mcd_license(settings, args.cms_license_accepted)
    lake = LocalLake(settings)
    cms_out = lake.path("raw", "cms", f"{args.run_id}_cms.jsonl")
    fda_out = lake.path("raw", "fda", f"{args.run_id}_fda.jsonl")
    pubmed_out = lake.path("raw", "pubmed", f"{args.run_id}_pubmed.jsonl")
    if args.cms_limit <= 0:
        cms_count = _jsonl_count(cms_out)
    elif args.force_refresh or not cms_out.exists():
        cms_count = fetch_cms_mcd_articles(cms_out, args.cms_code, args.cms_limit)
    else:
        cms_count = _jsonl_count(cms_out)
    if args.fda_limit <= 0:
        fda_count = _jsonl_count(fda_out)
    elif args.force_refresh or not fda_out.exists():
        fda_count = fetch_fda_labels(fda_out, args.fda_limit)
    else:
        fda_count = _jsonl_count(fda_out)
    if args.pubmed_limit <= 0:
        pubmed_count = _jsonl_count(pubmed_out)
    elif args.force_refresh or not pubmed_out.exists():
        pubmed_count = fetch_pubmed_abstracts(pubmed_out, args.pubmed_limit)
    else:
        pubmed_count = _jsonl_count(pubmed_out)

    print({
        "cms": cms_count,
        "fda": fda_count,
        "pubmed": pubmed_count,
        "raw_root": str(lake.root / "raw"),
        "reused_existing": not args.force_refresh,
    })


if __name__ == "__main__":
    main()
