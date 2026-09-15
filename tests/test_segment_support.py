"""A segment claim must quote the role word it asserts. Found by auditing the
deeper-page pass: every inaccurate fact in the top five briefs was a segment
label attached to a quote that never said "supplier" or "distributor"
(docs/VALIDATION.md V3). Offline (R13).
"""

from __future__ import annotations

import pytest

from trelium_gtm import extract as extract_mod
from trelium_gtm.extract import extract_claims

SNAPSHOT = (
    "Your business is unique, so we offer several ways to connect with you. "
    "Promotional Product Supplier & Custom Swag Company | Acme. "
    "Acme is the largest promotional merchandise distributor in the U.S. "
    "We are a full-service screen printing and embroidery shop. "
    "Acme LLP is a law firm serving clients nationwide."
)


def _run(monkeypatch, tmp_path, value, quote):
    claim = {
        "field": "segment",
        "value": value,
        "statement": f"Acme is a {value}.",
        "quote": quote,
        "model_confidence": "high",
    }
    monkeypatch.setattr(extract_mod, "_call_openai", lambda *a, **k: {"claims": [claim]})
    outcome = extract_claims(
        source_url="https://acme-test.example/about",
        company_domain="acme-test.example",
        snapshot_text=SNAPSHOT,
        publisher="Company website",
        title="About",
        retrieved_at="2026-09-15T00:00:00Z",
        snapshot_path="evidence/raw/src_test.txt",
        cache_dir=tmp_path / "cache",
    )
    assert len(outcome.facts) == 1  # verbatim, so it is kept as a fact either way
    return outcome.facts[0]


@pytest.mark.parametrize(
    "value, quote",
    [
        ("promotional_products_supplier", "Promotional Product Supplier & Custom Swag Company | Acme."),
        ("promotional_products_distributor", "Acme is the largest promotional merchandise distributor in the U.S."),
        ("decorator_print_shop", "We are a full-service screen printing and embroidery shop."),
    ],
)
def test_segment_claim_that_quotes_its_role_word_is_kept(monkeypatch, tmp_path, value, quote):
    fact = _run(monkeypatch, tmp_path, value, quote)
    assert fact.field == "segment"
    assert fact.value == value


@pytest.mark.parametrize(
    "value, quote",
    [
        ("promotional_products_supplier", "Your business is unique, so we offer several ways to connect with you."),
        ("promotional_products_distributor", "Promotional Product Supplier & Custom Swag Company | Acme."),
        ("decorator_print_shop", "Acme is the largest promotional merchandise distributor in the U.S."),
    ],
)
def test_segment_claim_without_its_role_word_is_downgraded(monkeypatch, tmp_path, value, quote):
    fact = _run(monkeypatch, tmp_path, value, quote)
    assert fact.field is None
    assert fact.value is None


def test_exclusion_labels_are_not_guarded(monkeypatch, tmp_path):
    fact = _run(monkeypatch, tmp_path, "out_of_icp", "Acme LLP is a law firm serving clients nationwide.")
    assert fact.field == "segment"
    assert fact.value == "out_of_icp"
