# Trelium GTM Intelligence

An internal-style GTM research utility: it turns a promotional-products company into an
evidence-backed account brief, naming the workflow most worth probing on a discovery call, with
every fact traceable to a committed source snapshot and every fit score computed
deterministically.

This is **not** a Trelium product and is not affiliated with, endorsed by, or built for Trelium.
It is an unaffiliated research/application project that studies Trelium's public positioning
(see `research/` and `docs/TRELIUM_RESEARCH_NOTES.md`) and builds the kind of tool a GTM team in
that position might use.

## The result, first

I ran it against 30 candidate accounts, twice: once reading each company's homepage, once reading
up to six pages per site. The honest answer to "can public web pages qualify this vertical on
workflow evidence?" is no.

| | |
|---|---|
| Accounts that blocked or defeated automated collection | 19 of 30, both passes |
| Accounts that scored | 11 of 30 |
| Accounts above the deprioritise band | 0 |
| Accounts where an operational-complexity or buying-trigger signal ever scored | 0 |
| Facts in the top five briefs that survived a by-hand audit against the page | 22 of 26 |
| Extraction defects found by that auditing, each fixed in code with a test | 6 |

Full memo: `docs/FINDINGS.md`. What one brief looks like, abridged from
`output/briefs/stran_com.md` (the full brief also carries the CRM de-duplication banner, a
second verified fact and the target persona):

> **Fit score: 32 / 100 — DEPRIORITIZE** · Evidence grade C
> Core vertical fit 25 · Operational complexity 0 · Software/ecosystem 3 · Scale 0 · Trigger 0 · Evidence quality 4
>
> **1. WF_SUPPLIER_PURCHASING — Supplier Purchasing Agent** (confidence: medium)
> *Hypothesis:* Supplier purchasing processes may be worth investigating at Stran, given its role
> as a promotional product supplier and the diverse range of products it oversees.
> *Validate before outreach:* How does Stran manage its supplier relationships and purchasing
> processes for promotional products? — kills the hypothesis if Stran has a fully automated
> supplier purchasing system in place.
>
> **Verified facts** — [2] Stran uses a Magento-based technology platform. Source: stran.com
> (retrieved 2026-09-15, tier 1) — "we harness the power of a Magento-based technology platform
> to oversee a diverse range of promotional products, gifts, and branded merchandise."
>
> **Research gaps** — No sourced scale figure; No growth, hiring or migration trigger found in
> public sources; Not de-duplicated against Trelium CRM; 1/7 extracted claims failed
> verbatim-quote verification and were discarded.

The hypothesis is generic and the brief says so. That is the point: it will not say more than
the evidence supports, and it tells you what it could not find.

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

## How it works

```
prospects.csv --> collect (fetch up to 6 pages/site + robots.txt + content-addressed snapshot)
              --> extract (LLM, verbatim quote only, never an offset)
              --> verify  (code: hash match + substring-at-offset match + context guards)
              --> signals (code: segment/scale/stack/triggers from verified facts)
              --> score   (code: pure function, integers only)
              --> hypothesise (LLM, closed workflow taxonomy, hedging-linted)
              --> render  (Markdown / JSON brief)
```

Three things make this trustworthy rather than merely plausible-sounding:

1. **Every fact is a verbatim substring of a committed snapshot.** The extraction model is
   asked for an exact quote, never an offset (models are reliably worse at exact character
   offsets than at exact quotes). The offset is found in code by searching the snapshot for a
   unique occurrence of that quote. A quote that doesn't appear, or appears more than once, is
   rejected before it can become a fact — not flagged, rejected.
2. **The score is a pure function of evidence-linked signals, and the model never sees the
   rubric.** `score(signals) -> ScoreResult` takes no network, no clock, no randomness. A signal
   with no evidence behind it scores zero, enforced at the type level, not by convention.
3. **Repetition strengthens evidence; it never creates a second signal, and disagreement is
   never quietly resolved.** Facts asserting the same normalised identity (one system name, one
   trigger type, one segment label) merge into a single signal that keeps every source, so a
   system named on two pages cannot score twice. Conflicting claims stay on the record: the
   winner is chosen by evidence tier, then breadth of support, then a fixed tie-break, never by
   input order and never by asking the model. An unresolved conflict lowers the score and
   always appears as a research gap naming both candidates. Shuffling the facts changes no
   signal and no score; a test enforces that (`docs/EVIDENCE_MODEL.md` sections 9-10,
   `docs/SCORING.md` sections 13-14, `docs/RESCORE_COMPARISON.md` for what this did to the
   committed dataset).

A fourth thing turned out to matter as much: **a verbatim quote can still be misread.** Six
times, the model quoted a real sentence and mislabelled what it meant (inventory as revenue,
years as headcount, a 2015 headline as a live trigger, customers' procurement systems as the
company's own, a page heading as a segment). Each is now a deterministic check on the quote's
own words, with a test. None was fixed by rewording the prompt, and the first one was tried.

Full architecture in `docs/PROJECT_SPEC.md`; the exact scoring rubric and why the report's
example rules were replaced (not just implemented) in `docs/SCORING.md`.

## Why I built it this way

Trelium's own materials explicitly separate reasoning from deterministic execution: use AI where
judgment is required, deterministic steps where it is not (`docs/TRELIUM_RESEARCH_NOTES.md`
section 1). This project mirrors that split on purpose. The model interprets messy public pages;
code verifies every claim, computes every score, and enforces the taxonomy. Neither side is
trusted to do the other's job.

## What I learned

Five findings, in full in `docs/FINDINGS.md` and `docs/VALIDATION.md`:

- **Two-thirds of this vertical cannot be researched from its own site.** 19 of 30 accounts
  produced nothing, mostly robots.txt and bot protection, and no amount of deeper crawling
  reaches a site that blocks the homepage. A GTM research tool for this segment needs a second
  data source, not a better prompt.
- **Deeper pages were the memo's own proposed next step, and they were not enough.** Reading
  careers, technology, press and services pages nearly tripled the pages read and added half
  again as many facts, and the two rubric components that describe Trelium's actual pain pattern
  (operational complexity, buying triggers) still scored zero on every account. The evidence
  is not on the company's domain at any depth (`docs/DEEP_COLLECTION.md`).
- **A prompt asked nicely is not a verification layer.** Six separate cases of a real quote
  described wrongly; each fixed with a deterministic keyword check in code. The sixth, segment
  labels on quotes that never stated the role, was carrying 25 of the top score's 39 points.
  Fixing it moved four accounts out of the top ten.
- **The reproducibility claim had to be checked, not assumed.** Verifying every cited quote
  against the bytes git actually stores, rather than the files on disk, found that 11 of 42
  committed snapshots had been silently rewritten by line-ending normalisation, four of them
  from the first run. A clean clone would have failed a quarter of the corpus. Fixed, and now
  enforced by a script (`docs/VALIDATION.md` V5).
- **Claim precision is measurable and should be published.** 22 of 26 facts in the top five
  briefs are fully accurate on a by-hand audit; the four that are not are all semantic
  over-readings the substring check cannot catch, and they are listed row by row in
  `docs/VALIDATION.md`.

A manual pilot of that second data source is in `docs/ACCOUNT_NOTES.md`: five accounts, three
scored and two blocked, researched from SEC filings, trade press and job boards, every quote
re-verified against its page by a script. The site pass found operational-complexity evidence on
0 of 30 accounts; the hand pass found it on 1 of 5, a dated 2026 trigger on 4 of 5, and made both
blocked accounts researchable. It also found that the top-scored account's scale points rest on
a subsidiary's headcount, which is recorded there as a defect for the next hardening pass.

## What I would do next

Add a second data source (job postings, industry-association listings) rather than crawl
deeper, with a stated prediction for what it should do to the trigger component. The hand pilot
shows the useful postings sit behind robots.txt rules the tool honours, so this means a licensed
feed, not a crawler. Then run a
frontier deep-research product on the same five audited accounts, hold its claims to the same
verbatim-quote standard, and publish the two precision numbers side by side. If deep research
wins on verified precision and reach, that is the recommendation. See the closing section of
`docs/FINDINGS.md`.

## Repository layout

```
src/trelium_gtm/     Pipeline: models, taxonomy, scoring, ranking, evidence store + verifier,
                     collection, extraction, signal derivation, hypothesis generation, hedging
                     linter, deterministic persona lookup, workflow coverage analysis,
                     validation experiments, rendering, CLI
tests/               226 tests covering every deterministic component: scoring boundaries,
                     evidence invariants, link discovery, snapshot preservation across passes,
                     the six extraction guards, signal dedup and contradiction policy incl.
                     order independence, the hedging linter, ranking, validation harness
data/prospects.csv   30 candidate accounts, domains verified by search (not guessed), with
                     disambiguation and exclusion notes
evidence/            Committed source snapshots, content-addressed, for every collected page
cache/llm/           Committed, content-addressed LLM responses — the whole pipeline replays
                     offline with no OPENAI_API_KEY
output/briefs/       Generated account briefs, JSON + Markdown, for all 30 accounts (deeper-page pass)
output/briefs_pass1_homepage/  The homepage-only pass, archived for comparison
output/negative_controls/  5 out-of-ICP companies run through the same pipeline (V4)
scripts/             One-off analysis drivers: validation, negative controls, pass comparison,
                     offline re-score of committed briefs, corpus verification against git blobs,
                     re-check of the hand-research quotes against their live pages
docs/                Planning docs, research notes, scoring/evidence model, findings, validation
```

Where to read, in order, if you have ten minutes:

| Document | What it answers |
|---|---|
| `docs/APPLICATION_MEMO.md` | One page: what I understood about Trelium, what the tool found, five accounts by hand |
| `docs/FINDINGS.md` | What running it on 30 accounts produced, and what that means for the tool |
| `docs/ACCOUNT_NOTES.md` | Five accounts researched by hand from filings, trade press and job boards, every quote sourced and script-verified |
| `docs/VALIDATION.md` | Rank correlation, component ablation, the by-hand claim audit, negative control, corpus integrity (V1-V5) |
| `docs/DEEP_COLLECTION.md` | Homepage-only pass versus the six-page pass, account by account |
| `docs/RANKING.md`, `docs/COVERAGE.md` | The current ranking; which of the nine workflows public evidence can and cannot reach |
| `docs/SCORING.md`, `docs/EVIDENCE_MODEL.md` | The rubric and the evidence rules the code enforces, with the invariants each test checks |
| `docs/ICP.md`, `docs/PROJECT_SPEC.md` | Who the tool is for, the closed workflow taxonomy, and what was deliberately not built |
| `docs/RESCORE_COMPARISON.md` | How the dedup and contradiction fixes changed the committed scores, account by account |
| `docs/IMPLEMENTATION_STATUS.md`, `docs/IMPLEMENTATION_PLAN.md` | What exists now, with known problems, and the order things would have been cut |
| `docs/TRELIUM_RESEARCH_NOTES.md` | Notes on Trelium's public positioning that the ICP and taxonomy are built from |
| `docs/DEMO_SCRIPT.md` | The 60-90 second walkthrough |

## Running it

Python 3.11 or later (developed and run on 3.13). Runtime dependencies are pydantic, httpx and
the OpenAI client; pytest is the only dev dependency.

```bash
pip install -e ".[dev]"
pytest                                    # 226 tests, no network, no API key needed
trelium brief --company "Stran Promotional Solutions" --domain stran.com
trelium run-all --input data/prospects.csv
trelium rank --output docs/RANKING.md
trelium score --from output/briefs/stran_com.json   # proves the score is reproducible
python scripts/compare_passes.py                    # regenerates docs/DEEP_COLLECTION.md
python scripts/verify_corpus.py --committed         # every cited quote, against the committed bytes
python scripts/rescore_existing.py                  # re-scores the committed briefs offline (no fetch, no model
                                                    # call) and rewrites them plus docs/RESCORE_COMPARISON.md in place
python scripts/run_validation.py                    # recomputes V1/V2/V4 and docs/COVERAGE.md; overwrites docs/VALIDATION.md,
                                                    # so the hand-written V3 audit and V5 sections must be restored from git
python scripts/run_negative_controls.py             # V4: 5 out-of-ICP companies through the full pipeline
python scripts/verify_hand_quotes.py                # re-checks every docs/ACCOUNT_NOTES.md quote against its live page (network)
```

Collection and extraction need `OPENAI_API_KEY` set (see `.env.example`) unless the exact
prompt has already been cached under `cache/llm/`. The company name is part of the hypothesis
prompt, so `brief` pins it to the name in `data/prospects.csv` when the domain matches; pass
the dataset's spelling to reproduce a committed brief exactly. Requests are spaced one second
apart and never exceed six per site.

## What this deliberately does not do

No CRM, no authentication, no database, no chat interface, no web server, no scheduler, and no
capability to contact anyone. See `docs/PROJECT_SPEC.md` section 8 and `CLAUDE.md` for the full,
closed list and why.

## Permanent project rules

`CLAUDE.md` records the rules this codebase follows and why breaking any of them would
undermine the project's central claim. Read alongside `docs/EVIDENCE_MODEL.md` and
`docs/SCORING.md`.
