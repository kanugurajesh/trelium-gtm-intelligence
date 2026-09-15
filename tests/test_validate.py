"""Tests for the validation harness (V1 rank correlation, V2 ablation,
V4 negative control). Pure functions over already-scored briefs; no network.
"""

from __future__ import annotations

from trelium_gtm.models import AccountBrief, Evidence, Fact, ScoreResult, SignalSet
from trelium_gtm.taxonomy import EvidenceGrade, SourceTier
from trelium_gtm.validate import ablate, check_negative_controls, spearman_rho


def make_scored_brief(company: str, components: dict[str, int]) -> AccountBrief:
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
    total = sum(components.values())
    return AccountBrief(
        company=company,
        domain=f"{company.lower().replace(' ', '')}.example",
        corpus_hash="deadbeef",
        evidence=[ev],
        facts=[fact],
        signals=SignalSet(),
        score=ScoreResult(
            status="SCORED", total=total, components=components, evidence_grade=EvidenceGrade.B
        ),
    )


def make_out_of_icp_brief(company: str) -> AccountBrief:
    return AccountBrief(
        company=company,
        domain=f"{company.lower().replace(' ', '')}.example",
        corpus_hash="deadbeef",
        signals=SignalSet(),
        score=ScoreResult(status="OUT_OF_ICP", evidence_grade=EvidenceGrade.D),
    )


def make_insufficient_evidence_brief(company: str) -> AccountBrief:
    return AccountBrief(
        company=company,
        domain=f"{company.lower().replace(' ', '')}.example",
        corpus_hash="deadbeef",
        signals=SignalSet(),
        score=ScoreResult(status="INSUFFICIENT_EVIDENCE", evidence_grade=EvidenceGrade.D),
    )


def test_spearman_rho_perfect_agreement_is_one():
    order = ["A", "B", "C", "D"]
    assert spearman_rho(order, order) == 1.0


def test_spearman_rho_perfect_disagreement_is_negative_one():
    assert spearman_rho(["A", "B", "C", "D"], ["D", "C", "B", "A"]) == -1.0


def test_spearman_rho_ignores_items_missing_from_one_side():
    rho = spearman_rho(["A", "B", "C"], ["A", "B", "X"])
    assert rho is not None  # A, B common -> comparable


def test_spearman_rho_none_with_fewer_than_two_common_items():
    assert spearman_rho(["A"], ["A"]) is None
    assert spearman_rho(["A", "B"], ["X", "Y"]) is None


def test_ablate_zeroing_dominant_component_changes_top_10():
    briefs = [
        make_scored_brief("HighC1", {"c1": 25, "c2": 0, "c3": 0, "c4": 0, "c5": 0, "c6": 0}),
        make_scored_brief("HighC4", {"c1": 0, "c2": 0, "c3": 0, "c4": 15, "c5": 0, "c6": 0}),
    ]
    results = ablate(briefs, top_n=1)
    c1_result = next(r for r in results if r.zeroed_component == "c1")
    assert c1_result.original_top_10 == ["HighC1"]
    assert c1_result.ablated_top_10 == ["HighC4"]  # HighC1 drops to 0 once c1 is zeroed
    assert c1_result.movement_count == 1


def test_ablate_returns_all_six_components():
    briefs = [make_scored_brief("A", {"c1": 10, "c2": 10, "c3": 10, "c4": 10, "c5": 10, "c6": 10})]
    results = ablate(briefs)
    assert {r.zeroed_component for r in results} == {"c1", "c2", "c3", "c4", "c5", "c6"}


def test_ablate_ignores_out_of_icp_briefs():
    briefs = [
        make_scored_brief("Scored", {"c1": 25, "c2": 0, "c3": 0, "c4": 0, "c5": 0, "c6": 0}),
        make_out_of_icp_brief("Excluded"),
    ]
    results = ablate(briefs, top_n=5)
    assert "Excluded" not in results[0].original_top_10


def test_check_negative_controls_all_excluded():
    briefs = [make_out_of_icp_brief(name) for name in ["LawFirm", "SaaSCo", "Bank"]]
    results = check_negative_controls(briefs)
    assert all(r.passed for r in results)


def test_check_negative_controls_flags_a_leak():
    briefs = [
        make_out_of_icp_brief("LawFirm"),
        make_scored_brief("LeakedSaaSCo", {"c1": 25, "c2": 20, "c3": 15, "c4": 15, "c5": 15, "c6": 10}),
    ]
    results = check_negative_controls(briefs)
    leaked = next(r for r in results if r.company == "LeakedSaaSCo")
    assert not leaked.passed
    assert leaked.total == 100


def test_check_negative_controls_scored_below_watch_threshold_passes():
    """A company left segment-UNRESOLVED (never explicitly gated OUT_OF_ICP)
    but scoring near the floor was never going to be recommended anyway —
    this must not count as a failure. Mirrors the real Asana case
    (docs/FINDINGS.md): scored 3/100, status SCORED, not OUT_OF_ICP."""
    briefs = [make_scored_brief("LowScoreSaaSCo", {"c1": 0, "c2": 0, "c3": 0, "c4": 0, "c5": 0, "c6": 3})]
    results = check_negative_controls(briefs)
    assert results[0].passed
    assert results[0].total == 3


def test_check_negative_controls_insufficient_evidence_passes():
    briefs = [make_insufficient_evidence_brief("NeverCollected")]
    results = check_negative_controls(briefs)
    assert results[0].passed
