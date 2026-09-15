"""Correctness-hardening regression tests (docs/EVIDENCE_MODEL.md sections
9-10, docs/SCORING.md sections 12-13).

Invariants asserted here:
- duplicate sources cannot inflate any score component
- evidence/fact input order cannot change the derived signals or the score
- contradictory classification evidence is never silently discarded
- merged signals retain the provenance of every supporting fact
- Fact / Inference separation remains intact
"""

from __future__ import annotations

import random

import pytest
from pydantic import ValidationError

from trelium_gtm.models import AccountBrief, Evidence, Fact, Inference, Signal, SignalSet
from trelium_gtm.scoring import score
from trelium_gtm.signals import conflict_gaps, derive_signals
from trelium_gtm.taxonomy import (
    OpsSubSignal,
    ScaleBand,
    SegmentLabel,
    SegmentTier,
    SourceTier,
    SystemClass,
)

# ---------------------------------------------------------------------------
# fixture helpers
# ---------------------------------------------------------------------------

HOME = "https://acme-test.example/"
CAREERS = "https://acme-test.example/careers"
PPAI = "https://www.ppai.org/ppai/acme-test/"
BLOG = "https://someblog.example/acme"


def ev(id_: str, url: str, tier: SourceTier) -> Evidence:
    return Evidence(
        id=id_, source_url=url, source_tier=tier, publisher="p", title="t",
        retrieved_at="2026-01-01T00:00:00Z", snapshot_path=f"evidence/raw/{id_}.txt",
        content_sha256="0" * 64, quote="placeholder quote", quote_offset=0,
    )


def fact(id_: str, field: str, value, evidence_ids: list[str]) -> Fact:
    return Fact(id=id_, statement=f"{field}={value}", evidence_ids=evidence_ids, field=field, value=value)


EV_HOME = ev("ev_home", HOME, SourceTier.COMPANY_PRIMARY)
EV_CAREERS = ev("ev_careers", CAREERS, SourceTier.COMPANY_PRIMARY)
EV_PPAI = ev("ev_ppai", PPAI, SourceTier.INDUSTRY_ASSOCIATION)
EV_BLOG = ev("ev_blog", BLOG, SourceTier.THIRD_PARTY_REPORTING)
ALL_EV = [EV_HOME, EV_CAREERS, EV_PPAI, EV_BLOG]

SEG_DIST = fact("f_seg", "segment", SegmentLabel.PROMO_DISTRIBUTOR.value, ["ev_home"])


def c3(facts: list[Fact], evidence=ALL_EV) -> int:
    return score(derive_signals(facts, evidence)).components["c3"]


# ---------------------------------------------------------------------------
# 1. C3 duplicate-system deduplication
# ---------------------------------------------------------------------------


def test_same_system_same_spelling_two_sources_is_one_system():
    facts = [
        SEG_DIST,
        fact("f_sys_home", "system", "SAGE", ["ev_home"]),
        fact("f_sys_careers", "system", "SAGE", ["ev_careers"]),
    ]
    signals = derive_signals(facts, ALL_EV)
    assert len(signals.stack_signals) == 1
    assert c3(facts) == 6  # first-system points only, never 6 + 2


def test_same_system_capitalisation_differences_is_one_system():
    facts = [
        SEG_DIST,
        fact("f1", "system", "SAGE", ["ev_home"]),
        fact("f2", "system", "Sage", ["ev_careers"]),
        fact("f3", "system", "  sage ", ["ev_ppai"]),
    ]
    signals = derive_signals(facts, ALL_EV)
    assert len(signals.stack_signals) == 1
    assert c3(facts) == 6


def test_same_system_repeated_on_one_page_is_one_system():
    facts = [
        SEG_DIST,
        fact("f1", "system", "SAGE", ["ev_home"]),
        fact("f2", "system", "SAGE", ["ev_home"]),
    ]
    signals = derive_signals(facts, ALL_EV)
    assert len(signals.stack_signals) == 1
    assert signals.stack_signals[0].evidence_ids == ["ev_home"]
    assert c3(facts) == 6


def test_genuinely_different_systems_in_same_class_still_both_count():
    facts = [
        SEG_DIST,
        fact("f1", "system", "SAGE", ["ev_home"]),
        fact("f2", "system", "ShopWorks", ["ev_home"]),
    ]
    signals = derive_signals(facts, ALL_EV)
    assert len(signals.stack_signals) == 2
    assert c3(facts) == 8  # 6 + 2 for a second distinct industry system


def test_merged_system_signal_retains_every_evidence_and_fact_id():
    facts = [
        SEG_DIST,
        fact("f_a", "system", "SAGE", ["ev_home"]),
        fact("f_b", "system", "sage", ["ev_careers"]),
        fact("f_c", "system", "SAGE", ["ev_ppai"]),
    ]
    sig = derive_signals(facts, ALL_EV).stack_signals[0]
    assert sig.evidence_ids == ["ev_careers", "ev_home", "ev_ppai"]  # sorted union
    assert sig.fact_ids == ["f_a", "f_b", "f_c"]


def test_scorer_itself_dedupes_by_name_for_hand_built_signal_sets():
    """Defence in depth: even if a caller bypasses derive_signals and feeds
    two rows for the same system, C3 must not award 'additional system' points."""
    signals = SignalSet(
        segment_label=SegmentLabel.PROMO_DISTRIBUTOR, segment_tier=SegmentTier.A,
        segment_signal=Signal(id="s", kind="segment", value="A", evidence_ids=["e"], fact_ids=["f"]),
        stack_signals=[
            Signal(id="a", kind="stack", value=f"{SystemClass.INDUSTRY_ORDER_SYSTEM.value}:sage", evidence_ids=["e1"], fact_ids=["f1"]),
            Signal(id="b", kind="stack", value=f"{SystemClass.INDUSTRY_ORDER_SYSTEM.value}:SAGE ", evidence_ids=["e2"], fact_ids=["f2"]),
        ],
        has_any_evidence=True, tier_1_2_fact_count=1,
    )
    result = score(signals)
    assert result.components["c3"] == 6
    assert set(result.contributing_signals["c3"]) == {"a", "b"}  # provenance of both rows kept


# ---------------------------------------------------------------------------
# 2. Contradictory segment evidence
# ---------------------------------------------------------------------------


def test_distributor_vs_supplier_equal_tier_is_an_unresolved_conflict():
    facts = [
        fact("f_d", "segment", SegmentLabel.PROMO_DISTRIBUTOR.value, ["ev_home"]),
        fact("f_s", "segment", SegmentLabel.PROMO_SUPPLIER.value, ["ev_careers"]),
    ]
    signals = derive_signals(facts, ALL_EV)
    assert signals.segment_conflict == "unresolved"
    assert {c.value for c in signals.segment_candidates} == {
        SegmentLabel.PROMO_DISTRIBUTOR.value, SegmentLabel.PROMO_SUPPLIER.value
    }
    result = score(signals)
    assert result.components["c1"] == 20  # (25 * 4) // 5 penalty
    assert "SEGMENT_CONFLICT_UNRESOLVED" in result.flags
    gaps = conflict_gaps(signals, ALL_EV)
    assert any("SEGMENT CONFLICT" in g for g in gaps)
    assert any("promotional_products_supplier" in g and "promotional_products_distributor" in g for g in gaps)


def test_identical_classification_from_multiple_sources_is_not_a_conflict():
    facts = [
        fact("f1", "segment", SegmentLabel.PROMO_DISTRIBUTOR.value, ["ev_home"]),
        fact("f2", "segment", SegmentLabel.PROMO_DISTRIBUTOR.value, ["ev_ppai"]),
    ]
    signals = derive_signals(facts, ALL_EV)
    assert signals.segment_conflict == "none"
    assert len(signals.segment_candidates) == 1
    assert signals.segment_signal.evidence_ids == ["ev_home", "ev_ppai"]
    assert score(signals).components["c1"] == 25
    assert conflict_gaps(signals, ALL_EV) == []


def test_stronger_tier_beats_weaker_tier_and_is_resolved_not_penalised():
    facts = [
        fact("f_weak", "segment", SegmentLabel.OPS_HEAVY_NON_PROMO.value, ["ev_blog"]),   # tier 5
        fact("f_strong", "segment", SegmentLabel.PROMO_DISTRIBUTOR.value, ["ev_ppai"]),   # tier 2
    ]
    signals = derive_signals(facts, ALL_EV)
    assert signals.segment_label == SegmentLabel.PROMO_DISTRIBUTOR
    assert signals.segment_conflict == "resolved_by_tier"
    assert len(signals.segment_candidates) == 2  # loser kept, not discarded
    result = score(signals)
    assert result.components["c1"] == 25
    assert "SEGMENT_CONFLICT_RESOLVED_BY_TIER" in result.flags
    assert any("resolved by evidence tier" in g for g in conflict_gaps(signals, ALL_EV))


def test_equal_tier_conflict_winner_is_the_label_with_more_support():
    facts = [
        fact("f_s", "segment", SegmentLabel.PROMO_SUPPLIER.value, ["ev_home"]),
        fact("f_d1", "segment", SegmentLabel.PROMO_DISTRIBUTOR.value, ["ev_careers"]),
        fact("f_d2", "segment", SegmentLabel.PROMO_DISTRIBUTOR.value, ["ev_home"]),
    ]
    signals = derive_signals(facts, ALL_EV)
    assert signals.segment_label == SegmentLabel.PROMO_DISTRIBUTOR
    assert signals.segment_conflict == "unresolved"


def test_equal_tier_equal_support_tie_break_is_lexical_and_documented():
    facts = [
        fact("f_s", "segment", SegmentLabel.PROMO_SUPPLIER.value, ["ev_home"]),
        fact("f_d", "segment", SegmentLabel.PROMO_DISTRIBUTOR.value, ["ev_home"]),
    ]
    signals = derive_signals(facts, ALL_EV)
    # 'promotional_products_distributor' < 'promotional_products_supplier'
    assert signals.segment_label == SegmentLabel.PROMO_DISTRIBUTOR


def test_segment_result_is_independent_of_input_order():
    facts = [
        fact("f_s", "segment", SegmentLabel.PROMO_SUPPLIER.value, ["ev_careers"]),
        fact("f_d", "segment", SegmentLabel.PROMO_DISTRIBUTOR.value, ["ev_home"]),
    ]
    forward = derive_signals(facts, ALL_EV)
    backward = derive_signals(list(reversed(facts)), list(reversed(ALL_EV)))
    assert forward == backward


# ---------------------------------------------------------------------------
# 3. Duplicates in every other category
# ---------------------------------------------------------------------------


def test_duplicate_ops_subsignal_is_one_signal_and_scores_once():
    facts = [
        SEG_DIST,
        fact("f1", "ops_subsignal", OpsSubSignal.OPS_CUSTOMIZATION.value, ["ev_home"]),
        fact("f2", "ops_subsignal", OpsSubSignal.OPS_CUSTOMIZATION.value, ["ev_careers"]),
    ]
    signals = derive_signals(facts, ALL_EV)
    assert len(signals.ops_signals) == 1
    assert signals.ops_signals[0].fact_ids == ["f1", "f2"]
    assert score(signals).components["c2"] == 4


def test_same_hiring_role_on_two_pages_counts_as_one_role():
    facts = [
        SEG_DIST,
        fact("f1", "ops_hiring_role", "Order Entry Specialist", ["ev_home"]),
        fact("f2", "ops_hiring_role", "order entry specialist", ["ev_careers"]),
    ]
    signals = derive_signals(facts, ALL_EV)
    hiring = next(s for s in signals.trigger_signals if s.value.startswith("OPS_HIRING"))
    assert hiring.value == "OPS_HIRING:1"
    assert hiring.fact_ids == ["f1", "f2"]
    assert score(signals).components["c5"] == 3


def test_three_distinct_hiring_roles_reach_the_higher_threshold():
    facts = [
        SEG_DIST,
        fact("f1", "ops_hiring_role", "Order Entry Specialist", ["ev_careers"]),
        fact("f2", "ops_hiring_role", "AP Clerk", ["ev_careers"]),
        fact("f3", "ops_hiring_role", "Customer Service Rep", ["ev_careers"]),
    ]
    assert score(derive_signals(facts, ALL_EV)).components["c5"] == 4


def test_duplicate_trigger_is_one_signal():
    facts = [
        SEG_DIST,
        fact("f1", "trigger", "GROWTH_HIGH", ["ev_ppai"]),
        fact("f2", "trigger", "GROWTH_HIGH", ["ev_blog"]),
    ]
    signals = derive_signals(facts, ALL_EV)
    assert [s.value for s in signals.trigger_signals] == ["GROWTH_HIGH"]
    assert score(signals).components["c5"] == 8


def test_duplicate_facts_do_not_inflate_evidence_quality_count():
    """C6 buckets on distinct tier-1/2 claims. Six copies of one claim is one claim."""
    facts = [fact(f"f{i}", "segment", SegmentLabel.PROMO_DISTRIBUTOR.value, ["ev_home"]) for i in range(6)]
    signals = derive_signals(facts, ALL_EV)
    assert signals.tier_1_2_fact_count == 1


def test_revenue_figures_in_different_bands_flag_a_scale_conflict():
    facts = [
        SEG_DIST,
        fact("f_big", "revenue_usd", 300_000_000, ["ev_blog"]),   # tier 5, SWEET_SPOT
        fact("f_small", "revenue_usd", 8_000_000, ["ev_ppai"]),   # tier 2, SMALL
    ]
    signals = derive_signals(facts, ALL_EV)
    assert signals.scale_conflict is True
    assert signals.scale_band == ScaleBand.SMALL          # strongest tier wins, not the larger number
    assert {c.value for c in signals.scale_candidates} == {"SWEET_SPOT", "SMALL"}
    result = score(signals)
    assert "SCALE_CONFLICT" in result.flags
    assert any("SCALE CONFLICT" in g for g in conflict_gaps(signals, ALL_EV))


def test_same_band_revenue_figures_are_not_a_conflict():
    facts = [
        SEG_DIST,
        fact("f1", "revenue_usd", 80_000_000, ["ev_home"]),
        fact("f2", "revenue_usd", 90_000_000, ["ev_ppai"]),
    ]
    signals = derive_signals(facts, ALL_EV)
    assert signals.scale_conflict is False
    assert signals.scale_band == ScaleBand.SWEET_SPOT
    assert signals.scale_signal.fact_ids == ["f1", "f2"]


# ---------------------------------------------------------------------------
# 4. Whole-pipeline invariants
# ---------------------------------------------------------------------------


def _rich_facts() -> list[Fact]:
    return [
        fact("s1", "segment", SegmentLabel.PROMO_DISTRIBUTOR.value, ["ev_home"]),
        fact("s2", "segment", SegmentLabel.PROMO_SUPPLIER.value, ["ev_careers"]),
        fact("r1", "revenue_usd", 87_000_000, ["ev_ppai"]),
        fact("r2", "revenue_usd", 87_500_000, ["ev_blog"]),
        fact("y1", "system", "SAGE", ["ev_home"]),
        fact("y2", "system", "sage", ["ev_careers"]),
        fact("y3", "system", "NetSuite", ["ev_careers"]),
        fact("o1", "ops_subsignal", OpsSubSignal.OPS_MULTI_SITE.value, ["ev_home"]),
        fact("o2", "ops_subsignal", OpsSubSignal.OPS_MULTI_SITE.value, ["ev_ppai"]),
        fact("h1", "ops_hiring_role", "AP Clerk", ["ev_careers"]),
        fact("h2", "ops_hiring_role", "ap clerk", ["ev_careers"]),
        fact("t1", "trigger", "ACQUISITION", ["ev_blog"]),
        fact("t2", "trigger", "ACQUISITION", ["ev_ppai"]),
    ]


def test_evidence_order_cannot_change_the_final_score():
    baseline = score(derive_signals(_rich_facts(), ALL_EV))
    rng = random.Random(1234)
    for _ in range(25):
        facts = _rich_facts()
        evidence = list(ALL_EV)
        rng.shuffle(facts)
        rng.shuffle(evidence)
        assert score(derive_signals(facts, evidence)) == baseline


def test_duplicate_sources_cannot_inflate_any_component():
    """Every category with the duplicates present must score exactly what it
    scores with the duplicates removed."""
    deduped = [f for f in _rich_facts() if f.id not in {"y2", "o2", "h2", "t2", "r2"}]
    with_dupes = score(derive_signals(_rich_facts(), ALL_EV))
    without = score(derive_signals(deduped, ALL_EV))
    assert with_dupes.components == without.components
    assert with_dupes.total == without.total


def test_contradictory_evidence_cannot_silently_disappear_from_a_brief():
    """The losing label must be visible in the SignalSet, in the flags, and
    in the rendered research gaps — three independent places."""
    signals = derive_signals(_rich_facts(), ALL_EV)
    result = score(signals)
    losing = SegmentLabel.PROMO_SUPPLIER.value
    assert any(c.value == losing for c in signals.segment_candidates)
    assert "SEGMENT_CONFLICT_UNRESOLVED" in result.flags
    assert any(losing in g for g in conflict_gaps(signals, ALL_EV))


def test_merged_signals_retain_provenance_end_to_end():
    signals = derive_signals(_rich_facts(), ALL_EV)
    all_fact_ids = {f.id for f in _rich_facts()}
    referenced = set()
    for sig in [signals.segment_signal, signals.scale_signal, *signals.segment_candidates,
                *signals.scale_candidates, *signals.stack_signals, *signals.ops_signals,
                *signals.trigger_signals]:
        if sig is not None:
            referenced.update(sig.fact_ids)
    assert referenced == all_fact_ids  # no scoring-relevant fact lost in merging


def test_fact_inference_separation_remains_intact():
    inf = Inference(
        id="inf_1", statement="x may be worth investigating", from_fact_ids=["f"],
        rule="ICP.WF.TEST", model_confidence="low", validation_question_ids=["vq"],
    )
    with pytest.raises(ValidationError):
        AccountBrief(company="Acme Test", domain="acme.example", corpus_hash="x", facts=[inf])  # type: ignore[list-item]
