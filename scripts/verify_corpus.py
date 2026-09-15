"""Verify every committed brief against the committed evidence corpus.

For every Evidence item in every brief under output/, check
  E1: sha256(snapshot file) == content_sha256
  E2: snapshot[quote_offset : quote_offset + len(quote)] == quote
and, with --committed, the same two checks against the blob git has stored
for that snapshot (``git show HEAD:<path>``), which is what a fresh clone
would receive. The second check exists because the first one passed for
months while eleven committed blobs were wrong: git's line-ending
normalisation had rewritten CRLF snapshots to LF on the way into the
repository, so the working copy verified and a clean checkout would not.
`.gitattributes` now stores evidence/raw/** byte-for-byte.

Exit status is non-zero on any failure. No network, no model calls.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BRIEF_DIRS = ("output/briefs", "output/briefs_pass1_homepage", "output/negative_controls")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def committed_blob(path: str, ref: str) -> bytes | None:
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"], capture_output=True, cwd=REPO_ROOT
    )
    return result.stdout if result.returncode == 0 else None


def check(text: str, evidence: dict, label: str, failures: list[str]) -> None:
    if sha256_bytes(text.encode("utf-8")) != evidence["content_sha256"]:
        failures.append(f"E1 {label}: {evidence['snapshot_path']} hash mismatch")
        return
    start = evidence["quote_offset"]
    end = start + len(evidence["quote"])
    if text[start:end] != evidence["quote"]:
        failures.append(f"E2 {label}: {evidence['id']} quote not at offset {start} in {evidence['snapshot_path']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--committed", action="store_true", help="also verify against git blobs")
    parser.add_argument("--ref", default="HEAD", help="git ref for --committed (default HEAD)")
    args = parser.parse_args()

    failures: list[str] = []
    checked_items = 0
    checked_snapshots: set[str] = set()
    for d in BRIEF_DIRS:
        for brief_path in sorted((REPO_ROOT / d).glob("*.json")):
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            for ev in brief["evidence"]:
                checked_items += 1
                snap = REPO_ROOT / ev["snapshot_path"]
                if not snap.exists():
                    failures.append(f"E1 working copy: {ev['snapshot_path']} missing")
                    continue
                text = snap.read_bytes().decode("utf-8")
                check(text, ev, "working copy", failures)
                checked_snapshots.add(ev["snapshot_path"])
                if args.committed:
                    blob = committed_blob(ev["snapshot_path"], args.ref)
                    if blob is None:
                        failures.append(f"E1 {args.ref}: {ev['snapshot_path']} not in git")
                        continue
                    check(blob.decode("utf-8"), ev, args.ref, failures)

    print(
        f"evidence items checked: {checked_items}; distinct snapshots: {len(checked_snapshots)}; "
        f"failures: {len(failures)}"
        + (f" (also verified against {args.ref})" if args.committed else "")
    )
    for f in failures:
        print("  " + f)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
