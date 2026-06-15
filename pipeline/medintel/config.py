from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "postgresql://medintel:medintel@localhost:5432/medintel")
    storage_mode: str = os.getenv("STORAGE_MODE", "local")
    local_data_root: Path = Path(os.getenv("LOCAL_DATA_ROOT", "data/lake"))
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key: str = os.getenv("QDRANT_API_KEY", "")
    embedding_model: str = os.getenv("LOCAL_EMBEDDING_MODEL", "hashing-local-384")
    r2_endpoint: str = os.getenv("R2_ENDPOINT", "")
    r2_bucket: str = os.getenv("R2_BUCKET", "")
    r2_access_key_id: str = os.getenv("R2_ACCESS_KEY_ID", "")
    r2_secret_access_key: str = os.getenv("R2_SECRET_ACCESS_KEY", "")
    cms_mcd_license_accepted: bool = os.getenv("CMS_MCD_LICENSE_ACCEPTED", "").lower() in {"1", "true", "yes", "accepted"}


def get_settings() -> Settings:
    return Settings()


def require_r2(settings: Settings) -> None:
    missing = [
        name
        for name, value in {
            "R2_ENDPOINT": settings.r2_endpoint,
            "R2_BUCKET": settings.r2_bucket,
            "R2_ACCESS_KEY_ID": settings.r2_access_key_id,
            "R2_SECRET_ACCESS_KEY": settings.r2_secret_access_key,
        }.items()
        if not value
    ]
    if missing:
        raise SystemExit(f"R2 mode requires: {', '.join(missing)}")


def require_cms_mcd_license(settings: Settings, accepted: bool = False) -> None:
    if settings.cms_mcd_license_accepted or accepted:
        return
    raise SystemExit(
        "CMS MCD downloads include CPT/CDT/UB-04 license terms. "
        "Set CMS_MCD_LICENSE_ACCEPTED=true or pass the job's license-accepted flag after confirming authorization."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-r2", action="store_true")
    args = parser.parse_args()
    if args.check_r2:
        require_r2(get_settings())
        print("R2 configuration is present.")


if __name__ == "__main__":
    main()
