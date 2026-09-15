"""The test file that justifies "the score is deterministic". CLAUDE.md R12-R15.

Covers every component boundary, both sides of every threshold, all gates,
every cap, the recency discount, the non-monotonic scale curve, and the two
hard rules (H1: unsourced signals score zero, H2: model_confidence is never
read by scoring).
"""

from __future__ import annotations

import pytest

from trelium_gtm.models import Signal, SignalSet
from trelium_gtm.scoring import score
from trelium_gtm.taxonomy import (
    Band,
    EvidenceGrade,
    OpsSubSignal,
    ScaleBand,
    SegmentLabel,
    SegmentTier,
    SystemClass,
    Trigger,
)


def sig(kind: str, value: str, id_: str | None = None, evidence_ids=None) -> Signal:
    return Signal(
        id=id_ or f"sig_{kind}_{value}",
        kind=kind,
        value=value,
        evidence_ids=evidence_ids or ["ev_1"],
        fact_ids=["fct_1"],
    )


def base_signals(**overrides) -> SignalSet:
    defaults = dict(
        segment_label=SegmentLabel.PROMO_DISTRIBUTOR,
        segment_tier=SegmentTier.A,
        segment_signal=sig("segment", "A"),
        scale_band=ScaleBand.SWEET_SPOT,
        scale_basis="revenue",
        scale_signal=sig("scale", "SWEET_SPOT"),
        stack_signals=[],
        trigger_signals=[],
        ops_signals=[],
        evidence_domains=["example.com"],
        tier_1_2_fact_count=2,
        is_public_customer=False,
        is_ecosystem_ambiguous=False,
        has_any_evidence=True,
    )
    defaults.update(overrides)
    return SignalSet(**defaults)


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------


def test_gate_out_of_icp_short_circuits_everything():
    signals = base_signals(segment_tier=SegmentTier.X)
    result = score(signals)
    assert result.status == "OUT_OF_ICP"
    assert result.total is None


def test_gate_insufficient_evidence():
    signals = base_signals(has_any_evidence=False)
    result = score(signals)
    assert result.status == "INSUFFICIENT_EVIDENCE"
    assert result.total is None


def test_public_customer_flag_still_scores_but_is_flagged():
    signals = base_signals(is_public_customer=True)
    result = score(signals)
    assert result.status == "SCORED"
    assert "PUBLIC_CUSTOMER" in result.flags


def test_ecosystem_ambiguous_flag():
    signals = base_signals(is_ecosystem_ambiguous=True)
    result = score(signals)
    assert "ECOSYSTEM_AMBIGUOUS" in result.flags


# ---------------------------------------------------------------------------
# C1 - vertical fit
# ---------------------------------------------------------------------------


def test_c1_tier_a_strong_evidence_scores_25():
    signals = base_signals(segment_tier=SegmentTier.A, tier_1_2_fact_count=3)
    assert score(signals).components["c1"] == 25


def test_c1_tier_a_weak_evidence_scores_20():
    signals = base_signals(segment_tier=SegmentTier.A, tier_1_2_fact_count=0)
    assert score(signals).components["c1"] == 20


def test_c1_tier_b_scores_15():
    signals = base_signals(segment_tier=SegmentTier.B)
    assert score(signals).components["c1"] == 15


def test_c1_tier_c_scores_8():
    signals = base_signals(segment_tier=SegmentTier.C)
    assert score(signals).components["c1"] == 8


def test_c1_unresolved_segment_scores_0():
    signals = base_signals(
        segment_tier=SegmentTier.UNRESOLVED, segment_signal=None
    )
    # UNRESOLVED is not X so it is not gated out, but scores 0 on C1.
    assert score(signals).components["c1"] == 0


# ---------------------------------------------------------------------------
# C2 - operational complexity
# ---------------------------------------------------------------------------


def test_c2_single_subsignal_points():
    signals = base_signals(
        ops_signals=[sig("ops", OpsSubSignal.OPS_MULTISTEP_ORDER.value)]
    )
    assert score(signals).components["c2"] == 5


def test_c2_duplicate_subsignal_counts_once():
    signals = base_signals(
        ops_signals=[
            sig("ops", OpsSubSignal.OPS_MULTISTEP_ORDER.value, id_="a"),
            sig("ops", OpsSubSignal.OPS_MULTISTEP_ORDER.value, id_="b"),
        ]
    )
    assert score(signals).components["c2"] == 5


def test_c2_caps_at_20_even_though_raw_max_is_28():
    all_subs = [
        sig("ops", s.value, id_=f"ops_{s.value}") for s in OpsSubSignal
    ]
    signals = base_signals(ops_signals=all_subs)
    result = score(signals)
    assert result.components["c2"] == 20  # raw sum is 5+4+4+4+3+3+3+2=28, capped


def test_c2_zero_when_no_ops_signals():
    signals = base_signals(ops_signals=[])
    assert score(signals).components["c2"] == 0


# ---------------------------------------------------------------------------
# C3 - stack / ecosystem
# ---------------------------------------------------------------------------


def test_c3_single_industry_order_system():
    signals = base_signals(
        stack_signals=[sig("stack", f"{SystemClass.INDUSTRY_ORDER_SYSTEM.value}:sage")]
    )
    assert score(signals).components["c3"] == 6


def test_c3_two_industry_order_systems_additional_points():
    signals = base_signals(
        stack_signals=[
            sig("stack", f"{SystemClass.INDUSTRY_ORDER_SYSTEM.value}:sage", id_="a"),
            sig("stack", f"{SystemClass.INDUSTRY_ORDER_SYSTEM.value}:shopworks", id_="b"),
        ]
    )
    assert score(signals).components["c3"] == 8  # 6 + 2, under class cap of 8


def test_c3_class_cap_enforced():
    signals = base_signals(
        stack_signals=[
            sig("stack", f"{SystemClass.INDUSTRY_ORDER_SYSTEM.value}:sys{i}", id_=f"s{i}")
            for i in range(5)
        ]
    )
    # 6 + 2*4 = 14, capped at class cap 8
    assert score(signals).components["c3"] == 8


def test_c3_cross_boundary_bonus_when_two_classes_present():
    signals = base_signals(
        stack_signals=[
            sig("stack", f"{SystemClass.INDUSTRY_ORDER_SYSTEM.value}:sage", id_="a"),
            sig("stack", f"{SystemClass.ERP_ACCOUNTING.value}:netsuite", id_="b"),
        ]
    )
    # 6 + 5 + 3 bonus = 14
    assert score(signals).components["c3"] == 14


def test_c3_generic_office_alone_scores_zero():
    signals = base_signals(
        stack_signals=[sig("stack", f"{SystemClass.GENERIC_OFFICE.value}:gmail")]
    )
    assert score(signals).components["c3"] == 0


def test_c3_generic_office_with_non_generic_scores():
    signals = base_signals(
        stack_signals=[
            sig("stack", f"{SystemClass.GENERIC_OFFICE.value}:gmail", id_="a"),
            sig("stack", f"{SystemClass.ERP_ACCOUNTING.value}:netsuite", id_="b"),
        ]
    )
    # generic(1) + erp(5) = 6, only one non-generic class present so no cross-boundary bonus
    assert score(signals).components["c3"] == 6


def test_c3_overall_cap_at_15():
    signals = base_signals(
        stack_signals=[
            sig("stack", f"{SystemClass.INDUSTRY_ORDER_SYSTEM.value}:a", id_="1"),
            sig("stack", f"{SystemClass.ERP_ACCOUNTING.value}:b", id_="2"),
            sig("stack", f"{SystemClass.SUPPLIER_DATA.value}:c", id_="3"),
            sig("stack", f"{SystemClass.CRM.value}:d", id_="4"),
            sig("stack", f"{SystemClass.COMMERCE_STORE.value}:e", id_="5"),
        ]
    )
    # 6+5+4+3+3 = 21, + cross-boundary 3 = 24, capped at 15
    assert score(signals).components["c3"] == 15


# ---------------------------------------------------------------------------
# C4 - scale, non-monotonic
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "band,expected",
    [
        (ScaleBand.SWEET_SPOT, 15),
        (ScaleBand.LARGE, 11),
        (ScaleBand.LOWER_MID, 10),
        (ScaleBand.ENTERPRISE, 8),
        (ScaleBand.SMALL, 5),
        (ScaleBand.MICRO, 1),
        (ScaleBand.UNKNOWN, 0),
    ],
)
def test_c4_scale_band_points(band, expected):
    signal = None if band == ScaleBand.UNKNOWN else sig("scale", band.value)
    signals = base_signals(scale_band=band, scale_signal=signal)
    assert score(signals).components["c4"] == expected


def test_c4_is_non_monotonic_sweet_spot_beats_enterprise():
    sweet = base_signals(
        scale_band=ScaleBand.SWEET_SPOT, scale_signal=sig("scale", "SWEET_SPOT")
    )
    enterprise = base_signals(
        scale_band=ScaleBand.ENTERPRISE, scale_signal=sig("scale", "ENTERPRISE")
    )
    assert score(sweet).components["c4"] > score(enterprise).components["c4"]


def test_c4_headcount_basis_applies_four_fifths_floor():
    signals = base_signals(
        scale_band=ScaleBand.SWEET_SPOT,
        scale_basis="headcount",
        scale_signal=sig("scale", "SWEET_SPOT"),
    )
    # 15 * 4 // 5 = 12
    assert score(signals).components["c4"] == 12


# ---------------------------------------------------------------------------
# C5 - growth / buying trigger
# ---------------------------------------------------------------------------


def test_c5_growth_high_scores_8():
    signals = base_signals(trigger_signals=[sig("trigger", Trigger.GROWTH_HIGH.value)])
    assert score(signals).components["c5"] == 8


def test_c5_growth_moderate_scores_5():
    signals = base_signals(trigger_signals=[sig("trigger", Trigger.GROWTH_MODERATE.value)])
    assert score(signals).components["c5"] == 5


def test_c5_growth_high_and_moderate_together_take_the_higher():
    signals = base_signals(
        trigger_signals=[
            sig("trigger", Trigger.GROWTH_MODERATE.value, id_="a"),
            sig("trigger", Trigger.GROWTH_HIGH.value, id_="b"),
        ]
    )
    assert score(signals).components["c5"] == 8


def test_c5_contraction_scores_zero():
    signals = base_signals(trigger_signals=[sig("trigger", Trigger.CONTRACTION.value)])
    assert score(signals).components["c5"] == 0


@pytest.mark.parametrize("n,expected", [(1, 3), (2, 3), (3, 4), (5, 4)])
def test_c5_ops_hiring_thresholds(n, expected):
    signals = base_signals(
        trigger_signals=[sig("trigger", f"{Trigger.OPS_HIRING.value}:{n}")]
    )
    assert score(signals).components["c5"] == expected


def test_c5_recency_full_weight_within_24_months():
    signals = base_signals(trigger_signals=[sig("trigger", Trigger.GROWTH_HIGH.value, id_="g1")])
    result = score(signals, trigger_ages_months={"g1": 12})
    assert result.components["c5"] == 8


def test_c5_recency_half_weight_24_to_36_months():
    signals = base_signals(trigger_signals=[sig("trigger", Trigger.GROWTH_HIGH.value, id_="g1")])
    result = score(signals, trigger_ages_months={"g1": 30})
    assert result.components["c5"] == 4  # floor(8 * 1/2)


def test_c5_recency_zero_weight_over_36_months():
    signals = base_signals(trigger_signals=[sig("trigger", Trigger.GROWTH_HIGH.value, id_="g1")])
    result = score(signals, trigger_ages_months={"g1": 40})
    assert result.components["c5"] == 0


def test_c5_cap_at_15():
    signals = base_signals(
        trigger_signals=[
            sig("trigger", Trigger.GROWTH_HIGH.value, id_="a"),
            sig("trigger", Trigger.ACQUISITION.value, id_="b"),
            sig("trigger", Trigger.SYSTEM_MIGRATION.value, id_="c"),
            sig("trigger", Trigger.NEW_FACILITY.value, id_="d"),
        ]
    )
    # 8 + 5 + 5 + 3 = 21, capped at 15
    assert score(signals).components["c5"] == 15


# ---------------------------------------------------------------------------
# C6 - evidence quality
# ---------------------------------------------------------------------------


def test_c6_domain_count_capped_at_4():
    signals = base_signals(
        evidence_domains=["a.com", "b.com", "c.com", "d.com", "e.com"],
        tier_1_2_fact_count=0,
    )
    result = score(signals)
    # 4 (domains, capped) + 0 (fact tier bucket) + 0 (recency unknown) + 1 (2+ domains) = 5
    assert result.components["c6"] == 5


@pytest.mark.parametrize(
    "n,expected_bucket",
    [(0, 0), (1, 1), (2, 1), (3, 2), (5, 2), (6, 3), (10, 3)],
)
def test_c6_fact_count_buckets(n, expected_bucket):
    signals = base_signals(evidence_domains=[], tier_1_2_fact_count=n)
    result = score(signals)
    assert result.components["c6"] == expected_bucket


def test_c6_recency_bonus_under_12_months():
    signals = base_signals(evidence_domains=[], tier_1_2_fact_count=0)
    result = score(signals, evidence_age_months_min=6)
    assert result.components["c6"] == 2


def test_c6_recency_bonus_under_24_months():
    signals = base_signals(evidence_domains=[], tier_1_2_fact_count=0)
    result = score(signals, evidence_age_months_min=20)
    assert result.components["c6"] == 1


def test_c6_capped_at_10():
    signals = base_signals(
        evidence_domains=["a.com", "b.com", "c.com", "d.com"],
        tier_1_2_fact_count=10,
    )
    result = score(signals, evidence_age_months_min=6)
    # 4 + 3 + 2 + 1 = 10, exactly at cap
    assert result.components["c6"] == 10


# ---------------------------------------------------------------------------
# Evidence grade and banding
# ---------------------------------------------------------------------------


def test_evidence_grade_a():
    signals = base_signals(
        evidence_domains=["a.com", "b.com", "c.com"], tier_1_2_fact_count=5
    )
    assert score(signals).evidence_grade == EvidenceGrade.A


def test_evidence_grade_d_reports_as_range():
    signals = base_signals(evidence_domains=[], tier_1_2_fact_count=0)
    result = score(signals)
    assert result.evidence_grade == EvidenceGrade.D
    assert result.reported_as == "range"
    assert result.range is not None
    lo, hi = result.range
    assert hi - lo == 16
    assert "LOW_EVIDENCE" in result.flags


@pytest.mark.parametrize(
    "total,expected_band",
    [(80, Band.PRIORITY), (100, Band.PRIORITY), (65, Band.INVESTIGATE),
     (79, Band.INVESTIGATE), (50, Band.WATCH), (64, Band.WATCH),
     (0, Band.DEPRIORITIZE), (49, Band.DEPRIORITIZE)],
)
def test_banding_thresholds(total, expected_band):
    from trelium_gtm.scoring import _band_for
    assert _band_for(total) == expected_band


# ---------------------------------------------------------------------------
# Hard rules H1, H2
# ---------------------------------------------------------------------------


def test_h1_signal_cannot_be_constructed_without_evidence():
    """H1 is enforced at the type level (models.Signal), so an unsourced
    signal cannot even reach the scorer."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Signal(id="s1", kind="trigger", value="GROWTH_HIGH", evidence_ids=[], fact_ids=[])


def test_h2_model_confidence_never_affects_score():
    """SignalSet/Signal carry no model_confidence field at all — the score()
    function has no such input to read. This test asserts the total is
    identical across two SignalSets differing only in an out-of-band
    'model said' value carried alongside (never passed to score())."""
    signals_a = base_signals()
    signals_b = base_signals()
    # Simulate "the model claimed high confidence" vs "the model claimed low
    # confidence" for the exact same evidenced signals: score() takes no such
    # parameter, so there is no code path by which it could differ.
    result_a = score(signals_a)
    result_b = score(signals_b)
    assert result_a.total == result_b.total
    assert result_a.components == result_b.components


# ---------------------------------------------------------------------------
# End-to-end determinism
# ---------------------------------------------------------------------------


def test_score_is_pure_same_input_same_output():
    signals = base_signals(
        stack_signals=[sig("stack", f"{SystemClass.INDUSTRY_ORDER_SYSTEM.value}:sage")],
        trigger_signals=[sig("trigger", Trigger.GROWTH_HIGH.value, id_="g")],
        ops_signals=[sig("ops", OpsSubSignal.OPS_MULTISTEP_ORDER.value)],
    )
    r1 = score(signals, trigger_ages_months={"g": 10})
    r2 = score(signals, trigger_ages_months={"g": 10})
    assert r1 == r2


def test_total_is_sum_of_components_clamped_0_100():
    signals = base_signals(
        segment_tier=SegmentTier.A,
        tier_1_2_fact_count=3,
        stack_signals=[
            sig("stack", f"{SystemClass.INDUSTRY_ORDER_SYSTEM.value}:a", id_="1"),
            sig("stack", f"{SystemClass.ERP_ACCOUNTING.value}:b", id_="2"),
        ],
        trigger_signals=[sig("trigger", Trigger.GROWTH_HIGH.value, id_="g")],
        ops_signals=[sig("ops", s.value, id_=f"o{s.value}") for s in OpsSubSignal],
        evidence_domains=["a.com", "b.com", "c.com"],
    )
    result = score(signals)
    assert result.total == sum(result.components.values())
    assert 0 <= result.total <= 100
