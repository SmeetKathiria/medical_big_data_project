from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DataProfile:
    name: str
    run_id: str
    storage_mode: str
    pubmed_target_gib: float | None
    pubmed_max_files: int | None
    description: str


PROFILES = {
    "local-small": DataProfile(
        name="local-small",
        run_id="local-real-small",
        storage_mode="local",
        pubmed_target_gib=None,
        pubmed_max_files=None,
        description="Small real-source smoke test for local UI and retrieval iteration.",
    ),
    "local-representative": DataProfile(
        name="local-representative",
        run_id="local-representative",
        storage_mode="local",
        pubmed_target_gib=8.0,
        pubmed_max_files=64,
        description="5-10 GiB local real-data slice in the same lake format as cloud full runs.",
    ),
    "cloud-full": DataProfile(
        name="cloud-full",
        run_id="cloud-full",
        storage_mode="r2",
        pubmed_target_gib=None,
        pubmed_max_files=None,
        description="Full official source copy for R2, RunPod Spark processing, and Hetzner serving.",
    ),
}


def profile_for(name: str) -> DataProfile:
    try:
        return PROFILES[name]
    except KeyError as exc:
        allowed = ", ".join(sorted(PROFILES))
        raise ValueError(f"Unknown data profile '{name}'. Allowed: {allowed}") from exc
