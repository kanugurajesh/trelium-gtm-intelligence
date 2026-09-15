# Evidence Model

The anti-fabrication layer. This is the part of the project that is actually hard, and the
part most worth showing a GTM leader, because it is the difference between a research tool and
a plausible-sounding lie generator.

**Design goal:** make fabrication *structurally impossible to render*, not merely discouraged
by a prompt. Every guarantee below is enforced by code and covered by a test.

---

## 1. The three claim types

Mandated by the brief, and by the research report's own worked example [notes section 9].

### `Fact`

A statement supported by at least one evidence item, where a verbatim quote from the stored
source snapshot supports it.

```python
Fact:
  id: str                  # fct_<8 hex>
  statement: str           # natural language, past or present tense, no hedging
  evidence_ids: list[str]  # >= 1, each must resolve
  field: str | None        # optional structured target, e.g. "segment", "revenue_usd"
  value: Any | None        # optional structured value
```

**Invariant F1:** `len(evidence_ids) >= 1`.
**Invariant F2:** every id resolves to an `Evidence` record in the corpus.
**Invariant F3:** every referenced `Evidence.quote` is a literal substring of the stored
snapshot for that evidence item. Verified by SHA-256-pinned re-read, not by trust.

A Fact violating any invariant is dropped from the brief and logged to `research_gaps`.
It is never silently downgraded to an inference.

### `Inference`

A hypothesis derived from facts plus the ICP model. Never a statement about what the company
does; always a statement about what is *worth investigating*.

```python
Inference:
  id: str                    # inf_<8 hex>
  statement: str             # MUST pass the hedging linter, see section 5
  from_fact_ids: list[str]   # >= 1
  rule: str                  # which ICP rule produced it, e.g. "ICP.WF.PO_ORDER_ENTRY"
  confidence: Literal["low", "medium", "high"]
  validation_question_ids: list[str]  # >= 1
```

**Invariant I1:** `len(from_fact_ids) >= 1`. An inference with no factual parent is dropped.
An inference cannot depend on another inference; the chain is one hop deep. That is a
deliberate restriction - two-hop reasoning over weak public data is where these systems start
inventing things.
**Invariant I2:** `len(validation_question_ids) >= 1`. An untestable hypothesis is not
allowed into a brief.
**Invariant I3:** `confidence` is assigned by rule from the evidence tier and count of its
parent facts, not by the model. See section 4.

### `ValidationQuestion`

```python
ValidationQuestion:
  id: str                 # vq_<8 hex>
  question: str           # answerable in one discovery call, not researchable online
  tests_inference_id: str
  kills_if: str           # what answer would falsify the hypothesis
```

`kills_if` is the field that makes this real. A question you cannot fail is not a validation
question. Example:

```
question: "How does an emailed PO get into your order system today?"
kills_if: "Customers submit through a portal that writes directly to the order system."
```

---

## 2. The Evidence record

```python
Evidence:
  id: str                 # ev_<10 hex of sha1(url + quote)>
  source_url: str
  source_tier: int        # 1..6, see section 3
  publisher: str          # "Company website", "PPAI", "Indeed", ...
  title: str
  retrieved_at: str       # ISO 8601, UTC
  published_at: str|None  # ISO 8601 if determinable, else None
  snapshot_path: str      # evidence/raw/<id>.txt, committed to the repo
  content_sha256: str     # of the snapshot file
  quote: str              # verbatim span, <= 400 chars
  quote_offset: int       # character offset into the snapshot
```

The snapshot is committed. That means a reviewer can open the repo six months from now, when
the page has changed, and still check every claim. It also means the pipeline is fully
reproducible offline, which matters for the demo.

**Invariant E1:** `sha256(snapshot_file) == content_sha256`.
**Invariant E2:** `snapshot[quote_offset : quote_offset + len(quote)] == quote`.

E2 is the load-bearing check. An LLM that paraphrases a source, invents a quote, or attributes
a real quote to the wrong page fails it deterministically. There is no prompt-level mitigation
that is as reliable as a substring comparison.

---

## 3. Source tiers

The hierarchy is the research report's [notes section 9], with tier 6 added for the case the
report does not name: a model asserting something with no retrievable source at all.

| Tier | Source | Examples | Max claim strength |
|---|---|---|---|
| 1 | Company primary | Their website, careers page, product pages, press releases, SEC filings | Fact |
| 2 | Industry association / reputable database | PPAI 100, ASI, trade registries | Fact, with attribution to the reporter |
| 3 | Job postings | The company's own listings on its site, Indeed, LinkedIn | Fact about the posting; **inference** about the workload |
| 4 | Executive public content | LinkedIn posts, conference talks, podcasts by named employees | Fact about the statement; inference about practice |
| 5 | Third-party reporting | Trade press, local business journals | Fact, attributed |
| 6 | Unsourced model output | - | **Nothing. Discarded.** |

Tier 3 deserves emphasis because it is where this class of tool usually lies. A job posting for
an order-entry clerk is a **Tier 1/3 fact that the posting exists**. It is an **inference**
that order entry is manual. The renderer enforces the distinction; see section 5.

---

## 4. Confidence assignment - deterministic

The LLM may emit a confidence value. **It is recorded and ignored for scoring.** The value used
in the brief is computed:

| Parent evidence profile | Confidence |
|---|---|
| >= 2 independent tier-1/2 sources, both < 24 months old | `high` |
| 1 tier-1/2 source, or >= 2 tier-3/4/5 sources | `medium` |
| Only tier-3/4/5 sources, or any source > 36 months old | `low` |

"Independent" means different registrable domains. Two pages of the same company website are
one source. This is checked in code.

The model's own confidence is kept in the JSON as `model_confidence` purely so the validation
pass can measure how badly calibrated it was. That is a finding for the memo, not an input to
the score.

---

## 5. The hedging linter

A deterministic check on every `Inference.statement` before render.

**Rejects** statements containing assertive operational verbs about the company:

```
"manually enters", "currently uses", "has no", "still relies on", "their team spends",
"they process ... by hand", "lacks", "does not have"
```

**Requires** at least one hypothesis marker:

```
"may", "likely", "appears", "worth investigating", "suggests", "could", "plausibly",
"is a candidate for"
```

A statement failing either check is rejected and the inference is regenerated once with the
failure fed back. If it fails twice it is dropped and logged as a research gap.

This is a crude check and it will have false positives. That is the correct trade: a rejected
true hypothesis costs a line in a brief, an accepted false assertion costs the credibility of
the whole artifact.

### Renderer separation

The brief renderer takes three separate lists and cannot mix them. There is no code path that
places an `Inference` in the `VERIFIED FACTS` section, because that section is built by
iterating `brief.facts`, whose element type is `Fact`. Type-level separation, not stylistic
discipline. A test asserts that a hand-constructed brief with an inference smuggled into the
facts list fails schema validation.

---

## 6. Research gaps

The report singles this field out: "Most AI lead-research demos try to hide uncertainty. You
should surface it" [notes section 11].

Gaps are generated by rule, not written by the model:

| Condition | Gap emitted |
|---|---|
| No evidence for `segment` at tier 1-2 | "Segment unconfirmed from primary sources" |
| No revenue or scale figure | "No sourced scale figure; scale scored 0" |
| Zero stack signals | "No order or ERP system identified in public sources" |
| Zero trigger signals | "No growth, hiring or migration trigger found in the last 24 months" |
| Any component scored on tier 3-5 only | "Component X rests on secondary sources" |
| Always | "Not de-duplicated against Trelium CRM" |

A brief with many gaps is not a failure of the tool. It is the tool working. One of the
intended findings is that a meaningful share of accounts cannot be qualified from public data
at all, and knowing that before spending discovery time is itself the product.

---

## 7. Provenance through the pipeline

```
fetch -> snapshot (sha256, committed)
      -> extract (LLM, must return quote + offset per claim)
      -> verify  (E1, E2 - substring and hash checks; failures dropped)
      -> facts   (typed, evidence-linked)
      -> ICP rules (deterministic) -> signals
      -> infer   (LLM, constrained to fact ids + fixed taxonomy) -> hedging linter
      -> score   (pure function of signals)
      -> render  (type-separated sections)
```

Two properties fall out of this shape and both are demonstrable in the demo:

1. **Re-running scoring on a stored brief reproduces the identical number**, because scoring
   reads only the signals struct. `trelium score --from examples/stran.json` is a one-command
   proof.
2. **Deleting the evidence corpus makes facts disappear rather than making the tool confident.**
   Also worth showing.

---

## 8. What can still go wrong

Stated plainly, because the memo should say it too.

- **A verbatim quote can still be misread.** The substring check proves the text exists on the
  page; it does not prove the extraction understood it. Only the manual validation pass catches
  this, which is why phase 5 exists.
- **Source pages lie.** Marketing copy overstates. PPAI figures are partly estimates
  [notes section 10]. Tier 1 means "primary", not "true".
- **Absence of evidence reads as absence of the thing.** A company with a terse website scores
  low on stack signals while possibly running eleven systems. The gap list mitigates this; it
  does not fix it.
- **The whole ICP model is an inference.** No part of this has been checked against Trelium's
  actual win data, because no outsider can. See `SCORING.md` section 8.
