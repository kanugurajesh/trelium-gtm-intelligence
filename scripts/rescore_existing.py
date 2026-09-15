"""Offline, deterministic re-score of already-generated briefs.

Does NO fresh research and NO model calls: it re-derives signals from the
facts and evidence already stored in each output/briefs/*.json, re-scores
them with the current scoring.py, rewrites the brief (JSON + Markdown), and
writes docs/RESCORE_COMPARISON.md listing every account's old score, new
score, difference and the reason. Workflow hypotheses, facts and evidence
are left exactly as they were.

The "as of" date used for recency is taken from each brief's own evidence
retrieval date, so replaying this script later yields identical numbers.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from trelium_gtm.models import AccountBrief  # noqa: E402
from trelium_gtm.ranking import rank  # noqa: E402
from trelium_gtm.render.json_out import render_brief_json  # noqa: E402
from trelium_gtm.render.markdown import render_brief_markdown  # noqa: E402
from trelium_gtm.scoring import score as score_signals  # noqa: E402
from trelium_gtm.signals import (  # noqa: E402
    compute_evidence_age_months_max,
    compute_trigger_ages_months,
    conflict_gaps,
    derive_signals,
)

BRIEFS_DIR = REPO_ROOT / "output" / "briefs"
COMPONENT_LABELS = {
    "c1": "core vertical fit", "c2": "operational complexity", "c3": "software/ecosystem",
    "c4": "scale", "c5": "growth trigger", "c6": "evidence quality",
}


def _as_of(brief: AccountBrief) -> date:
    if brief.evidence:
        return date.fromisoformat(min(e.retrieved_at for e in brief.evidence)[:10])
    return date(2026, 9, 15)


def _reason(old: AccountBrief, new: AccountBrief) -> str:
    if old.score.status != new.score.status:
        return f"status {old.score.status} -> {new.score.status}"
    if old.score.status != "SCORED":
        return "not scored (unchanged)"
    parts = []
    for key, label in COMPONENT_LABELS.items():
        o, n = old.score.components.get(key, 0), new.score.components.get(key, 0)
        if o != n:
            parts.append(f"{label} {o}->{n}")
    new_flags = sorted(set(new.score.flags) - set(old.score.flags))
    if new_flags:
        parts.append("new flags: " + ", ".join(new_flags))
    if not parts:
        return "no change"
    if new.signals.segment_conflict == "unresolved" and any(p.startswith("core vertical fit") for p in parts):
        parts.append("(unresolved segment conflict penalty)")
    if any(p.startswith("evidence quality") for p in parts):
        parts.append("(duplicate claims now counted once)")
    return "; ".join(parts)


def main() -> None:
    rows = []
    old_briefs: list[AccountBrief] = []
    new_briefs: list[AccountBrief] = []

    for path in sorted(BRIEFS_DIR.glob("*.json")):
        old = AccountBrief.model_validate_json(path.read_text(encoding="utf-8"))
        as_of = _as_of(old)
        signals = derive_signals(
            old.facts, old.evidence,
            is_public_customer=old.signals.is_public_customer,
            is_ecosystem_ambiguous=old.signals.is_ecosystem_ambiguous,
        )
        result = score_signals(
            signals,
            trigger_ages_months=compute_trigger_ages_months(signals, as_of),
            evidence_age_months_max=compute_evidence_age_months_max(old.evidence, as_of),
        )
        gaps = [g for g in old.research_gaps if "CONFLICT" not in g and "conflict resolved" not in g]
        gaps.extend(conflict_gaps(signals, old.evidence))
        new = AccountBrief.model_validate(
            old.model_copy(
                update={"signals": signals, "score": result, "flags": list(result.flags), "research_gaps": gaps}
            ).model_dump()
        )
        path.write_text(render_brief_json(new), encoding="utf-8", newline="\n")
        path.with_suffix(".md").write_text(render_brief_markdown(new), encoding="utf-8", newline="\n")
        old_briefs.append(old)
        new_briefs.append(new)
        rows.append((old.company, old.score.total, new.score.total, _reason(old, new)))

    old_rank = {b.company: i for i, b in enumerate(rank(old_briefs), start=1)}
    new_rank = {b.company: i for i, b in enumerate(rank(new_briefs), start=1)}

    lines = [
        "# Re-score Comparison (offline replay, no fresh research)\n",
        "Re-derived from the facts/evidence already committed in `output/briefs/*.json` after the ",
        "correctness-hardening changes (deduplication + contradiction policy). No pages were ",
        "re-fetched and no model calls were made.\n",
        "| Company | Old score | New score | Diff | Old rank | New rank | Reason |",
        "|---|---|---|---|---|---|---|",
    ]
    changed = 0
    for company, o, n, reason in sorted(rows, key=lambda r: (-(r[2] if r[2] is not None else -1), r[0])):
        diff = (n - o) if (o is not None and n is not None) else 0
        if o != n or old_rank[company] != new_rank[company]:
            changed += 1
        lines.append(
            f"| {company} | {o} | {n} | {diff:+d} | {old_rank[company]} | {new_rank[company]} | {reason} |"
        )
    lines.append("")
    lines.append(f"**{changed} of {len(rows)} accounts changed score or rank.**")
    (REPO_ROOT / "docs" / "RESCORE_COMPARISON.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
