"""Deterministic ranking: same corpus in, byte-identical order out, always."""

from __future__ import annotations

import random

from trelium_gtm.models import AccountBrief, Evidence, Fact, ScoreResult, SignalSet
from trelium_gtm.ranking import rank
from trelium_gtm.taxonomy import EvidenceGrade, ScaleBand, SourceTier


def make_brief(company: str, total: int | None, grade: EvidenceGrade, scale: ScaleBand) -> AccountBrief:
    ev = Evidence(
        id="ev_1",
        source_url="https://example.com",
        source_tier=SourceTier.COMPANY_PRIMARY,
        publisher="Company website",
        title="Home",
        retrieved_at="2026-01-01T00:00:00Z",
        snapshot_path="evidence/raw/ev_1.txt",
        content_sha256="0" * 64,
        quote="A distributor of promotional products.",
        quote_offset=0,
    )
    fact = Fact(id="fct_1", statement="x", evidence_ids=["ev_1"])
    status = "SCORED" if total is not None else "OUT_OF_ICP"
    return AccountBrief(
        company=company,
        domain=f"{company.lower().replace(' ', '')}.example",
        corpus_hash="deadbeef",
        evidence=[ev],
        facts=[fact],
        signals=SignalSet(scale_band=scale),
        score=ScoreResult(status=status, total=total, evidence_grade=grade),
    )


def test_rank_orders_by_total_descending():
    briefs = [
        make_brief("Low", 40, EvidenceGrade.B, ScaleBand.SWEET_SPOT),
        make_brief("High", 90, EvidenceGrade.B, ScaleBand.SWEET_SPOT),
        make_brief("Mid", 65, EvidenceGrade.B, ScaleBand.SWEET_SPOT),
    ]
    ordered = rank(briefs)
    assert [b.company for b in ordered] == ["High", "Mid", "Low"]


def test_rank_tiebreaks_on_evidence_grade_when_totals_equal():
    briefs = [
        make_brief("GradeC", 70, EvidenceGrade.C, ScaleBand.SWEET_SPOT),
        make_brief("GradeA", 70, EvidenceGrade.A, ScaleBand.SWEET_SPOT),
    ]
    ordered = rank(briefs)
    assert [b.company for b in ordered] == ["GradeA", "GradeC"]


def test_rank_tiebreaks_on_scale_proximity_to_sweet_spot():
    briefs = [
        make_brief("Enterprise", 70, EvidenceGrade.A, ScaleBand.ENTERPRISE),
        make_brief("SweetSpot", 70, EvidenceGrade.A, ScaleBand.SWEET_SPOT),
    ]
    ordered = rank(briefs)
    assert [b.company for b in ordered] == ["SweetSpot", "Enterprise"]


def test_rank_final_tiebreak_is_company_name_ascending():
    briefs = [
        make_brief("Zeta Corp", 70, EvidenceGrade.A, ScaleBand.SWEET_SPOT),
        make_brief("Alpha Corp", 70, EvidenceGrade.A, ScaleBand.SWEET_SPOT),
    ]
    ordered = rank(briefs)
    assert [b.company for b in ordered] == ["Alpha Corp", "Zeta Corp"]


def test_out_of_icp_sorts_last():
    briefs = [
        make_brief("Excluded", None, EvidenceGrade.D, ScaleBand.UNKNOWN),
        make_brief("Included", 50, EvidenceGrade.B, ScaleBand.SWEET_SPOT),
    ]
    ordered = rank(briefs)
    assert [b.company for b in ordered] == ["Included", "Excluded"]


def test_rank_is_stable_across_shuffled_input_order():
    briefs = [
        make_brief("A", 90, EvidenceGrade.A, ScaleBand.SWEET_SPOT),
        make_brief("B", 80, EvidenceGrade.B, ScaleBand.SWEET_SPOT),
        make_brief("C", 70, EvidenceGrade.C, ScaleBand.LARGE),
        make_brief("D", 60, EvidenceGrade.D, ScaleBand.MICRO),
    ]
    expected = [b.company for b in rank(briefs)]
    shuffled = briefs[:]
    random.Random(42).shuffle(shuffled)
    result = [b.company for b in rank(shuffled)]
    assert result == expected
