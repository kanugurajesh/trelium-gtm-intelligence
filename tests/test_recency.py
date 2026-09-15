"""Recency: a claim that dates itself must be discounted for age, and the
C6 "all evidence fresh" bonus must require *all* dated evidence, not one
fresh item. Both rules were latent until the deeper-page pass hit a press
page whose 2015 headline scored as a live growth trigger (docs/FINDINGS.md,
finding C, fourth instance). Offline, no model calls (CLAUDE.md R13).
"""

from __future__ import annotations

from datetime import date

from trelium_gtm import extract as extract_mod
from trelium_gtm.extract import extract_claims, infer_dated_year
from trelium_gtm.models import Evidence, Fact
from trelium_gtm.scoring import score
from trelium_gtm.signals import (
    compute_evidence_age_months_max,
    compute_trigger_ages_months,
    derive_signals,
)
from trelium_gtm.taxonomy import SourceTier

AS_OF = date(2026, 9, 15)
RETRIEVED = "2026-09-15T00:00:00Z"


# ---- infer_dated_year -----------------------------------------------------

def test_infer_dated_year_uses_latest_year_in_quote():
    assert infer_dated_year("Founded in 1993; record growth in 2015.", RETRIEVED) == "2015-01-01"


def test_infer_dated_year_returns_none_without_a_year():
    assert infer_dated_year("For the past ten years we have grown.", RETRIEVED) is None


def test_infer_dated_year_ignores_future_years_and_non_year_numbers():
    assert infer_dated_year("Our 2030 vision; 2,024 SKUs; suite 2050.", RETRIEVED) is None
    assert infer_dated_year("Since 2024, ahead of our 2030 vision.", RETRIEVED) == "2024-01-01"


def test_infer_dated_year_ignores_digits_embedded_in_longer_numbers():
    assert infer_dated_year("Part number 120150 ships nationwide.", RETRIEVED) is None


# ---- extraction populates published_at from the quote --------------------

def test_extraction_dates_a_self_dating_quote(monkeypatch, tmp_path):
    snapshot = "ACME_TEST_SUPPLIER announces record growth in 2015. Open role: AP Clerk."
    payload = {
        "claims": [
            {
                "field": "trigger",
                "value": "GROWTH_HIGH",
                "statement": "ACME_TEST_SUPPLIER announced record growth in 2015.",
                "quote": "ACME_TEST_SUPPLIER announces record growth in 2015.",
                "model_confidence": "high",
            },
            {
                "field": "ops_hiring_role",
                "value": "AP Clerk",
                "statement": "ACME_TEST_SUPPLIER has an open AP Clerk role.",
                "quote": "Open role: AP Clerk.",
                "model_confidence": "high",
            },
        ]
    }
    monkeypatch.setattr(extract_mod, "_call_openai", lambda *a, **k: payload)
    outcome = extract_claims(
        source_url="https://acme-test-supplier.example/news",
        company_domain="acme-test-supplier.example",
        snapshot_text=snapshot,
        publisher="Company website",
        title="News",
        retrieved_at=RETRIEVED,
        snapshot_path="evidence/raw/src_test.txt",
        cache_dir=tmp_path / "cache",
    )
    by_quote = {e.quote: e for e in outcome.evidence}
    assert by_quote["ACME_TEST_SUPPLIER announces record growth in 2015."].published_at == "2015-01-01"
    assert by_quote["Open role: AP Clerk."].published_at is None


def test_extraction_keeps_an_explicit_page_publication_date(monkeypatch, tmp_path):
    payload = {
        "claims": [
            {
                "field": "trigger",
                "value": "GROWTH_HIGH",
                "statement": "Record growth in 2015.",
                "quote": "record growth in 2015",
                "model_confidence": "high",
            }
        ]
    }
    monkeypatch.setattr(extract_mod, "_call_openai", lambda *a, **k: payload)
    outcome = extract_claims(
        source_url="https://acme-test-supplier.example/news",
        company_domain="acme-test-supplier.example",
        snapshot_text="Posted 2016-02-01: record growth in 2015 announced.",
        publisher="Company website",
        title="News",
        retrieved_at=RETRIEVED,
        snapshot_path="evidence/raw/src_test.txt",
        cache_dir=tmp_path / "cache",
        published_at="2016-02-01",
    )
    assert outcome.evidence[0].published_at == "2016-02-01"


# ---- a decade-old growth headline scores zero trigger points -------------

def _ev(eid: str, url: str, quote: str, published_at: str | None) -> Evidence:
    return Evidence(
        id=eid,
        source_url=url,
        source_tier=SourceTier.COMPANY_PRIMARY,
        publisher="Company website",
        title="News",
        retrieved_at=RETRIEVED,
        published_at=published_at,
        snapshot_path="evidence/raw/src_test.txt",
        content_sha256="a" * 64,
        quote=quote,
        quote_offset=0,
    )


def _growth_fixture(published_at: str | None):
    evidence = [
        _ev("ev_seg", "https://acme-test-supplier.example", "a promotional products supplier", None),
        _ev("ev_growth", "https://acme-test-supplier.example/news", "record growth in 2015", published_at),
    ]
    facts = [
        Fact(
            id="fct_seg",
            statement="ACME_TEST_SUPPLIER is a promotional products supplier.",
            evidence_ids=["ev_seg"],
            field="segment",
            value="promotional_products_supplier",
        ),
        Fact(
            id="fct_growth",
            statement="ACME_TEST_SUPPLIER announced record growth.",
            evidence_ids=["ev_growth"],
            field="trigger",
            value="GROWTH_HIGH",
        ),
    ]
    return facts, evidence


def test_undated_growth_trigger_scores_full_weight():
    facts, evidence = _growth_fixture(None)
    signals = derive_signals(facts, evidence)
    ages = compute_trigger_ages_months(signals, AS_OF)
    result = score(signals, trigger_ages_months=ages)
    assert result.components["c5"] == 8


def test_decade_old_growth_trigger_scores_zero():
    facts, evidence = _growth_fixture("2015-01-01")
    signals = derive_signals(facts, evidence)
    ages = compute_trigger_ages_months(signals, AS_OF)
    assert all(age is not None and age > 36 for age in ages.values())
    result = score(signals, trigger_ages_months=ages)
    assert result.components["c5"] == 0


def test_growth_trigger_from_last_year_scores_full_weight():
    facts, evidence = _growth_fixture("2025-01-01")
    signals = derive_signals(facts, evidence)
    ages = compute_trigger_ages_months(signals, AS_OF)
    result = score(signals, trigger_ages_months=ages)
    assert result.components["c5"] == 8


# ---- C6 freshness bonus needs every item dated ---------------------------

def test_evidence_age_is_none_when_any_item_is_undated():
    _, evidence = _growth_fixture("2026-06-01")  # ev_seg is undated
    assert compute_evidence_age_months_max(evidence, AS_OF) is None


def test_evidence_age_is_the_oldest_item_when_all_are_dated():
    evidence = [
        _ev("ev_a", "https://acme-test-supplier.example", "fresh", "2026-06-01"),
        _ev("ev_b", "https://acme-test-supplier.example/news", "old", "2023-06-01"),
    ]
    assert compute_evidence_age_months_max(evidence, AS_OF) == 39


def test_evidence_age_is_none_for_no_evidence():
    assert compute_evidence_age_months_max([], AS_OF) is None
