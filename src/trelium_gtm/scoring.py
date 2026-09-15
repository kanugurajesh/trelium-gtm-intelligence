"""Pure deterministic scoring. score(signals) -> ScoreResult.

No I/O, no network, no model calls, no clock reads, no randomness, no floats
(CLAUDE.md R8). Every point in the total is traceable to a Signal via
``contributing_signals``, and every Signal already carries >=1 evidence_ids
(SCORING.md hard rule H1, enforced at the type level in models.Signal).

See docs/SCORING.md for the full rationale behind every threshold below —
this module intentionally mirrors that document's section numbering in its
function names and comments so the two can be read side by side.
"""

from __future__ import annotations

from trelium_gtm.models import Signal, SignalSet, ScoreResult
from trelium_gtm.taxonomy import (
    Band,
    EvidenceGrade,
    OPS_SUBSIGNAL_POINTS,
    OpsSubSignal,
    ScaleBand,
    SegmentTier,
    SystemClass,
    Trigger,
)

# ---------------------------------------------------------------------------
# Gates (SCORING.md section 2)
# ---------------------------------------------------------------------------


def _gate_out_of_icp(signals: SignalSet) -> bool:
    """G1."""
    return signals.segment_tier == SegmentTier.X


def _gate_insufficient_evidence(signals: SignalSet) -> bool:
    """G4."""
    return not signals.has_any_evidence


# ---------------------------------------------------------------------------
# C1 - Core vertical fit (0-25). SCORING.md section 3.
# ---------------------------------------------------------------------------

def _score_c1_vertical_fit(signals: SignalSet) -> tuple[int, list[str]]:
    sig = signals.segment_signal
    contributing: list[str] = []
    if sig is None or signals.segment_tier == SegmentTier.UNRESOLVED:
        return 0, contributing

    contributing.append(sig.id)
    tier = signals.segment_tier
    strong_evidence = signals.tier_1_2_fact_count >= 1

    if tier == SegmentTier.A:
        points = 25 if strong_evidence else 20
    elif tier == SegmentTier.B:
        points = 15
    elif tier == SegmentTier.C:
        points = 8
    else:
        return 0, contributing

    # Contradiction policy (SCORING.md section 14): an UNRESOLVED segment
    # conflict — two labels claimed at the same evidence tier — is scored at
    # 4/5 (integer floor) of the winner's points. A conflict resolved by
    # evidence tier carries no penalty: the source hierarchy did its job.
    if signals.segment_conflict == "unresolved":
        points = (points * 4) // 5
    return points, contributing


# ---------------------------------------------------------------------------
# C2 - Operational and process complexity (0-20, raw cap 28). SCORING.md sec 4.
# ---------------------------------------------------------------------------

C2_CAP = 20


def _score_c2_ops_complexity(signals: SignalSet) -> tuple[int, list[str]]:
    total = 0
    contributing: list[str] = []
    seen: set[OpsSubSignal] = set()
    for sig in signals.ops_signals:
        try:
            key = OpsSubSignal(sig.value)
        except ValueError:
            continue
        if key in seen:
            continue  # each sub-signal counts once regardless of how many facts support it
        seen.add(key)
        total += OPS_SUBSIGNAL_POINTS[key]
        contributing.append(sig.id)
    return min(total, C2_CAP), contributing


# ---------------------------------------------------------------------------
# C3 - Software and ecosystem signals (0-15). SCORING.md section 5.
# ---------------------------------------------------------------------------

C3_CAP = 15
_CLASS_FIRST_POINTS = {
    SystemClass.INDUSTRY_ORDER_SYSTEM: 6,
    SystemClass.ERP_ACCOUNTING: 5,
    SystemClass.SUPPLIER_DATA: 4,
    SystemClass.CRM: 3,
    SystemClass.COMMERCE_STORE: 3,
    SystemClass.GENERIC_OFFICE: 1,
}
_CLASS_ADDITIONAL_POINTS = {
    SystemClass.INDUSTRY_ORDER_SYSTEM: 2,
    SystemClass.ERP_ACCOUNTING: 1,
    SystemClass.SUPPLIER_DATA: 1,
    SystemClass.CRM: 1,
    SystemClass.COMMERCE_STORE: 1,
    SystemClass.GENERIC_OFFICE: 0,
}
_CLASS_CAP = {
    SystemClass.INDUSTRY_ORDER_SYSTEM: 8,
    SystemClass.ERP_ACCOUNTING: 6,
    SystemClass.SUPPLIER_DATA: 5,
    SystemClass.CRM: 4,
    SystemClass.COMMERCE_STORE: 4,
    SystemClass.GENERIC_OFFICE: 1,
}
_CROSS_BOUNDARY_BONUS = 3


def _score_c3_stack(signals: SignalSet) -> tuple[int, list[str]]:
    # Deduplication policy (SCORING.md section 13): points are awarded per
    # DISTINCT system identity (class + normalised name), never per signal
    # row. signals.derive_signals already merges duplicates, but the scorer
    # re-groups by name defensively so a hand-built SignalSet — or a future
    # caller that forgets to merge — cannot inflate C3 by repeating a name.
    by_class: dict[SystemClass, dict[str, list[Signal]]] = {}
    for sig in signals.stack_signals:
        # Signal.value for stack signals is "<SystemClass>:<system name>"
        cls_str, _, name = sig.value.partition(":")
        try:
            cls = SystemClass(cls_str)
        except ValueError:
            continue
        by_class.setdefault(cls, {}).setdefault(" ".join(name.split()).strip().lower(), []).append(sig)

    non_generic_classes_present = {
        c for c in by_class if c != SystemClass.GENERIC_OFFICE
    }

    total = 0
    contributing: list[str] = []
    for cls in sorted(by_class, key=lambda c: c.value):
        by_name = by_class[cls]
        if cls == SystemClass.GENERIC_OFFICE and not non_generic_classes_present:
            # Generic-office rule (ICP.md section 4): scores 0 in isolation.
            continue
        distinct_systems = len(by_name)
        pts = _CLASS_FIRST_POINTS[cls] + _CLASS_ADDITIONAL_POINTS[cls] * (distinct_systems - 1)
        pts = min(pts, _CLASS_CAP[cls])
        total += pts
        for name in sorted(by_name):
            contributing.extend(s.id for s in by_name[name])

    if len(non_generic_classes_present) >= 2:
        total += _CROSS_BOUNDARY_BONUS

    return min(total, C3_CAP), contributing


# ---------------------------------------------------------------------------
# C4 - Transaction and organisation scale (0-15), non-monotonic. SCORING.md sec 6.
# ---------------------------------------------------------------------------

C4_CAP = 15
_SCALE_BAND_POINTS_REVENUE = {
    ScaleBand.SWEET_SPOT: 15,
    ScaleBand.LARGE: 11,
    ScaleBand.LOWER_MID: 10,
    ScaleBand.ENTERPRISE: 8,
    ScaleBand.SMALL: 5,
    ScaleBand.MICRO: 1,
    ScaleBand.UNKNOWN: 0,
}


def _score_c4_scale(signals: SignalSet) -> tuple[int, list[str]]:
    if signals.scale_signal is None or signals.scale_band == ScaleBand.UNKNOWN:
        return 0, []
    base = _SCALE_BAND_POINTS_REVENUE[signals.scale_band]
    if signals.scale_basis == "headcount":
        base = (base * 4) // 5  # integer floor, per ICP.md section 3 fallback
    return min(base, C4_CAP), [signals.scale_signal.id]


# ---------------------------------------------------------------------------
# C5 - Growth and buying trigger (0-15). SCORING.md section 7.
# ---------------------------------------------------------------------------

C5_CAP = 15
_TRIGGER_POINTS = {
    Trigger.GROWTH_HIGH: 8,
    Trigger.GROWTH_MODERATE: 5,
    Trigger.ACQUISITION: 5,
    Trigger.SYSTEM_MIGRATION: 5,
    Trigger.AP_AR_HIRING: 3,
    Trigger.NEW_FACILITY: 3,
    Trigger.LEADERSHIP_CHANGE_OPS: 2,
    Trigger.MARGIN_PRESSURE: 2,
    Trigger.SERVICE_VOLUME: 2,
    Trigger.CONTRACTION: 0,
}


def _ops_hiring_points(count: int) -> int:
    if count >= 3:
        return 4
    if count >= 1:
        return 3
    return 0


def _recency_multiplier_num_den(age_months: int | None) -> tuple[int, int]:
    """Returns (numerator, denominator) for integer-floor recency discount."""
    if age_months is None:
        return 1, 1  # unknown age: treat as full weight rather than penalise
    if age_months <= 24:
        return 1, 1
    if age_months <= 36:
        return 1, 2
    return 0, 1


def _score_c5_triggers(
    signals: SignalSet, trigger_ages_months: dict[str, int | None] | None = None
) -> tuple[int, list[str]]:
    trigger_ages_months = trigger_ages_months or {}
    total = 0
    contributing: list[str] = []

    growth_signals = [
        s for s in signals.trigger_signals
        if s.value in (Trigger.GROWTH_HIGH.value, Trigger.GROWTH_MODERATE.value)
    ]
    if growth_signals:
        best = growth_signals[0]
        for s in growth_signals:
            if s.value == Trigger.GROWTH_HIGH.value:
                best = s
                break
        base = _TRIGGER_POINTS[Trigger(best.value)]
        num, den = _recency_multiplier_num_den(trigger_ages_months.get(best.id))
        total += (base * num) // den
        contributing.append(best.id)

    ops_hiring_signals = [
        s
        for s in signals.trigger_signals
        if s.value.partition(":")[0] == Trigger.OPS_HIRING.value
    ]
    if ops_hiring_signals:
        # value carries role count encoded as "OPS_HIRING:<n>" by convention
        n = 0
        for s in ops_hiring_signals:
            _, _, count_str = s.value.partition(":")
            try:
                n = max(n, int(count_str))
            except ValueError:
                n = max(n, 1)
        base = _ops_hiring_points(n)
        rep = ops_hiring_signals[0]
        num, den = _recency_multiplier_num_den(trigger_ages_months.get(rep.id))
        total += (base * num) // den
        contributing.extend(s.id for s in ops_hiring_signals)

    other_single_triggers = (
        Trigger.ACQUISITION,
        Trigger.SYSTEM_MIGRATION,
        Trigger.AP_AR_HIRING,
        Trigger.NEW_FACILITY,
        Trigger.LEADERSHIP_CHANGE_OPS,
        Trigger.MARGIN_PRESSURE,
        Trigger.SERVICE_VOLUME,
    )
    for trig in other_single_triggers:
        matches = [s for s in signals.trigger_signals if s.value == trig.value]
        if not matches:
            continue
        base = _TRIGGER_POINTS[trig]
        rep = matches[0]
        num, den = _recency_multiplier_num_den(trigger_ages_months.get(rep.id))
        total += (base * num) // den
        contributing.extend(s.id for s in matches)

    return min(total, C5_CAP), contributing


# ---------------------------------------------------------------------------
# C6 - Evidence quality (0-10). SCORING.md section 8.
# ---------------------------------------------------------------------------

C6_CAP = 10


def _score_c6_evidence_quality(
    signals: SignalSet, all_evidence_ages_months_max: int | None
) -> int:
    total = 0
    total += min(len(set(signals.evidence_domains)), 4)

    n = signals.tier_1_2_fact_count
    if n >= 6:
        total += 3
    elif n >= 3:
        total += 2
    elif n >= 1:
        total += 1

    if all_evidence_ages_months_max is not None:
        if all_evidence_ages_months_max <= 12:
            total += 2
        elif all_evidence_ages_months_max <= 24:
            total += 1

    if len(set(signals.evidence_domains)) >= 2:
        total += 1

    return min(total, C6_CAP)


# ---------------------------------------------------------------------------
# Evidence grade (SCORING.md section 8)
# ---------------------------------------------------------------------------


def _evidence_grade(signals: SignalSet) -> EvidenceGrade:
    domains = len(set(signals.evidence_domains))
    facts_1_2 = signals.tier_1_2_fact_count
    if domains >= 3 and facts_1_2 >= 5:
        return EvidenceGrade.A
    if domains >= 2 and facts_1_2 >= 3:
        return EvidenceGrade.B
    if facts_1_2 >= 1:
        return EvidenceGrade.C
    return EvidenceGrade.D


# ---------------------------------------------------------------------------
# Banding (SCORING.md section 9)
# ---------------------------------------------------------------------------


def _band_for(total: int) -> Band:
    if total >= 80:
        return Band.PRIORITY
    if total >= 65:
        return Band.INVESTIGATE
    if total >= 50:
        return Band.WATCH
    return Band.DEPRIORITIZE


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def score(
    signals: SignalSet,
    *,
    trigger_ages_months: dict[str, int | None] | None = None,
    evidence_age_months_max: int | None = None,
) -> ScoreResult:
    """Pure function: same SignalSet in, same ScoreResult out, always.

    ``trigger_ages_months`` and ``evidence_age_months_max`` are integer ages
    in months, precomputed by the caller from Evidence.published_at against a
    fixed "as of" date — kept out of this function so it never reads a clock
    (CLAUDE.md R8).
    """
    if _gate_out_of_icp(signals):
        return ScoreResult(status="OUT_OF_ICP", total=None, evidence_grade=EvidenceGrade.D)

    if _gate_insufficient_evidence(signals):
        return ScoreResult(
            status="INSUFFICIENT_EVIDENCE", total=None, evidence_grade=EvidenceGrade.D
        )

    c1, c1_sigs = _score_c1_vertical_fit(signals)
    c2, c2_sigs = _score_c2_ops_complexity(signals)
    c3, c3_sigs = _score_c3_stack(signals)
    c4, c4_sigs = _score_c4_scale(signals)
    c5, c5_sigs = _score_c5_triggers(signals, trigger_ages_months)
    c6 = _score_c6_evidence_quality(signals, evidence_age_months_max)

    total = c1 + c2 + c3 + c4 + c5 + c6
    total = max(0, min(100, total))

    grade = _evidence_grade(signals)
    flags: list[str] = []
    if signals.is_public_customer:
        flags.append("PUBLIC_CUSTOMER")
    if signals.is_ecosystem_ambiguous:
        flags.append("ECOSYSTEM_AMBIGUOUS")
    if signals.segment_conflict == "unresolved":
        flags.append("SEGMENT_CONFLICT_UNRESOLVED")
    elif signals.segment_conflict == "resolved_by_tier":
        flags.append("SEGMENT_CONFLICT_RESOLVED_BY_TIER")
    if signals.scale_conflict:
        flags.append("SCALE_CONFLICT")
    if grade == EvidenceGrade.D:
        flags.append("LOW_EVIDENCE")

    reported_as: str = "point"
    rng: tuple[int, int] | None = None
    if grade == EvidenceGrade.D:
        reported_as = "range"
        rng = (max(0, total - 8), min(100, total + 8))

    return ScoreResult(
        status="SCORED",
        total=total,
        components={"c1": c1, "c2": c2, "c3": c3, "c4": c4, "c5": c5, "c6": c6},
        contributing_signals={
            "c1": c1_sigs,
            "c2": c2_sigs,
            "c3": c3_sigs,
            "c4": c4_sigs,
            "c5": c5_sigs,
            "c6": [],  # evidence quality is a corpus-wide property, not signal-specific
        },
        evidence_grade=grade,
        band=_band_for(total),
        flags=flags,
        reported_as=reported_as,
        range=rng,
    )
