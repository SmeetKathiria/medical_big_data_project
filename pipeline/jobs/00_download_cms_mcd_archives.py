from __future__ import annotations

import argparse

from medintel.config import get_settings, require_cms_mcd_license
from medintel.r2_storage import LocalLake, write_jsonl
from medintel.source_fetchers import CMS_MCD_DOWNLOADS, download_cms_mcd_archives


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="cms-mcd-full")
    parser.add_argument(
        "--dataset",
        action="append",
        choices=sorted(CMS_MCD_DOWNLOADS),
        help="CMS MCD package to download. Repeat to download multiple packages. Defaults to all official packages.",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--cms-license-accepted", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    require_cms_mcd_license(settings, args.cms_license_accepted)
    lake = LocalLake(settings)
    datasets = args.dataset or sorted(CMS_MCD_DOWNLOADS)
    archive_dir = lake.path("raw", "cms_mcd_archives", args.run_id, ".keep").parent
    records = download_cms_mcd_archives(archive_dir, datasets, args.force)
    manifest_path = lake.path("raw", "cms_mcd_archives", f"{args.run_id}_manifest.jsonl")
    write_jsonl(manifest_path, records)
    print({"datasets": datasets, "archives": len(records), "manifest": str(manifest_path)})


if __name__ == "__main__":
    main()
