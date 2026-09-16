"""Re-check the hand-research quotes in docs/ACCOUNT_NOTES.md against their live pages.

The pipeline verifies every fact against a committed snapshot (E1/E2). The hand research in
docs/ACCOUNT_NOTES.md was done by a person, not the pipeline, so this script holds it to the
nearest equivalent standard it can: one request per page, robots.txt honoured, a descriptive
user agent, and every quoted string must appear verbatim in the page text after whitespace and
typographic-quote normalisation.

Usage:  python scripts/verify_hand_quotes.py [--save DIR]

Prints one line per source and one per quote (OK / DUP / MISSING). A source whose robots.txt
disallows automated fetching is reported as SKIPPED_ROBOTS and its quotes stay unverified by
this script; open the URL in a browser instead. No network access is needed by the tests; this
script is a one-off driver, not part of the pipeline or the CLI (CLAUDE.md R17, R21, R22).
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.robotparser
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
QUOTES = REPO_ROOT / "data" / "hand_research_quotes.json"
UA = "trelium-gtm-intelligence hand-research/0.1 (unaffiliated application project)"
DELAY_SECONDS = 1.0

_TYPOGRAPHIC = (
    ("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'),
    ("®", ""), ("–", "-"), ("—", "-"), (" ", " "),
)


def normalise(text: str) -> str:
    text = html.unescape(text)
    for src, dst in _TYPOGRAPHIC:
        text = text.replace(src, dst)
    return re.sub(r"\s+", " ", text).strip()


def strip_html(page: str) -> str:
    page = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", page)
    page = re.sub(r"(?s)<[^>]+>", " ", page)
    return normalise(page)


def robots_allows(url: str, cache: dict[str, urllib.robotparser.RobotFileParser]) -> bool:
    parts = urllib.parse.urlparse(url)
    base = f"{parts.scheme}://{parts.netloc}"
    if base not in cache:
        parser = urllib.robotparser.RobotFileParser()
        try:
            resp = httpx.get(base + "/robots.txt", headers={"User-Agent": UA}, timeout=20, follow_redirects=True)
            parser.parse(resp.text.splitlines() if resp.status_code == 200 else [])
        except httpx.HTTPError:
            parser.parse([])
        cache[base] = parser
    return cache[base].can_fetch("*", url)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--save", help="Directory to save fetched page text into, for inspection")
    args = ap.parse_args(argv)
    save_dir = Path(args.save) if args.save else None
    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)

    items = json.loads(QUOTES.read_text(encoding="utf-8"))
    robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}
    missing = 0
    unverified = 0
    for item in items:
        url = item["url"]
        if not robots_allows(url, robots_cache):
            status = "SKIPPED_ROBOTS"
            text = None
        else:
            time.sleep(DELAY_SECONDS)
            try:
                resp = httpx.get(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"}, timeout=40, follow_redirects=True)
                status = f"HTTP {resp.status_code}"
                text = strip_html(resp.text) if resp.status_code == 200 else None
            except httpx.HTTPError as exc:
                status = f"ERROR {type(exc).__name__}"
                text = None
        print(f"{item['id']:5} {status:16} {url}")
        if text is None:
            unverified += len(item["quotes"])
            continue
        if save_dir:
            (save_dir / f"{item['id']}.txt").write_text(text, encoding="utf-8")
        for quote in item["quotes"]:
            count = text.count(normalise(quote))
            tag = "OK " if count == 1 else ("DUP" if count > 1 else "MISSING")
            if count == 0:
                missing += 1
            print(f"      {tag} x{count}  {quote[:100]}")
    print(f"\n{missing} missing, {unverified} not verifiable by script (robots or fetch failure)")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
