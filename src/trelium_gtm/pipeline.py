"""End-to-end orchestration for one account: collect -> extract -> verify ->
signals -> score -> hypothesise -> AccountBrief.

This is the only module that calls collect.py, extract.py and
hypothesise.py together; nothing here does interpretation or scoring
itself, it just wires the already-tested pieces together and adds the
rule-based research gaps from docs/EVIDENCE_MODEL.md section 6.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field as dataclass_field
from datetime import date
from pathlib import Path

from trelium_gtm.collect import CollectResult, collect_source
from trelium_gtm.extract import extract_claims
from trelium_gtm.hypothesise import generate_hypotheses
from trelium_gtm.models import AccountBrief, Evidence, Fact
from trelium_gtm.scoring import score as score_signals
from trelium_gtm.signals import (
    compute_evidence_age_months_max,
    compute_trigger_ages_months,
    conflict_gaps,
    derive_signals,
)
from trelium_gtm.taxonomy import ScaleBand, SegmentTier


@dataclass
class SourceSpec:
    url: str
    publisher: str
    title: str
    # A source the caller already fetched (the homepage, whose HTML was
    # needed for link discovery). Reused as-is so one page is requested
    # once per run, and so the text extraction sees is byte-identical to
    # the text discovery saw.
    prefetched: CollectResult | None = None


@dataclass
class RunReport:
    brief: AccountBrief
    collection_errors: list[str] = dataclass_field(default_factory=list)
    extraction_rejection_rate: float | None = None
    raw_claims_count: int = 0
    raw_hypotheses_count: int = 0
    sources_collected: int = 0


def _corpus_hash(evidence: list[Evidence]) -> str:
    parts = sorted(f"{e.id}:{e.content_sha256}" for e in evidence)
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _rule_based_gaps(
    facts: list[Fact],
    evidence: list[Evidence],
    signals,
    collection_errors: list[str],
) -> list[str]:
    gaps: list[str] = []
    if signals.segment_tier == SegmentTier.UNRESOLVED:
        gaps.append("Segment unconfirmed from primary sources")
    if signals.scale_band == ScaleBand.UNKNOWN:
        gaps.append("No sourced scale figure; scale scored 0")
    if not signals.stack_signals:
        gaps.append("No order or ERP system identified in public sources")
    if not signals.trigger_signals:
        gaps.append("No growth, hiring or migration trigger found in public sources")
    gaps.extend(conflict_gaps(signals, evidence))
    gaps.extend(collection_errors)
    gaps.append("Not de-duplicated against Trelium CRM")
    return gaps


def run_account(
    *,
    company: str,
    domain: str,
    sources: list[SourceSpec],
    evidence_dir: Path,
    cache_dir: Path,
    as_of: date,
    is_public_customer: bool = False,
    is_ecosystem_ambiguous: bool = False,
    generate_workflow_hypotheses: bool = True,
    inter_request_delay: float = 0.0,
) -> RunReport:
    """``inter_request_delay`` is the pause, in seconds, between consecutive
    live fetches for one account (R22: one request at a time, spaced out).
    Prefetched sources cost no request and trigger no pause. Tests leave it
    at zero because they never hit the network.
    """
    all_facts: list[Fact] = []
    all_evidence: list[Evidence] = []
    collection_errors: list[str] = []
    zero_yield_pages: list[str] = []
    total_raw_claims = 0
    total_rejected = 0
    total_duplicates = 0
    sources_collected = 0
    live_fetches = 0

    for source in sources:
        if source.prefetched is not None:
            collect_result = source.prefetched
        else:
            if live_fetches > 0 and inter_request_delay > 0:
                time.sleep(inter_request_delay)
            collect_result = collect_source(source.url, evidence_dir)
            live_fetches += 1
        if not collect_result.ok:
            collection_errors.append(f"Failed to collect {source.url}: {collect_result.error}")
            continue
        sources_collected += 1

        outcome = extract_claims(
            source_url=source.url,
            company_domain=domain,
            snapshot_text=collect_result.text,
            publisher=source.publisher,
            title=source.title,
            retrieved_at=f"{as_of.isoformat()}T00:00:00Z",
            snapshot_path=collect_result.snapshot_path,
            cache_dir=cache_dir,
        )
        all_facts.extend(outcome.facts)
        all_evidence.extend(outcome.evidence)
        total_raw_claims += outcome.raw_claims_count
        duplicates = sum(1 for r in outcome.rejected if "duplicate" in str(r.get("reason", "")))
        total_duplicates += duplicates
        total_rejected += len(outcome.rejected) - duplicates
        # A page that was read but contributed nothing is part of the
        # research record (R6): the reader should know it was looked at.
        if outcome.raw_claims_count == 0:
            zero_yield_pages.append(f"Read {source.url}: no extractable claims")
        elif not outcome.facts:
            zero_yield_pages.append(
                f"Read {source.url}: all {outcome.raw_claims_count} extracted claims failed "
                "verbatim-quote verification"
            )

    signals = derive_signals(
        all_facts,
        all_evidence,
        is_public_customer=is_public_customer,
        is_ecosystem_ambiguous=is_ecosystem_ambiguous,
    )
    trigger_ages = compute_trigger_ages_months(signals, as_of)
    evidence_age_min = compute_evidence_age_months_max(all_evidence, as_of)
    score_result = score_signals(
        signals, trigger_ages_months=trigger_ages, evidence_age_months_max=evidence_age_min
    )

    inferences = []
    validation_questions = []
    workflow_hypotheses = []
    hyp_gaps: list[str] = []
    raw_hyp_count = 0

    should_hypothesise = (
        generate_workflow_hypotheses
        and score_result.status == "SCORED"
        and all_facts
    )
    if should_hypothesise:
        hyp_outcome = generate_hypotheses(
            company=company,
            facts=all_facts,
            signals=signals,
            cache_dir=cache_dir,
        )
        inferences = hyp_outcome.inferences
        validation_questions = hyp_outcome.validation_questions
        workflow_hypotheses = hyp_outcome.workflow_hypotheses
        hyp_gaps = hyp_outcome.gaps
        raw_hyp_count = hyp_outcome.raw_count

    gaps = _rule_based_gaps(all_facts, all_evidence, signals, collection_errors + zero_yield_pages)
    if total_raw_claims > 0 and total_rejected > 0:
        gaps.append(
            f"{total_rejected}/{total_raw_claims} extracted claims failed verbatim-quote "
            "verification and were discarded"
        )
    if total_duplicates > 0:
        gaps.append(
            f"{total_duplicates}/{total_raw_claims} extracted claims duplicated an already "
            "accepted claim on the same page and were collapsed"
        )
    gaps.extend(hyp_gaps)

    brief = AccountBrief(
        company=company,
        domain=domain,
        corpus_hash=_corpus_hash(all_evidence),
        facts=all_facts,
        inferences=inferences,
        validation_questions=validation_questions,
        workflow_hypotheses=workflow_hypotheses,
        evidence=all_evidence,
        signals=signals,
        score=score_result,
        research_gaps=gaps,
        flags=list(score_result.flags),
    )

    return RunReport(
        brief=brief,
        collection_errors=collection_errors,
        extraction_rejection_rate=(total_rejected / total_raw_claims) if total_raw_claims else None,
        raw_claims_count=total_raw_claims,
        raw_hypotheses_count=raw_hyp_count,
        sources_collected=sources_collected,
    )
