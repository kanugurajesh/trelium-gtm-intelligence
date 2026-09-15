"""Content-addressed cache for LLM calls, committed to the repo.

The cache key is a hash of the exact prompt sent. A cache hit needs no API
key at all, which is what lets a reviewer clone the repo and reproduce the
whole pipeline's output offline (docs/PROJECT_SPEC.md architecture table).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def make_key(*parts: str) -> str:
    joined = "\x1f".join(parts)  # unit separator, unlikely to collide with content
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def get(key: str, cache_dir: Path) -> Any | None:
    path = cache_dir / f"{key}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def put(key: str, value: Any, cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{key}.json"
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
