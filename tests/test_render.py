"""Render tests: the CRM banner is always present, and the markdown/JSON
renderers cannot mix facts and inferences because they read from separate
typed lists (models.py already guarantees this at construction; these tests
check the renderer actually surfaces both sections correctly)."""

from __future__ import annotations

from trelium_gtm.models import (
    AccountBrief,
    Evidence,
    Fact,
    Inference,
    ScoreResult,
    SignalSet,
    ValidationQuestion,
    WorkflowHypothesis,
)
from trelium_gtm.render.json_out import render_brief_json
from trelium_gtm.render.markdown import CRM_DEDUP_BANNER, render_brief_markdown
from trelium_gtm.taxonomy import Band, EvidenceGrade, SourceTier, WorkflowID


def make_full_brief() -> AccountBrief:
    ev = Evidence(
        id="ev_1",
        source_url="https://acme-test.example/about",
        source_tier=SourceTier.COMPANY_PRIMARY,
        publisher="Company website",
        title="About",
        retrieved_at="2026-01-01T00:00:00Z",
        snapshot_path="evidence/raw/ev_1.txt",
        content_sha256="0" * 64,
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
    vq = ValidationQuestion(
        id="vq_1",
        question="How are POs currently entered?",
        tests_inference_id="inf_1",
        kills_if="They already flow automatically into the order system.",
    )
    inf = Inference(
        id="inf_1",
        statement="PO entry may be worth investigating at Acme Test Distributor.",
        from_fact_ids=["fct_1"],
        rule="ICP.WF.WF_PO_ORDER_ENTRY",
        model_confidence="medium",
        validation_question_ids=["vq_1"],
    )
    wh = WorkflowHypothesis(
        workflow_id=WorkflowID.PO_ORDER_ENTRY,
        inference_id="inf_1",
        boundary_count=2,
        confidence="medium",
        persona="COO / VP Operations",
        persona_rationale="Smaller distributors are typically hands-on operationally.",
    )
    score = ScoreResult(
        status="SCORED",
        total=72,
        components={"c1": 25, "c2": 10, "c3": 10, "c4": 15, "c5": 7, "c6": 5},
        evidence_grade=EvidenceGrade.B,
        band=Band.INVESTIGATE,
    )
    return AccountBrief(
        company="Acme Test Distributor",
        domain="acme-test.example",
        corpus_hash="deadbeefcafefeed",
        facts=[fact],
        inferences=[inf],
        validation_questions=[vq],
        workflow_hypotheses=[wh],
        evidence=[ev],
        signals=SignalSet(),
        score=score,
        research_gaps=["Not de-duplicated against Trelium CRM"],
    )


def test_markdown_includes_crm_banner():
    brief = make_full_brief()
    out = render_brief_markdown(brief)
    assert CRM_DEDUP_BANNER in out


def test_markdown_hypothesis_statement_appears_in_workflow_section_not_facts_section():
    brief = make_full_brief()
    out = render_brief_markdown(brief)
    facts_section = out.split("## Verified facts")[1].split("## Research gaps")[0]
    workflow_section = out.split("## Workflow opportunities")[1].split("## Verified facts")[0]
    assert "PO entry may be worth investigating" in workflow_section
    assert "PO entry may be worth investigating" not in facts_section


def test_markdown_shows_score_and_band():
    out = render_brief_markdown(make_full_brief())
    assert "72 / 100" in out
    assert "INVESTIGATE" in out


def test_markdown_shows_validation_question_and_kills_if():
    out = render_brief_markdown(make_full_brief())
    assert "How are POs currently entered?" in out
    assert "Kills the hypothesis if" in out


def test_markdown_out_of_icp_status_shown():
    brief = make_full_brief().model_copy(
        update={"score": ScoreResult(status="OUT_OF_ICP", evidence_grade=EvidenceGrade.D)}
    )
    out = render_brief_markdown(brief)
    assert "OUT OF ICP" in out


def test_json_render_round_trips_through_pydantic():
    brief = make_full_brief()
    raw = render_brief_json(brief)
    reloaded = AccountBrief.model_validate_json(raw)
    assert reloaded.company == brief.company
    assert reloaded.score.total == brief.score.total
    assert len(reloaded.facts) == 1
    assert len(reloaded.inferences) == 1
