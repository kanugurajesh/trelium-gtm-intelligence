"""One-off driver: loads all generated briefs and writes docs/VALIDATION.md
and docs/COVERAGE.md. Not a CLI subcommand — this is analysis code that
runs once per real batch, not part of the small permanent interface
(CLAUDE.md R17).
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from trelium_gtm.coverage import compute_coverage, render_coverage_markdown  # noqa: E402
from trelium_gtm.models import AccountBrief  # noqa: E402
from trelium_gtm.ranking import rank  # noqa: E402
from trelium_gtm.validate import ablate, spearman_rho  # noqa: E402

BRIEFS_DIR = REPO_ROOT / "output" / "briefs"
PROSPECTS_CSV = REPO_ROOT / "data" / "prospects.csv"


def load_briefs() -> list[AccountBrief]:
    briefs = []
    for path in sorted(BRIEFS_DIR.glob("*.json")):
        briefs.append(AccountBrief.model_validate_json(path.read_text(encoding="utf-8")))
    return briefs


def load_report_priority_order() -> list[str]:
    with PROSPECTS_CSV.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: int(r["priority"]))
    return [r["company"].strip() for r in rows]


def main() -> None:
    briefs = load_briefs()
    scored = [b for b in briefs if b.score.status == "SCORED"]
    excluded = [b for b in briefs if b.score.status != "SCORED"]

    ordered = rank(briefs)
    model_order = [b.company for b in ordered if b.score.status == "SCORED"]
    report_order = load_report_priority_order()

    rho = spearman_rho(model_order, report_order)
    ablation_results = ablate(scored, top_n=10)

    lines = ["# Validation Results\n"]
    lines.append(f"Total briefs: {len(briefs)} | Scored: {len(scored)} | Excluded/insufficient: {len(excluded)}\n")

    lines.append("## V1 — Rank correlation against the research report's independent priority order\n")
    lines.append(
        "The report ranked these 30 accounts by its own judgment, from the same public "
        "universe, without reference to this scoring model (docs/TRELIUM_RESEARCH_NOTES.md "
        "section 10). This is a second opinion, not ground truth — no external party has "
        "Trelium's actual win data (docs/SCORING.md section 10).\n"
    )
    if rho is not None:
        lines.append(f"**Spearman's rho: {rho:.3f}**\n")
    else:
        lines.append("Not enough comparable accounts to compute a correlation.\n")
    lines.append(f"Model ranking (scored accounts, best first): {', '.join(model_order)}\n")
    lines.append(f"Report priority order: {', '.join(report_order)}\n")

    lines.append("\n## V2 — Component ablation (top-10 movement)\n")
    lines.append("Each row zeroes one score component and reports how many of the original ")
    lines.append("top-10 accounts fell out of the top 10 once that component is removed.\n")
    lines.append("| Component zeroed | Accounts that fell out of top 10 |")
    lines.append("|---|---|")
    for r in ablation_results:
        lines.append(f"| {r.zeroed_component} | {r.movement_count} |")

    lines.append("\n## V4 — Negative control\n")
    lines.append("See scripts/run_negative_controls.py output (run separately; not part of ")
    lines.append("the 30-account prospect batch).\n")

    lines.append("\n## V3 — Manual claim audit\n")
    lines.append("Not computed by this script — see docs/FINDINGS.md for the manual audit ")
    lines.append("results on the top-scored briefs.\n")

    (REPO_ROOT / "docs" / "VALIDATION.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"Wrote docs/VALIDATION.md (rho={rho})")

    coverage_rows = compute_coverage(scored)
    coverage_md = render_coverage_markdown(coverage_rows, total_accounts=len(scored))
    (REPO_ROOT / "docs" / "COVERAGE.md").write_text(coverage_md, encoding="utf-8", newline="\n")
    print("Wrote docs/COVERAGE.md")


if __name__ == "__main__":
    main()
