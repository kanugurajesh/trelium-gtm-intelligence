"""Extraction tests. Per CLAUDE.md R13, none of these call the LLM: the
network/API boundary (_call_openai) is monkeypatched, so these tests assert
the verification and field-coercion logic that runs on whatever the model
returns — including when it returns something it shouldn't.
"""

from __future__ import annotations

import pytest

from trelium_gtm import extract as extract_mod
from trelium_gtm.extract import extract_claims

SNAPSHOT = (
    "Acme Test Distributor is a promotional products distributor serving "
    "clients nationwide. We reported $87M in revenue last year. "
    "Open role: Order Entry Specialist. Open role: Order Entry Specialist."
)


def _patch_openai(monkeypatch, payload: dict, call_counter: list | None = None):
    def fake_call(system_prompt, user_prompt, model):
        if call_counter is not None:
            call_counter.append(1)
        return payload

    monkeypatch.setattr(extract_mod, "_call_openai", fake_call)


def _run(monkeypatch, tmp_path, payload, **kwargs):
    _patch_openai(monkeypatch, payload)
    return extract_claims(
        source_url=kwargs.get("source_url", "https://acme-test.example/about"),
        company_domain="acme-test.example",
        snapshot_text=kwargs.get("snapshot_text", SNAPSHOT),
        publisher="Company website",
        title="About",
        retrieved_at="2026-01-01T00:00:00Z",
        snapshot_path="evidence/raw/src_test.txt",
        cache_dir=tmp_path / "cache",
    )


def test_accepts_claim_with_verbatim_unique_quote(monkeypatch, tmp_path):
    payload = {
        "claims": [
            {
                "field": "segment",
                "value": "promotional_products_distributor",
                "statement": "Acme Test Distributor is a promotional products distributor",
                "quote": "Acme Test Distributor is a promotional products distributor",
                "model_confidence": "high",
            }
        ]
    }
    outcome = _run(monkeypatch, tmp_path, payload)
    assert len(outcome.facts) == 1
    assert len(outcome.evidence) == 1
    assert outcome.facts[0].field == "segment"
    assert outcome.rejected == []


def test_rejects_paraphrased_quote_not_present_verbatim(monkeypatch, tmp_path):
    payload = {
        "claims": [
            {
                "field": "segment",
                "value": "promotional_products_distributor",
                "statement": "Acme is a distributor",
                "quote": "Acme is a nationwide promo products distributor",  # paraphrase
                "model_confidence": "high",
            }
        ]
    }
    outcome = _run(monkeypatch, tmp_path, payload)
    assert outcome.facts == []
    assert len(outcome.rejected) == 1
    assert "E2" in outcome.rejected[0]["reason"]


def test_rejects_ambiguous_quote_appearing_twice(monkeypatch, tmp_path):
    payload = {
        "claims": [
            {
                "field": "ops_hiring_role",
                "value": "Order Entry Specialist",
                "statement": "There is an open order entry role",
                "quote": "Open role: Order Entry Specialist.",  # appears twice in SNAPSHOT
                "model_confidence": "medium",
            }
        ]
    }
    outcome = _run(monkeypatch, tmp_path, payload)
    assert outcome.facts == []
    assert len(outcome.rejected) == 1


def test_unknown_segment_value_downgrades_to_other():
    from trelium_gtm.extract import _ALLOWED_FIELDS, _SEGMENT_VALUES

    assert "not_a_real_segment" not in _SEGMENT_VALUES
    assert "segment" in _ALLOWED_FIELDS


def test_unknown_segment_value_end_to_end_downgrades_to_other(monkeypatch, tmp_path):
    payload = {
        "claims": [
            {
                "field": "segment",
                "value": "space_tourism_company",  # not a real segment label
                "statement": "Acme is a space tourism company",
                "quote": "Acme Test Distributor is a promotional products distributor",
                "model_confidence": "low",
            }
        ]
    }
    outcome = _run(monkeypatch, tmp_path, payload)
    assert len(outcome.facts) == 1
    assert outcome.facts[0].field is None  # downgraded to "other" -> None on the Fact


def test_revenue_with_m_suffix_parsed_to_full_number(monkeypatch, tmp_path):
    payload = {
        "claims": [
            {
                "field": "revenue_usd",
                "value": "87M",
                "statement": "Acme reported $87M in revenue",
                "quote": "We reported $87M in revenue last year.",
                "model_confidence": "medium",
            }
        ]
    }
    outcome = _run(monkeypatch, tmp_path, payload)
    assert len(outcome.facts) == 1
    assert outcome.facts[0].field == "revenue_usd"
    assert outcome.facts[0].value == 87_000_000.0


def test_non_numeric_revenue_value_downgrades_to_other(monkeypatch, tmp_path):
    payload = {
        "claims": [
            {
                "field": "revenue_usd",
                "value": "a lot of money",
                "statement": "Acme reported strong revenue",
                "quote": "We reported $87M in revenue last year.",
                "model_confidence": "low",
            }
        ]
    }
    outcome = _run(monkeypatch, tmp_path, payload)
    assert len(outcome.facts) == 1
    assert outcome.facts[0].field is None


def test_inventory_value_misclassified_as_revenue_is_downgraded(monkeypatch, tmp_path):
    """Regression test for a real bug found during live testing (see
    docs/FINDINGS.md): gpt-4o-mini classified "$2.5 million dollars of
    blank soft goods" (inventory value) as revenue_usd even after the
    prompt was tightened to exclude inventory explicitly. The deterministic
    keyword backstop must catch what the prompt alone did not.
    """
    snapshot = "We have space to hold over $2.5 million dollars of blank soft goods."
    payload = {
        "claims": [
            {
                "field": "revenue_usd",
                "value": "2500000",
                "statement": "The company holds $2.5 million of blank soft goods.",
                "quote": "space to hold over $2.5 million dollars of blank soft goods",
                "model_confidence": "high",
            }
        ]
    }
    outcome = _run(monkeypatch, tmp_path, payload, snapshot_text=snapshot)
    assert len(outcome.facts) == 1
    assert outcome.facts[0].field is None  # downgraded to "other", not scored as scale


def test_missing_quote_or_statement_is_rejected(monkeypatch, tmp_path):
    payload = {"claims": [{"field": "segment", "value": "x", "statement": "", "quote": ""}]}
    outcome = _run(monkeypatch, tmp_path, payload)
    assert outcome.facts == []
    assert len(outcome.rejected) == 1


def test_cache_hit_avoids_second_api_call(monkeypatch, tmp_path):
    call_counter: list = []
    payload = {"claims": []}
    _patch_openai(monkeypatch, payload, call_counter)

    kwargs = dict(
        source_url="https://acme-test.example/about",
        company_domain="acme-test.example",
        snapshot_text=SNAPSHOT,
        publisher="Company website",
        title="About",
        retrieved_at="2026-01-01T00:00:00Z",
        snapshot_path="evidence/raw/src_test.txt",
        cache_dir=tmp_path / "cache",
    )
    extract_claims(**kwargs)
    extract_claims(**kwargs)
    assert len(call_counter) == 1


def test_rejection_rate_computed_correctly(monkeypatch, tmp_path):
    payload = {
        "claims": [
            {
                "field": "segment",
                "value": "promotional_products_distributor",
                "statement": "ok claim",
                "quote": "Acme Test Distributor is a promotional products distributor",
            },
            {
                "field": "segment",
                "value": "x",
                "statement": "bad claim",
                "quote": "this text does not appear anywhere in the snapshot",
            },
        ]
    }
    outcome = _run(monkeypatch, tmp_path, payload)
    assert outcome.raw_claims_count == 2
    assert len(outcome.rejected) == 1
    assert outcome.rejection_rate == 0.5
