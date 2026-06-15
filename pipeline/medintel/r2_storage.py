from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Iterable

from .config import Settings


class LocalLake:
    def __init__(self, settings: Settings):
        self.root = settings.local_data_root
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, *parts: str) -> Path:
        path = self.root.joinpath(*parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def list_files(self, prefix: str) -> list[Path]:
        base = self.root / prefix
        if not base.exists():
            return []
        return sorted(p for p in base.rglob("*") if p.is_file())

    def copy_into(self, source: Path, dest_prefix: str) -> Path:
        dest = self.path(dest_prefix, source.name)
        shutil.copyfile(source, dest)
        return dest


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
            count += 1
    return count
