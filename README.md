# Trelium GTM Intelligence

An internal-style GTM research utility: it turns a promotional-products company into an
evidence-backed account brief, naming the workflow most worth probing on a discovery call, with
every fact traceable to a committed source snapshot and every fit score computed
deterministically.

This is **not** a Trelium product and is not affiliated with, endorsed by, or built for Trelium.
It is an unaffiliated research/application project that studies Trelium's public positioning
(see `research/` and `docs/TRELIUM_RESEARCH_NOTES.md`) and builds the kind of tool a GTM team in
that position might use.

## Problem

Trelium's GTM team needs a way to decide which accounts have an operational workflow worth
automating, before spending discovery-call time finding out by hand. Most "AI lead research"
tools fail this job for one reason: they produce confident paragraphs about a company and give
the reader no way to tell which sentences are true. A brief you have to re-verify before acting
on it isn't a time-saving tool.

## What I built

A pipeline that, given a company and a domain, fetches its own public pages, extracts
claims that are verified against those pages word-for-word, derives deterministic signals from
those claims, computes a 0-100 fit score with a fully decomposable rubric, and generates ranked
workflow hypotheses — each hedged, each with a validation question that would falsify it — from
a fixed nine-item taxonomy mapped onto Trelium's own published agents.

Run for real against 30 candidate accounts drawn from the research report's independently
researched prospect list (`docs/TRELIUM_RESEARCH_NOTES.md` section 10), plus a 5-company negative
control and a full validation pass. See `docs/FINDINGS.md` for what came out of that.

## How it works

```
prospects.csv --> collect (fetch + robots.txt + snapshot)
              --> extract (LLM, verbatim quote only, never an offset)
              --> verify  (code: hash match + substring-at-offset match)
              --> signals (code: segment/scale/stack/triggers from verified facts)
              --> score   (code: pure function, integers only)
              --> hypothesise (LLM, closed workflow taxonomy, hedging-linted)
              --> render  (Markdown / JSON brief)
```

Two things make this trustworthy rather than merely plausible-sounding:

1. **Every fact is a verbatim substring of a committed snapshot.** The extraction model is
   asked for an exact quote, never an offset (models are reliably worse at exact character
   offsets than at exact quotes). The offset is found in code by searching the snapshot for a
   unique occurrence of that quote. A quote that doesn't appear, or appears more than once, is
   rejected before it can become a fact — not flagged, rejected.
2. **The score is a pure function of evidence-linked signals, and the model never sees the
   rubric.** `score(signals) -> ScoreResult` takes no network, no clock, no randomness. A signal
   with no evidence behind it scores zero, enforced at the type level, not by convention.

Full architecture in `docs/PROJECT_SPEC.md`; the exact scoring rubric and why the report's
example rules were replaced (not just implemented) in `docs/SCORING.md`.

## Why I built it this way

Trelium's own materials explicitly separate reasoning from deterministic execution: use AI where
judgment is required, deterministic steps where it is not (`docs/TRELIUM_RESEARCH_NOTES.md`
section 1). This project mirrors that split on purpose. The model interprets messy public pages;
code verifies every claim, computes every score, and enforces the taxonomy. Neither side is
trusted to do the other's job.

## What I learned

Three findings, in full in `docs/FINDINGS.md`:

- **Public-page collection alone fails on roughly two-thirds of this vertical**, mostly to bot
  protection (robots.txt and WAF/403s), not thin content. A GTM research tool for this segment
  needs a second data source, not a better prompt.
- **Homepage-level evidence can name a segment but rarely a workflow.** Across every account
  that did score, public content surfaced generic "supplier purchasing" and "order status"
  hypotheses; it never once surfaced Trelium's own flagship pattern (inbound PO to order entry)
  from a homepage alone. Specificity requires deeper pages than a homepage-only pass reaches.
- **A prompt asked nicely is not a verification layer.** Three separate live extraction runs
  produced a number that was technically present on the page but described the wrong thing
  (inventory value read as revenue, twice in different forms; years-in-business read as
  headcount). Tightening the prompt did not fix the first instance; a deterministic keyword
  check in code did, and caught the next two instances for free.

## What I would do next

Test the single clearest falsifiable prediction from this run: see `docs/FINDINGS.md`'s closing
section for the prediction, the sample size needed, and the first-week experiment that would
test it.

## Repository layout

```
src/trelium_gtm/     Pipeline: models, taxonomy, scoring, evidence verification, collection,
                     extraction, hypothesis generation, rendering, CLI
tests/               165+ tests covering every deterministic component: scoring boundaries,
                     evidence invariants, the hedging linter, ranking, validation harness
data/prospects.csv   30 candidate accounts, domains verified by search (not guessed), with
                     disambiguation and exclusion notes
evidence/            Committed source snapshots (hash-pinned) for every collected page
cache/llm/           Committed, content-addressed LLM responses — the whole pipeline replays
                     offline with no OPENAI_API_KEY
output/briefs/       Generated account briefs, JSON + Markdown, for all 30 accounts
output/negative_controls/  5 out-of-ICP companies run through the same pipeline (V4)
docs/                Planning docs, research notes, scoring/evidence model, findings, validation
```

## Running it

```bash
pip install -e .
pytest                                    # 165+ tests, no network, no API key needed
trelium brief --company "..." --domain example.com
trelium run-all --input data/prospects.csv
trelium rank --output docs/RANKING.md
trelium score --from output/briefs/example_com.json   # proves the score is reproducible
```

Collection and extraction need `OPENAI_API_KEY` set (see `.env.example`) unless the exact
prompt has already been cached under `cache/llm/`.

## What this deliberately does not do

No CRM, no authentication, no database, no chat interface, no web server, no scheduler, and no
capability to contact anyone. See `docs/PROJECT_SPEC.md` section 8 and `CLAUDE.md` for the full,
closed list and why.

## Permanent project rules

`CLAUDE.md` records the rules this codebase follows and why breaking any of them would
undermine the project's central claim. Read alongside `docs/EVIDENCE_MODEL.md` and
`docs/SCORING.md`.
