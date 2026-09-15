"""Phase 2 exit tests: E1 hash check, E2 substring-at-offset check, tier
assignment, domain independence. This is the layer that makes fabrication
structurally rejected rather than merely discouraged.
"""

from __future__ import annotations

from trelium_gtm.evidence.store import compute_evidence_id, sha256_text
from trelium_gtm.evidence.verify import (
    classify_source_tier,
    find_quote_offset,
    independent_domain_count,
    registrable_domain,
    verify_evidence,
    verify_hash,
    verify_quote,
)
from trelium_gtm.models import Evidence
from trelium_gtm.taxonomy import SourceTier

SNAPSHOT = (
    "Stran Promotional Solutions is a leading distributor of branded "
    "merchandise. We process thousands of purchase orders every month "
    "across our SAGE and NetSuite systems."
)


def make_evidence(quote: str, offset: int, sha: str | None = None) -> Evidence:
    return Evidence(
        id=compute_evidence_id("https://stran.com/about", quote),
        source_url="https://stran.com/about",
        source_tier=SourceTier.COMPANY_PRIMARY,
        publisher="Company website",
        title="About",
        retrieved_at="2026-01-01T00:00:00Z",
        snapshot_path="evidence/raw/ev_test.txt",
        content_sha256=sha or sha256_text(SNAPSHOT),
        quote=quote,
        quote_offset=offset,
    )


def test_e1_hash_matches_valid_snapshot():
    ev = make_evidence("Stran Promotional Solutions", 0)
    assert verify_hash(ev, SNAPSHOT).ok


def test_e1_hash_fails_on_tampered_snapshot():
    ev = make_evidence("Stran Promotional Solutions", 0)
    tampered = SNAPSHOT + " EXTRA TEXT NOT IN ORIGINAL"
    result = verify_hash(ev, tampered)
    assert not result.ok
    assert "E1" in result.reason


def test_e2_substring_check_passes_for_exact_verbatim_quote():
    quote = "is a leading distributor of branded merchandise"
    offset = SNAPSHOT.index(quote)
    ev = make_evidence(quote, offset)
    assert verify_quote(ev, SNAPSHOT).ok


def test_e2_fails_for_paraphrased_quote_not_present_verbatim():
    """The core anti-fabrication guarantee: a paraphrase is not a substring."""
    paraphrase = "is a major branded merchandise supplier"  # not literally in SNAPSHOT
    ev = make_evidence(paraphrase, 0)
    result = verify_quote(ev, SNAPSHOT)
    assert not result.ok
    assert "E2" in result.reason


def test_e2_fails_when_offset_points_at_wrong_span():
    quote = "SAGE and NetSuite"
    correct_offset = SNAPSHOT.index(quote)
    ev = make_evidence(quote, correct_offset + 1)  # off by one
    result = verify_quote(ev, SNAPSHOT)
    assert not result.ok


def test_e2_fails_when_offset_out_of_bounds():
    ev = make_evidence("anything", len(SNAPSHOT) + 10)
    result = verify_quote(ev, SNAPSHOT)
    assert not result.ok
    assert "out of bounds" in result.reason


def test_verify_evidence_short_circuits_on_hash_failure():
    ev = make_evidence("Stran Promotional Solutions", 0, sha="0" * 64)
    result = verify_evidence(ev, SNAPSHOT)
    assert not result.ok
    assert "E1" in result.reason


def test_verify_evidence_passes_end_to_end():
    quote = "thousands of purchase orders every month"
    offset = SNAPSHOT.index(quote)
    ev = make_evidence(quote, offset)
    assert verify_evidence(ev, SNAPSHOT).ok


def test_find_quote_offset_unique_occurrence():
    offset = find_quote_offset(SNAPSHOT, "SAGE and NetSuite")
    assert offset == SNAPSHOT.index("SAGE and NetSuite")


def test_find_quote_offset_returns_none_when_absent():
    assert find_quote_offset(SNAPSHOT, "not present anywhere") is None


def test_find_quote_offset_returns_none_when_ambiguous():
    text = "order order order"
    assert find_quote_offset(text, "order") is None


def test_registrable_domain_strips_www_and_path():
    assert registrable_domain("https://www.stran.com/about/us") == "stran.com"
    assert registrable_domain("stran.com") == "stran.com"


def test_classify_source_tier_company_primary():
    assert classify_source_tier("https://stran.com/about", "stran.com") == SourceTier.COMPANY_PRIMARY


def test_classify_source_tier_industry_association():
    assert (
        classify_source_tier("https://www.ppai.org/media/ppai-100/", "stran.com")
        == SourceTier.INDUSTRY_ASSOCIATION
    )


def test_classify_source_tier_job_posting():
    assert (
        classify_source_tier("https://www.indeed.com/jobs?q=order+entry", "stran.com")
        == SourceTier.JOB_POSTING
    )


def test_classify_source_tier_executive_content():
    assert (
        classify_source_tier(
            "https://www.linkedin.com/posts/someone_activity-123", "stran.com"
        )
        == SourceTier.EXECUTIVE_PUBLIC_CONTENT
    )


def test_classify_source_tier_falls_back_to_third_party():
    assert (
        classify_source_tier("https://localbusinessjournal.example/stran-grows", "stran.com")
        == SourceTier.THIRD_PARTY_REPORTING
    )


def test_independent_domain_count_dedupes_same_domain():
    evs = [
        make_evidence("a", 0),
        make_evidence("b", 0).model_copy(update={"source_url": "https://stran.com/careers"}),
    ]
    assert independent_domain_count(evs) == 1


def test_independent_domain_count_counts_distinct_domains():
    evs = [
        make_evidence("a", 0),
        make_evidence("b", 0).model_copy(update={"source_url": "https://www.ppai.org/media/ppai-100/"}),
    ]
    assert independent_domain_count(evs) == 2
