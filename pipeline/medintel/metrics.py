from __future__ import annotations

from . import db


def stage(run_id: str, name: str, message: str) -> None:
    db.upsert_run(run_id, "running", name)
    db.event(run_id, name, message)
