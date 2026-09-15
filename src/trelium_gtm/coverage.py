"""Workflow coverage analysis: across the scored portfolio, how often is
each taxonomy workflow hypothesised, and at what confidence? See
docs/SCORING.md section 12 and docs/PROJECT_SPEC.md section 10 (objection 2).

Answers a question a GTM reader can act on directly: which of Trelium's
published agents can be targeted from public evidence, and which cannot.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field as dataclass_field

from trelium_gtm.models import AccountBrief
from trelium_gtm.taxonomy import WORKFLOW_TO_TRELIUM_AGENT, WorkflowID


@dataclass
class WorkflowCoverageRow:
    workflow_id: WorkflowID
    trelium_agent: str
    total_count: int
    by_confidence: dict[str, int] = dataclass_field(default_factory=dict)
    by_scale_band: dict[str, int] = dataclass_field(default_factory=dict)
    by_segment_label: dict[str, int] = dataclass_field(default_factory=dict)
    example_companies: list[str] = dataclass_field(default_factory=list)


def compute_coverage(briefs: list[AccountBrief], examples_per_workflow: int = 3) -> list[WorkflowCoverageRow]:
    rows: dict[WorkflowID, WorkflowCoverageRow] = {
        wf: WorkflowCoverageRow(workflow_id=wf, trelium_agent=WORKFLOW_TO_TRELIUM_AGENT[wf], total_count=0)
        for wf in WorkflowID
    }
    confidence_counters: dict[WorkflowID, Counter] = {wf: Counter() for wf in WorkflowID}
    scale_counters: dict[WorkflowID, Counter] = {wf: Counter() for wf in WorkflowID}
    segment_counters: dict[WorkflowID, Counter] = {wf: Counter() for wf in WorkflowID}

    for brief in briefs:
        for wh in brief.workflow_hypotheses:
            row = rows[wh.workflow_id]
            row.total_count += 1
            confidence_counters[wh.workflow_id][wh.confidence] += 1
            scale_counters[wh.workflow_id][brief.signals.scale_band.value] += 1
            segment_counters[wh.workflow_id][brief.signals.segment_label.value] += 1
            if len(row.example_companies) < examples_per_workflow:
                row.example_companies.append(brief.company)

    for wf, row in rows.items():
        row.by_confidence = dict(confidence_counters[wf])
        row.by_scale_band = dict(scale_counters[wf])
        row.by_segment_label = dict(segment_counters[wf])

    return sorted(rows.values(), key=lambda r: (-r.total_count, r.workflow_id.value))


def render_coverage_markdown(rows: list[WorkflowCoverageRow], total_accounts: int) -> str:
    lines = [
        "# Workflow Coverage Analysis\n",
        f"Across {total_accounts} scored accounts, how often was each Trelium-mapped "
        "workflow hypothesised, and at what confidence?\n",
        "| Workflow | Trelium agent | Count | High conf. | Medium conf. | Low conf. |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row.workflow_id.value} | {row.trelium_agent} | {row.total_count} | "
            f"{row.by_confidence.get('high', 0)} | {row.by_confidence.get('medium', 0)} | "
            f"{row.by_confidence.get('low', 0)} |"
        )
    lines.append("")
    lines.append("## Detail\n")
    for row in rows:
        lines.append(f"### {row.workflow_id.value} — {row.trelium_agent}")
        lines.append(f"Hypothesised {row.total_count} time(s).")
        if row.example_companies:
            lines.append(f"Examples: {', '.join(row.example_companies)}")
        if row.by_scale_band:
            lines.append(f"By scale band: {row.by_scale_band}")
        lines.append("")
    return "\n".join(lines)
