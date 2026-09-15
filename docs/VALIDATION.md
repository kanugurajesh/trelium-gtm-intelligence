# Validation Results

Run against the final corrected pipeline (all three extraction fixes applied — see
`docs/FINDINGS.md` finding 3). Total briefs: 30 | Scored: 11 | Insufficient evidence: 19.

---

## V1 — Rank correlation against the research report's independent priority order

The report ranked these 30 accounts by its own judgment, from the same public universe, without
reference to this scoring model (`docs/TRELIUM_RESEARCH_NOTES.md` section 10). This is a second
opinion, not ground truth — no external party has Trelium's actual win data
(`docs/SCORING.md` section 10).

**Spearman's rho: −0.045** (was 0.182 before the correctness-hardening re-score; see
`RESCORE_COMPARISON.md`) — effectively zero correlation, on 11 comparable accounts.

Model ranking (scored accounts, best first): Showdown Displays, HALO, High Caliber Line, Stran
Promotional Solutions, Hirsch, Concord Marketing Solutions, Nadel, SanMar, Ball Pro, Staples
Promotional Products, LeaderPromos.

**Why it got worse, stated plainly:** the report's #1 pick, Concord Marketing Solutions, fell
from model rank 3 to 6 because its own pages disagree about whether it is a distributor or a
supplier, and the contradiction policy now penalises that instead of silently picking the
first claim. That is the system behaving correctly on bad evidence, not the rubric agreeing
less with the report — but the number is what it is.

**Read honestly:** a rho near zero means this run's ranking is not a proxy for the report's
independent judgment. The most direct explanation, cross-checked against V2 below: with only
homepage-level evidence, the score is driven almost entirely by which segment label got
assigned and how many source pages were reachable — not by the growth, scale and stack signals
the report weighted heavily and that this rubric was designed around. The rubric is not wrong;
the evidence feeding it is too shallow on this run to exercise most of it. See finding 1 in
`docs/FINDINGS.md`.

---

## V2 — Component ablation (top-10 movement)

Each row zeroes one score component on the 11 scored accounts and reports how many of the
original top-10 fell out of the top 10 once that component is removed.

| Component zeroed | Accounts that fell out of top 10 |
|---|---|
| c1 (core vertical fit) | 1 |
| c2 (operational complexity) | 0 |
| c3 (software/ecosystem signals) | 0 |
| c4 (transaction/org scale) | 0 |
| c5 (growth/buying trigger) | 0 |
| c6 (evidence quality) | 1 |

**Read honestly, this is the sharpest single result in this validation pass.** On this run, the
ranking is effectively decided by two components: whether the segment classifier fired (c1) and
how many independent sources got collected (c6). The four components meant to capture the
report's actual pain pattern — operational complexity, named systems, scale, and growth
triggers — currently move nothing, because homepage-only evidence essentially never populates
them (`docs/COVERAGE.md` shows the same gap from a different angle: 6 of 9 taxonomy workflows
were never hypothesised at all). The rubric was built to reward the report's strongest signal
("a high-volume process crossing several systems"); this run cannot yet test whether it does,
because the evidence never reaches that signal. Deeper collection (job postings, integration
pages, press releases) is a precondition for this rubric to be exercised at all, not an
optional enhancement.

---

## V3 — Manual claim audit

Every fact in the top three scored briefs (Showdown Displays, HALO, Concord Marketing
Solutions — 10 facts total) checked by hand against its quote and statement.

| # | Company | Statement | Verdict |
|---|---|---|---|
| 1 | Showdown Displays | "...premier, privately-held global manufacturer and supplier of...display products" | Accurate |
| 2 | Showdown Displays | Europe team of 185 professionals | Accurate |
| 3 | HALO | More than 1,800 employees | Accurate |
| 4 | HALO | Grown to over $1B in revenue | **Ambiguous** — quote says "grown exponentially to over $1B" without stating *what* reached $1B; revenue is the plausible reading given it's on a careers/growth page, but the quote does not say "revenue" |
| 5 | HALO | Promotional products and recognition company | Accurate |
| 6 | Concord | Promotional products distributor | Accurate |
| 7 | Concord | *(segment: supplier)* — founded 1993 by Kirk Graves and Robert Conte, "ushering retail name-brands to the corporate marketplace" | **Inaccurate** — the quote is company-history prose and does not support "supplier" as a segment label at all. *Since the correctness-hardening pass this disagreement with row 6 is detected: the brief now carries `SEGMENT_CONFLICT_UNRESOLVED`, a research gap naming both labels, and a C1 penalty (25→20). The bad extraction still exists; it can no longer hide.* |
| 8 | Concord | Holds $2.5M of blank soft goods (inventory) | Accurate (correctly rendered as an unscored "other" fact after the fix) |
| 9 | Concord | Named a "Best Place to Work" for 10 years | Accurate |
| 10 | Concord | Ranked 19 on the 2024 PPAI 100 Distributors | Accurate |

**Claim precision: 8/10 fully accurate, 1/10 ambiguous, 1/10 inaccurate.**

Both non-clean results are the same underlying limitation, stated in `docs/EVIDENCE_MODEL.md`
section 8 before any data existed to confirm it: **the substring check (E2) proves a quote
exists on the page; it does not prove the extraction understood what the quote means.** Row 4
mislabels an unstated "what" as revenue from context; row 7 asserts a segment a generic
founding-story quote does not actually establish. Neither would be caught by tightening the
extraction prompt alone — that was already tried, and failed, on three other numeric-field
cases (finding 3). A stronger fix (out of scope for this project) would require a second,
narrower "does this quote actually support this specific claim" verification pass, itself
grounded and tested the same way extraction currently is.

One taxonomy gap surfaced here too: row 10 (a PPAI 100 rank) is a real, useful scale-adjacent
signal with no field to hold it — the current taxonomy has `revenue_usd` and `employee_count`
but no `industry_rank` field. Noted as a next-iteration addition, not a defect in what exists.

---

## V4 — Negative control

Full results in `docs/VALIDATION_V4.md` and `output/negative_controls/`. Five real, unambiguous
out-of-ICP companies (a law firm, a SaaS vendor, a restaurant group, a staffing agency, a
regional bank) run through the identical live pipeline.

**5/5 produced no usable, rankable recommendation** — 4 by INSUFFICIENT_EVIDENCE (fetch blocked
or no extractable claims), 1 (Asana) by scoring 3/100 with segment left UNRESOLVED rather than
explicitly OUT_OF_ICP. See `docs/VALIDATION_V4.md` for why the pass/fail definition was refined
after this run — the first definition was stricter than the outcome actually warranted.
