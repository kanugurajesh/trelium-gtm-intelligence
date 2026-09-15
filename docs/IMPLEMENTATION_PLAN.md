# Implementation Plan

Eight phases. Each has an exit test - a thing that is true or false, not a feeling of progress.
Phases 0-3 are pure code and can be built and tested with no network and no API key.

Total estimate: 15-18 working hours. The report frames this as one focused day
[notes section 11]; realistically it is a long day or a day and a half, and the cut list below
exists so that overrun is handled by dropping scope in a pre-decided order rather than by
skipping validation.

---

## Phase 0 - Skeleton and schemas (1.5h)

Types first, because the fact/inference separation is enforced at the type boundary and
everything downstream depends on it.

- `pyproject.toml`, package layout, pytest config, `.gitignore`.
- `models.py`: `Evidence`, `Fact`, `Inference`, `ValidationQuestion`, `Signal`, `SignalSet`,
  `WorkflowHypothesis`, `ScoreResult`, `AccountBrief` as pydantic v2 models.
- Invariants as pydantic validators: F1, I1, I2, E1, E2 from `EVIDENCE_MODEL.md`.
- `taxonomy.py`: the nine workflow IDs, six segment tiers, system class tables, trigger enum.
  All frozen data, no logic.

**Exit test:** constructing a `Fact` with an empty `evidence_ids` raises. Constructing an
`AccountBrief` with an `Inference` in the `facts` list raises. Both are tests, not assertions
in a docstring.

---

## Phase 1 - Deterministic scoring (2h)

Built before any model call exists, so the scorer cannot accidentally depend on one.

- `scoring.py`: `score(signals: SignalSet) -> ScoreResult`, pure, integers only.
- Components C1-C6 exactly as specified in `SCORING.md` sections 3-8.
- Gates G1-G4, hard rules H1-H3.
- Evidence grade A-D, banding, `contributing_signals` audit trail.
- `ranking.py`: the five-step deterministic tie-break.

**Exit test:** `tests/test_scoring.py` covers every component boundary, both sides of every
threshold, all four gates, every cap, the recency discount, the non-monotonic scale curve, and
H1 (a signal with empty evidence contributes zero) and H2 (mutating every `model_confidence` in
a fixture changes nothing). Roughly 40 cases. This is the test file that justifies the claim
that the score is deterministic, so it gets written properly rather than for coverage.

---

## Phase 2 - Evidence store and verifier (1.5h)

- `evidence/store.py`: write snapshot, compute sha256, append to `evidence/index.jsonl`, load.
- `evidence/verify.py`: E1 hash check, E2 substring-at-offset check, tier assignment from a URL
  and publisher map, independence check by registrable domain.
- Rejected claims routed to a structured reject log, never silently dropped.

**Exit test:** a fixture with a tampered snapshot fails E1. A fixture whose quote is a
paraphrase rather than a substring fails E2. A fixture citing two pages of one domain reports
one independent source, not two.

---

## Phase 3 - Signal derivation (1.5h)

- `signals.py`: rules mapping verified facts onto the `SignalSet` - segment tier, stack classes
  and cross-boundary bonus, scale band with headcount fallback, trigger enum with recency,
  eight operational sub-signals.
- Every signal carries its source `fact_ids` through to `contributing_signals`.

**Exit test:** a hand-written fact fixture for a synthetic company produces exactly the expected
`SignalSet`, and the score it yields matches a hand-computed number. One end-to-end arithmetic
check nobody can argue with.

**Checkpoint.** At this point the entire deterministic core is finished and tested with zero
model calls and zero network. If the day goes badly from here, this still demonstrates the
thesis.

---

## Phase 4 - Collection and extraction (3h)

First network, first model call.

- `collect.py`: `httpx` fetch, robots.txt check, one request at a time, descriptive user agent,
  HTML to text, snapshot write. Failures recorded as gaps, never as empty successes.
- `extract.py`: per-source structured extraction. Prompt returns candidate claims, each with a
  verbatim quote and character offset. OpenAI API, `gpt-4o-mini` by default (env `OPENAI_MODEL`
  overrides), using JSON-schema structured
  output.
- `llm_cache.py`: content-addressed cache keyed on sha256 of the full prompt. Committed to the
  repo. Cache hit needs no API key.
- Every extraction passes through phase 2's verifier before becoming a `Fact`.

**Exit test:** run the full collect-extract-verify path on three accounts. Report the fraction
of candidate claims rejected by E2. **That number is itself a finding** - it is a direct
measurement of how often the model fabricates or paraphrases a quote when told not to, and it
belongs in the memo whatever it turns out to be.

**Risk note:** budget the first hour here for prompt iteration on quote-offset fidelity. Models
are reliably worse at returning exact character offsets than at returning exact quotes. Fallback
if offsets prove unreliable: search for the quote in the snapshot and derive the offset in code,
requiring exactly one occurrence. Decide by measurement, not preference.

---

## Phase 5 - Hypothesis generation and linting (2h)

- `hypothesise.py`: given verified facts plus the `SignalSet`, the model selects workflows from
  the nine-item taxonomy, gives reasons referencing `fact_ids`, and writes validation questions
  with `kills_if` clauses. It cannot return a workflow outside the taxonomy - that is a schema
  constraint, not an instruction.
- `lint.py`: the hedging linter from `EVIDENCE_MODEL.md` section 5. One regeneration attempt on
  failure, then drop and log a gap.
- Deterministic boundary count per hypothesis from the observed stack.
- Persona lookup from the segment-and-scale table in `ICP.md` section 7.

**Exit test:** a hypothesis phrased "Stran manually enters purchase orders" is rejected by the
linter. Every hypothesis in every generated brief carries at least one validation question with
a non-empty `kills_if`.

---

## Phase 6 - Rendering and the full run (2h)

- `render/json.py`, `render/markdown.py`, `render/html.py`. Three sections, three types, no
  code path that can mix them.
- Brief layout follows the report's sketch [notes section 11]: score and components, top
  workflow opportunity with confidence and reasons, numbered evidence with URLs and dates,
  "validate before outreach" questions, persona and rationale, research gaps, and the
  non-removable CRM de-duplication banner.
- Static HTML: one self-contained file per brief plus an index, generated from the JSON. No
  server, no framework, opens from the filesystem.
- `run-all` over the 30-account CSV; `rank` writes `docs/RANKING.md`.

**Exit test:** 30 briefs generated. Every fact in every brief resolves. Re-running `run-all`
from cache produces byte-identical output.

---

## Phase 7 - Validation and coverage (3h) - the phase not to cut

The four experiments in `SCORING.md` section 11, plus the coverage analysis in section 12.

- **V1** rank correlation against the report's independent priority ordering of the 30 accounts.
- **V2** component ablation: six re-rankings, each zeroing one component, reporting top-10
  movement.
- **V3** manual claim audit of the top five briefs. Every fact opened and checked against its
  source by hand. Claim precision reported as a fraction, with every correction listed.
- **V4** negative control: five deliberately out-of-ICP companies through the full pipeline.
  All five should exit at gate G1. Twenty minutes.
- **Coverage analysis** to `docs/COVERAGE.md`: the nine taxonomy workflows against the 30
  accounts, by frequency, confidence, scale band and segment. Roughly 30 minutes, since the
  data exists by phase 6.

Then a re-read of the five briefs asking one question per brief: *would a founder walk into a
call with this?*

**Exit test:** `docs/VALIDATION.md` contains four results and an explicit list of what the
system got wrong. `docs/COVERAGE.md` names at least one workflow that public evidence cannot
target.

---

## Phase 8 - Communication (2h)

- `README.md` in the report's six sections [notes section 11]: Problem, What I built, How it
  works, Why I built it this way, What I learned, What I would do next.
- `docs/FINDINGS.md`, one page: Question, Method, three findings, next experiment. Findings are
  written after phase 7 from what was actually measured. If the measurements contradict the
  report's expected findings [notes section 11], the measurements win and the memo says so.
  **At least one finding must be about the market, not the method** - a statement about the
  30-account population that changes how someone would target it. See `PROJECT_SPEC.md`
  section 10, objection 1.
- The memo closes with **one falsifiable prediction and the experiment that tests it**, sized
  for a first week, with the sample size needed to detect the effect. Not a sentiment about
  next steps.
- Demo script, 60-90 seconds, structured as the report suggests [notes section 11], with one
  change: spend the technical beat on **showing a rejected claim** rather than on showing the
  scoring code. Watching the tool refuse to state something is more persuasive than watching it
  compute.

**Exit test:** someone unfamiliar with the project reads one brief and correctly states which
parts are established and which are guesses.

---

## Sequencing rationale

Deterministic core first, model second. Three reasons:

1. If the API key, rate limits or prompt iteration eat the day, phases 0-3 still stand alone as
   a complete, tested demonstration of the reasoning-versus-execution separation.
2. Writing the scorer before any model exists makes it structurally impossible for scoring to
   depend on model output.
3. The extraction prompt is easier to write once the exact target types exist.

The report's own ordering also puts the schema and score rules before the pipeline
[notes section 11]. Same instinct.

---

## Cut list, in order

If time runs short, cut in this order. Recorded now so the decision is not made under pressure.

1. Static HTML renderer - Markdown briefs are sufficient for the demo.
2. Accounts 21-30 - report honestly on 20.
3. V2 ablation - the cheapest experiment to defer.
4. `--format html` index page.
5. V1 rank correlation - it is the weakest of the four experiments, being a second opinion
   rather than ground truth.

**Never cut:** phase 1 tests, the E2 substring check, the hedging linter, the V3 manual audit,
the V4 negative control, the coverage analysis, and the research gaps section. Those are the
project.

---

## Proposed repository structure

```
trelium-gtm-intelligence/
├── README.md
├── CLAUDE.md
├── pyproject.toml
├── research/
│   └── Trelium Deep Research and Application Strategy.pdf
├── docs/
│   ├── PROJECT_SPEC.md
│   ├── TRELIUM_RESEARCH_NOTES.md
│   ├── ICP.md
│   ├── EVIDENCE_MODEL.md
│   ├── SCORING.md
│   ├── IMPLEMENTATION_PLAN.md
│   ├── FINDINGS.md          # phase 8
│   ├── VALIDATION.md        # phase 7
│   ├── COVERAGE.md          # phase 7
│   └── RANKING.md           # generated
├── src/trelium_gtm/
│   ├── __init__.py
│   ├── cli.py
│   ├── models.py            # pydantic schemas + invariants
│   ├── taxonomy.py          # workflows, segments, system classes, triggers
│   ├── collect.py           # fetch + snapshot
│   ├── extract.py           # LLM claim extraction
│   ├── llm_cache.py         # content-addressed, committed
│   ├── signals.py           # facts -> SignalSet
│   ├── scoring.py           # pure deterministic scorer
│   ├── ranking.py           # deterministic tie-break
│   ├── hypothesise.py       # LLM, taxonomy-constrained
│   ├── lint.py              # hedging linter
│   ├── evidence/
│   │   ├── store.py
│   │   └── verify.py
│   └── render/
│       ├── json_out.py
│       ├── markdown.py
│       └── html.py
├── tests/
│   ├── test_scoring.py      # the big one
│   ├── test_ranking.py
│   ├── test_evidence_verify.py
│   ├── test_signals.py
│   ├── test_models_invariants.py
│   ├── test_lint.py
│   └── fixtures/
├── data/
│   └── prospects.csv        # 30 accounts + exclusion reasons
├── evidence/
│   ├── index.jsonl
│   └── raw/                 # committed snapshots
├── cache/llm/               # committed, enables offline runs
└── output/briefs/           # 30 JSON + 5 MD + HTML
```

Close to the report's sketch [notes section 11], with three additions it did not have:
`evidence/` and `cache/` because reproducibility is the credibility argument, and `tests/`
because deterministic business logic that is not tested is just a claim.

---

## Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Extraction fabricates or paraphrases quotes | High | Would destroy the project's whole claim | E2 substring check rejects them deterministically. The rejection rate is measured and published as a finding |
| R2 | Public sources too thin to differentiate 30 accounts; scores cluster | Medium-high | Ranking becomes uninformative | The ablation in V2 detects it. If real, it *is* the headline finding - and a more useful one than a clean ranking |
| R3 | Character offsets from the model are unreliable | High | Blocks phase 4 | Derive offsets in code by unique-occurrence search. Decided by measurement in phase 4 |
| R4 | No API key available | Medium | Blocks phases 4-6 | Phases 0-3 stand alone. Fallback in decision D2 |
| R5 | Sites block automated fetching | Medium | Gaps in the corpus | Respect it, record the gap, move on. Never route around a block |
| R6 | Manual audit of top five overruns 2.5h | Medium | Squeezes phase 8 | Audit three briefs fully rather than five partially. Report N honestly |
| R7 | Scoring model is unvalidated against real outcomes | Certain | Limits every claim made about it | Stated plainly in the memo and in `SCORING.md` section 10. Not a risk to mitigate, a limit to disclose |
| R8 | Project reads as "I built Trelium's product" | Low-medium | Backfires with the reader | Framed as an internal GTM utility throughout; README says so in its first paragraph [notes section 11] |
| R9 | Someone treats a brief as verified truth and contacts an account | Low | Real-world harm | CRM de-duplication banner on every brief, no sending capability in the codebase, prohibition in `CLAUDE.md` |
| R10 | 30 accounts of collection takes longer than budgeted | Medium | Squeezes validation | Cut list above: report on 20 accounts rather than skipping phase 7 |

---

## Decisions needed before implementation

**D1 - Python or TypeScript?** Recommend **Python 3.13 + pydantic + pytest**. Everything needed
is already installed, and runtime validation is what enforces the evidence model. The report
sketched a `.ts` schema file but also said a clean CLI is enough [notes section 11]; the
language is not what is being evaluated. Choose TypeScript only if the reviewing audience is
expected to weight stack familiarity, which seems unlikely for a GTM reader.

**D2 - LLM access.** `ANTHROPIC_API_KEY` is not set in this environment. Options: (a) provide a
key, recommended, roughly $2-5 of tokens for 30 accounts; (b) run the model calls through this
Claude Code session and commit the outputs to the cache, which works and is slower;
(c) deterministic-only mode with hand-authored facts for a few accounts, which is weaker
because the extraction rejection rate is one of the more interesting findings.

**D3 - Account universe.** Use the report's 30 as-is, or substitute some for mid-market
decorators and print shops. The report's list skews large; Trelium's pricing suggests mid-market.
Recommend keeping all 30 for comparability with the report's independent picks, and noting the
skew as a finding.

**D4 - Repository visibility.** Public GitHub is implied by the application. Confirm, and
confirm that committing evidence snapshots of third-party sites is acceptable. Recommended
posture: store extracted text with URL and retrieval date, not full HTML mirrors, with a note
in the README that snapshots exist for verification and will be removed on request.

**D5 - Git.** The working directory is not a git repository. Recommend initialising now so
phases are committed incrementally and the history itself shows how the work proceeded.

**D6 - PPAI data.** Confirm comfort with citing individual PPAI 100 figures with attribution.
The plan cites per-account figures as PPAI-reported and does not reproduce the ranking in bulk.
