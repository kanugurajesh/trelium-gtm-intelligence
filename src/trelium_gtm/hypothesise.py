"""Workflow hypothesis generation, constrained to the closed taxonomy.

The model selects from taxonomy.WorkflowID and cannot extend it (CLAUDE.md
R11) — an unrecognised workflow_id is dropped in code, not trusted. Every
hypothesis statement must pass the hedging linter (lint.py) before it can
become an Inference; a failure gets exactly one regeneration attempt with
the failure reason fed back, then the hypothesis is dropped and logged as a
research gap (docs/IMPLEMENTATION_PLAN.md phase 5).

Persona and boundary_count are NOT asked of the model — both are looked up
or computed deterministically (persona.py, _boundary_count below), per
docs/ICP.md section 7: persona selection is a lookup, not a judgment.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field as dataclass_field
from pathlib import Path

from trelium_gtm.lint import lint_inference_statement
from trelium_gtm.llm_cache import get as cache_get, make_key, put as cache_put
from trelium_gtm.models import Fact, Inference, SignalSet, ValidationQuestion, WorkflowHypothesis
from trelium_gtm.persona import select_persona
from trelium_gtm.taxonomy import SystemClass, WORKFLOW_TO_TRELIUM_AGENT, WorkflowID

DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
MAX_HYPOTHESES = 3

_WORKFLOW_LIST = "\n".join(
    f'  - "{wf.value}": {WORKFLOW_TO_TRELIUM_AGENT[wf]}' for wf in WorkflowID
)

_SYSTEM_PROMPT_TEMPLATE = """You are a GTM research analyst proposing which operational workflow(s) \
at a company might be worth Trelium investigating, based ONLY on the facts provided below.

You will be given a numbered list of verified facts about the company (each with an id). You \
must pick 1 to {max_hyp} workflow hypotheses from this FIXED list only - do not invent a \
workflow outside it:
{workflow_list}

CRITICAL RULES:
1. Every hypothesis is a HYPOTHESIS, never a stated fact about the company. The "statement" \
field MUST use hedging language such as "may", "likely", "appears", "worth investigating", \
"could", "plausibly", "is a candidate for". NEVER write an assertive claim like "the company \
manually does X" or "the company currently uses X" - the company's actual internal process is \
unknown to you.
2. "from_fact_ids" must be a subset of the provided fact ids that actually support this \
hypothesis. Do not reference fact ids that were not provided.
3. Each hypothesis needs at least one "validation_question": a question answerable in a single \
discovery call (not researchable online), plus a "kills_if" describing what answer would \
falsify the hypothesis.
4. Rank hypotheses by how well the provided facts support them; put the strongest first.
5. "confidence" is your own assessment: "low", "medium", or "high".

Worked example statement (correct style): "Inbound PO handling into the order system may be \
worth investigating at this company, given its distributor segment and multiple named order \
systems." (Note: hedged, not asserting the company's internal process.)

Respond with ONLY a JSON object of this shape:
{{"hypotheses": [{{"workflow_id": "...", "statement": "...", "reason": "...", \
"from_fact_ids": ["..."], "confidence": "...", "validation_questions": \
[{{"question": "...", "kills_if": "..."}}]}}]}}
If no hypothesis is well supported by the facts, respond {{"hypotheses": []}}.
"""


def _build_system_prompt() -> str:
    return _SYSTEM_PROMPT_TEMPLATE.format(max_hyp=MAX_HYPOTHESES, workflow_list=_WORKFLOW_LIST)


def _build_user_prompt(company: str, facts: list[Fact]) -> str:
    lines = [f"COMPANY: {company}", "", "FACTS:"]
    for f in facts:
        extra = f" [{f.field}={f.value}]" if f.field else ""
        lines.append(f"- id={f.id}: {f.statement}{extra}")
    return "\n".join(lines)


def _call_openai(system_prompt: str, user_prompt: str, model: str) -> dict:
    from openai import OpenAI  # lazy import; not needed on a cache hit

    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    return json.loads(response.choices[0].message.content)


def _boundary_count(signals: SignalSet) -> int:
    """Deterministic: number of distinct non-generic system classes observed
    in the account's stack. Same value for every hypothesis on this account
    — a simplification documented in docs/IMPLEMENTATION_PLAN.md phase 5;
    refining it per-workflow was judged not worth the added complexity for
    a one-day project.
    """
    classes: set[str] = set()
    for sig in signals.stack_signals:
        cls_str, _, _ = sig.value.partition(":")
        if cls_str and cls_str != SystemClass.GENERIC_OFFICE.value:
            classes.add(cls_str)
    return len(classes)


@dataclass
class HypothesisOutcome:
    inferences: list[Inference]
    validation_questions: list[ValidationQuestion]
    workflow_hypotheses: list[WorkflowHypothesis]
    gaps: list[str] = dataclass_field(default_factory=list)
    raw_count: int = 0


def _parse_and_validate(
    payload: dict,
    fact_ids: set[str],
    id_prefix: str,
) -> tuple[list[Inference], list[ValidationQuestion], list[tuple[str, dict]], list[str]]:
    """Returns (accepted_inferences, accepted_questions, needs_regen, gaps).

    needs_regen holds (workflow_id, raw_claim) pairs whose statement failed
    the hedging linter, for one retry by the caller.
    """
    accepted_inferences: list[Inference] = []
    accepted_questions: list[ValidationQuestion] = []
    needs_regen: list[tuple[str, dict]] = []
    gaps: list[str] = []

    raw_hyps = payload.get("hypotheses", []) if isinstance(payload, dict) else []
    for i, h in enumerate(raw_hyps):
        workflow_id_raw = h.get("workflow_id")
        try:
            WorkflowID(workflow_id_raw)
        except ValueError:
            gaps.append(f"Dropped hypothesis: unrecognised workflow_id {workflow_id_raw!r}")
            continue

        statement = str(h.get("statement", "")).strip()
        from_fact_ids = [fid for fid in h.get("from_fact_ids", []) if fid in fact_ids]
        if not from_fact_ids:
            gaps.append(
                f"Dropped {workflow_id_raw} hypothesis: no valid from_fact_ids (I1)"
            )
            continue

        raw_questions = h.get("validation_questions", [])
        questions = [
            q for q in raw_questions if q.get("question") and q.get("kills_if")
        ]
        if not questions:
            gaps.append(
                f"Dropped {workflow_id_raw} hypothesis: no validation question with kills_if (I2)"
            )
            continue

        lint_result = lint_inference_statement(statement)
        if not lint_result.ok:
            needs_regen.append((workflow_id_raw, h))
            continue

        inf_id = f"inf_{id_prefix}_{i}"
        vqs: list[ValidationQuestion] = []
        for j, q in enumerate(questions):
            vqs.append(
                ValidationQuestion(
                    id=f"vq_{id_prefix}_{i}_{j}",
                    question=str(q["question"]),
                    tests_inference_id=inf_id,
                    kills_if=str(q["kills_if"]),
                )
            )
        accepted_questions.extend(vqs)
        accepted_inferences.append(
            Inference(
                id=inf_id,
                statement=statement,
                from_fact_ids=from_fact_ids,
                rule=f"ICP.WF.{workflow_id_raw}",
                model_confidence=h.get("confidence", "low")
                if h.get("confidence") in ("low", "medium", "high")
                else "low",
                validation_question_ids=[vq.id for vq in vqs],
            )
        )

    return accepted_inferences, accepted_questions, needs_regen, gaps


def generate_hypotheses(
    *,
    company: str,
    facts: list[Fact],
    signals: SignalSet,
    cache_dir: Path,
    model: str = DEFAULT_MODEL,
    id_prefix: str = "h",
) -> HypothesisOutcome:
    if not facts:
        return HypothesisOutcome(
            inferences=[],
            validation_questions=[],
            workflow_hypotheses=[],
            gaps=["No facts available: cannot generate workflow hypotheses"],
        )

    fact_ids = {f.id for f in facts}
    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(company, facts)

    cache_key = make_key(model, system_prompt, user_prompt)
    payload = cache_get(cache_key, cache_dir)
    if payload is None:
        payload = _call_openai(system_prompt, user_prompt, model)
        cache_put(cache_key, payload, cache_dir)

    inferences, questions, needs_regen, gaps = _parse_and_validate(payload, fact_ids, id_prefix)

    if needs_regen:
        failures_desc = "\n".join(
            f'- workflow_id={wid}, original statement={h.get("statement", "")!r} was rejected: '
            "must use hedged language, not an assertive claim about the company's actual process."
            for wid, h in needs_regen
        )
        retry_user_prompt = (
            user_prompt
            + "\n\nThe following hypotheses you previously proposed were rejected for using "
            "assertive (non-hedged) language. Rewrite ONLY these, using hedged language, and "
            "return them in the same JSON shape under \"hypotheses\":\n" + failures_desc
        )
        retry_key = make_key(model, system_prompt, retry_user_prompt)
        retry_payload = cache_get(retry_key, cache_dir)
        if retry_payload is None:
            retry_payload = _call_openai(system_prompt, retry_user_prompt, model)
            cache_put(retry_key, retry_payload, cache_dir)

        retry_inferences, retry_questions, still_failing, retry_gaps = _parse_and_validate(
            retry_payload, fact_ids, id_prefix + "_r"
        )
        inferences.extend(retry_inferences)
        questions.extend(retry_questions)
        gaps.extend(retry_gaps)
        for wid, h in still_failing:
            gaps.append(
                f"Dropped {wid} hypothesis after one regeneration attempt: "
                f"still failed hedging linter ({h.get('statement', '')!r})"
            )

    primary, _secondary, rationale = select_persona(signals.segment_label, signals.scale_band)
    boundary_count = _boundary_count(signals)

    workflow_hypotheses: list[WorkflowHypothesis] = []
    for inf in inferences:
        workflow_id_str = inf.rule.removeprefix("ICP.WF.")
        try:
            wf_id = WorkflowID(workflow_id_str)
        except ValueError:
            continue
        workflow_hypotheses.append(
            WorkflowHypothesis(
                workflow_id=wf_id,
                inference_id=inf.id,
                boundary_count=boundary_count,
                confidence=inf.model_confidence,
                persona=primary,
                persona_rationale=rationale,
            )
        )

    return HypothesisOutcome(
        inferences=inferences,
        validation_questions=questions,
        workflow_hypotheses=workflow_hypotheses,
        gaps=gaps,
        raw_count=len(payload.get("hypotheses", [])) if isinstance(payload, dict) else 0,
    )
