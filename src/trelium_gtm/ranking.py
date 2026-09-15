"""Deterministic ranking with a total tie-break order. SCORING.md section 9.

Two runs over the same corpus must produce byte-identical rankings, so every
comparison key bottoms out at something with no ties left (company name).
"""

from __future__ import annotations

from trelium_gtm.models import AccountBrief
from trelium_gtm.taxonomy import EvidenceGrade, ScaleBand

_GRADE_RANK = {
    EvidenceGrade.A: 0,
    EvidenceGrade.B: 1,
    EvidenceGrade.C: 2,
    EvidenceGrade.D: 3,
}

# Smaller = closer to SWEET_SPOT = better tie-break position.
_SCALE_PROXIMITY = {
    ScaleBand.SWEET_SPOT: 0,
    ScaleBand.LARGE: 1,
    ScaleBand.LOWER_MID: 1,
    ScaleBand.ENTERPRISE: 2,
    ScaleBand.SMALL: 2,
    ScaleBand.MICRO: 3,
    ScaleBand.UNKNOWN: 4,
}


def _top_boundary_count(brief: AccountBrief) -> int:
    if not brief.workflow_hypotheses:
        return 0
    return max(wh.boundary_count for wh in brief.workflow_hypotheses)


def sort_key(brief: AccountBrief) -> tuple:
    total = brief.score.total if brief.score.total is not None else -1
    return (
        -total,
        _GRADE_RANK.get(brief.score.evidence_grade, 99),
        _SCALE_PROXIMITY.get(brief.signals.scale_band, 99),
        -_top_boundary_count(brief),
        brief.company.lower(),
    )


def rank(briefs: list[AccountBrief]) -> list[AccountBrief]:
    """Rank scored briefs. OUT_OF_ICP / INSUFFICIENT_EVIDENCE briefs (total is
    None) sort last, in the same deterministic order among themselves.
    """
    return sorted(briefs, key=sort_key)
