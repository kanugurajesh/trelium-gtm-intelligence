# Trelium GTM Research — What I Found

## Question

Can public signals identify promotional-products companies with potentially strong Trelium
workflow opportunities, using only their own public web pages?

## Answer

No, not from their own web pages. Two-thirds of the vertical blocks automated collection
outright. On the third that does not, reading careers, technology, press and services pages as
well as the homepage adds facts but not operational evidence: across two full passes over 30
accounts, the rubric's operational-complexity and buying-trigger components never scored a
single point for any account. The tool's most useful output is that measurement, not a lead
list.

## Method

Built an evidence-verified research pipeline (`docs/PROJECT_SPEC.md`) and ran it against 30
candidate accounts drawn from independent industry research
(`docs/TRELIUM_RESEARCH_NOTES.md` section 10), plus a 5-company negative control. Extracted
claims were kept only if verified as an exact, unique substring of the fetched page (E2 in
`docs/EVIDENCE_MODEL.md`); everything else was rejected before it could become a fact. Scoring
was a pure deterministic function of evidence-linked signals (`docs/SCORING.md`); the model
never saw the rubric.

Two passes. Pass 1 read the homepage plus at most one about page and one careers page. Pass 2,
the experiment pass 1's memo proposed, added one technology/integrations page, one press/news
page and one services page per account, discovered from the site's own navigation, at most six
requests per account. Same prompts, same scorer, same taxonomy. Pass 1 briefs are archived in
`output/briefs_pass1_homepage/`; pass 2 is `output/briefs/`; the comparison is
`docs/DEEP_COLLECTION.md`. Every fact in the top five pass-2 briefs was audited by hand against
its quote and its page (`docs/VALIDATION.md` V3).

## Finding A — Two-thirds of this vertical cannot be researched from its own site, and deeper crawling does not change that

**19 of 30 accounts (63%) produced zero usable evidence in both passes.** The pass-1 breakdown
holds unchanged:

| Cause | Accounts | Share of failures |
|---|---|---|
| Blocked by robots.txt | 10 | 53% |
| Bot detection (HTTP 403) | 4 | 21% |
| Page fetched, nothing extractable (JS shell, region-select interstitial, pure navigation) | 3 | 16% |
| No visible text at all (JS-rendered homepage) | 1 | 5% |
| Domain resolution issue on my part | 1 | 5% |

Pass 2 could not help these accounts by construction: the deeper pages are discovered from the
homepage, and a blocked homepage yields no links. The three "nothing extractable" accounts did
get deeper pages in pass 2 (Ariel Premium Supply read four) and still produced no claims. The
pipeline respected every block (`CLAUDE.md` R22). **This is a finding about the market, not
the method:** promotional-products companies at this scale disproportionately run
bot-protected or JS-rendered commerce platforms, which is the same fragmented-systems posture
Trelium's workflow thesis is built around.

## Finding B — Deeper pages were tested as a precondition for the rubric, and they were not enough

Pass 1 ended with a prediction: the four operational components (c2 operational complexity, c3
named systems, c4 scale, c5 growth triggers) could not fire from homepage evidence, so deeper
pages were a precondition for testing the rubric. Pass 2 tested it.

| Measure | Pass 1 (homepage-only) | Pass 2 (deeper pages) |
|---|---|---|
| Pages read | 16 | 44 |
| Verified facts | 33 | 50 |
| Accounts with a workflow hypothesis | 3 of 11 | 6 of 11 |
| Scored accounts where c2 (ops complexity) > 0 | 0 | 0 |
| Scored accounts where c5 (growth / hiring trigger) > 0 | 0 | 0 |
| Scored accounts where c3 (named systems) > 0 | 1 | 2 |
| Scored accounts where c4 (scale) > 0 | 3 | 2 |
| Highest score | 39 | 39 |
| Accounts at or above the WATCH band (50) | 0 | 0 |

Reading nearly three times as many pages produced half again as many facts and twice as many
hypotheses, and moved no account out of DEPRIORITIZE. The two components that describe the
report's actual pain pattern, a high-volume process with repeatable rules crossing systems,
still never fired. No careers page produced a single open operations, order-entry or AP/AR
role. The only new system signals were a Magento storefront (Stran) and a Shopify footer (Ball
Pro).

**Read plainly:** the prediction that deeper pages were the missing precondition was wrong in
the way that matters. The evidence the rubric needs is not on these companies' sites at any
depth. Job postings, industry-association listings and press coverage live on other domains,
and this collector, by design, stays on the company's own domain. The next step is a second
data source, not more crawling (see below).

Workflow coverage did widen. Pass 1 hypothesised three of nine taxonomy workflows; pass 2
hypothesised four (`docs/COVERAGE.md`), and the report's flagship pattern, inbound PO to order
entry, appeared for the first time, once, at Ball Pro, at medium confidence, resting on a
Shopify footer and a blog post about a custom outing programme. That is the honest ceiling of a
homepage-and-neighbours pass: it can name a plausible workflow, and it cannot support it.

## Finding C — A prompt asked nicely is not a verification layer, six times over

The manual audits surfaced the same failure class six times: the model quoted a real sentence
correctly, then misread what it meant. Each was fixed with a deterministic check in code plus
a regression test, never with prompt wording, because the first instance was re-tested live
after a prompt rewrite and still failed.

1. "space to hold over $2.5 million dollars of blank soft goods" (inventory) tagged as revenue.
2. "over 25 years of experience" tagged as a headcount of 25.
3. "produces approximately 30 million items annually" (unit volume) tagged as revenue.
4. *(pass 2)* "announces record growth in 2015", a press-page headline, scored as a live growth
   trigger at full weight, because no evidence ever carried a date and unknown age is
   deliberately not penalised. A claim that names a year is now dated by it.
5. *(pass 2)* "We support a wide range of punch-out connections, including GEP, PerfectCommerce,
   SciQuest, Oracle, SAP and Ariba", on a distributor's technology page, produced six system
   facts, and Oracle and SAP scored as the company's own ERP stack. Those are the customers'
   procurement systems. Second-person or punch-out framing now keeps a system claim unscored.
6. *(pass 2, from the audit of the top five briefs)* every inaccurate fact was a segment label
   attached to a quote that never stated the role: "several ways to connect with you" tagged
   supplier, a page heading tagged supplier, a mission statement tagged supplier. Segment is
   worth 25 points, the largest component, and it was being fed by the weakest quotes. A
   segment claim must now quote its role word, which `docs/SCORING.md` section 3 had specified
   from the start and the code had never enforced.

The sixth fix changed the ranking more than any evidence did: SanMar fell from 35 to 10, Ball
Pro from 30 to 5, Staples from 28 to 3 and High Caliber Line from 28 to 3, because their scores
had rested on unsupported segment claims. Rank correlation with the research report's own
priority order moved from −0.045 to 0.400 on the 11 comparable accounts, which is a
consequence of removing false positives, not of finding new evidence, and on 11 accounts is
not a significant result either way.

The remaining defects the substring check cannot reach are semantic, and they are disclosed
rather than fixed: a regional headcount ("team of 185 professionals", Europe) set a company
scale band; "record growth" was labelled a 25%+ growth trigger with no percentage in the
quote; a downgraded claim's model-written statement still renders as a fact even when its
quote does not support it (`docs/VALIDATION.md` V3).

## Finding D — Claim precision on the final briefs: 22 of 26 fully accurate

Every fact in the top five pass-2 briefs (Showdown Displays, Stran, Concord, HALO, Hirsch; 26
facts) was checked by hand against its quote and its page. **22 fully accurate, 3 ambiguous, 1
inaccurate.** The pass-1 audit of the top three was 8 of 10. The full table, with the verdict
reasoning per row, is in `docs/VALIDATION.md` V3. The single inaccurate row and all three
ambiguous rows are the semantic class described above, where the quote exists on the page and
the extraction's reading of it is what is wrong.

## What I would do next

**1. A second data source, before any more crawling.** The rubric's operational components need
job postings (source tier 3) and industry-association listings (tier 2), both off the company's
domain. Falsifiable prediction: with job-board data for the same 30 accounts, the buying-trigger
component (c5) fires for at least a third of them, and at least one account crosses the WATCH
band. If it does not, the rubric's operational components are not measurable from any public
source and should be dropped from the score, which would be a more useful result than any lead.

**2. A deep-research comparison, held to the same standard.** Run a frontier deep-research
product on the same five audited accounts, hold every claim it makes to the same verbatim-quote
check, and publish its verified precision and its reach next to this tool's. Deep research
reaches sources this crawler cannot and synthesises far better; the open question is how many
of its sentences survive the substring test. If it wins on verified precision and reach, that is
the recommendation for Trelium's GTM team, and finding it is worth more than defending this
tool.

**3. The outbound test the first memo proposed** (briefs backed by a named system are more
actionable than briefs backed by segment and scale) is now testable on exactly two accounts,
Stran and Ball Pro. That is too few. It waits on (1).
