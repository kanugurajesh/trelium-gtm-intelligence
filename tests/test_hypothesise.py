"""Hypothesis generation tests. Per CLAUDE.md R13, the API boundary is
monkeypatched — these assert taxonomy enforcement, I1/I2 invariants, the
hedging-linter regeneration loop, and deterministic persona/boundary lookup.
"""

from __future__ import annotations

from trelium_gtm import hypothesise as hyp_mod
from trelium_gtm.hypothesise import generate_hypotheses
from trelium_gtm.models import Fact, Signal, SignalSet
from trelium_gtm.taxonomy import ScaleBand, SegmentLabel, SegmentTier, SystemClass

FACTS = [
    Fact(id="fct_1", statement="Acme Test is a promotional products distributor", evidence_ids=["ev_1"], field="segment", value="promotional_products_distributor"),
    Fact(id="fct_2", statement="Careers page mentions SAGE", evidence_ids=["ev_2"], field="system", value="SAGE"),
]

SIGNALS = SignalSet(
    segment_label=SegmentLabel.PROMO_DISTRIBUTOR,
    segment_tier=SegmentTier.A,
    scale_band=ScaleBand.SWEET_SPOT,
    stack_signals=[
        Signal(id="s1", kind="stack", value=f"{SystemClass.INDUSTRY_ORDER_SYSTEM.value}:sage", evidence_ids=["ev_2"], fact_ids=["fct_2"]),
        Signal(id="s2", kind="stack", value=f"{SystemClass.ERP_ACCOUNTING.value}:netsuite", evidence_ids=["ev_2"], fact_ids=["fct_2"]),
    ],
    has_any_evidence=True,
)


def _patch_sequence(monkeypatch, payloads):
    calls = {"n": 0}

    def fake_call(system_prompt, user_prompt, model):
        idx = min(calls["n"], len(payloads) - 1)
        calls["n"] += 1
        return payloads[idx]

    monkeypatch.setattr(hyp_mod, "_call_openai", fake_call)
    return calls


def test_well_formed_hypothesis_is_accepted(monkeypatch, tmp_path):
    payload = {
        "hypotheses": [
            {
                "workflow_id": "WF_PO_ORDER_ENTRY",
                "statement": "Inbound PO handling may be worth investigating at Acme Test.",
                "reason": "Distributor segment with a named order system.",
                "from_fact_ids": ["fct_1", "fct_2"],
                "confidence": "medium",
                "validation_questions": [
                    {
                        "question": "How do incoming POs get entered today?",
                        "kills_if": "They already flow automatically into SAGE.",
                    }
                ],
            }
        ]
    }
    _patch_sequence(monkeypatch, [payload])
    outcome = generate_hypotheses(
        company="Acme Test Distributor", facts=FACTS, signals=SIGNALS, cache_dir=tmp_path / "cache"
    )
    assert len(outcome.inferences) == 1
    assert len(outcome.validation_questions) == 1
    assert len(outcome.workflow_hypotheses) == 1
    wh = outcome.workflow_hypotheses[0]
    assert wh.workflow_id.value == "WF_PO_ORDER_ENTRY"
    assert wh.boundary_count == 2  # two distinct non-generic system classes
    assert wh.persona  # deterministic persona lookup populated
    assert outcome.gaps == []


def test_unrecognised_workflow_id_is_dropped(monkeypatch, tmp_path):
    payload = {
        "hypotheses": [
            {
                "workflow_id": "WF_MADE_UP_WORKFLOW",
                "statement": "This may be worth investigating.",
                "from_fact_ids": ["fct_1"],
                "confidence": "low",
                "validation_questions": [{"question": "q", "kills_if": "k"}],
            }
        ]
    }
    _patch_sequence(monkeypatch, [payload])
    outcome = generate_hypotheses(
        company="Acme Test Distributor", facts=FACTS, signals=SIGNALS, cache_dir=tmp_path / "cache"
    )
    assert outcome.inferences == []
    assert any("unrecognised workflow_id" in g for g in outcome.gaps)


def test_hypothesis_with_only_unknown_fact_ids_is_dropped(monkeypatch, tmp_path):
    payload = {
        "hypotheses": [
            {
                "workflow_id": "WF_QUOTING",
                "statement": "Quoting may be worth investigating.",
                "from_fact_ids": ["fct_does_not_exist"],
                "confidence": "low",
                "validation_questions": [{"question": "q", "kills_if": "k"}],
            }
        ]
    }
    _patch_sequence(monkeypatch, [payload])
    outcome = generate_hypotheses(
        company="Acme Test Distributor", facts=FACTS, signals=SIGNALS, cache_dir=tmp_path / "cache"
    )
    assert outcome.inferences == []
    assert any("no valid from_fact_ids" in g for g in outcome.gaps)


def test_hypothesis_with_no_validation_question_is_dropped(monkeypatch, tmp_path):
    payload = {
        "hypotheses": [
            {
                "workflow_id": "WF_QUOTING",
                "statement": "Quoting may be worth investigating.",
                "from_fact_ids": ["fct_1"],
                "confidence": "low",
                "validation_questions": [],
            }
        ]
    }
    _patch_sequence(monkeypatch, [payload])
    outcome = generate_hypotheses(
        company="Acme Test Distributor", facts=FACTS, signals=SIGNALS, cache_dir=tmp_path / "cache"
    )
    assert outcome.inferences == []
    assert any("no validation question" in g for g in outcome.gaps)


def test_assertive_statement_triggers_regeneration_and_succeeds(monkeypatch, tmp_path):
    first = {
        "hypotheses": [
            {
                "workflow_id": "WF_PO_ORDER_ENTRY",
                "statement": "Acme Test manually enters purchase orders.",  # assertive, fails lint
                "from_fact_ids": ["fct_1"],
                "confidence": "medium",
                "validation_questions": [{"question": "q", "kills_if": "k"}],
            }
        ]
    }
    second = {
        "hypotheses": [
            {
                "workflow_id": "WF_PO_ORDER_ENTRY",
                "statement": "PO entry may be worth investigating at Acme Test.",  # hedged
                "from_fact_ids": ["fct_1"],
                "confidence": "medium",
                "validation_questions": [{"question": "q", "kills_if": "k"}],
            }
        ]
    }
    calls = _patch_sequence(monkeypatch, [first, second])
    outcome = generate_hypotheses(
        company="Acme Test Distributor", facts=FACTS, signals=SIGNALS, cache_dir=tmp_path / "cache"
    )
    assert calls["n"] == 2
    assert len(outcome.inferences) == 1
    assert outcome.inferences[0].statement == "PO entry may be worth investigating at Acme Test."


def test_assertive_statement_still_failing_after_regeneration_is_dropped(monkeypatch, tmp_path):
    always_assertive = {
        "hypotheses": [
            {
                "workflow_id": "WF_PO_ORDER_ENTRY",
                "statement": "Acme Test manually enters purchase orders.",
                "from_fact_ids": ["fct_1"],
                "confidence": "medium",
                "validation_questions": [{"question": "q", "kills_if": "k"}],
            }
        ]
    }
    calls = _patch_sequence(monkeypatch, [always_assertive, always_assertive])
    outcome = generate_hypotheses(
        company="Acme Test Distributor", facts=FACTS, signals=SIGNALS, cache_dir=tmp_path / "cache"
    )
    assert calls["n"] == 2
    assert outcome.inferences == []
    assert any("after one regeneration attempt" in g for g in outcome.gaps)


def test_no_facts_returns_empty_outcome_with_no_api_call(monkeypatch, tmp_path):
    calls = _patch_sequence(monkeypatch, [{"hypotheses": []}])
    outcome = generate_hypotheses(
        company="Acme Test Distributor", facts=[], signals=SIGNALS, cache_dir=tmp_path / "cache"
    )
    assert calls["n"] == 0
    assert outcome.inferences == []
    assert outcome.gaps
