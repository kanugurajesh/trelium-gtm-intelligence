"""Deterministic persona selection. Lookup, not judgment — per docs/ICP.md
section 7, this is exactly the part of "GTM reasoning" that must not be left
to the model: which role plausibly owns a workflow is a function of segment
and scale, not something to be inferred fresh per account.
"""

from __future__ import annotations

from trelium_gtm.taxonomy import PERSONA_MAP, ScaleBand, SegmentLabel

_LARGE_OR_ABOVE = {ScaleBand.LARGE, ScaleBand.ENTERPRISE}


def _segment_group(label: SegmentLabel) -> str:
    if label == SegmentLabel.PROMO_DISTRIBUTOR:
        return "distributor"
    if label == SegmentLabel.PROMO_SUPPLIER:
        return "supplier"
    if label == SegmentLabel.DECORATOR_PRINT_SHOP:
        return "decorator"
    return "other"


def select_persona(segment_label: SegmentLabel, scale_band: ScaleBand) -> tuple[str, str, str]:
    """Returns (primary_persona, secondary_persona, rationale)."""
    group = _segment_group(segment_label)

    if group == "distributor":
        scale_key = "large_or_above" if scale_band in _LARGE_OR_ABOVE else "small_or_below"
        primary, secondary, rationale = PERSONA_MAP[("distributor", scale_key)]
    elif group in ("supplier", "decorator"):
        primary, secondary, rationale = PERSONA_MAP[(group, "any")]
    else:
        primary, secondary, rationale = PERSONA_MAP[("other", "any")]

    return primary.value, secondary.value, rationale
