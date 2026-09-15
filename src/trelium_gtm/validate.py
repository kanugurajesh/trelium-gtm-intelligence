"""Validation experiments V1 (rank correlation), V2 (component ablation),
V4 (negative control). See docs/SCORING.md section 11-12.

V3 (manual claim audit) is inherently a human review pass over rendered
briefs and has no code counterpart here.
"""

from __future__ import annotations

from dataclasses import dataclass

from trelium_gtm.models import AccountBrief
from trelium_gtm.ranking import rank

COMPONENT_KEYS = ("c1", "c2", "c3", "c4", "c5", "c6")


def spearman_rho(rank_a: list[str], rank_b: list[str]) -> float | None:
    """Spearman rank correlation between two orderings of the same item set
    (by name). Items missing from either list are dropped from both before
    correlating. Returns None if fewer than 2 comparable items remain.

    Implemented directly (no scipy dependency) as 1 - 6*sum(d^2)/(n*(n^2-1)),
    which is exact when there are no ties; ties are broken by the caller's
    original ordering, which is acceptable here since briefs already carry
    a fully deterministic tie-break (ranking.py).
    """
    common = [x for x in rank_a if x in set(rank_b)]
    if len(common) < 2:
        return None
    pos_a = {name: i for i, name in enumerate(common)}
    pos_b = {name: i for i, name in enumerate([x for x in rank_b if x in set(common)])}
    n = len(common)
    d_squared_sum = sum((pos_a[name] - pos_b[name]) ** 2 for name in common)
    return 1 - (6 * d_squared_sum) / (n * (n**2 - 1))


@dataclass
class AblationResult:
    zeroed_component: str
    original_top_10: list[str]
    ablated_top_10: list[str]
    movement_count: int  # how many of the original top 10 fell out of the new top 10


def _rescored_brief(brief: AccountBrief, zeroed_component: str) -> AccountBrief:
    """Returns a copy of ``brief`` with one score component zeroed and the
    total, band and evidence_grade recomputed from the remaining
    components. Evidence grade and flags are left untouched — ablation
    tests component *weight*, not evidence quality.
    """
    if brief.score.status != "SCORED" or brief.score.total is None:
        return brief

    from trelium_gtm.scoring import _band_for  # reuse the exact banding rule

    new_components = dict(brief.score.components)
    new_components[zeroed_component] = 0
    new_total = max(0, min(100, sum(new_components.values())))
    new_score = brief.score.model_copy(
        update={
            "components": new_components,
            "total": new_total,
            "band": _band_for(new_total),
        }
    )
    return brief.model_copy(update={"score": new_score})


def ablate(briefs: list[AccountBrief], top_n: int = 10) -> list[AblationResult]:
    scored = [b for b in briefs if b.score.status == "SCORED"]
    original_top = [b.company for b in rank(scored)[:top_n]]

    results = []
    for component in COMPONENT_KEYS:
        ablated_briefs = [_rescored_brief(b, component) for b in scored]
        ablated_top = [b.company for b in rank(ablated_briefs)[:top_n]]
        moved_out = len(set(original_top) - set(ablated_top))
        results.append(
            AblationResult(
                zeroed_component=component,
                original_top_10=original_top,
                ablated_top_10=ablated_top,
                movement_count=moved_out,
            )
        )
    return results


@dataclass
class NegativeControlResult:
    company: str
    domain: str
    status: str
    total: int | None
    passed: bool  # True iff excluded (status == OUT_OF_ICP)


def check_negative_controls(briefs: list[AccountBrief]) -> list[NegativeControlResult]:
    results = []
    for b in briefs:
        passed = b.score.status == "OUT_OF_ICP"
        results.append(
            NegativeControlResult(
                company=b.company,
                domain=b.domain,
                status=b.score.status,
                total=b.score.total,
                passed=passed,
            )
        )
    return results
