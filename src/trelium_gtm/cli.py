"""Command-line entry points. See docs/PROJECT_SPEC.md section 4 for the
command list this implements.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import date
from pathlib import Path

from trelium_gtm.collect import collect_source, discover_links
from trelium_gtm.models import AccountBrief
from trelium_gtm.pipeline import SourceSpec, run_account
from trelium_gtm.ranking import rank
from trelium_gtm.render.json_out import render_brief_json
from trelium_gtm.render.markdown import render_brief_markdown
from trelium_gtm.scoring import score as score_signals

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE_DIR = REPO_ROOT / "evidence"
DEFAULT_CACHE_DIR = REPO_ROOT / "cache" / "llm"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "output" / "briefs"

# Public customer / ecosystem-ambiguous names from docs/TRELIUM_RESEARCH_NOTES.md
# section 2 and section 10. Matched case-insensitively against the CSV's
# company column. Kept here (not in the CSV) so the exclusion logic is
# auditable in one place.
PUBLIC_CUSTOMER_NAMES = {
    "vapor apparel", "vantage", "hpg", "numo", "ipromo", "brand fuel", "icebox cool stuff",
}
ECOSYSTEM_AMBIGUOUS_NAMES = {"s&s activewear", "sanmar"}

def _discover_sources(domain: str, evidence_dir: Path) -> list[SourceSpec]:
    """Fetch the homepage once, discover real about/careers links from its
    navigation rather than guessing fixed paths blindly, and return a
    small source list. The homepage's raw HTML is used only for link
    discovery and is never itself persisted (R25) — only the cleaned text
    snapshots collect_source normally writes are kept.
    """
    homepage_url = f"https://{domain}"
    sources = [SourceSpec(url=homepage_url, publisher="Company website", title="Home")]
    try:
        discovery = collect_source(homepage_url, evidence_dir, keep_html=True)
    except Exception:
        discovery = None

    if discovery and discovery.ok and discovery.raw_html:
        for url in discover_links(discovery.raw_html, homepage_url, ("about",), max_links=1):
            sources.append(SourceSpec(url=url, publisher="Company website", title="About"))
        for url in discover_links(
            discovery.raw_html, homepage_url, ("career", "job"), max_links=1
        ):
            sources.append(SourceSpec(url=url, publisher="Company careers page", title="Careers"))
    return sources


def cmd_collect_brief(args: argparse.Namespace) -> None:
    sources = _discover_sources(args.domain, Path(args.evidence_dir))
    name_key = args.company.strip().lower()
    report = run_account(
        company=args.company,
        domain=args.domain,
        sources=sources,
        evidence_dir=Path(args.evidence_dir),
        cache_dir=Path(args.cache_dir),
        as_of=date.today(),
        is_public_customer=name_key in PUBLIC_CUSTOMER_NAMES,
        is_ecosystem_ambiguous=name_key in ECOSYSTEM_AMBIGUOUS_NAMES,
    )
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_name = args.domain.replace(".", "_")
    (out_dir / f"{safe_name}.json").write_text(
        render_brief_json(report.brief), encoding="utf-8", newline="\n"
    )
    (out_dir / f"{safe_name}.md").write_text(
        render_brief_markdown(report.brief), encoding="utf-8", newline="\n"
    )
    print(f"{args.company}: status={report.brief.score.status} total={report.brief.score.total} "
          f"collection_errors={len(report.collection_errors)} "
          f"rejection_rate={report.extraction_rejection_rate}")


def cmd_score_from(args: argparse.Namespace) -> None:
    brief = AccountBrief.model_validate_json(Path(args.from_path).read_text(encoding="utf-8"))
    from trelium_gtm.signals import compute_evidence_age_months_min, compute_trigger_ages_months

    trigger_ages = compute_trigger_ages_months(brief.signals, date.today())
    evidence_age_min = compute_evidence_age_months_min(brief.evidence, date.today())
    result = score_signals(
        brief.signals, trigger_ages_months=trigger_ages, evidence_age_months_min=evidence_age_min
    )
    print(json.dumps(result.model_dump(mode="json"), indent=2))
    if result.total != brief.score.total:
        print(
            f"NOTE: rescored total ({result.total}) differs from stored total "
            f"({brief.score.total}) - trigger recency ages shift as 'as_of' moves forward.",
            file=sys.stderr,
        )


def cmd_run_all(args: argparse.Namespace) -> None:
    csv_path = Path(args.input)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir = Path(args.evidence_dir)
    cache_dir = Path(args.cache_dir)

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    limit = args.limit if args.limit else len(rows)
    for i, row in enumerate(rows[:limit]):
        company = row["company"].strip()
        domain = row["domain"].strip()
        if not domain:
            print(f"SKIP {company}: no domain")
            continue
        name_key = company.lower()
        sources = _discover_sources(domain, evidence_dir)
        try:
            report = run_account(
                company=company,
                domain=domain,
                sources=sources,
                evidence_dir=evidence_dir,
                cache_dir=cache_dir,
                as_of=date.today(),
                is_public_customer=name_key in PUBLIC_CUSTOMER_NAMES,
                is_ecosystem_ambiguous=name_key in ECOSYSTEM_AMBIGUOUS_NAMES,
            )
        except Exception as exc:  # noqa: BLE001 - keep going across 30 accounts
            print(f"ERROR {company}: {exc!r}", file=sys.stderr)
            continue

        safe_name = domain.replace(".", "_")
        (out_dir / f"{safe_name}.json").write_text(
            render_brief_json(report.brief), encoding="utf-8", newline="\n"
        )
        (out_dir / f"{safe_name}.md").write_text(
            render_brief_markdown(report.brief), encoding="utf-8", newline="\n"
        )
        print(
            f"[{i+1}/{limit}] {company}: status={report.brief.score.status} "
            f"total={report.brief.score.total} errors={len(report.collection_errors)}"
        )
        if args.delay:
            time.sleep(args.delay)


def cmd_rank(args: argparse.Namespace) -> None:
    briefs_dir = Path(args.briefs_dir)
    briefs = []
    for path in sorted(briefs_dir.glob("*.json")):
        briefs.append(AccountBrief.model_validate_json(path.read_text(encoding="utf-8")))

    ordered = rank(briefs)
    lines = ["# Account Ranking\n", "| # | Company | Score | Band | Grade | Flags |", "|---|---|---|---|---|---|"]
    for i, b in enumerate(ordered, start=1):
        score_str = (
            f"{b.score.range[0]}-{b.score.range[1]}"
            if b.score.reported_as == "range" and b.score.range
            else str(b.score.total)
        )
        band = b.score.band.value if b.score.band else b.score.status
        lines.append(
            f"| {i} | {b.company} | {score_str} | {band} | {b.score.evidence_grade.value} | "
            f"{', '.join(b.flags) or '-'} |"
        )
    Path(args.output).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {args.output} ({len(ordered)} accounts)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trelium")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_collect = sub.add_parser("brief", help="Research one account and write a brief")
    p_collect.add_argument("--company", required=True)
    p_collect.add_argument("--domain", required=True)
    p_collect.add_argument("--evidence-dir", dest="evidence_dir", default=str(DEFAULT_EVIDENCE_DIR))
    p_collect.add_argument("--cache-dir", dest="cache_dir", default=str(DEFAULT_CACHE_DIR))
    p_collect.add_argument("--output-dir", dest="output_dir", default=str(DEFAULT_OUTPUT_DIR))
    p_collect.set_defaults(func=cmd_collect_brief)

    p_score = sub.add_parser("score", help="Rescore a stored brief to prove determinism")
    p_score.add_argument("--from", dest="from_path", required=True)
    p_score.set_defaults(func=cmd_score_from)

    p_run_all = sub.add_parser("run-all", help="Run the pipeline over a prospects CSV")
    p_run_all.add_argument("--input", required=True)
    p_run_all.add_argument("--evidence-dir", dest="evidence_dir", default=str(DEFAULT_EVIDENCE_DIR))
    p_run_all.add_argument("--cache-dir", dest="cache_dir", default=str(DEFAULT_CACHE_DIR))
    p_run_all.add_argument("--output-dir", dest="output_dir", default=str(DEFAULT_OUTPUT_DIR))
    p_run_all.add_argument("--limit", type=int, default=0)
    p_run_all.add_argument("--delay", type=float, default=1.0, help="Seconds between accounts")
    p_run_all.set_defaults(func=cmd_run_all)

    p_rank = sub.add_parser("rank", help="Rank all generated briefs")
    p_rank.add_argument("--briefs-dir", dest="briefs_dir", default=str(DEFAULT_OUTPUT_DIR))
    p_rank.add_argument("--output", default=str(REPO_ROOT / "docs" / "RANKING.md"))
    p_rank.set_defaults(func=cmd_rank)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
