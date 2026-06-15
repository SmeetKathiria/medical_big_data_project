from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any, Iterator

try:
    import psycopg
except ImportError:  # Local artifact-only mode can run before dependencies are installed.
    psycopg = None

from .config import get_settings


@contextmanager
def connect() -> Iterator[Any]:
    if psycopg is None:
        raise RuntimeError("psycopg is not installed")
    conn = psycopg.connect(get_settings().database_url)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def db_available() -> bool:
    try:
        with connect():
            return True
    except Exception:
        return False


def execute(sql: str, params: tuple[Any, ...] = ()) -> None:
    if not db_available():
        return
    with connect() as conn:
        conn.execute(sql, params)


def json_param(value: Any) -> str:
    return json.dumps(value)


def upsert_run(run_id: str, status: str, stage: str) -> None:
    execute(
        """
        INSERT INTO pipeline_runs (run_id, status, current_stage, started_at, updated_at)
        VALUES (%s, %s, %s, now(), now())
        ON CONFLICT (run_id) DO UPDATE SET
          status = EXCLUDED.status,
          current_stage = EXCLUDED.current_stage,
          updated_at = now()
        """,
        (run_id, status, stage),
    )


def update_run(run_id: str, **fields: Any) -> None:
    if not fields or not db_available():
        return
    assignments = ", ".join(f"{key} = %s" for key in fields)
    values = tuple(fields.values()) + (run_id,)
    with connect() as conn:
        conn.execute(f"UPDATE pipeline_runs SET {assignments}, updated_at = now() WHERE run_id = %s", values)


def event(run_id: str, stage: str, message: str, level: str = "info", metadata: dict | None = None) -> None:
    execute(
        "INSERT INTO pipeline_events (run_id, stage, level, message, metadata) VALUES (%s, %s, %s, %s, %s::jsonb)",
        (run_id, stage, level, message, json.dumps(metadata or {})),
    )
