from __future__ import annotations

import hashlib
from pathlib import Path


def source_id_for(path: Path, source_type: str) -> str:
    digest = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:12]
    return f"{source_type}-{digest}"
