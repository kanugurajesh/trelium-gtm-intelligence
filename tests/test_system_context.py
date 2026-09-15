"""A system named on a page is not necessarily a system the company runs.
Found on the deeper-page pass: a distributor's technology page listing the
procurement systems its customers can punch out from scored as the
distributor's own ERP stack. The guard is a deterministic context check on
the quote (docs/SCORING.md section 5, "Whose system?"). Offline (R13).
"""

from __future__ import annotations

from trelium_gtm import extract as extract_mod
from trelium_gtm.extract import extract_claims
from trelium_gtm.models import Evidence, Fact
from trelium_gtm.signals import derive_signals
from trelium_gtm.taxonomy import SYSTEM_NAME_TO_CLASS, SourceTier, SystemClass

SNAPSHOT = (
    "We support a wide range of punch-out connections, including GEP, Oracle, SAP and Ariba. "
    "Our order desk runs on NetSuite. "
    "We harness a Magento-based technology platform to oversee our catalogue."
)


def _run(monkeypatch, tmp_path, claims):
    monkeypatch.setattr(extract_mod, "_call_openai", lambda *a, **k: {"claims": claims})
    return extract_claims(
        source_url="https://acme-test-distributor.example/technology",
        company_domain="acme-test-distributor.example",
        snapshot_text=SNAPSHOT,
        publisher="Company website",
        title="Technology",
        retrieved_at="2026-09-15T00:00:00Z",
        snapshot_path="evidence/raw/src_test.txt",
        cache_dir=tmp_path / "cache",
    )


def _system_claim(value: str, quote: str) -> dict:
    return {
        "field": "system",
        "value": value,
        "statement": f"Mentions {value}.",
        "quote": quote,
        "model_confidence": "high",
    }


def test_punch_out_targets_are_kept_as_unscored_facts(monkeypatch, tmp_path):
    quote = "We support a wide range of punch-out connections, including GEP, Oracle, SAP and Ariba."
    outcome = _run(
        monkeypatch, tmp_path, [_system_claim("Oracle", quote), _system_claim("SAP", quote)]
    )
    assert len(outcome.facts) == 2  # verbatim, so kept ...
    assert all(f.field is None for f in outcome.facts)  # ... but not as stack signals


def test_the_companys_own_system_still_counts(monkeypatch, tmp_path):
    outcome = _run(
        monkeypatch, tmp_path, [_system_claim("NetSuite", "Our order desk runs on NetSuite.")]
    )
    assert outcome.facts[0].field == "system"
    assert outcome.facts[0].value == "NetSuite"


def test_second_person_framing_disqualifies_a_system(monkeypatch, tmp_path):
    snapshot = "Connect with your ERP, including SAP and NetSuite, through our API."
    monkeypatch.setattr(
        extract_mod, "_call_openai",
        lambda *a, **k: {"claims": [_system_claim("SAP", "Connect with your ERP, including SAP and NetSuite, through our API.")]},
    )
    outcome = extract_claims(
        source_url="https://acme-test-supplier.example/integrations",
        company_domain="acme-test-supplier.example",
        snapshot_text=snapshot,
        publisher="Company website",
        title="Integrations",
        retrieved_at="2026-09-15T00:00:00Z",
        snapshot_path="evidence/raw/src_test.txt",
        cache_dir=tmp_path / "cache",
    )
    assert outcome.facts[0].field is None


def test_magento_is_a_commerce_store_platform():
    assert SYSTEM_NAME_TO_CLASS["magento"] == SystemClass.COMMERCE_STORE
    ev = Evidence(
        id="ev_1",
        source_url="https://acme-test-distributor.example",
        source_tier=SourceTier.COMPANY_PRIMARY,
        publisher="Company website",
        title="Home",
        retrieved_at="2026-09-15T00:00:00Z",
        snapshot_path="evidence/raw/src_test.txt",
        content_sha256="a" * 64,
        quote="a Magento-based technology platform",
        quote_offset=0,
    )
    fact = Fact(
        id="fct_1",
        statement="Uses a Magento-based platform.",
        evidence_ids=["ev_1"],
        field="system",
        value="Magento",
    )
    signals = derive_signals([fact], [ev])
    assert [s.value for s in signals.stack_signals] == [f"{SystemClass.COMMERCE_STORE.value}:magento"]


def test_identical_claims_over_one_quote_are_kept_once(monkeypatch, tmp_path):
    quote = "We support a wide range of punch-out connections, including GEP, Oracle, SAP and Ariba."
    claims = [
        {"field": "system", "value": v, "statement": quote, "quote": quote, "model_confidence": "high"}
        for v in ("GEP", "Oracle", "SAP", "Ariba")
    ]
    outcome = _run(monkeypatch, tmp_path, claims)
    # all four are downgraded to "other" by the context guard, so they collapse to one fact
    assert len(outcome.facts) == 1
    assert outcome.facts[0].field is None
    assert sum(1 for r in outcome.rejected if "duplicate" in r["reason"]) == 3
    assert outcome.raw_claims_count == 4


def test_distinct_systems_over_one_quote_are_separate_facts(monkeypatch, tmp_path):
    quote = "Our order desk runs on NetSuite."
    monkeypatch.setattr(
        extract_mod, "_call_openai",
        lambda *a, **k: {"claims": [
            {"field": "system", "value": "NetSuite", "statement": "Runs NetSuite.", "quote": quote, "model_confidence": "high"},
            {"field": "system", "value": "NetSuite", "statement": "Runs NetSuite.", "quote": quote, "model_confidence": "high"},
        ]},
    )
    outcome = extract_claims(
        source_url="https://acme-test-distributor.example/technology",
        company_domain="acme-test-distributor.example",
        snapshot_text=SNAPSHOT,
        publisher="Company website",
        title="Technology",
        retrieved_at="2026-09-15T00:00:00Z",
        snapshot_path="evidence/raw/src_test.txt",
        cache_dir=tmp_path / "cache",
    )
    assert len(outcome.facts) == 1  # exact duplicate collapses
    assert outcome.facts[0].field == "system"
