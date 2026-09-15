"""Coverage analysis tests: counts and breakdowns over a synthetic set of
briefs with known workflow hypotheses."""

from __future__ import annotations

from trelium_gtm.coverage import compute_coverage, render_coverage_markdown
from trelium_gtm.models import AccountBrief, Inference, SignalSet, ValidationQuestion, WorkflowHypothesis
from trelium_gtm.taxonomy import ScaleBand, SegmentLabel, WorkflowID


def make_brief_with_hypotheses(company: str, workflow_ids: list[WorkflowID], scale=ScaleBand.SWEET_SPOT, segment=SegmentLabel.PROMO_DISTRIBUTOR) -> AccountBrief:
    inferences = []
    vqs = []
    whs = []
    for i, wf in enumerate(workflow_ids):
        vq = ValidationQuestion(id=f"vq_{company}_{i}", question="q", tests_inference_id=f"inf_{company}_{i}", kills_if="k")
        inf = Inference(
            id=f"inf_{company}_{i}",
            statement="may be worth investigating",
            from_fact_ids=["fct_1"],
            rule=f"ICP.WF.{wf.value}",
            model_confidence="high",
            validation_question_ids=[vq.id],
        )
        wh = WorkflowHypothesis(
            workflow_id=wf, inference_id=inf.id, boundary_count=1, confidence="high",
            persona="COO", persona_rationale="r",
        )
        inferences.append(inf)
        vqs.append(vq)
        whs.append(wh)
    from trelium_gtm.models import Evidence, Fact
    from trelium_gtm.taxonomy import SourceTier

    ev = Evidence(
        id="ev_1", source_url="https://x.example", source_tier=SourceTier.COMPANY_PRIMARY,
        publisher="p", title="t", retrieved_at="2026-01-01T00:00:00Z",
        snapshot_path="e", content_sha256="0" * 64, quote="q", quote_offset=0,
    )
    fact = Fact(id="fct_1", statement="x", evidence_ids=["ev_1"])
    return AccountBrief(
        company=company, domain=f"{company}.example", corpus_hash="x",
        evidence=[ev], facts=[fact], inferences=inferences, validation_questions=vqs,
        workflow_hypotheses=whs,
        signals=SignalSet(scale_band=scale, segment_label=segment),
    )


def test_compute_coverage_counts_occurrences_across_accounts():
    briefs = [
        make_brief_with_hypotheses("A", [WorkflowID.PO_ORDER_ENTRY, WorkflowID.QUOTING]),
        make_brief_with_hypotheses("B", [WorkflowID.PO_ORDER_ENTRY]),
    ]
    rows = compute_coverage(briefs)
    po_row = next(r for r in rows if r.workflow_id == WorkflowID.PO_ORDER_ENTRY)
    quoting_row = next(r for r in rows if r.workflow_id == WorkflowID.QUOTING)
    assert po_row.total_count == 2
    assert quoting_row.total_count == 1


def test_compute_coverage_includes_all_nine_workflows_even_at_zero():
    briefs = [make_brief_with_hypotheses("A", [WorkflowID.PO_ORDER_ENTRY])]
    rows = compute_coverage(briefs)
    assert len(rows) == 9
    zero_rows = [r for r in rows if r.total_count == 0]
    assert len(zero_rows) == 8


def test_compute_coverage_sorted_by_count_descending():
    briefs = [
        make_brief_with_hypotheses("A", [WorkflowID.PO_ORDER_ENTRY]),
        make_brief_with_hypotheses("B", [WorkflowID.PO_ORDER_ENTRY]),
        make_brief_with_hypotheses("C", [WorkflowID.QUOTING]),
    ]
    rows = compute_coverage(briefs)
    assert rows[0].workflow_id == WorkflowID.PO_ORDER_ENTRY
    assert rows[0].total_count == 2


def test_render_coverage_markdown_includes_table_and_detail():
    briefs = [make_brief_with_hypotheses("A", [WorkflowID.PO_ORDER_ENTRY])]
    rows = compute_coverage(briefs)
    out = render_coverage_markdown(rows, total_accounts=1)
    assert "# Workflow Coverage Analysis" in out
    assert "WF_PO_ORDER_ENTRY" in out
    assert "## Detail" in out
