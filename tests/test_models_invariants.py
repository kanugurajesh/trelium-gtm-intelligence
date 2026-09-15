"""Phase 0 exit tests: the fact/inference separation is enforced at the type
boundary, not by convention. See CLAUDE.md R4, R7 and EVIDENCE_MODEL.md.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from trelium_gtm.models import (
    AccountBrief,
    Evidence,
    Fact,
    Inference,
    Signal,
    ValidationQuestion,
)
from trelium_gtm.taxonomy import SourceTier


def make_evidence(id_="ev_1") -> Evidence:
    return Evidence(
        id=id_,
        source_url="https://example.com/about",
        source_tier=SourceTier.COMPANY_PRIMARY,
        publisher="Company website",
        title="About",
        retrieved_at="2026-01-01T00:00:00Z",
        snapshot_path=f"evidence/raw/{id_}.txt",
        content_sha256="0" * 64,
        quote="We are a leading promotional products distributor.",
        quote_offset=10,
    )


def test_fact_requires_at_least_one_evidence_id():
    with pytest.raises(ValidationError):
        Fact(id="fct_1", statement="x", evidence_ids=[])


def test_fact_with_evidence_id_constructs():
    f = Fact(id="fct_1", statement="x", evidence_ids=["ev_1"])
    assert f.kind == "fact"


def test_inference_requires_at_least_one_fact_id():
    with pytest.raises(ValidationError):
        Inference(
            id="inf_1",
            statement="x may be worth investigating",
            from_fact_ids=[],
            rule="ICP.WF.TEST",
            model_confidence="low",
            validation_question_ids=["vq_1"],
        )


def test_inference_requires_at_least_one_validation_question():
    with pytest.raises(ValidationError):
        Inference(
            id="inf_1",
            statement="x may be worth investigating",
            from_fact_ids=["fct_1"],
            rule="ICP.WF.TEST",
            model_confidence="low",
            validation_question_ids=[],
        )


def test_signal_requires_at_least_one_evidence_id():
    with pytest.raises(ValidationError):
        Signal(id="sig_1", kind="segment", value="A", evidence_ids=[], fact_ids=[])


def test_evidence_quote_must_not_be_empty():
    with pytest.raises(ValidationError):
        Evidence(
            id="ev_x",
            source_url="https://example.com",
            source_tier=SourceTier.COMPANY_PRIMARY,
            publisher="Company website",
            title="X",
            retrieved_at="2026-01-01T00:00:00Z",
            snapshot_path="evidence/raw/ev_x.txt",
            content_sha256="0" * 64,
            quote="   ",
            quote_offset=0,
        )


def test_account_brief_rejects_fact_with_unresolved_evidence():
    with pytest.raises(ValidationError):
        AccountBrief(
            company="Acme Test Distributor",
            domain="acme-test.example",
            corpus_hash="deadbeef",
            evidence=[],
            facts=[Fact(id="fct_1", statement="x", evidence_ids=["ev_missing"])],
        )


def test_account_brief_facts_field_cannot_hold_an_inference():
    """The type-level guarantee CLAUDE.md R4 and EVIDENCE_MODEL.md section 5
    rely on: an Inference cannot be smuggled into AccountBrief.facts, because
    Fact.kind is a Literal["fact"] and Inference.kind is Literal["inference"].
    """
    inf = Inference(
        id="inf_1",
        statement="x may be worth investigating",
        from_fact_ids=["fct_1"],
        rule="ICP.WF.TEST",
        model_confidence="low",
        validation_question_ids=["vq_1"],
    )
    with pytest.raises(ValidationError):
        AccountBrief(
            company="Acme Test Distributor",
            domain="acme-test.example",
            corpus_hash="deadbeef",
            facts=[inf],  # type: ignore[list-item]
        )


def test_account_brief_valid_construction_round_trips():
    ev = make_evidence()
    fact = Fact(id="fct_1", statement="x is a distributor", evidence_ids=[ev.id])
    vq = ValidationQuestion(
        id="vq_1",
        question="How are POs currently entered?",
        tests_inference_id="inf_1",
        kills_if="Customers submit through a portal that writes directly to the order system.",
    )
    inf = Inference(
        id="inf_1",
        statement="Order entry may be worth investigating at x",
        from_fact_ids=[fact.id],
        rule="ICP.WF.PO_ORDER_ENTRY",
        model_confidence="medium",
        validation_question_ids=[vq.id],
    )
    brief = AccountBrief(
        company="Acme Test Distributor",
        domain="acme-test.example",
        corpus_hash="deadbeef",
        evidence=[ev],
        facts=[fact],
        inferences=[inf],
        validation_questions=[vq],
    )
    assert brief.facts[0].kind == "fact"
    assert brief.inferences[0].kind == "inference"


def test_account_brief_rejects_workflow_hypothesis_with_unresolved_inference():
    from trelium_gtm.models import WorkflowHypothesis
    from trelium_gtm.taxonomy import WorkflowID

    with pytest.raises(ValidationError):
        AccountBrief(
            company="Acme Test Distributor",
            domain="acme-test.example",
            corpus_hash="deadbeef",
            workflow_hypotheses=[
                WorkflowHypothesis(
                    workflow_id=WorkflowID.PO_ORDER_ENTRY,
                    inference_id="inf_missing",
                    boundary_count=3,
                    confidence="medium",
                    persona="COO",
                    persona_rationale="test",
                )
            ],
        )
