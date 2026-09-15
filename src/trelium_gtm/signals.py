"""Deterministic rules mapping verified Facts onto a SignalSet.

Every Signal produced here carries the evidence_ids and fact_ids that support
it (SCORING.md hard rule H1 is enforced upstream at the Signal type, but this
module is what actually threads provenance through). No model calls; this is
pure code over already-verified facts.

Field contract for extraction (docs/EVIDENCE_MODEL.md / phase 4 producer):
a Fact contributes to signals only when its ``field`` is one of the keys
below, with ``value`` shaped as documented per field. Facts with any other
``field`` (or ``field=None``) are ignored here — they still render in the
brief's verified-facts section, they simply carry no scoring weight.
"""

from __future__ import annotations

from datetime import date, datetime

from trelium_gtm.evidence.verify import registrable_domain
from trelium_gtm.models import Evidence, Fact, Signal, SignalSet
from trelium_gtm.taxonomy import (
    SEGMENT_TIER_MAP,
    ScaleBand,
    SegmentLabel,
    SegmentTier,
    SourceTier,
    SYSTEM_NAME_TO_CLASS,
)

_REVENUE_BANDS: list[tuple[float, ScaleBand]] = [
    (1_000_000_000, ScaleBand.ENTERPRISE),
    (500_000_000, ScaleBand.LARGE),
    (50_000_000, ScaleBand.SWEET_SPOT),
    (20_000_000, ScaleBand.LOWER_MID),
    (5_000_000, ScaleBand.SMALL),
]

_HEADCOUNT_BANDS: list[tuple[int, ScaleBand]] = [
    (500, ScaleBand.LARGE),
    (100, ScaleBand.SWEET_SPOT),
    (25, ScaleBand.LOWER_MID),
]


def _revenue_to_band(revenue_usd: float) -> ScaleBand:
    for threshold, band in _REVENUE_BANDS:
        if revenue_usd >= threshold:
            return band
    return ScaleBand.MICRO


def _headcount_to_band(headcount: int) -> ScaleBand:
    for threshold, band in _HEADCOUNT_BANDS:
        if headcount >= threshold:
            return band
    return ScaleBand.SMALL


def _fact_min_tier(fact: Fact, evidence_by_id: dict[str, Evidence]) -> SourceTier:
    tiers = [
        evidence_by_id[eid].source_tier
        for eid in fact.evidence_ids
        if eid in evidence_by_id
    ]
    if not tiers:
        return SourceTier.UNSOURCED
    return min(tiers, key=lambda t: int(t))


def derive_signals(
    facts: list[Fact],
    evidence: list[Evidence],
    *,
    is_public_customer: bool = False,
    is_ecosystem_ambiguous: bool = False,
) -> SignalSet:
    evidence_by_id = {e.id: e for e in evidence}

    segment_signal: Signal | None = None
    segment_label = SegmentLabel.UNRESOLVED
    best_segment_tier_rank = 999

    scale_signal: Signal | None = None
    scale_band = ScaleBand.UNKNOWN
    scale_basis: str = "unknown"
    best_revenue: float | None = None
    best_headcount: int | None = None

    stack_signals: list[Signal] = []
    ops_signals: list[Signal] = []
    ops_hiring_facts: list[Fact] = []
    other_trigger_signals: list[Signal] = []

    for fact in facts:
        if fact.field == "segment" and fact.value is not None:
            try:
                label = SegmentLabel(str(fact.value))
            except ValueError:
                continue
            tier_rank = int(_fact_min_tier(fact, evidence_by_id))
            if tier_rank < best_segment_tier_rank:
                best_segment_tier_rank = tier_rank
                segment_label = label
                segment_signal = Signal(
                    id=f"sig_segment_{fact.id}",
                    kind="segment",
                    value=label.value,
                    evidence_ids=fact.evidence_ids,
                    fact_ids=[fact.id],
                )

        elif fact.field == "revenue_usd" and fact.value is not None:
            try:
                revenue = float(fact.value)
            except (TypeError, ValueError):
                continue
            if best_revenue is None or revenue > best_revenue:
                best_revenue = revenue
                scale_band = _revenue_to_band(revenue)
                scale_basis = "revenue"
                scale_signal = Signal(
                    id=f"sig_scale_{fact.id}",
                    kind="scale",
                    value=scale_band.value,
                    evidence_ids=fact.evidence_ids,
                    fact_ids=[fact.id],
                )

        elif fact.field == "employee_count" and fact.value is not None and best_revenue is None:
            try:
                headcount = int(fact.value)
            except (TypeError, ValueError):
                continue
            if best_headcount is None or headcount > best_headcount:
                best_headcount = headcount
                scale_band = _headcount_to_band(headcount)
                scale_basis = "headcount"
                scale_signal = Signal(
                    id=f"sig_scale_{fact.id}",
                    kind="scale",
                    value=scale_band.value,
                    evidence_ids=fact.evidence_ids,
                    fact_ids=[fact.id],
                )

        elif fact.field == "system" and fact.value is not None:
            name = str(fact.value).strip().lower()
            cls = SYSTEM_NAME_TO_CLASS.get(name)
            if cls is None:
                continue  # unrecognised system name: not scored, see module docstring
            stack_signals.append(
                Signal(
                    id=f"sig_stack_{fact.id}",
                    kind="stack",
                    value=f"{cls.value}:{name}",
                    evidence_ids=fact.evidence_ids,
                    fact_ids=[fact.id],
                )
            )

        elif fact.field == "ops_subsignal" and fact.value is not None:
            ops_signals.append(
                Signal(
                    id=f"sig_ops_{fact.id}",
                    kind="ops",
                    value=str(fact.value),
                    evidence_ids=fact.evidence_ids,
                    fact_ids=[fact.id],
                )
            )

        elif fact.field == "ops_hiring_role" and fact.value is not None:
            ops_hiring_facts.append(fact)

        elif fact.field == "trigger" and fact.value is not None:
            published_at = None
            for eid in fact.evidence_ids:
                ev = evidence_by_id.get(eid)
                if ev and ev.published_at:
                    published_at = ev.published_at
                    break
            other_trigger_signals.append(
                Signal(
                    id=f"sig_trigger_{fact.id}",
                    kind="trigger",
                    value=str(fact.value),
                    evidence_ids=fact.evidence_ids,
                    fact_ids=[fact.id],
                    published_at=published_at,
                )
            )

    trigger_signals = list(other_trigger_signals)
    if ops_hiring_facts:
        combined_evidence: list[str] = []
        combined_facts: list[str] = []
        published_at = None
        for f in ops_hiring_facts:
            combined_evidence.extend(f.evidence_ids)
            combined_facts.append(f.id)
            if published_at is None:
                for eid in f.evidence_ids:
                    ev = evidence_by_id.get(eid)
                    if ev and ev.published_at:
                        published_at = ev.published_at
                        break
        trigger_signals.append(
            Signal(
                id="sig_trigger_ops_hiring",
                kind="trigger",
                value=f"OPS_HIRING:{len(ops_hiring_facts)}",
                evidence_ids=combined_evidence,
                fact_ids=combined_facts,
                published_at=published_at,
            )
        )

    tier_1_2_fact_count = sum(
        1 for fact in facts if int(_fact_min_tier(fact, evidence_by_id)) <= 2
    )
    evidence_domains = sorted({registrable_domain(e.source_url) for e in evidence})

    segment_tier = SEGMENT_TIER_MAP.get(segment_label, SegmentTier.UNRESOLVED)

    return SignalSet(
        segment_label=segment_label,
        segment_tier=segment_tier,
        segment_signal=segment_signal,
        scale_band=scale_band,
        scale_basis=scale_basis,
        scale_signal=scale_signal,
        stack_signals=stack_signals,
        trigger_signals=trigger_signals,
        ops_signals=ops_signals,
        evidence_domains=evidence_domains,
        tier_1_2_fact_count=tier_1_2_fact_count,
        is_public_customer=is_public_customer,
        is_ecosystem_ambiguous=is_ecosystem_ambiguous,
        has_any_evidence=len(evidence) > 0,
    )


def _parse_iso_date(value: str) -> date | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def compute_trigger_ages_months(
    signals: SignalSet, as_of: date
) -> dict[str, int | None]:
    """Convenience helper for callers (cli/pipeline): converts each trigger
    Signal's published_at into an integer age in months as of a fixed date,
    for scoring.score()'s trigger_ages_months parameter. Kept out of
    scoring.py itself so the scorer never reads a clock (CLAUDE.md R8).
    """
    ages: dict[str, int | None] = {}
    for sig in signals.trigger_signals:
        if not sig.published_at:
            ages[sig.id] = None
            continue
        published = _parse_iso_date(sig.published_at)
        if published is None:
            ages[sig.id] = None
            continue
        months = (as_of.year - published.year) * 12 + (as_of.month - published.month)
        ages[sig.id] = max(0, months)
    return ages


def compute_evidence_age_months_min(evidence: list[Evidence], as_of: date) -> int | None:
    ages = []
    for e in evidence:
        if not e.published_at:
            continue
        parsed = _parse_iso_date(e.published_at)
        if parsed is None:
            continue
        months = (as_of.year - parsed.year) * 12 + (as_of.month - parsed.month)
        ages.append(max(0, months))
    return min(ages) if ages else None
