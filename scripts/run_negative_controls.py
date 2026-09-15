"""V4 negative control (docs/SCORING.md section 11): run 5 deliberately
out-of-ICP companies through the full live pipeline and confirm every one
is excluded at gate G1. See docs/IMPLEMENTATION_PLAN.md phase 7.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from trelium_gtm.cli import _discover_sources  # noqa: E402
from trelium_gtm.pipeline import run_account  # noqa: E402
from trelium_gtm.render.json_out import render_brief_json  # noqa: E402
from trelium_gtm.render.markdown import render_brief_markdown  # noqa: E402
from trelium_gtm.validate import check_negative_controls  # noqa: E402

# Five real, well-known companies chosen specifically because they are
# unambiguously outside the promo-products/decorator/print ICP: a law firm,
# a SaaS vendor, a restaurant group, a staffing agency, a regional bank.
CONTROLS = [
    ("Baker McKenzie", "bakermckenzie.com"),
    ("Asana", "asana.com"),
    ("Darden Restaurants", "darden.com"),
    ("Robert Half", "roberthalf.com"),
    ("Umpqua Bank", "umpquabank.com"),
]

EVIDENCE_DIR = REPO_ROOT / "evidence"
CACHE_DIR = REPO_ROOT / "cache" / "llm"
OUT_DIR = REPO_ROOT / "output" / "negative_controls"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    briefs = []
    for company, domain in CONTROLS:
        sources = _discover_sources(domain, EVIDENCE_DIR)
        report = run_account(
            company=company,
            domain=domain,
            sources=sources,
            evidence_dir=EVIDENCE_DIR,
            cache_dir=CACHE_DIR,
            as_of=date.today(),
        )
        briefs.append(report.brief)
        safe_name = domain.replace(".", "_")
        (OUT_DIR / f"{safe_name}.json").write_text(
            render_brief_json(report.brief), encoding="utf-8", newline="\n"
        )
        (OUT_DIR / f"{safe_name}.md").write_text(
            render_brief_markdown(report.brief), encoding="utf-8", newline="\n"
        )
        print(f"{company}: status={report.brief.score.status} total={report.brief.score.total}")

    results = check_negative_controls(briefs)
    lines = ["## V4 — Negative control results\n", "| Company | Domain | Status | Total | Passed | Reason |", "|---|---|---|---|---|---|"]
    for r in results:
        lines.append(
            f"| {r.company} | {r.domain} | {r.status} | {r.total} | "
            f"{'YES' if r.passed else '**NO — LEAK**'} | {r.reason} |"
        )
    all_passed = all(r.passed for r in results)
    lines.append("")
    lines.append(f"**{sum(r.passed for r in results)}/{len(results)} correctly excluded at the segment gate.**")
    if not all_passed:
        lines.append("\n**At least one negative control leaked through the ICP gate — see docs/FINDINGS.md.**")

    (REPO_ROOT / "docs" / "VALIDATION_V4.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
    )
    print("\n".join(lines))


if __name__ == "__main__":
    main()
