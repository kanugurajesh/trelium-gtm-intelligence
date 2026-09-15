"""Markdown brief renderer. Three sections, three types, no code path that
can mix them (docs/EVIDENCE_MODEL.md section 5): this function reads only
``brief.facts`` for the verified-facts section and only
``brief.inferences``/``brief.workflow_hypotheses`` for the hypothesis
section. There is no shared list an Inference could be appended to that
would render it as a Fact.
"""

from __future__ import annotations

from trelium_gtm.models import AccountBrief, Inference, WorkflowHypothesis
from trelium_gtm.taxonomy import WORKFLOW_TO_TRELIUM_AGENT

CRM_DEDUP_BANNER = (
    "> **Before any outreach:** this account has NOT been checked against Trelium's CRM "
    "or active pipeline. This tool has no visibility into existing customers, prospects "
    "or in-flight conversations. De-duplicate before contacting anyone."
)


def _score_block(brief: AccountBrief) -> str:
    score = brief.score
    if score.status == "OUT_OF_ICP":
        return "**Status: OUT OF ICP** — excluded from ranking at the segment gate.\n"
    if score.status == "INSUFFICIENT_EVIDENCE":
        return "**Status: INSUFFICIENT EVIDENCE** — no usable public evidence was collected.\n"

    lines = []
    if score.reported_as == "range" and score.range:
        lines.append(f"## Fit score: {score.range[0]}-{score.range[1]} / 100 (range — low evidence grade)")
    else:
        lines.append(f"## Fit score: {score.total} / 100 — {score.band.value if score.band else '?'}")
    lines.append("")
    lines.append(f"Evidence grade: **{score.evidence_grade.value}**")
    if score.flags:
        lines.append(f"Flags: {', '.join(score.flags)}")
    lines.append("")
    lines.append("| Component | Points |")
    lines.append("|---|---|")
    labels = {
        "c1": "Core vertical fit (0-25)",
        "c2": "Operational complexity (0-20)",
        "c3": "Software/ecosystem signals (0-15)",
        "c4": "Transaction/org scale (0-15)",
        "c5": "Growth/buying trigger (0-15)",
        "c6": "Evidence quality (0-10)",
    }
    for key, label in labels.items():
        lines.append(f"| {label} | {score.components.get(key, 0)} |")
    return "\n".join(lines) + "\n"


def _inference_for(brief: AccountBrief, inference_id: str) -> Inference | None:
    for inf in brief.inferences:
        if inf.id == inference_id:
            return inf
    return None


def _workflow_block(brief: AccountBrief) -> str:
    if not brief.workflow_hypotheses:
        return "## Workflow opportunity\n\nNo workflow hypothesis was generated for this account.\n"

    ranked = sorted(brief.workflow_hypotheses, key=lambda wh: -wh.boundary_count)
    lines = ["## Workflow opportunities (ranked)\n"]
    for rank, wh in enumerate(ranked, start=1):
        inf = _inference_for(brief, wh.inference_id)
        agent = WORKFLOW_TO_TRELIUM_AGENT.get(wh.workflow_id, wh.workflow_id.value)
        lines.append(f"### {rank}. {wh.workflow_id.value} — {agent}")
        lines.append(f"Confidence: **{wh.confidence}** | System boundaries crossed: {wh.boundary_count}")
        lines.append("")
        if inf:
            lines.append(f"**Hypothesis:** {inf.statement}")
            lines.append("")
            lines.append(f"*Supporting rule:* `{inf.rule}` (model-stated confidence: {inf.model_confidence})")
        lines.append("")
        lines.append(f"**Persona:** {wh.persona}")
        lines.append(f"*Why this role:* {wh.persona_rationale}")
        lines.append("")
        vqs = [q for q in brief.validation_questions if inf and q.id in inf.validation_question_ids]
        if vqs:
            lines.append("**Validate before outreach:**")
            for q in vqs:
                lines.append(f"- {q.question}")
                lines.append(f"  - *Kills the hypothesis if:* {q.kills_if}")
        lines.append("")
    return "\n".join(lines)


def _evidence_block(brief: AccountBrief) -> str:
    if not brief.facts:
        return "## Verified facts\n\nNone.\n"
    lines = ["## Verified facts\n"]
    evidence_by_id = {e.id: e for e in brief.evidence}
    for i, fact in enumerate(brief.facts, start=1):
        lines.append(f"**[{i}]** {fact.statement}")
        for eid in fact.evidence_ids:
            ev = evidence_by_id.get(eid)
            if ev:
                lines.append(
                    f"  - Source: [{ev.publisher}]({ev.source_url}) "
                    f"(retrieved {ev.retrieved_at[:10]}, tier {int(ev.source_tier)}) — "
                    f'"{ev.quote}"'
                )
        lines.append("")
    return "\n".join(lines)


def _gaps_block(brief: AccountBrief) -> str:
    if not brief.research_gaps:
        return ""
    lines = ["## Research gaps\n"]
    for gap in brief.research_gaps:
        lines.append(f"- {gap}")
    return "\n".join(lines) + "\n"


def render_brief_markdown(brief: AccountBrief) -> str:
    parts = [
        f"# {brief.company}\n",
        f"Domain: `{brief.domain}` | Corpus hash: `{brief.corpus_hash[:12]}`\n",
        CRM_DEDUP_BANNER,
        "",
        _score_block(brief),
        "",
        _workflow_block(brief),
        "",
        _evidence_block(brief),
        "",
        _gaps_block(brief),
    ]
    return "\n".join(p for p in parts if p is not None)
