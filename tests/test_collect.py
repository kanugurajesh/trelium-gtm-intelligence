"""Collection-layer tests: link discovery is a pure function of HTML, and
snapshot storage must never overwrite a page an earlier brief cites
(E1 preservation across collection passes). No network: the HTTP client is
an httpx.MockTransport and robots.txt is monkeypatched (CLAUDE.md R13).
"""

from __future__ import annotations

from datetime import date

import httpx

from trelium_gtm import collect as collect_mod
from trelium_gtm.collect import (
    CollectResult,
    collect_source,
    discover_links,
    html_to_text,
    snapshot_id_for,
)
from trelium_gtm.extract import ExtractionOutcome
from trelium_gtm.pipeline import SourceSpec, run_account

BASE = "https://acme-test-distributor.com"

NAV_HTML = """
<html><body>
<a href="/rapid-quote">Rapid quote</a>
<a href="/editorial">Editorial</a>
<a href="/integrations">Integrations</a>
<a href="/Company?display=AboutUs">About</a>
<a href="/about-us">About us</a>
<a href="https://other-domain.example/about">External about</a>
<a href="/catalog/brochure.pdf">Brochure</a>
<a href="/hubfs/module_Services_Slider.min.css" rel="stylesheet">CSS</a>
<a href="/assets/services-widget.js">JS</a>
<a href="mailto:ops@acme-test-distributor.com">Mail</a>
<a href="/careers#openings">Careers</a>
<a href="/careers">Careers again</a>
<a href="/news/press-release-1">News</a>
</body></html>
"""


def test_discover_links_matches_path_words_by_prefix_not_substring():
    # "api" must not match "/rapid-quote": a keyword has to start a path word.
    assert discover_links(NAV_HTML, BASE, ("api",)) == []
    assert discover_links(NAV_HTML, BASE, ("integrat",)) == [f"{BASE}/integrations"]
    # Prefix matching is deliberate, so a keyword that is itself a common
    # prefix ("edi" -> "editorial") does match; discovery keywords in
    # cli.DISCOVERY_GROUPS are chosen to avoid that.
    assert discover_links(NAV_HTML, BASE, ("edi",)) == [f"{BASE}/editorial"]


def test_discover_links_matches_query_string_words_and_respects_max_links():
    found = discover_links(NAV_HTML, BASE, ("about",), max_links=5)
    assert found == [f"{BASE}/Company?display=AboutUs", f"{BASE}/about-us"]
    assert discover_links(NAV_HTML, BASE, ("about",), max_links=1) == [
        f"{BASE}/Company?display=AboutUs"
    ]


def test_discover_links_drops_external_non_page_and_non_http_targets_and_dedupes():
    assert discover_links(NAV_HTML, BASE, ("brochure", "mail")) == []
    # a stylesheet or script whose path happens to contain a keyword is not a page
    assert discover_links(NAV_HTML, BASE, ("service",)) == []
    assert discover_links(NAV_HTML, BASE, ("about",), max_links=10) == [
        f"{BASE}/Company?display=AboutUs",
        f"{BASE}/about-us",
    ]
    # fragment stripped, then the duplicate URL is returned once
    assert discover_links(NAV_HTML, BASE, ("career",), max_links=10) == [f"{BASE}/careers"]


def test_discover_links_is_document_ordered_and_deterministic():
    first = discover_links(NAV_HTML, BASE, ("news", "career", "about"), max_links=10)
    second = discover_links(NAV_HTML, BASE, ("news", "career", "about"), max_links=10)
    assert first == second
    assert first[0] == f"{BASE}/Company?display=AboutUs"


def test_html_to_text_drops_script_and_style():
    text = html_to_text("<p>Hello</p><script>var x = 1;</script><style>p{}</style><p>World</p>")
    assert "var x" not in text
    assert "p{}" not in text
    assert "Hello" in text and "World" in text


def test_snapshot_id_is_content_addressed():
    a = snapshot_id_for(f"{BASE}/about", "version one")
    b = snapshot_id_for(f"{BASE}/about", "version two")
    c = snapshot_id_for(f"{BASE}/about", "version one")
    assert a == c
    assert a != b
    # same page prefix, different content suffix
    assert a.rsplit("_", 1)[0] == b.rsplit("_", 1)[0]
    assert a.startswith("src_")


def _client_returning(body: str) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=body, headers={"content-type": "text/html"})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_recollecting_a_changed_page_never_overwrites_the_earlier_snapshot(monkeypatch, tmp_path):
    monkeypatch.setattr(collect_mod, "robots_allowed", lambda *a, **k: True)
    evidence_dir = tmp_path / "evidence"
    url = f"{BASE}/about"

    first = collect_source(url, evidence_dir, client=_client_returning("<p>Founded 1990.</p>"))
    second = collect_source(url, evidence_dir, client=_client_returning("<p>Founded 1990. Acquired 2025.</p>"))

    assert first.ok and second.ok
    assert first.snapshot_id != second.snapshot_id
    first_file = evidence_dir / "raw" / f"{first.snapshot_id}.txt"
    second_file = evidence_dir / "raw" / f"{second.snapshot_id}.txt"
    assert first_file.read_text(encoding="utf-8") == "Founded 1990."
    assert second_file.read_text(encoding="utf-8") == "Founded 1990. Acquired 2025."
    # E1 for the first brief still holds after the second collection pass.
    assert collect_mod.sha256_text(first_file.read_text(encoding="utf-8")) == first.content_sha256


def test_recollecting_an_unchanged_page_reuses_the_same_snapshot(monkeypatch, tmp_path):
    monkeypatch.setattr(collect_mod, "robots_allowed", lambda *a, **k: True)
    evidence_dir = tmp_path / "evidence"
    url = f"{BASE}/about"
    first = collect_source(url, evidence_dir, client=_client_returning("<p>Same.</p>"))
    second = collect_source(url, evidence_dir, client=_client_returning("<p>Same.</p>"))
    assert first.snapshot_id == second.snapshot_id
    assert len(list((evidence_dir / "raw").iterdir())) == 1


def test_collect_source_blocked_by_robots_is_a_recorded_gap(monkeypatch, tmp_path):
    monkeypatch.setattr(collect_mod, "robots_allowed", lambda *a, **k: False)
    result = collect_source(f"{BASE}/careers", tmp_path / "evidence")
    assert result.ok is False
    assert result.blocked_by_robots is True
    assert "robots" in (result.error or "")
    assert not (tmp_path / "evidence").exists()


def test_run_account_uses_prefetched_source_without_a_second_fetch(monkeypatch, tmp_path):
    def _must_not_fetch(url, evidence_dir, **kwargs):
        raise AssertionError(f"collect_source called for prefetched url {url}")

    def _fake_extract(**kwargs):
        return ExtractionOutcome(facts=[], evidence=[], rejected=[], raw_claims_count=0)

    monkeypatch.setattr("trelium_gtm.pipeline.collect_source", _must_not_fetch)
    monkeypatch.setattr("trelium_gtm.pipeline.extract_claims", _fake_extract)

    prefetched = CollectResult(
        ok=True,
        url=BASE,
        snapshot_id="src_test_deadbeef",
        snapshot_path="evidence/raw/src_test_deadbeef.txt",
        content_sha256="a" * 64,
        text="ACME_TEST_DISTRIBUTOR home page",
    )
    report = run_account(
        company="ACME_TEST_DISTRIBUTOR",
        domain="acme-test-distributor.com",
        sources=[SourceSpec(url=BASE, publisher="Company website", title="Home", prefetched=prefetched)],
        evidence_dir=tmp_path / "evidence",
        cache_dir=tmp_path / "cache",
        as_of=date(2026, 9, 15),
    )
    assert report.sources_collected == 1
    assert report.collection_errors == []
    # the page was read and yielded nothing: that is a published gap, not silence
    assert f"Read {BASE}: no extractable claims" in report.brief.research_gaps


def test_run_account_records_a_failed_prefetched_source_as_a_gap(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "trelium_gtm.pipeline.extract_claims",
        lambda **kwargs: ExtractionOutcome(facts=[], evidence=[], rejected=[], raw_claims_count=0),
    )
    failed = CollectResult(ok=False, url=BASE, snapshot_id="src_x", error="Blocked by robots.txt")
    report = run_account(
        company="ACME_TEST_DISTRIBUTOR",
        domain="acme-test-distributor.com",
        sources=[SourceSpec(url=BASE, publisher="Company website", title="Home", prefetched=failed)],
        evidence_dir=tmp_path / "evidence",
        cache_dir=tmp_path / "cache",
        as_of=date(2026, 9, 15),
    )
    assert report.sources_collected == 0
    assert report.collection_errors == [f"Failed to collect {BASE}: Blocked by robots.txt"]
    assert report.brief.score.status == "INSUFFICIENT_EVIDENCE"
