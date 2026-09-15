"""Typed schema for the evidence model: Evidence, Fact, Inference, Signal, Brief.

The fact/inference separation (CLAUDE.md R4, R7) is enforced here at the type
boundary, not by convention:

- ``Fact`` and ``Inference`` carry a discriminating ``kind`` Literal so a
  pydantic model cannot silently coerce one into the other.
- ``AccountBrief.facts`` is typed ``list[Fact]`` and ``AccountBrief.inferences``
  is typed ``list[Inference]``. There is no field either type can occupy in
  place of the other.
- Structural invariants (F1, I1, I2, H1 from docs/EVIDENCE_MODEL.md and
  docs/SCORING.md) are pydantic validators, so a violation raises at
  construction time rather than surfacing later as a bad brief.

Content invariants that require the raw snapshot text (E1, E2) live in
``evidence/verify.py`` because they need bytes this module does not have.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from trelium_gtm.taxonomy import (
    Band,
    EvidenceGrade,
    ScaleBand,
    SegmentLabel,
    SegmentTier,
    SourceTier,
    WorkflowID,
)

Confidence = Literal["low", "medium", "high"]


class Evidence(BaseModel):
    """One committed source snapshot plus a verbatim quote drawn from it."""

    model_config = ConfigDict(frozen=True)

    id: str
    source_url: str
    source_tier: SourceTier
    publisher: str
    title: str
    retrieved_at: str  # ISO 8601 UTC
    published_at: str | None = None
    snapshot_path: str
    content_sha256: str
    quote: str
    quote_offset: int

    @field_validator("quote")
    @classmethod
    def _quote_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Evidence.quote must not be empty")
        if len(v) > 400:
            raise ValueError("Evidence.quote must be <= 400 chars")
        return v

    @field_validator("quote_offset")
    @classmethod
    def _offset_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Evidence.quote_offset must be >= 0")
        return v


class Fact(BaseModel):
    """A claim directly supported by evidence. See EVIDENCE_MODEL.md F1-F3."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["fact"] = "fact"
    id: str
    statement: str
    evidence_ids: list[str]
    field: str | None = None
    value: Any | None = None

    @field_validator("evidence_ids")
    @classmethod
    def _f1_min_one_evidence(cls, v: list[str]) -> list[str]:
        if len(v) < 1:
            raise ValueError("Fact violates F1: requires >= 1 evidence_ids")
        return v


class ValidationQuestion(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    question: str
    tests_inference_id: str
    kills_if: str

    @field_validator("kills_if")
    @classmethod
    def _kills_if_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("ValidationQuestion.kills_if must not be empty")
        return v


class Inference(BaseModel):
    """A hypothesis derived from >=1 Fact. Never a statement of what is true.

    See EVIDENCE_MODEL.md I1-I3. Confidence here is the model's own emitted
    value (kept for calibration measurement, CLAUDE.md R9) — the confidence
    actually used in rendering is recomputed deterministically in
    ``signals.assign_confidence`` from the parent evidence profile.
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["inference"] = "inference"
    id: str
    statement: str
    from_fact_ids: list[str]
    rule: str
    model_confidence: Confidence
    validation_question_ids: list[str]

    @field_validator("from_fact_ids")
    @classmethod
    def _i1_min_one_fact(cls, v: list[str]) -> list[str]:
        if len(v) < 1:
            raise ValueError("Inference violates I1: requires >= 1 from_fact_ids")
        return v

    @field_validator("validation_question_ids")
    @classmethod
    def _i2_min_one_question(cls, v: list[str]) -> list[str]:
        if len(v) < 1:
            raise ValueError("Inference violates I2: requires >= 1 validation_question_ids")
        return v


class Signal(BaseModel):
    """A single evidenced input to deterministic scoring. See SCORING.md H1."""

    model_config = ConfigDict(frozen=True)

    id: str
    kind: str  # "segment" | "scale" | "stack" | "trigger" | "ops"
    value: str
    evidence_ids: list[str]
    fact_ids: list[str]
    published_at: str | None = None  # for recency discount on triggers

    @field_validator("evidence_ids")
    @classmethod
    def _h1_min_one_evidence(cls, v: list[str]) -> list[str]:
        if len(v) < 1:
            raise ValueError("Signal violates H1: requires >= 1 evidence_ids")
        return v


class SignalSet(BaseModel):
    """All derived signals for one account, the sole input to score()."""

    model_config = ConfigDict(frozen=True)

    segment_label: SegmentLabel = SegmentLabel.UNRESOLVED
    segment_tier: SegmentTier = SegmentTier.UNRESOLVED
    segment_signal: Signal | None = None

    scale_band: ScaleBand = ScaleBand.UNKNOWN
    scale_basis: Literal["revenue", "headcount", "unknown"] = "unknown"
    scale_signal: Signal | None = None

    stack_signals: list[Signal] = []
    trigger_signals: list[Signal] = []
    ops_signals: list[Signal] = []

    evidence_domains: list[str] = []
    tier_1_2_fact_count: int = 0
    is_public_customer: bool = False
    is_ecosystem_ambiguous: bool = False
    has_any_evidence: bool = False


class WorkflowHypothesis(BaseModel):
    model_config = ConfigDict(frozen=True)

    workflow_id: WorkflowID
    inference_id: str
    boundary_count: int
    confidence: Confidence
    persona: str
    persona_rationale: str

    @field_validator("boundary_count")
    @classmethod
    def _boundary_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("boundary_count must be >= 0")
        return v


class ScoreResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["SCORED", "OUT_OF_ICP", "INSUFFICIENT_EVIDENCE"] = "SCORED"
    total: int | None = None
    components: dict[str, int] = {}
    contributing_signals: dict[str, list[str]] = {}
    evidence_grade: EvidenceGrade = EvidenceGrade.D
    band: Band | None = None
    flags: list[str] = []
    reported_as: Literal["point", "range"] = "point"
    range: tuple[int, int] | None = None

    @model_validator(mode="after")
    def _total_bounds(self) -> "ScoreResult":
        if self.total is not None and not (0 <= self.total <= 100):
            raise ValueError("ScoreResult.total must be within 0-100")
        return self


class AccountBrief(BaseModel):
    """The rendered unit of output. Facts and inferences are structurally
    separated: this is the type that CLAUDE.md R4 and EVIDENCE_MODEL.md
    section 5 point at when they say the renderer "cannot mix them".
    """

    model_config = ConfigDict(frozen=True)

    company: str
    domain: str
    corpus_hash: str

    facts: list[Fact] = []
    inferences: list[Inference] = []
    validation_questions: list[ValidationQuestion] = []
    workflow_hypotheses: list[WorkflowHypothesis] = []
    evidence: list[Evidence] = []

    signals: SignalSet = SignalSet()
    score: ScoreResult = ScoreResult(status="INSUFFICIENT_EVIDENCE")

    research_gaps: list[str] = []
    flags: list[str] = []

    @model_validator(mode="after")
    def _references_resolve(self) -> "AccountBrief":
        evidence_ids = {e.id for e in self.evidence}
        fact_ids = {f.id for f in self.facts}
        vq_ids = {q.id for q in self.validation_questions}

        for f in self.facts:
            missing = [eid for eid in f.evidence_ids if eid not in evidence_ids]
            if missing:
                raise ValueError(f"Fact {f.id} references unresolved evidence: {missing}")

        for inf in self.inferences:
            missing_facts = [fid for fid in inf.from_fact_ids if fid not in fact_ids]
            if missing_facts:
                raise ValueError(
                    f"Inference {inf.id} references unresolved facts: {missing_facts}"
                )
            missing_vq = [
                vid for vid in inf.validation_question_ids if vid not in vq_ids
            ]
            if missing_vq:
                raise ValueError(
                    f"Inference {inf.id} references unresolved validation questions: {missing_vq}"
                )

        inference_ids = {i.id for i in self.inferences}
        for wh in self.workflow_hypotheses:
            if wh.inference_id not in inference_ids:
                raise ValueError(
                    f"WorkflowHypothesis {wh.workflow_id} references "
                    f"unresolved inference: {wh.inference_id}"
                )
        return self
