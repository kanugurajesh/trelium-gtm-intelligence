# Trelium GTM Research — What I Found

## Question

Can public signals identify promotional-products companies with potentially strong Trelium
workflow opportunities, using only their own public web pages?

## Method

Built an evidence-verified research pipeline (`docs/PROJECT_SPEC.md`) and ran it against 30
candidate accounts drawn from independent industry research
(`docs/TRELIUM_RESEARCH_NOTES.md` section 10), plus a 5-company negative control. Extracted
claims were kept only if verified as an exact, unique substring of the fetched page (E2 in
`docs/EVIDENCE_MODEL.md`); everything else was rejected before it could become a fact. Scoring
was a pure deterministic function of evidence-linked signals (`docs/SCORING.md`) — the model
never saw the rubric. Manually audited every fact in the top three scored briefs against source
(`docs/VALIDATION.md`).

## Finding A — Public homepage collection alone failed on roughly two-thirds of this vertical, mostly to access control, not thin content

**19 of 30 accounts (63%) produced zero usable evidence.** Broken down:

| Cause | Count | Share of failures |
|---|---|---|
| Blocked by robots.txt | 10 | 53% |
| Bot detection (HTTP 403) | 4 | 21% |
| Page fetched, but nothing extractable (JS shell, region-select interstitial, pure nav menu) | 3 | 16% |
| No visible text at all (JS-rendered homepage) | 1 | 5% |
| Domain resolution issue on my part | 1 | 5% |

**14 of 19 failures (74%) were the site actively declining automated access, not a limitation
of the extraction step.** The pipeline respected every one of these — it recorded the gap and
moved on rather than routing around a block (`CLAUDE.md` R22) — which is the correct behavior,
but it means a research tool built this way has a hard ceiling on this vertical's addressable
research set well before evidence quality becomes the bottleneck. **This is a finding about the
market, not the method**: promotional-products distributors and suppliers at this scale
disproportionately run bot-protected or JS-heavy commerce platforms (several of the blocked or
empty pages were recognizably Shopify or similar storefront platforms), which is itself a
signal about this vertical's typical technology posture — the same posture Trelium's own
workflow thesis is built around.

## Finding B — Homepage-level evidence names a segment; it essentially never names a workflow

Across the 11 accounts that did score, only 3 of the 9 taxonomy workflows were ever
hypothesised at all (`docs/COVERAGE.md`): supplier purchasing (2), order status (2), quoting
(1). **Inbound PO to order entry — the report's own flagship pain pattern and the workflow its
SanMar/S&S material uses as the clearest example — was never hypothesised once, from any
account, in this run.** The component ablation (V2 in `docs/VALIDATION.md`) shows why: with
homepage-only evidence, the score is effectively decided by two things — whether a segment
label was assigned, and how many source pages were reachable. The four components meant to
capture the report's actual pain pattern (operational complexity, named systems, scale, growth
triggers) moved nothing in this run, because a homepage essentially never contains the
operational detail — named order systems, job postings, integration pages — that those
components need. The rubric was built correctly for the report's target signal; the evidence
collected here never reaches it. Getting past the homepage (careers, technology/integrations
pages, press) is a precondition for testing whether the rubric works, not a nice-to-have.

## Finding C — A prompt asked nicely is not a verification layer

The manual audit and live testing surfaced the same failure mode three separate times: the
extraction model read a real number on the page correctly, then misclassified *what it
measured*.

1. "space to hold over $2.5 million dollars of blank soft goods" (inventory capacity) tagged as
   `revenue_usd`.
2. "over 25 years of experience" tagged as `employee_count`.
3. "produces approximately 30 million items annually" (unit production volume) tagged as
   `revenue_usd` again, for the same company, on a separate run.

Tightening the extraction prompt's field definitions fixed none of these — case 1 was re-tested
live after a prompt rewrite and still failed. Each was fixed instead with a deterministic
keyword check in code (a required positive indicator for `revenue_usd`/`employee_count`, plus a
disqualifying-context blacklist), verified with a regression test, and re-confirmed live. The
manual audit then found a fourth, related but distinct failure the code checks cannot catch: a
segment claim ("supplier") supported only by a generic founding-history quote that never
mentions the word — a case where the quote is genuinely on the page (E2 passes) but does not
actually support the specific claim attached to it. That gap is disclosed, not fixed, in
`docs/VALIDATION.md` V3 — it is the honest edge of what a substring check can guarantee.

## What I would do next

**Falsifiable prediction:** briefs whose top-ranked workflow hypothesis is supported by a named
order/ERP/industry system (a C3 signal) will be perceived by a GTM reviewer as more
actionable — and would produce a higher discovery-call booking rate in real outbound — than
briefs whose hypothesis rests only on segment and scale. Finding B implies this is currently
untestable from homepage evidence alone, because C3 essentially never fires from a homepage.

**First-week experiment:** extend collection to 2-3 deeper page types per account (careers
listings, an integrations/technology page if one exists, one press release) for the 19
accounts that returned no evidence this run, prioritizing the 4 blocked only by robots.txt-
adjacent soft failures rather than hard bot detection. Re-run scoring and the coverage analysis.
The prediction is falsified if PO-entry-class hypotheses still fail to appear even with deeper
source coverage — that would mean the gap is about what these companies choose to publish, not
about how many of their pages get read, which is a different and more interesting finding.
Fourteen scored-or-insufficient accounts is enough to detect a shift in workflow coverage from
0/9 to a materially different distribution without needing the full 30 re-run.
