"""Deterministic rules mapping verified Facts onto a SignalSet.

Every Signal produced here carries the evidence_ids and fact_ids that support
it (SCORING.md hard rule H1 is enforced upstream at the Signal type, but this
module is what actually threads provenance through). No model calls; this is
pure code over already-verified facts.

Two policies live here and are documented in docs/EVIDENCE_MODEL.md
sections 9 and 10 (do not undo them casually — see CLAUDE.md R36/R37):

NORMALIZATION / DEDUPLICATION. The unit of a scoring signal is an *identity*
(one system, one trigger type, one ops sub-signal, one segment label), never a
fact. Every fact asserting the same identity is merged into ONE Signal whose
``evidence_ids`` and ``fact_ids`` are the sorted union of all supporting
facts. "SAGE" on the homepage and "SAGE" on the careers page is one system
with two pieces of evidence, not two systems. Identity keys are normalised
(``_norm``: lower-case, whitespace-collapsed, stripped) — no fuzzy matching;
"NetSuite" and "Net Suite" are deliberately treated as different until a
human adds an alias to taxonomy.SYSTEM_NAME_TO_CLASS.

CONTRADICTION. For mutually exclusive classifications (segment, scale band)
all candidate values are kept as merged signals and a winner is chosen by an
explicit, order-independent rule (evidence tier first, then breadth of
support, then a fixed lexical tie-break). A conflict is never resolved by
processing order and never hidden: it is recorded on the SignalSet
(``segment_conflict`` / ``scale_conflict``), surfaced as a research gap by
the pipeline, and — for an unresolved segment conflict — penalised by the
scorer. The LLM is never asked to adjudicate.

Determinism guarantee: ``derive_signals`` is a pure function of the *set* of
facts and evidence. Reordering the input lists cannot change any field of the
returned SignalSet (tested in tests/test_signals_integrity.py).

Field contract for extraction (docs/EVIDENCE_MODEL.md / phase 4 producer):
a Fact contributes to signals only when its ``field`` is one of the keys
handled below, with ``value`` shaped as documented per field. Facts with any
other ``field`` (or ``field=None``) are ignored here — they still render in
the brief's verified-facts section, they simply carry no scoring weight.
"""

from __future__ import annotations

import re
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

_WS_RE = re.compile(r"\s+")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _norm(value: object) -> str:
    """Identity normalisation: lower-case, collapse whitespace, strip.
    Deliberately nothing cleverer (no fuzzy matching, no alias tables)."""
    return _WS_RE.sub(" ", str(value)).strip().lower()


def _slug(value: str) -> str:
    return _SLUG_RE.sub("_", value).strip("_")


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


def _group_best_tier(facts: list[Fact], evidence_by_id: dict[str, Evidence]) -> int:
    return min(int(_fact_min_tier(f, evidence_by_id)) for f in facts)


def _group_domains(facts: list[Fact], evidence_by_id: dict[str, Evidence]) -> set[str]:
    domains: set[str] = set()
    for f in facts:
        for eid in f.evidence_ids:
            ev = evidence_by_id.get(eid)
            if ev:
                domains.add(registrable_domain(ev.source_url))
    return domains


def _latest_published_at(facts: list[Fact], evidence_by_id: dict[str, Evidence]) -> str | None:
    """Most recent published_at among all supporting evidence (ISO strings
    compare lexically). Order-independent by construction."""
    stamps = [
        evidence_by_id[eid].published_at
        for f in facts
        for eid in f.evidence_ids
        if eid in evidence_by_id and evidence_by_id[eid].published_at
    ]
    return max(stamps) if stamps else None


def _merged_signal(
    signal_id: str,
    kind: str,
    value: str,
    facts: list[Fact],
    evidence_by_id: dict[str, Evidence],
    *,
    with_published_at: bool = False,
) -> Signal:
    """One signal per identity; provenance is the sorted union of every
    supporting fact's evidence — nothing is dropped when merging."""
    evidence_ids = sorted({eid for f in facts for eid in f.evidence_ids})
    fact_ids = sorted(f.id for f in facts)
    return Signal(
        id=signal_id,
        kind=kind,
        value=value,
        evidence_ids=evidence_ids,
        fact_ids=fact_ids,
        published_at=_latest_published_at(facts, evidence_by_id) if with_published_at else None,
    )


def _claim_identity(fact: Fact) -> tuple[str, str]:
    """Key used to count *distinct* claims for evidence-quality purposes:
    structured facts collapse on (field, normalised value); unstructured
    facts on their normalised statement."""
    if fact.field:
        return (fact.field, _norm(fact.value))
    return ("statement", _norm(fact.statement).rstrip(".!"))


def derive_signals(
    facts: list[Fact],
    evidence: list[Evidence],
    *,
    is_public_customer: bool = False,
    is_ecosystem_ambiguous: bool = False,
) -> SignalSet:
    evidence_by_id = {e.id: e for e in evidence}

    segment_groups: dict[SegmentLabel, list[Fact]] = {}
    revenue_facts: list[tuple[float, Fact]] = []
    headcount_facts: list[tuple[int, Fact]] = []
    stack_groups: dict[tuple[str, str], list[Fact]] = {}  # (class, norm name)
    ops_groups: dict[str, list[Fact]] = {}
    hiring_groups: dict[str, list[Fact]] = {}  # norm role title
    trigger_groups: dict[str, list[Fact]] = {}

    for fact in facts:
        if fact.value is None:
            continue
        if fact.field == "segment":
            try:
                label = SegmentLabel(_norm(fact.value))
            except ValueError:
                continue
            segment_groups.setdefault(label, []).append(fact)

        elif fact.field == "revenue_usd":
            try:
                revenue_facts.append((float(fact.value), fact))
            except (TypeError, ValueError):
                continue

        elif fact.field == "employee_count":
            try:
                headcount_facts.append((int(float(fact.value)), fact))
            except (TypeError, ValueError):
                continue

        elif fact.field == "system":
            name = _norm(fact.value)
            cls = SYSTEM_NAME_TO_CLASS.get(name)
            if cls is None:
                continue  # unrecognised system name: not scored, see module docstring
            stack_groups.setdefault((cls.value, name), []).append(fact)

        elif fact.field == "ops_subsignal":
            ops_groups.setdefault(str(fact.value).strip().upper(), []).append(fact)

        elif fact.field == "ops_hiring_role":
            hiring_groups.setdefault(_norm(fact.value), []).append(fact)

        elif fact.field == "trigger":
            trigger_groups.setdefault(str(fact.value).strip().upper(), []).append(fact)

    # ---- segment: candidates, deterministic winner, explicit conflict -------
    segment_candidates: list[Signal] = []
    ranked_labels: list[tuple[tuple[int, int, int, str], SegmentLabel]] = []
    for label, group in segment_groups.items():
        key = (
            _group_best_tier(group, evidence_by_id),   # stronger tier first
            -len(group),                                # then more supporting facts
            -len(_group_domains(group, evidence_by_id)),  # then more independent domains
            label.value,                                # then fixed lexical order
        )
        ranked_labels.append((key, label))
    ranked_labels.sort(key=lambda kv: kv[0])
    for _key, label in ranked_labels:
        segment_candidates.append(
            _merged_signal(
                f"sig_segment_{_slug(label.value)}", "segment", label.value,
                segment_groups[label], evidence_by_id,
            )
        )

    segment_label = SegmentLabel.UNRESOLVED
    segment_signal: Signal | None = None
    segment_conflict = "none"
    if ranked_labels:
        segment_label = ranked_labels[0][1]
        segment_signal = segment_candidates[0]
        if len(ranked_labels) >= 2:
            winner_tier = ranked_labels[0][0][0]
            runner_tier = ranked_labels[1][0][0]
            segment_conflict = "resolved_by_tier" if winner_tier < runner_tier else "unresolved"
    segment_tier = SEGMENT_TIER_MAP.get(segment_label, SegmentTier.UNRESOLVED)

    # ---- scale: revenue preferred over headcount; conflict = band disagreement
    scale_band = ScaleBand.UNKNOWN
    scale_basis: str = "unknown"
    scale_signal: Signal | None = None
    scale_candidates: list[Signal] = []
    scale_conflict = False

    if revenue_facts:
        # winner: strongest evidence tier, then the larger figure, then fact id
        ordered = sorted(
            revenue_facts,
            key=lambda rf: (int(_fact_min_tier(rf[1], evidence_by_id)), -rf[0], rf[1].id),
        )
        bands = {_revenue_to_band(v) for v, _ in revenue_facts}
        scale_conflict = len(bands) > 1
        best_value, best_fact = ordered[0]
        scale_band = _revenue_to_band(best_value)
        scale_basis = "revenue"
        band_groups: dict[ScaleBand, list[Fact]] = {}
        for v, f in ordered:
            band_groups.setdefault(_revenue_to_band(v), []).append(f)
        for band in sorted(band_groups, key=lambda b: b.value):
            scale_candidates.append(
                _merged_signal(
                    f"sig_scale_revenue_{band.value.lower()}", "scale", band.value,
                    band_groups[band], evidence_by_id,
                )
            )
        scale_signal = next(c for c in scale_candidates if c.value == scale_band.value)
    elif headcount_facts:
        ordered_hc = sorted(
            headcount_facts,
            key=lambda hf: (int(_fact_min_tier(hf[1], evidence_by_id)), -hf[0], hf[1].id),
        )
        bands = {_headcount_to_band(v) for v, _ in headcount_facts}
        scale_conflict = len(bands) > 1
        best_value, _ = ordered_hc[0]
        scale_band = _headcount_to_band(best_value)
        scale_basis = "headcount"
        band_groups_hc: dict[ScaleBand, list[Fact]] = {}
        for v, f in ordered_hc:
            band_groups_hc.setdefault(_headcount_to_band(v), []).append(f)
        for band in sorted(band_groups_hc, key=lambda b: b.value):
            scale_candidates.append(
                _merged_signal(
                    f"sig_scale_headcount_{band.value.lower()}", "scale", band.value,
                    band_groups_hc[band], evidence_by_id,
                )
            )
        scale_signal = next(c for c in scale_candidates if c.value == scale_band.value)

    # ---- stack: one signal per (class, normalised system name) ---------------
    stack_signals = [
        _merged_signal(
            f"sig_stack_{cls_value.lower()}_{_slug(name)}", "stack", f"{cls_value}:{name}",
            stack_groups[(cls_value, name)], evidence_by_id,
        )
        for cls_value, name in sorted(stack_groups)
    ]

    # ---- ops sub-signals: one per identity ------------------------------------
    ops_signals = [
        _merged_signal(f"sig_ops_{_slug(value)}", "ops", value, ops_groups[value], evidence_by_id)
        for value in sorted(ops_groups)
    ]

    # ---- triggers: one per trigger type; hiring counted by DISTINCT role ------
    trigger_signals = [
        _merged_signal(
            f"sig_trigger_{_slug(value)}", "trigger", value, trigger_groups[value],
            evidence_by_id, with_published_at=True,
        )
        for value in sorted(trigger_groups)
    ]
    if hiring_groups:
        all_hiring_facts = [f for group in hiring_groups.values() for f in group]
        trigger_signals.append(
            _merged_signal(
                "sig_trigger_ops_hiring", "trigger", f"OPS_HIRING:{len(hiring_groups)}",
                all_hiring_facts, evidence_by_id, with_published_at=True,
            )
        )

    # ---- evidence quality inputs: DISTINCT claims, not fact rows -------------
    distinct_tier_1_2 = {
        _claim_identity(f) for f in facts if int(_fact_min_tier(f, evidence_by_id)) <= 2
    }
    evidence_domains = sorted({registrable_domain(e.source_url) for e in evidence})

    return SignalSet(
        segment_label=segment_label,
        segment_tier=segment_tier,
        segment_signal=segment_signal,
        segment_candidates=segment_candidates,
        segment_conflict=segment_conflict,
        scale_band=scale_band,
        scale_basis=scale_basis,
        scale_signal=scale_signal,
        scale_candidates=scale_candidates,
        scale_conflict=scale_conflict,
        stack_signals=stack_signals,
        trigger_signals=trigger_signals,
        ops_signals=ops_signals,
        evidence_domains=evidence_domains,
        tier_1_2_fact_count=len(distinct_tier_1_2),
        is_public_customer=is_public_customer,
        is_ecosystem_ambiguous=is_ecosystem_ambiguous,
        has_any_evidence=len(evidence) > 0,
    )


def conflict_gaps(signals: SignalSet, evidence: list[Evidence]) -> list[str]:
    """Human-readable research gaps for every recorded contradiction. Used by
    the pipeline and by offline re-scoring so the two never disagree."""
    evidence_by_id = {e.id: e for e in evidence}

    def _describe(sig: Signal) -> str:
        urls = sorted({evidence_by_id[eid].source_url for eid in sig.evidence_ids if eid in evidence_by_id})
        return f"{sig.value} ({len(sig.fact_ids)} fact(s); {', '.join(urls) or 'no resolvable source'})"

    gaps: list[str] = []
    if signals.segment_conflict != "none":
        listing = "; ".join(_describe(c) for c in signals.segment_candidates)
        if signals.segment_conflict == "unresolved":
            gaps.append(
                "SEGMENT CONFLICT (unresolved, equal evidence tier) — sources disagree on "
                f"the company's segment: {listing}. Winner '{signals.segment_label.value}' chosen "
                "by breadth of support then fixed lexical order, C1 penalised; validate manually "
                "before relying on the segment."
            )
        else:
            gaps.append(
                "Segment conflict resolved by evidence tier — a stronger-tier source outranked "
                f"a weaker one: {listing}. Winner '{signals.segment_label.value}'."
            )
    if signals.scale_conflict:
        listing = "; ".join(_describe(c) for c in signals.scale_candidates)
        gaps.append(
            "SCALE CONFLICT — sourced figures fall in different scale bands: "
            f"{listing}. Using '{signals.scale_band.value}' (strongest tier, then largest "
            "figure); validate manually."
        )
    return gaps


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
