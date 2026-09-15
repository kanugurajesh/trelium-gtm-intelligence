"""LLM-based claim extraction, gated by mandatory verbatim-quote verification.

The model is asked for a verbatim quote, never an offset — models are
reliably worse at exact character offsets than at exact quotes (see
docs/IMPLEMENTATION_PLAN.md phase 4 risk note). The offset is derived in
code by searching the snapshot for a unique occurrence of the quote
(``evidence.verify.find_quote_offset``); a quote that doesn't occur, or
occurs more than once, is rejected here and never becomes a Fact.

Every accepted claim is classified into a fixed field taxonomy in code, not
trusted from the model's own labelling: an unrecognised or malformed field
value is downgraded to "other" (rendered, but scored as zero — see
signals.py's docstring), never dropped silently and never coerced into a
scoring field it doesn't actually satisfy.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field as dataclass_field
from pathlib import Path

from trelium_gtm.evidence.store import compute_evidence_id, sha256_text
from trelium_gtm.evidence.verify import classify_source_tier, find_quote_offset
from trelium_gtm.llm_cache import get as cache_get, make_key, put as cache_put
from trelium_gtm.models import Evidence, Fact
from trelium_gtm.taxonomy import OpsSubSignal, SegmentLabel, Trigger

DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
MAX_PAGE_CHARS = 12000

_ALLOWED_FIELDS = {
    "segment",
    "revenue_usd",
    "employee_count",
    "system",
    "trigger",
    "ops_subsignal",
    "ops_hiring_role",
    "other",
}
_SEGMENT_VALUES = {e.value for e in SegmentLabel}
_TRIGGER_VALUES = {e.value for e in Trigger if e != Trigger.OPS_HIRING}
_OPS_SUBSIGNAL_VALUES = {e.value for e in OpsSubSignal}

# Deterministic backstop for revenue_usd misclassification: prompt-level
# instruction alone was insufficient in practice (verified live — a claim
# about "$2.5 million dollars of blank soft goods" in inventory was still
# tagged revenue_usd after tightening the prompt). If the supporting quote
# contains any of these, the figure is describing something other than the
# company's own annual revenue and the claim is downgraded to "other"
# regardless of what field the model assigned. Consistent with this
# project's own principle: verify in code, don't just ask more nicely.
_REVENUE_DISQUALIFYING_KEYWORDS = (
    "inventory", "warehouse", "square feet", "sq ft", "sq. ft", "space to hold",
    "square foot", "raised", "funding", "valued at", "valuation", "capacity",
    "invested", "investment of", "grant of", "loan of", "insured for",
)

# Same problem, same fix, found on the same live batch: "over 25 years of
# experience" was tagged employee_count=25 (High Caliber Line). A number is
# only a headcount if the quote actually says so; require a positive
# indicator rather than trying to blacklist every non-headcount phrasing.
_EMPLOYEE_COUNT_REQUIRED_KEYWORDS = (
    "employee", "staff", "team of", "workforce", "professional", "personnel",
    "headcount", "workers", "people work",
)

_SYSTEM_PROMPT_TEMPLATE = """You are a careful research analyst extracting claims from ONE webpage of \
company text for a GTM research tool. You must never invent or paraphrase.

Rules, all mandatory:
1. Every claim's "quote" MUST be copied EXACTLY, character-for-character, from the \
provided text. No paraphrasing, no ellipses, no combining separate sentences, no \
fixing typos or spacing. If you cannot find an exact verbatim span supporting a \
claim, do not include that claim at all.
2. Only extract claims actually stated by specific text on the page. Do not use \
outside knowledge about the company.
3. Classify each claim into exactly one "field":
   - "segment": value must be exactly one of: {segment_values}
   - "revenue_usd": value is the COMPANY'S OWN TOTAL ANNUAL REVENUE (sales/turnover) in US \
dollars as a plain number or "NNNM"/"NNNB" string (e.g. "87000000" or "87M"), only if the \
text specifically states an annual revenue or sales figure for the company. Do NOT use this \
field for inventory value, warehouse capacity, funding raised, a single product's price, deal \
size, or any dollar figure that is not the company's own annual revenue - classify those as \
"other" instead.
   - "employee_count": value is a plain integer string, only if a specific headcount \
appears in the text
   - "system": value is the name of one named software/platform/system mentioned \
(e.g. "SAGE", "NetSuite", "Shopify")
   - "trigger": value must be exactly one of: {trigger_values}
   - "ops_subsignal": value must be exactly one of: {ops_values}
   - "ops_hiring_role": value is the job title of one specific open operations, \
order-entry, AP or AR role found on the page
   - "other": any other factual claim worth recording that does not fit above; \
value may be an empty string
4. Output 0 to 20 claims. Fewer, accurate claims beat many speculative ones.
5. "statement" is a short factual sentence describing the claim, stated plainly \
(not hedged, not a hypothesis - hypotheses about workflows are generated elsewhere \
by a separate, later step and must NOT be produced here).
6. "model_confidence" is your own confidence: "low", "medium", or "high".

"field" is always the CATEGORY NAME from the list above (e.g. the literal string \
"segment"). "value" is always the payload for that category (e.g. the literal \
string "promotional_products_distributor"). Never swap them.

Worked example for a page that says "Acme Corp is a promotional products \
distributor serving nationwide clients.":
{{"claims": [{{"field": "segment", "value": "promotional_products_distributor", \
"statement": "Acme Corp is a promotional products distributor.", "quote": "Acme \
Corp is a promotional products distributor serving nationwide clients.", \
"model_confidence": "high"}}]}}

Respond with ONLY a JSON object of this exact shape:
{{"claims": [{{"field": "...", "value": "...", "statement": "...", "quote": "...", \
"model_confidence": "..."}}]}}
If there are no extractable claims, respond {{"claims": []}}.
"""


def _build_system_prompt() -> str:
    return _SYSTEM_PROMPT_TEMPLATE.format(
        segment_values=", ".join(sorted(_SEGMENT_VALUES)),
        trigger_values=", ".join(sorted(_TRIGGER_VALUES)),
        ops_values=", ".join(sorted(_OPS_SUBSIGNAL_VALUES)),
    )


def _coerce_numeric(value: object) -> float | None:
    if value is None:
        return None
    cleaned = str(value).strip().replace(",", "").replace("$", "")
    match = re.match(r"^([\d.]+)\s*([MBK])$", cleaned, re.IGNORECASE)
    multiplier = 1.0
    if match:
        cleaned, suffix = match.groups()
        multiplier = {"K": 1_000.0, "M": 1_000_000.0, "B": 1_000_000_000.0}[suffix.upper()]
    try:
        return float(cleaned) * multiplier
    except ValueError:
        return None


@dataclass
class ExtractionOutcome:
    facts: list[Fact]
    evidence: list[Evidence]
    rejected: list[dict] = dataclass_field(default_factory=list)
    raw_claims_count: int = 0

    @property
    def rejection_rate(self) -> float:
        if self.raw_claims_count == 0:
            return 0.0
        return len(self.rejected) / self.raw_claims_count


def _call_openai(system_prompt: str, user_prompt: str, model: str) -> dict:
    from openai import OpenAI  # imported lazily so offline/cached runs need no SDK config

    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(response.choices[0].message.content)


def extract_claims(
    *,
    source_url: str,
    company_domain: str,
    snapshot_text: str,
    publisher: str,
    title: str,
    retrieved_at: str,
    snapshot_path: str,
    cache_dir: Path,
    model: str = DEFAULT_MODEL,
    published_at: str | None = None,
) -> ExtractionOutcome:
    """Extract, then verify every claim before it becomes a Fact.

    Cache-first: identical (model, system prompt, user prompt) never calls
    the API twice, and a cache hit needs no API key at all.
    """
    system_prompt = _build_system_prompt()
    user_prompt = f"URL: {source_url}\nTITLE: {title}\n\nPAGE TEXT:\n{snapshot_text[:MAX_PAGE_CHARS]}"

    cache_key = make_key(model, system_prompt, user_prompt)
    payload = cache_get(cache_key, cache_dir)
    if payload is None:
        payload = _call_openai(system_prompt, user_prompt, model)
        cache_put(cache_key, payload, cache_dir)

    content_sha256 = sha256_text(snapshot_text)
    source_tier = classify_source_tier(source_url, company_domain)

    raw_claims = payload.get("claims", []) if isinstance(payload, dict) else []
    facts: list[Fact] = []
    evidence: list[Evidence] = []
    rejected: list[dict] = []

    for i, claim in enumerate(raw_claims):
        field = claim.get("field")
        value = claim.get("value")
        statement = str(claim.get("statement", "")).strip()
        quote = str(claim.get("quote", ""))

        if not quote or not statement:
            rejected.append({"quote": quote, "field": field, "reason": "missing quote or statement"})
            continue
        if len(quote) > 400:
            rejected.append({"quote": quote[:80] + "...", "field": field, "reason": "quote exceeds 400 chars"})
            continue

        offset = find_quote_offset(snapshot_text, quote)
        if offset is None:
            rejected.append(
                {
                    "quote": quote,
                    "field": field,
                    "reason": "E2: quote not found verbatim, or found more than once, in snapshot",
                }
            )
            continue

        if field not in _ALLOWED_FIELDS:
            field = "other"
        if field == "segment" and value not in _SEGMENT_VALUES:
            field = "other"
        if field == "trigger" and value not in _TRIGGER_VALUES:
            field = "other"
        if field == "ops_subsignal" and value not in _OPS_SUBSIGNAL_VALUES:
            field = "other"
        if field == "revenue_usd" and any(
            kw in quote.lower() for kw in _REVENUE_DISQUALIFYING_KEYWORDS
        ):
            field = "other"
        if field == "employee_count" and not any(
            kw in quote.lower() for kw in _EMPLOYEE_COUNT_REQUIRED_KEYWORDS
        ):
            field = "other"

        parsed_value: object = value
        if field in ("revenue_usd", "employee_count"):
            numeric = _coerce_numeric(value)
            if numeric is None:
                field = "other"
            else:
                parsed_value = numeric

        evidence_id = compute_evidence_id(source_url, quote)
        ev = Evidence(
            id=evidence_id,
            source_url=source_url,
            source_tier=source_tier,
            publisher=publisher,
            title=title,
            retrieved_at=retrieved_at,
            published_at=published_at,
            snapshot_path=snapshot_path,
            content_sha256=content_sha256,
            quote=quote,
            quote_offset=offset,
        )
        evidence.append(ev)
        facts.append(
            Fact(
                id=f"fct_{evidence_id[3:]}_{i}",
                statement=statement,
                evidence_ids=[evidence_id],
                field=None if field == "other" else field,
                value=None if field == "other" else parsed_value,
            )
        )

    return ExtractionOutcome(
        facts=facts, evidence=evidence, rejected=rejected, raw_claims_count=len(raw_claims)
    )
