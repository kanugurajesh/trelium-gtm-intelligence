# Project Spec - Trelium GTM Intelligence

**Status:** planning complete, awaiting approval. Nothing implemented.

**One line:** an internal-style GTM research utility that turns a promotional-products company
into an evidence-backed account brief naming the single workflow most worth probing on a
discovery call, with every fact traceable to a committed source snapshot and every score
computed deterministically.

---

## 1. The evaluation this project is really subject to

The artifact will be read by a founder or GTM lead in roughly four minutes. The question they
ask is the one in the brief that commissioned this work:

> "If a candidate showed me this, would it tell me something useful, or merely demonstrate that
> they can build software?"

Almost every "AI account research" demo fails that question the same way: it produces confident
paragraphs about companies, and the reader cannot tell which sentences are true. Its value to
the reader is therefore zero regardless of how well it is engineered, because verifying it
costs more than doing the research by hand.

So the project's primary claim is not "I built a research pipeline." It is:

> **Here is an account research system whose output you can trust without re-checking it,
> because it cannot emit an unsourced claim, and here is the measurement proving that.**

Everything in the architecture follows from that, and the manual validation pass (phase 5) is
not a nice-to-have. It is the deliverable.

---

## 2. Product thesis

Trelium's conversion event is a 30-minute session in which it automates one of the prospect's
actual workflows using their actual tools [notes section 6]. The scarce input to that motion is
not a list of companies. It is a defensible guess about **which workflow to put on the table.**

So the unit of output is a **company-workflow pair**, not a company. See `ICP.md` section 1.

A brief answers three questions, in this order:

1. **Which account appears worth investigating?** Deterministic 0-100 fit score, decomposable
   to the signal and evidence that produced each point.
2. **Which operational workflow might be worth discussing?** Ranked hypotheses drawn from a
   fixed taxonomy mapped onto Trelium's own published agents, so the named workflow is one
   Trelium can actually demo.
3. **What evidence supports that hypothesis?** Verbatim quotes with URLs, retrieval dates and
   committed snapshots, separated from the hypotheses by type, plus the validation questions
   that would kill each hypothesis.

---

## 3. Evaluation of the proposed project

The brief asked whether "Trelium GTM Intelligence" is the strongest one-day project, and to
propose something better if it is.

**It is the right project. Kept, with four modifications.** The reasoning, checked against the
report's own experiment ranking [notes section 9]:

| Alternative | Why not |
|---|---|
| #1 Workflow Opportunity Audit outbound | The *research* is this project. The *sending* is prohibited - contacting Trelium's prospects uninvited, as a non-employee, is the single fastest way to turn a strong application into an incident. The report bans it [notes section 12] |
| #5 Partner activation sprint | A defensible list of implementation consultants, but it demonstrates sourcing, not judgment. Little to validate, little to measure, thin technical demonstration |
| #7 Trigger-based watchlist | A subset of this system plus a scheduler. Strictly less than what is proposed |
| #9 Customer workflow expansion audit | Highest business value of all ten and impossible pre-hire; requires customer and product data [notes section 9] |
| A Trelium product clone | Actively bad. It competes with their engineering instead of helping their GTM, and the report warns against appearing to replicate Trelium [notes section 11] |

Checked against the seven capabilities the brief asks the project to demonstrate:

| Capability | How it shows |
|---|---|
| Claude Code proficiency | A typed pipeline with schema validation, deterministic scoring and a real test suite, built in a day |
| GTM thinking | Qualifying company-workflow pairs, non-monotonic scale scoring tied to Trelium's price point, persona-to-workflow-ownership reasoning |
| Market research | 30 accounts researched against a real evidence corpus, with the limits of public data measured rather than asserted |
| Operational execution | 30 accounts actually run end to end, not 3 |
| Self-direction | The ICP, the taxonomy and the rubric critique are decisions made, documented and defended, not requirements handed down |
| Reliability | Reproducible offline from committed fixtures; deterministic ranking; tests on business logic |
| Communication | A one-page memo that leads with what did not work |
| Ownership | Publishing a measured claim-precision number, including if it is mediocre |

**Modification 1 - evidence-first, not research-first.** The pipeline's spine is a committed,
hash-pinned evidence corpus; facts are produced by quoting it and are rejected when the quote
does not literally appear in the stored snapshot. This converts "please don't hallucinate" from
a prompt instruction into a substring comparison. It is the difference between a demo and a
tool, and it is testable.

**Modification 2 - the workflow taxonomy is closed and maps to Trelium's own agents.** Nine
workflows, each corresponding to a published Trelium use case [`ICP.md` section 5]. The model
selects from the list; it cannot invent a category. A brief that says "inbound PO to order
entry, which is Trelium's Order Entry Agent for Distributors" is immediately actionable. One
that says "AI-driven operational optimisation" is noise.

**Modification 3 - the rubric is rebuilt, not just implemented.** The report's example rules
are six binary switches that cannot rank 30 accounts, make scale monotonic in contradiction of
the report's own account picks, have no disqualifier, and never forbid unsourced signals from
scoring. `SCORING.md` section 1 sets out all six problems and fixes them. Showing that critique
is worth more than showing obedience to the rubric.

**Modification 4 - a measured validation pass, in the repo.** Manual verification of every fact
in the top five briefs, a component ablation showing which parts of the score actually change
decisions, and a rank correlation against the report's independent human pick of five accounts.
`SCORING.md` section 11. Without this the project is software. With it, it is an experiment.

**One thing the report recommends that is being reduced.** The report allocates hours 14-15 to a
visual interface [notes section 11]. This plan spends that time on validation instead and ships
a generated static HTML brief - no server, no framework, no state. The demo shows a real brief
either way; the tradeoff buys a measured number instead of a nicer-looking one.

---

## 4. Architecture

Smallest thing that produces a convincing experiment.

```
                       prospects.csv (30 accounts, curated)
                                    |
              +---------------------+---------------------+
              |                                           |
        [1] COLLECT                                 (re-run: skipped,
        fetch public pages, write                    corpus is committed)
        snapshot + sha256 + metadata
              |
              v
     evidence/raw/ev_*.txt   evidence/index.jsonl
              |
              v
        [2] EXTRACT                        <-- LLM, structured output only
        per source: candidate claims,
        each with verbatim quote + offset
              |
              v
        [3] VERIFY                         <-- pure code, no model
        sha256 match, substring match,
        tier assignment, dedupe
              |
              v
          Fact[]  (typed, evidence-linked)
              |
              v
        [4] SIGNALS                        <-- deterministic rules over facts
        segment tier, stack classes, scale
        band, triggers, ops sub-signals
              |
              +---------------------------+
              |                           |
              v                           v
        [5] SCORE                   [6] HYPOTHESISE     <-- LLM, constrained to
        pure function,              workflow choice from fixed
        int in / int out            taxonomy + reasons + questions
              |                           |
              |                           v
              |                     [7] HEDGING LINT + INVARIANTS
              |                     reject assertive phrasing,
              |                     require validation questions
              +------------+--------------+
                           v
                     [8] RENDER
              JSON brief / Markdown brief / static HTML
                           |
                           v
              [9] RANK  (deterministic tie-break)
                           |
                           v
                 docs/FINDINGS.md, docs/VALIDATION.md
```

Stages 3, 4, 5 and 9 contain no model calls and are the ones under test. Stages 2 and 6 are the
only places a model runs, and both have their output validated by stage 3 and stage 7
respectively before anything reaches a brief.

### Stack

| Choice | Decision | Why |
|---|---|---|
| Language | Python 3.13 | Present and working. `pydantic` 2.11, `pytest`, `httpx` already installed |
| Schemas | pydantic v2 | Validation at the type boundary is how the fact/inference separation is enforced |
| CLI | argparse | One dependency fewer. Three commands is not a framework problem |
| LLM | OpenAI API, `gpt-4o-mini` (configurable via `OPENAI_MODEL`) | Extraction and constrained hypothesis generation. Decision D2: resolved, key available |
| LLM caching | Responses cached to `cache/llm/<sha256 of prompt>.json`, committed | Reviewer runs the whole pipeline with **no API key** and gets identical output. Reproducibility is the credibility argument |
| Tests | pytest | Business logic only, per `CLAUDE.md` |
| Interface | Static HTML generated from the JSON brief | No server, no build step, opens from the filesystem. Demo-friendly at near-zero cost |
| Network | `httpx`, one request at a time, descriptive user agent, robots.txt respected | See `CLAUDE.md` collection rules |

The report sketched `schemas/account.ts` [notes section 11], implying TypeScript. Python is
recommended instead: pydantic gives stronger runtime validation than TS types, which vanish at
runtime, and runtime enforcement is the entire point of the evidence model. Flagged as
decision D1.

### Commands

```
trelium collect --company "Stran Promotional Solutions" --domain stran.com
trelium brief   --domain stran.com [--format md|json|html]
trelium score   --from examples/stran.json        # rescore stored signals, proves determinism
trelium run-all --input data/prospects.csv        # all 30
trelium rank    --output docs/RANKING.md
trelium ablate                                    # validation experiment V2
```

---

## 5. Research strategy

**Universe.** The 30 accounts from the report [notes section 10], used as the starting list
because they are a real, defensible, already-screened sample. Additions and exclusions are
recorded with reasons in `data/prospects.csv`, including the iPROMOTEu / iPromo name collision
and the SanMar / S&S ecosystem ambiguity.

**Sources per account**, in the report's priority order [notes section 9], budgeted at roughly
6-10 pages:

| Priority | Source | What it gives |
|---|---|---|
| 1 | Company homepage, about, services | Segment, business model, operational language |
| 2 | Careers page and job listings | Ops/AP/CS roles, named systems in requirements |
| 3 | PPAI 100 entry | Scale band, growth figure, segment confirmation |
| 4 | Company news and press releases | Acquisitions, facilities, system migrations |
| 5 | Technology, integrations, partner pages | Stack signals |
| 6 | Executive public content | Operational statements |

Job listings are the highest-yield source for stack signals, because requirements sections name
systems that marketing pages never mention. They are also the source most likely to be
over-read: a posting for an order-entry clerk is a fact that the posting exists, and an
inference about what it implies. `EVIDENCE_MODEL.md` section 3.

**Collection rules.** Public pages only. No logins, no paywalls, no personal contact details,
no bulk crawling, one request at a time with a descriptive user agent, robots.txt honoured.
PPAI figures are cited as PPAI-reported values with attribution, never reproduced in bulk.

**Depth tiers.** All 30 get the automated pass. The top five by score get the manual deep dive
using the report's checklist [notes section 10]: website, business model, products, operations
language, job postings, technology references, growth, workflow, buyer role, three discovery
questions.

---

## 6. Scoring strategy

Full spec in `SCORING.md`. The four decisions worth surfacing here:

1. **Nothing unsourced scores.** Hard rule H1. A signal with no resolving, quote-verified
   evidence contributes zero, enforced at construction and re-checked at scoring time.
2. **The model never produces a number.** It produces evidence-linked signals. `score()` is a
   pure integer function of those signals, and a test asserts that corrupting every
   `model_confidence` field leaves the total unchanged.
3. **Scale peaks at mid-market rather than rising with size.** $50M-$500M scores 15; over $1B
   scores 8. Trelium's pricing tops out near $2,000/month before Enterprise, and the report's
   own deep-dive five skew mid-market while it flags 4imprint as a *less* certain fit
   [notes sections 2, 10].
4. **Score and evidence grade are separate axes.** A 0-100 number and an A-D grade. Grade D
   suppresses the point estimate in favour of a +/- 8 band, because false precision is worse
   than a range.

---

## 7. Deliverables

| Deliverable | Path | Demonstrates |
|---|---|---|
| Working CLI | `src/trelium_gtm/` | Claude Code proficiency |
| 30 scored accounts | `output/briefs/*.json`, `docs/RANKING.md` | Operational execution |
| 5 manually verified briefs | `output/briefs/*.md` | GTM judgment, quality control |
| Evidence corpus | `evidence/` | Reproducibility, provenance |
| Validation results | `docs/VALIDATION.md` | Intellectual honesty |
| Workflow coverage analysis | `docs/COVERAGE.md` | GTM decision support |
| Findings memo, one page | `docs/FINDINGS.md` | Communication |
| README | `README.md` | Framing |
| 60-90s demo | recorded separately | Ability to explain work |

---

## 8. Scope boundaries

Not built, deliberately. Each would cost hours and add nothing to the question the reader is
actually asking.

Authentication, users, billing, organisations, a database, a CRM or any CRM sync, a chat
interface, a web server or API, a job scheduler, a React or Next.js app, a vector store or RAG
layer, email sending of any kind, contact or personal-email enrichment, multi-tenant anything,
Docker, CI pipelines, telemetry.

Explicitly also not built: any capability that would let this tool contact a prospect.
That is a safety property, not an omission.

---

## 9. Success criteria

| # | Criterion | Measured how |
|---|---|---|
| S1 | 30 accounts scored end to end | `docs/RANKING.md` has 30 rows |
| S2 | Every fact in every brief resolves to a committed snapshot with a verified quote | Invariant test over all output |
| S3 | Zero inferences rendered as facts | Type separation test plus manual read of 5 briefs |
| S4 | Scoring reproducible from stored signals | `trelium score --from` reproduces the number; test asserts it |
| S5 | Pipeline runs offline with no API key from committed cache | Clean-clone test |
| S6 | Claim precision measured and published on the top 5 | `docs/VALIDATION.md`, including if it is poor |
| S7 | Ablation shows which components change the ranking | `docs/VALIDATION.md` |
| S8 | A reader can decide in under 4 minutes whether to act on a brief | Judgment, tested by showing one brief cold to someone unfamiliar |
| S9 | Five out-of-ICP negative controls all excluded at gate G1 | `docs/VALIDATION.md` V4 |
| S10 | At least one finding is about the market, not the method | `docs/FINDINGS.md`, plus `docs/COVERAGE.md` naming a workflow public evidence cannot target |

S6 is the one that matters most. A project that reports "of 214 extracted facts across five
briefs, 197 survived manual verification; here are the 17 that did not and why" is doing
something no polished dashboard can substitute for.

---

## 10. Founder review pass

The plan above was re-read from the perspective of a Trelium founder or GTM lead, asking the
question the brief poses: *would this tell me something useful, or merely that the candidate can
build software?* Five objections surfaced. Four produced changes to the plan; the fifth is
accepted as a limit.

**Objection 1 - "Every finding is about your tool, not about my market."** The strongest
version of this project teaches Trelium something about the promotional-products segment that
they did not already know, not something about research methodology. Methodology findings are
interesting to an engineer and inert to a GTM lead.

*Change:* `docs/FINDINGS.md` must contain **at least one market-level finding** - a statement
about the 30-account population that changes how someone would target it. Candidates that the
data will support or refuse: what fraction of accounts publicly name any order or ERP system at
all; whether that fraction varies by scale band; whether growth signals and stack signals
co-occur or are disjoint populations requiring different messages. A memo of three methodology
findings fails this criterion even if all three are true.

**Objection 2 - "Which of my nine use cases should I lead with?"** The hypotheses produce this
for free and the plan was throwing it away. Across 30 accounts, some workflows in the taxonomy
will be supportable from public evidence far more often than others. That is directly
actionable: it says which Trelium agent to lead outbound with, and which one cannot be targeted
from public signals no matter how good the research is.

*Change:* add a **workflow coverage analysis** - a matrix of the nine taxonomy workflows against
the 30 accounts, reporting how often each is hypothesised and at what confidence. Written to
`docs/COVERAGE.md`, summarised in the memo. Cost is roughly 30 minutes because the data already
exists by phase 6. This is the single highest value-per-minute addition in the whole plan.

**Objection 3 - "Does your score beat shuffling the list?"** A fair and slightly hostile
question, and the plan had no answer for it. V1 and V2 test correlation and component
contribution, but neither shows the model rejecting something it should obviously reject.

*Change:* add **V4, a negative control.** Run five deliberately out-of-ICP companies - a law
firm, a SaaS vendor, a restaurant group, a staffing agency, a regional bank - through the full
pipeline. Gate G1 should exclude all five. If any scores into `WATCH` or above, the segment
classifier is broken and that is worth knowing before anyone trusts a number. Twenty minutes,
and it makes the determinism claim concrete rather than asserted.

**Objection 4 - "So what do I do on Monday?"** The report's memo skeleton ends with "next
experiment" [notes section 11], but a vague next step reads as a book report ending.

*Change:* the memo closes with **one falsifiable prediction and the experiment that tests it**,
sized for a first week. Concretely: briefs whose top workflow hypothesis rests on a named order
or ERP system will produce a higher discovery-call booking rate than briefs whose hypothesis
rests only on segment and scale - with the sample size needed to detect it stated. That is a
proposal a GTM lead can approve or reject, not a sentiment.

**Objection 5 - "You have not proved any of this predicts revenue."** Correct, and
unfixable from outside the company. No external party has Trelium's win data. Accepted and
disclosed rather than papered over: `SCORING.md` section 10 states it, the memo states it, and
V1 is framed as a second opinion rather than ground truth. Claiming calibration here would be
the exact failure mode the project is built to avoid.

**Net effect on the plan:** three artifacts added (`docs/COVERAGE.md`, V4, the falsifiable
prediction), roughly one extra hour, no change to the architecture. The additions all convert
work the pipeline already does into something a GTM reader can act on, which was the objection
in the first place.
