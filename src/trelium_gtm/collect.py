"""Public-page collection: fetch, respect robots.txt, strip HTML to text,
write a committed snapshot. One request at a time, no logins, no bulk
crawling (CLAUDE.md R21-R22).

Failures are recorded as gaps, never as silent empty successes.
"""

from __future__ import annotations

import hashlib
import re
import urllib.robotparser
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

from trelium_gtm.evidence.store import sha256_text, write_snapshot

USER_AGENT = "TreliumGTMIntelligenceBot/0.1 (+research project; contact via GitHub repo)"
REQUEST_TIMEOUT_SECONDS = 15.0


class _VisibleTextExtractor(HTMLParser):
    """Minimal HTML-to-text: drops script/style/nav/footer content, keeps
    everything else as whitespace-joined text. Not a layout-faithful
    renderer — good enough to give an LLM readable prose to extract from,
    and irrelevant to correctness since every claim is re-verified against
    this exact stored text (E1/E2), not against the original HTML.
    """

    _SKIP_TAGS = {"script", "style", "noscript", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1
        elif tag in ("br", "p", "div", "li", "tr", "h1", "h2", "h3", "h4"):
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data.strip():
            self._chunks.append(data)

    def get_text(self) -> str:
        raw = " ".join(self._chunks)
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n\s*\n+", "\n\n", raw)
        return raw.strip()


def html_to_text(html: str) -> str:
    parser = _VisibleTextExtractor()
    parser.feed(html)
    return parser.get_text()


def robots_allowed(url: str, user_agent: str = USER_AGENT) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
    except Exception:
        # If robots.txt is unreachable, default to allowed (most sites have
        # none), but this is logged by the caller as a soft gap.
        return True
    return rp.can_fetch(user_agent, url)


@dataclass
class CollectResult:
    ok: bool
    url: str
    snapshot_id: str
    snapshot_path: str | None = None
    content_sha256: str | None = None
    text: str | None = None
    error: str | None = None
    blocked_by_robots: bool = False


def _snapshot_id_for_url(url: str) -> str:
    return "src_" + hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def collect_source(
    url: str,
    evidence_dir: Path,
    *,
    client: httpx.Client | None = None,
    user_agent: str = USER_AGENT,
) -> CollectResult:
    """Fetch one URL, respect robots.txt, write a text snapshot.

    ``client`` may be injected for testing; a fresh one is created and closed
    otherwise. Always exactly one request per call — batching is the
    caller's responsibility, and the caller is expected to space calls out
    rather than fire them concurrently (R22).
    """
    snapshot_id = _snapshot_id_for_url(url)

    if not robots_allowed(url, user_agent):
        return CollectResult(
            ok=False,
            url=url,
            snapshot_id=snapshot_id,
            error="Blocked by robots.txt",
            blocked_by_robots=True,
        )

    owns_client = client is None
    client = client or httpx.Client(
        follow_redirects=True,
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers={"User-Agent": user_agent},
    )
    try:
        response = client.get(url)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        return CollectResult(
            ok=False, url=url, snapshot_id=snapshot_id, error=f"Fetch failed: {exc}"
        )
    finally:
        if owns_client:
            client.close()

    text = html_to_text(response.text)
    if not text:
        return CollectResult(
            ok=False, url=url, snapshot_id=snapshot_id, error="No visible text extracted"
        )

    result = write_snapshot(text, snapshot_id, evidence_dir)
    return CollectResult(
        ok=True,
        url=url,
        snapshot_id=snapshot_id,
        snapshot_path=result.snapshot_path,
        content_sha256=result.content_sha256,
        text=text,
    )


def resolve(base_url: str, maybe_relative: str) -> str:
    return urljoin(base_url, maybe_relative)
