# Validation Results

Run against the deeper-page collection pass (`docs/DEEP_COLLECTION.md`), with all six
extraction guards applied (`docs/FINDINGS.md` finding C). Total briefs: 30 | Scored: 11 |
Insufficient evidence: 19. The earlier homepage-only results are quoted where they differ.

---

## V1 — Rank correlation against the research report's independent priority order

The report ranked these 30 accounts by its own judgment, from the same public universe, without
reference to this scoring model (`docs/TRELIUM_RESEARCH_NOTES.md` section 10). This is a second
opinion, not ground truth — no external party has Trelium's actual win data
(`docs/SCORING.md` section 10).

**Spearman's rho: 0.400** on the 11 comparable accounts (homepage-only pass: −0.045).

Model ranking (scored accounts, best first): Showdown Displays 39, Stran Promotional Solutions
32, Concord Marketing Solutions 29, HALO 28, Hirsch 27, Nadel 17, SanMar 10, Ball Pro 5,
LeaderPromos 4, High Caliber Line 3, Staples Promotional Products 3.

**Why it moved, stated plainly:** not because deeper pages found better evidence. Before the
segment role-word guard, SanMar (report priority 30), Ball Pro (22), Staples (14) and High
Caliber Line (23) sat at 35, 30, 28 and 28 on segment claims whose quotes never said what the
company was. Removing those false positives is what pulled the two orderings closer. Concord,
the report's #1, rose to #3 because two unsupported "supplier" claims that had contradicted its
own "distributor" claim were downgraded and the conflict penalty lifted.

**Read honestly:** 11 accounts is too few for this number to mean much in either direction; one
account moving three places changes rho by roughly 0.1. What the comparison does show is that
the rubric's ordering is still decided almost entirely by which accounts have a supported
segment claim and a sourced headcount (V2 below). The components the report weighted heavily,
growth, systems and operational complexity, contribute nothing on 9 of the 11 scored accounts,
because the company's own pages never contain them.

---

## V2 — Component ablation (top-10 movement)

Each row zeroes one score component on the 11 scored accounts and reports how many of the
original top 10 fell out of the top 10 once that component is removed. With 11 scored accounts
"top 10" leaves one seat, so the measure is coarse: any component that moves the last-place
boundary registers as 1.

| Component zeroed | Homepage-only | Deeper pages |
|---|---|---|
| c1 (core vertical fit) | 1 | 1 |
| c2 (operational complexity) | 0 | 0 |
| c3 (software/ecosystem signals) | 0 | 1 |
| c4 (transaction/org scale) | 0 | 1 |
| c5 (growth/buying trigger) | 0 | 0 |
| c6 (evidence quality) | 1 | 0 |

c3 and c4 now register because two accounts each carry one such signal (Stran and Ball Pro for
systems; Showdown Displays and SanMar for scale). c2 and c5, the two components that describe
the report's actual pain pattern, scored zero on every account in both passes. The rubric was
built to reward "a high-volume process crossing several systems"; two collection passes have
not produced a single fact that reaches it.

---

## V3 — Manual claim audit

Every fact in the top five scored briefs (Showdown Displays, Stran, Concord, HALO, Hirsch: 26
facts) checked by hand against its quote, its statement and the page it came from. "Unscored"
means the fact is rendered but contributes nothing to the score (field `other`).

| # | Company | Statement (abridged) | Quote supports it? | Verdict |
|---|---|---|---|---|
| 1 | Showdown Displays | Privately-held global manufacturer and supplier of display products (segment: supplier) | Role word "supplier" present; the promotional-products vertical is not in the quote (PPAI lists them as a supplier) | Accurate |
| 2 | Showdown Displays | Team of 185 professionals in two European locations | Accurate as stated, but it set the company scale band from a regional headcount; company-wide headcount unknown | **Ambiguous** (as a scale signal) |
| 3 | Stran | Promotional product supplier (from the page title) | Yes | Accurate |
| 4 | Stran | Uses a Magento-based technology platform | Yes | Accurate |
| 5 | Stran | Established in 1994 (unscored) | Yes | Accurate |
| 6 | Stran | "Stran is a promotional products supplier" from the heading "Stran Promotional Product Solutions" | No — a heading, not a role statement. Now unscored by the role-word guard, but the model-written statement still renders as a fact | **Inaccurate** |
| 7 | Stran | Over 30 years in business (unscored) | Yes | Accurate |
| 8 | Stran | Offers creative account services and technology solutions (unscored) | Yes | Accurate |
| 9 | Concord | Promotional products distributor | Yes | Accurate |
| 10 | Concord | Established 1993 (unscored) | Yes | Accurate |
| 11 | Concord | Holds over $2.5M of blank soft goods (unscored; correctly not revenue) | Yes | Accurate |
| 12 | Concord | Best Places to Work for ten years (unscored) | Yes | Accurate |
| 13 | Concord | PPAI Greatest Companies to Work For, 2023 (unscored) | Yes | Accurate |
| 14 | Concord | Ranked 19 on the 2024 PPAI 100 Distributors (unscored; no `industry_rank` field yet) | Yes | Accurate |
| 15 | Concord | Announces record growth in 2015 (trigger: GROWTH_HIGH) | Statement accurate; the label GROWTH_HIGH means 25%+ YoY and the quote gives no figure. Scored 0 anyway: dated 2015 by the quote-year rule | **Ambiguous** (as a trigger label) |
| 16 | Concord | Counselor 2024 Best Places to Work (unscored) | Yes | Accurate |
| 17 | Concord | PPAI 2023 Greatest Companies list (unscored) | Yes | Accurate |
| 18 | Concord | #20 on ASI Counselor's Best Places to Work 2018 (unscored) | Yes | Accurate |
| 19 | Concord | Full-service corporate identity company (unscored; previously misread as "supplier") | Yes | Accurate |
| 20 | HALO | "Provides branded merchandise" from the title "Branded Solutions That Break Through" (unscored) | Loosely — the quote says "branded solutions", not merchandise | **Ambiguous** |
| 21 | HALO | Largest promotional merchandise distributor in the U.S. (per ASI Counselor) | Yes | Accurate |
| 22 | HALO | Deploys the latest technology (unscored marketing prose) | Yes | Accurate |
| 23 | HALO | Supports punch-out connections incl. GEP, PerfectCommerce, SciQuest, Oracle, SAP, Ariba (unscored after the whose-system guard; was six facts, now one) | Yes | Accurate |
| 24 | HALO | Single employee-recognition platform for worldwide programmes (unscored) | Yes | Accurate |
| 25 | Hirsch | Built on premium products (unscored prose) | Yes | Accurate |
| 26 | Hirsch | One of the leading suppliers of promotional products (from the careers page) | Yes | Accurate |

**Claim precision: 22/26 fully accurate, 3/26 ambiguous, 1/26 inaccurate.** Homepage-only
pass, top three briefs: 8/10, 1/10, 1/10.

All four non-clean rows are the limitation `docs/EVIDENCE_MODEL.md` section 8 stated before any
data existed: **the substring check (E2) proves a quote exists on the page; it does not prove
the extraction understood what the quote means.** Row 6 is a paraphrase the quote does not
support; rows 2, 15 and 20 are correct sentences whose scoring label or wording over-reads them.
Rows 6, 15 and 20 have been made harmless to the score by the pass-2 guards (role word,
recency, whose-system) but they still render, because a verbatim quote is a verbatim quote.
Row 2 is a scale-basis problem with no guard: a headcount that the quote scopes to one region
should not set the company band. Noted as the next guard to write, not written, because one
instance is not a pattern yet.

Two of the fourteen unscored rows above (14 and 23) are useful signals the taxonomy has no
field for: an industry rank and a customer-facing e-procurement capability. Both are
next-iteration taxonomy additions, not defects in what exists.

---

## V4 — Negative control

Full results in `docs/VALIDATION_V4.md` and `output/negative_controls/`. Five real, unambiguous
out-of-ICP companies (a law firm, a SaaS vendor, a restaurant group, a staffing agency, a
regional bank) run through the identical live pipeline, re-run on the deeper-page collector.

**5/5 produced no usable, rankable recommendation** — 4 by INSUFFICIENT_EVIDENCE (fetch blocked
or no extractable claims), 1 (Asana) by scoring 3/100 with segment left UNRESOLVED rather than
explicitly OUT_OF_ICP. Unchanged from the homepage-only pass. See `docs/VALIDATION_V4.md` for
why the pass/fail definition was refined after the first run.
