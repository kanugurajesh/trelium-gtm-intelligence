"""Pipeline orchestration tests. Network/model calls are monkeypatched per
CLAUDE.md R13; these assert the gap-assembly rules and the "don't spend a
hypothesis call on an OUT_OF_ICP or evidence-free account" short-circuit.
"""

from __future__ import annotations

from datetime import date

from trelium_gtm import collect as collect_mod
from trelium_gtm import extract as extract_mod
from trelium_gtm import hypothesise as hyp_mod
from trelium_gtm.collect import CollectResult
from trelium_gtm.extract import ExtractionOutcome
from trelium_gtm.hypothesise import HypothesisOutcome
from trelium_gtm.models import Evidence, Fact
from trelium_gtm.pipeline import SourceSpec, run_account
from trelium_gtm.taxonomy import SourceTier


def _fake_collect_ok(url, evidence_dir, **kwargs):
    return CollectResult(
        ok=True,
        url=url,
        snapshot_id="src_test",
        snapshot_path="evidence/raw/src_test.txt",
        content_sha256="a" * 64,
        text="Acme Test Distributor is a promotional products distributor.",
    )


def _fake_extract_segment_only(**kwargs):
    ev = Evidence(
        id="ev_1",
        source_url=kwargs["source_url"],
        source_tier=SourceTier.COMPANY_PRIMARY,
        publisher=kwargs["publisher"],
        title=kwargs["title"],
        retrieved_at=kwargs["retrieved_at"],
        snapshot_path=kwargs["snapshot_path"],
        content_sha256="a" * 64,
        quote="Acme Test Distributor is a promotional products distributor.",
        quote_offset=0,
    )
    fact = Fact(
        id="fct_1",
        statement="Acme Test Distributor is a promotional products distributor",
        evidence_ids=["ev_1"],
        field="segment",
        value="promotional_products_distributor",
    )
    return ExtractionOutcome(facts=[fact], evidence=[ev], rejected=[], raw_claims_count=1)


def test_run_account_assembles_rule_based_gaps(monkeypatch, tmp_path):
    monkeypatch.setattr(collect_mod, "collect_source", _fake_collect_ok)
    monkeypatch.setattr(extract_mod, "extract_claims", _fake_extract_segment_only)
    monkeypatch.setattr("trelium_gtm.pipeline.collect_source", _fake_collect_ok)
    monkeypatch.setattr("trelium_gtm.pipeline.extract_claims", _fake_extract_segment_only)
    monkeypatch.setattr(
        "trelium_gtm.pipeline.generate_hypotheses",
        lambda **kwargs: HypothesisOutcome(inferences=[], validation_questions=[], workflow_hypotheses=[]),
    )

    report = run_account(
        company="Acme Test Distributor",
        domain="acme-test.example",
        sources=[SourceSpec(url="https://acme-test.example/about", publisher="Company website", title="About")],
        evidence_dir=tmp_path / "evidence",
        cache_dir=tmp_path / "cache",
        as_of=date(2026, 1, 1),
    )

    brief = report.brief
    assert brief.score.status == "SCORED"
    # No stack, no trigger, sourced scale is absent -> corresponding gaps present
    assert "No sourced scale figure; scale scored 0" in brief.research_gaps
    assert "No order or ERP system identified in public sources" in brief.research_gaps
    assert "No growth, hiring or migration trigger found in public sources" in brief.research_gaps
    assert "Not de-duplicated against Trelium CRM" in brief.research_gaps
    assert "Segment unconfirmed from primary sources" not in brief.research_gaps


def test_run_account_skips_hypothesis_generation_when_out_of_icp(monkeypatch, tmp_path):
    def fake_extract_out_of_icp(**kwargs):
        ev = Evidence(
            id="ev_x",
            source_url=kwargs["source_url"],
            source_tier=SourceTier.COMPANY_PRIMARY,
            publisher=kwargs["publisher"],
            title=kwargs["title"],
            retrieved_at=kwargs["retrieved_at"],
            snapshot_path=kwargs["snapshot_path"],
            content_sha256="a" * 64,
            quote="Acme is a law firm.",
            quote_offset=0,
        )
        fact = Fact(
            id="fct_x",
            statement="Acme is a law firm",
            evidence_ids=["ev_x"],
            field="segment",
            value="out_of_icp",
        )
        return ExtractionOutcome(facts=[fact], evidence=[ev], rejected=[], raw_claims_count=1)

    monkeypatch.setattr("trelium_gtm.pipeline.collect_source", _fake_collect_ok)
    monkeypatch.setattr("trelium_gtm.pipeline.extract_claims", fake_extract_out_of_icp)

    called = {"n": 0}

    def fake_hyp(**kwargs):
        called["n"] += 1
        return HypothesisOutcome(inferences=[], validation_questions=[], workflow_hypotheses=[])

    monkeypatch.setattr("trelium_gtm.pipeline.generate_hypotheses", fake_hyp)

    report = run_account(
        company="Acme Law Firm",
        domain="acme-law.example",
        sources=[SourceSpec(url="https://acme-law.example/about", publisher="Company website", title="About")],
        evidence_dir=tmp_path / "evidence",
        cache_dir=tmp_path / "cache",
        as_of=date(2026, 1, 1),
    )
    assert report.brief.score.status == "OUT_OF_ICP"
    assert called["n"] == 0  # never spend a hypothesis call on an excluded account


def test_run_account_records_collection_failure_as_gap(monkeypatch, tmp_path):
    def fake_collect_fail(url, evidence_dir, **kwargs):
        return CollectResult(ok=False, url=url, snapshot_id="src_fail", error="Blocked by robots.txt")

    monkeypatch.setattr("trelium_gtm.pipeline.collect_source", fake_collect_fail)
    monkeypatch.setattr(
        "trelium_gtm.pipeline.generate_hypotheses",
        lambda **kwargs: HypothesisOutcome(inferences=[], validation_questions=[], workflow_hypotheses=[]),
    )

    report = run_account(
        company="Acme Test Distributor",
        domain="acme-test.example",
        sources=[SourceSpec(url="https://acme-test.example/about", publisher="Company website", title="About")],
        evidence_dir=tmp_path / "evidence",
        cache_dir=tmp_path / "cache",
        as_of=date(2026, 1, 1),
    )
    assert report.brief.score.status == "INSUFFICIENT_EVIDENCE"
    assert any("Blocked by robots.txt" in g for g in report.brief.research_gaps)


def test_corpus_hash_is_stable_for_identical_evidence(monkeypatch, tmp_path):
    monkeypatch.setattr("trelium_gtm.pipeline.collect_source", _fake_collect_ok)
    monkeypatch.setattr("trelium_gtm.pipeline.extract_claims", _fake_extract_segment_only)
    monkeypatch.setattr(
        "trelium_gtm.pipeline.generate_hypotheses",
        lambda **kwargs: HypothesisOutcome(inferences=[], validation_questions=[], workflow_hypotheses=[]),
    )

    def one_run():
        return run_account(
            company="Acme Test Distributor",
            domain="acme-test.example",
            sources=[SourceSpec(url="https://acme-test.example/about", publisher="Company website", title="About")],
            evidence_dir=tmp_path / "evidence",
            cache_dir=tmp_path / "cache",
            as_of=date(2026, 1, 1),
        ).brief.corpus_hash

    assert one_run() == one_run()


def test_run_account_surfaces_segment_conflict_as_research_gap_and_flag(monkeypatch, tmp_path):
    """Contradiction policy end to end: two segment labels at equal tier must
    reach the rendered brief as a flag AND a research gap, never vanish."""

    def fake_extract_conflicting(**kwargs):
        ev = Evidence(
            id="ev_c", source_url=kwargs["source_url"], source_tier=SourceTier.COMPANY_PRIMARY,
            publisher=kwargs["publisher"], title=kwargs["title"], retrieved_at=kwargs["retrieved_at"],
            snapshot_path=kwargs["snapshot_path"], content_sha256="a" * 64,
            quote="Acme Test Distributor is a promotional products distributor.", quote_offset=0,
        )
        facts = [
            Fact(id="fct_d", statement="distributor", evidence_ids=["ev_c"], field="segment", value="promotional_products_distributor"),
            Fact(id="fct_s", statement="supplier", evidence_ids=["ev_c"], field="segment", value="promotional_products_supplier"),
        ]
        return ExtractionOutcome(facts=facts, evidence=[ev], rejected=[], raw_claims_count=2)

    monkeypatch.setattr("trelium_gtm.pipeline.collect_source", _fake_collect_ok)
    monkeypatch.setattr("trelium_gtm.pipeline.extract_claims", fake_extract_conflicting)
    monkeypatch.setattr(
        "trelium_gtm.pipeline.generate_hypotheses",
        lambda **kwargs: HypothesisOutcome(inferences=[], validation_questions=[], workflow_hypotheses=[]),
    )
    report = run_account(
        company="Acme Test Distributor", domain="acme-test.example",
        sources=[SourceSpec(url="https://acme-test.example/about", publisher="Company website", title="About")],
        evidence_dir=tmp_path / "evidence", cache_dir=tmp_path / "cache", as_of=date(2026, 1, 1),
    )
    brief = report.brief
    assert brief.signals.segment_conflict == "unresolved"
    assert "SEGMENT_CONFLICT_UNRESOLVED" in brief.flags
    assert any("SEGMENT CONFLICT" in g for g in brief.research_gaps)
    assert brief.score.components["c1"] == 20
