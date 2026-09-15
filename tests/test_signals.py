"""Phase 3 exit test: hand-written facts for a synthetic company produce the
exact expected SignalSet, and scoring that SignalSet matches a hand-computed
number. One end-to-end arithmetic check nobody can argue with.
"""

from __future__ import annotations

from trelium_gtm.models import Evidence, Fact
from trelium_gtm.scoring import score
from trelium_gtm.signals import (
    compute_evidence_age_months_max,
    compute_trigger_ages_months,
    derive_signals,
)
from trelium_gtm.taxonomy import (
    ScaleBand,
    SegmentLabel,
    SegmentTier,
    SourceTier,
    SystemClass,
)


def ev(id_, url, tier, published_at=None) -> Evidence:
    return Evidence(
        id=id_,
        source_url=url,
        source_tier=tier,
        publisher="test",
        title="test",
        retrieved_at="2026-01-01T00:00:00Z",
        published_at=published_at,
        snapshot_path=f"evidence/raw/{id_}.txt",
        content_sha256="0" * 64,
        quote="placeholder quote text",
        quote_offset=0,
    )


def test_derive_signals_from_synthetic_company_fixture():
    evidence = [
        ev("ev_1", "https://acme-test.example/about", SourceTier.COMPANY_PRIMARY),
        ev("ev_2", "https://www.ppai.org/media/ppai-100/", SourceTier.INDUSTRY_ASSOCIATION),
        ev(
            "ev_3",
            "https://acme-test.example/careers",
            SourceTier.COMPANY_PRIMARY,
            published_at="2025-08-01T00:00:00Z",
        ),
    ]
    facts = [
        Fact(
            id="fct_segment",
            statement="Acme Test Distributor is a promotional products distributor",
            evidence_ids=["ev_1"],
            field="segment",
            value=SegmentLabel.PROMO_DISTRIBUTOR.value,
        ),
        Fact(
            id="fct_revenue",
            statement="PPAI reports Acme Test Distributor at $87M",
            evidence_ids=["ev_2"],
            field="revenue_usd",
            value=87_000_000,
        ),
        Fact(
            id="fct_system_sage",
            statement="Careers page mentions SAGE",
            evidence_ids=["ev_3"],
            field="system",
            value="SAGE",
        ),
        Fact(
            id="fct_system_netsuite",
            statement="Careers page mentions NetSuite",
            evidence_ids=["ev_3"],
            field="system",
            value="NetSuite",
        ),
        Fact(
            id="fct_growth",
            statement="PPAI reports very high recent growth",
            evidence_ids=["ev_2"],
            field="trigger",
            value="GROWTH_HIGH",
        ),
        Fact(
            id="fct_hiring_1",
            statement="Open role: Order Entry Specialist",
            evidence_ids=["ev_3"],
            field="ops_hiring_role",
            value="Order Entry Specialist",
        ),
        Fact(
            id="fct_hiring_2",
            statement="Open role: AP Clerk",
            evidence_ids=["ev_3"],
            field="ops_hiring_role",
            value="AP Clerk",
        ),
        Fact(
            id="fct_ops_customization",
            statement="Site describes decoration and artwork approval workflow",
            evidence_ids=["ev_1"],
            field="ops_subsignal",
            value="OPS_CUSTOMIZATION",
        ),
    ]

    signals = derive_signals(facts, evidence)

    assert signals.segment_label == SegmentLabel.PROMO_DISTRIBUTOR
    assert signals.segment_tier == SegmentTier.A
    assert signals.scale_band == ScaleBand.SWEET_SPOT
    assert signals.scale_basis == "revenue"
    assert {s.value for s in signals.stack_signals} == {
        f"{SystemClass.INDUSTRY_ORDER_SYSTEM.value}:sage",
        f"{SystemClass.ERP_ACCOUNTING.value}:netsuite",
    }
    trigger_values = {s.value for s in signals.trigger_signals}
    assert "GROWTH_HIGH" in trigger_values
    assert "OPS_HIRING:2" in trigger_values
    assert len(signals.ops_signals) == 1
    assert signals.ops_signals[0].value == "OPS_CUSTOMIZATION"
    assert signals.tier_1_2_fact_count == len(facts)  # every fact here is tier 1 or 2
    assert signals.evidence_domains == ["acme-test.example", "ppai.org"]
    assert signals.has_any_evidence is True

    # Hand-computed score for this exact fixture:
    # C1 = 25 (tier A, tier1/2 evidence present)
    # C2 = 4  (OPS_CUSTOMIZATION only)
    # C3 = 6 (SAGE, industry order system, first-system points) + 5 (NetSuite,
    #         ERP, first-system points) + 3 (cross-boundary bonus, 2 classes) = 14
    # C4 = 15 (SWEET_SPOT, revenue basis)
    # C5 = 8 (GROWTH_HIGH) + 3 (OPS_HIRING with 2 roles) = 11
    # C6 = domains(2, capped 4->2) + tier1/2 bucket(8 facts -> 3) + recency
    #      (evidence ages: only ev_3 has published_at, evaluated separately)
    result = score(
        signals,
        trigger_ages_months=compute_trigger_ages_months(
            signals, as_of=__import__("datetime").date(2026, 1, 1)
        ),
        evidence_age_months_max=compute_evidence_age_months_max(
            evidence, as_of=__import__("datetime").date(2026, 1, 1)
        ),
    )
    assert result.components["c1"] == 25
    assert result.components["c2"] == 4
    assert result.components["c3"] == 14
    assert result.components["c4"] == 15
    assert result.components["c5"] == 11
    # C6: 2 domains (capped irrelevant, =2) + tier1/2 bucket for 8 facts (>=6 -> 3)
    #     + recency: only ev_3 is dated (2025-08-01); ev_1 and ev_2 are of
    #       unknown age, so "all key evidence under N months" cannot be
    #       claimed -> +0 (tests/test_recency.py covers the all-dated case)
    #     + 2+ domains bonus +1  => 2+3+0+1 = 6
    assert result.components["c6"] == 6
    assert result.total == 25 + 4 + 14 + 15 + 11 + 6
    assert result.status == "SCORED"


def test_derive_signals_ignores_unknown_system_names():
    evidence = [ev("ev_1", "https://acme-test.example/about", SourceTier.COMPANY_PRIMARY)]
    facts = [
        Fact(
            id="fct_1",
            statement="Uses SomeObscureTool",
            evidence_ids=["ev_1"],
            field="system",
            value="SomeObscureTool",
        )
    ]
    signals = derive_signals(facts, evidence)
    assert signals.stack_signals == []


def test_derive_signals_no_facts_yields_empty_signal_set_but_has_evidence_flag_false_without_evidence():
    signals = derive_signals([], [])
    assert signals.has_any_evidence is False
    assert signals.segment_tier == SegmentTier.UNRESOLVED
    assert signals.scale_band == ScaleBand.UNKNOWN


def test_derive_signals_headcount_fallback_used_only_without_revenue():
    evidence = [ev("ev_1", "https://acme-test.example/about", SourceTier.COMPANY_PRIMARY)]
    facts = [
        Fact(
            id="fct_headcount",
            statement="About 150 employees",
            evidence_ids=["ev_1"],
            field="employee_count",
            value=150,
        )
    ]
    signals = derive_signals(facts, evidence)
    assert signals.scale_basis == "headcount"
    assert signals.scale_band == ScaleBand.SWEET_SPOT


def test_derive_signals_revenue_takes_precedence_over_headcount():
    evidence = [ev("ev_1", "https://acme-test.example/about", SourceTier.COMPANY_PRIMARY)]
    facts = [
        Fact(
            id="fct_headcount",
            statement="About 5 employees",
            evidence_ids=["ev_1"],
            field="employee_count",
            value=5,
        ),
        Fact(
            id="fct_revenue",
            statement="Revenue of $100M",
            evidence_ids=["ev_1"],
            field="revenue_usd",
            value=100_000_000,
        ),
    ]
    signals = derive_signals(facts, evidence)
    assert signals.scale_basis == "revenue"
    assert signals.scale_band == ScaleBand.SWEET_SPOT


def test_out_of_icp_segment_flows_through_to_gate():
    evidence = [ev("ev_1", "https://acme-test.example/about", SourceTier.COMPANY_PRIMARY)]
    facts = [
        Fact(
            id="fct_segment",
            statement="Acme Test is a law firm",
            evidence_ids=["ev_1"],
            field="segment",
            value=SegmentLabel.OUT_OF_ICP.value,
        )
    ]
    signals = derive_signals(facts, evidence)
    assert signals.segment_tier == SegmentTier.X
    result = score(signals)
    assert result.status == "OUT_OF_ICP"
