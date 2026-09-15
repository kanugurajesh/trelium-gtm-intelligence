"""Content-addressed evidence snapshot storage.

Every fetched source is written to disk once, hashed, and indexed. The hash
is what makes the E1 invariant (docs/EVIDENCE_MODEL.md) checkable years later
even if the live page has changed or disappeared.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path


def compute_evidence_id(source_url: str, quote: str) -> str:
    """ev_<10 hex of sha1(url + quote)>, per EVIDENCE_MODEL.md section 2."""
    digest = hashlib.sha1(f"{source_url}\n{quote}".encode("utf-8")).hexdigest()
    return f"ev_{digest[:10]}"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class SnapshotWriteResult:
    snapshot_path: str
    content_sha256: str


def write_snapshot(text: str, snapshot_id: str, evidence_dir: Path) -> SnapshotWriteResult:
    """Write raw extracted text to evidence/raw/<snapshot_id>.txt.

    ``snapshot_id`` is a stable identifier for the *source page* (not the
    per-quote evidence id), so multiple quotes from one page share one
    snapshot file rather than duplicating the whole page per quote.
    """
    raw_dir = evidence_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{snapshot_id}.txt"
    path.write_text(text, encoding="utf-8", newline="\n")
    try:
        rel_path = str(path.relative_to(evidence_dir.parent)).replace("\\", "/")
    except ValueError:
        rel_path = str(path)
    return SnapshotWriteResult(
        snapshot_path=rel_path,
        content_sha256=sha256_text(text),
    )


def append_index_record(record: dict, evidence_dir: Path) -> None:
    index_path = evidence_dir / "index.jsonl"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


def load_index(evidence_dir: Path) -> list[dict]:
    index_path = evidence_dir / "index.jsonl"
    if not index_path.exists():
        return []
    records = []
    with index_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_snapshot_text(snapshot_path: str, evidence_dir: Path) -> str:
    path = Path(snapshot_path)
    if not path.is_absolute():
        # snapshot_path is stored relative to the repo root; evidence_dir's
        # parent is the repo root by convention.
        path = evidence_dir.parent / snapshot_path
    return path.read_text(encoding="utf-8")
