from __future__ import annotations

import argparse

from medintel.config import get_settings, require_cms_mcd_license
from medintel.r2_storage import LocalLake
from medintel.source_fetchers import parse_cms_mcd_current_archives


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="local-representative")
    parser.add_argument("--archive-run-id", default="cms-mcd-current")
    parser.add_argument("--max-articles", type=int, default=5000)
    parser.add_argument("--max-lcds", type=int, default=5000)
    parser.add_argument("--max-ncds", type=int, default=1000)
    parser.add_argument("--cms-license-accepted", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    require_cms_mcd_license(settings, args.cms_license_accepted)
    lake = LocalLake(settings)
    archive_dir = lake.path("raw", "cms_mcd_archives", args.archive_run_id, ".keep").parent
    output = lake.path("raw", "cms", f"{args.run_id}_cms.jsonl")
    count = parse_cms_mcd_current_archives(
        archive_dir,
        output,
        max_articles=args.max_articles,
        max_lcds=args.max_lcds,
        max_ncds=args.max_ncds,
    )
    print({
        "run_id": args.run_id,
        "archive_run_id": args.archive_run_id,
        "cms_documents": count,
        "output": str(output),
        "archive_dir": str(archive_dir),
    })


if __name__ == "__main__":
    main()
