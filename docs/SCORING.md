# Scoring Model

A pure function: `score(signals: SignalSet) -> ScoreResult`. No I/O, no model calls, no
randomness, no floats. Same signals in, same integer out, forever.

The LLM's job ends at producing evidence-linked signals. It never sees this file's numbers and
never emits a score. That separation is the point of the exercise, and it mirrors Trelium's own
stated reasoning-versus-deterministic-execution split [notes section 1].

---

## 1. Critique of the rubric as the research report states it

The report proposes [notes section 9]:

```
Core vertical fit                   25
Operational/process complexity      20
Relevant software/ecosystem signals 15
Transaction/organization scale      15
Growth/buying trigger               15
Evidence quality                    10
```

with example rules:

```
promotional distributor/supplier/decorator: +25
strong evidence of multiple operating systems: +15
>$50M relevant revenue / material operation: +15
high-growth or acquisition trigger: +15
documented repetitive workflow clue: +20
multiple high-quality sources: +10
```

**The weights are kept. The rules are not.** Six problems:

1. **Every rule is binary.** All six are all-or-nothing, so across a 30-account set the model
   produces a handful of clustered values instead of a ranking. A prioritisation tool that
   cannot discriminate between rank 4 and rank 11 has not done its job.
2. **"documented repetitive workflow clue: +20"** awards a fifth of the total score on a single
   subjective judgment - and it is exactly the judgment the model is least able to make from
   public data. It is also the judgment the report elsewhere insists we cannot make
   [notes section 9, the Concord warning].
3. **Scale is monotonic.** ">$50M: +15" implies 4imprint at $1.3B outscores Concord at $87M on
   scale. The report's own deep-dive five contradicts this, and Trelium's $500-$2,000/month
   pricing contradicts it harder. Fixed in section 5.
4. **No disqualifier.** A software consultancy scores 75 by missing only vertical fit and lands
   mid-table. Fixed with a gate in section 2.
5. **Evidence quality is scored as if it were a property of the account.** It is a property of
   *our research effort*. An account does not become a better fit because we found more pages
   about it. Discussed and partially fixed in section 7.
6. **Nothing stops an unsourced signal from scoring.** The most important rule in the whole
   model is absent from the report. Added in section 2.

---

## 2. Gates and hard rules

Evaluated before scoring.

| Gate | Condition | Result |
|---|---|---|
| G1 | Segment tier X (`OUT_OF_ICP`) | Exit. `score = null`, status `OUT_OF_ICP`. Not ranked |
| G2 | Company in Trelium's public customer list | `score` computed, flag `PUBLIC_CUSTOMER`, excluded from the ranked list |
| G3 | Supplier whose data Trelium already integrates (SanMar, S&S Activewear) | Flag `ECOSYSTEM_AMBIGUOUS`, excluded from the ranked list [notes section 10] |
| G4 | No evidence items at all | Exit. Status `INSUFFICIENT_EVIDENCE` |

**Hard rule H1 - the evidence gate.**

> A signal whose `evidence_ids` is empty, or any of whose evidence ids fail to resolve, or any
> of whose quotes fail the substring check in `EVIDENCE_MODEL.md` section 2, contributes
> **zero** points.

Enforced at construction: the `Signal` type requires a non-empty `evidence_ids` field, and the
scorer re-validates against the corpus before summing. This is the rule that makes the number
trustworthy, and it gets its own test file.

**Hard rule H2 - no model-supplied numbers.** `model_confidence` is stored in the JSON and is
not read by the scorer. A test asserts that mutating every `model_confidence` in a fixture
leaves the score unchanged.

**Hard rule H3 - integers only.** Every component and the total are `int`. Recency discounts
use integer floor division.

---

## 3. C1 - Core vertical fit (0-25)

| Condition | Points |
|---|---|
| Segment tier A (promo distributor, supplier, decorator/print) with tier 1-2 evidence | 25 |
| Segment tier A with tier 3-5 evidence only | 20 |
| Segment tier B (adjacent branded merchandise) | 15 |
| Segment tier C (operations-heavy non-promo) | 8 |
| Segment unresolved (no sourced segment evidence) | 0 + gap |

Segment tier comes from a deterministic map over the LLM's segment label plus required keyword
evidence in the corpus. The model proposes a label; the mapping table decides the tier.

---

**Whose word?** A segment claim only counts when its quote contains the role word it asserts
("supplier" or "manufacturer", "distributor", "decorator"/"print"/"embroidery"/"engraving",
"branded merchandise"/"swag"/"promotional"). Added after the manual audit of the deeper-page
pass found that every inaccurate fact in the top five briefs was a segment label attached to a
quote that never stated the role: "several ways to connect with you" as supplier, a page heading
as supplier, a mission statement as supplier (`docs/VALIDATION.md` V3, `docs/FINDINGS.md`
finding C, sixth instance). C1 is the largest component and was being fed by the weakest
quotes. Exclusion labels are not guarded: a missed exclusion is the conservative direction and
the negative control covers it. Enforced in `extract.py`, tested in
`tests/test_segment_support.py`.

---

## 4. C2 - Operational and process complexity (0-20)

Replaces the single +20 binary with eight independently evidenced sub-signals. Each requires
its own evidence under H1.

| Sub-signal | Evidence shape | Pts |
|---|---|---|
| `OPS_MULTISTEP_ORDER` | Public description of an order lifecycle with 3+ handoffs | 5 |
| `OPS_CUSTOMIZATION` | Decoration, personalisation, artwork approval, proofing | 4 |
| `OPS_SUPPLIER_NETWORK` | Claim of many suppliers/brands, or a supplier directory | 4 |
| `OPS_COMPANY_STORES` | Company store / program management offering | 4 |
| `OPS_QUOTE_INTAKE` | Public quote request form or custom-quote flow | 3 |
| `OPS_SERVICE_TEAM` | Named customer service or order support function | 3 |
| `OPS_MULTI_SITE` | Multiple facilities, warehouses or decoration sites | 3 |
| `OPS_RETURNS_EXCEPTIONS` | Documented returns, claims or exception process | 2 |

Raw maximum 28, **capped at 20**. The cap is deliberate: several routes reach the ceiling, so
no single lucky page determines a fifth of the score.

Note what this measures. It measures *process surface area visible in public sources* - the
number of places information plausibly changes hands. It does **not** measure whether any of it
is manual. That distinction is stated on the brief itself.

---

## 5. C3 - Software and ecosystem signals (0-15)

| Class | First system | Each additional | Class cap |
|---|---|---|---|
| Industry order/business system (SAGE, commonsku, ShopWorks, Printavo, DistributorCentral, Syncore, AIM) | 6 | +2 | 8 |
| ERP / accounting (NetSuite, SAP, Oracle, QuickBooks, Acumatica, Dynamics) | 5 | +1 | 6 |
| Supplier data (PromoStandards, SanMar API, S&S API, alphabroder) | 4 | +1 | 5 |
| CRM (Salesforce, HubSpot) | 3 | +1 | 4 |
| Commerce / company store platform (Shopify, OrderMyGear, Magento/Adobe Commerce, BigCommerce, WooCommerce, custom) | 3 | +1 | 4 |
| Generic office (Gmail, Outlook, Sheets, Excel, Slack) | 1 | 0 | 1 |

**Cross-boundary bonus:** +3 if two or more distinct non-generic classes are present.

**Whose system?** A system name only counts when the page presents it as the company's own.
A quote that frames the system as the reader's ("connect with your ERP") or as a punch-out /
e-procurement connection is kept as an unscored fact, not a stack signal. Added after a
distributor's list of customer punch-out targets (Oracle, SAP, Ariba, ...) scored as its own
ERP stack (`docs/FINDINGS.md`, finding C, fifth instance). Enforced in `extract.py` by a
disqualifying-context check on the quote, the same mechanism as the revenue guard.

**Generic-office rule:** the generic class scores 0 unless at least one non-generic class is
also present. A company that mentions Excel and nothing else has told us nothing; a company
that mentions Excel *and* NetSuite has told us where a boundary is.

Sum capped at 15. This is the component that most directly tests Trelium's thesis, since
Trelium sells the layer between systems [notes section 1].

---

## 6. C4 - Transaction and organisation scale (0-15)

Non-monotonic, peaking at mid-market. Justified in `ICP.md` section 3.

| Band | Promo-relevant revenue | Pts |
|---|---|---|
| `SWEET_SPOT` | $50M - $500M | 15 |
| `LARGE` | $500M - $1B | 11 |
| `LOWER_MID` | $20M - $50M | 10 |
| `ENTERPRISE` | > $1B | 8 |
| `SMALL` | $5M - $20M | 5 |
| `MICRO` | < $5M | 1 |
| `UNKNOWN` | no sourced figure | 0 + gap |

**Headcount fallback** when no revenue figure exists: 500+ employees maps to `LARGE`, 100-499 to
`SWEET_SPOT`, 25-99 to `LOWER_MID`, under 25 to `SMALL`. Result is multiplied by 4/5 (integer
floor) and tagged `scale_basis: headcount`, because headcount-to-transaction-volume is a weaker
proxy.

**Mandatory caveat** when the figure comes from PPAI: the brief states it is 2025
promotional-products revenue reported or estimated by PPAI, not audited total corporate
revenue [notes section 10].

---

## 7. C5 - Growth and buying trigger (0-15)

| Trigger | Pts |
|---|---|
| `GROWTH_HIGH` - 25%+ YoY, sourced | 8 |
| `GROWTH_MODERATE` - 10-25% YoY, sourced | 5 |
| `ACQUISITION` - completed in last 24 months | 5 |
| `SYSTEM_MIGRATION` - announced ERP/order-platform change | 5 |
| `OPS_HIRING` - 3+ open ops/order-entry/CS roles | 4 |
| `OPS_HIRING` - 1-2 such roles | 3 |
| `AP_AR_HIRING` - open AP or AR roles | 3 |
| `NEW_FACILITY` - new site, warehouse or decoration capacity | 3 |
| `LEADERSHIP_CHANGE_OPS` - new COO/VP Ops in last 12 months | 2 |
| `CONTRACTION` | **0**, and sets `angle = efficiency` |

`GROWTH_HIGH` and `GROWTH_MODERATE` are mutually exclusive. Sum capped at 15.

**Recency discount**, applied per trigger from `Evidence.published_at`. `published_at` is the
page's publication date when the source provides one; otherwise, if the supporting quote names
a year, the latest year it names (as 1 January of that year, the earliest possible date, so the
discount is never under-applied); otherwise unknown, which scores at full weight. The quote-year
rule was added after a press-page headline dated 2015 scored as a live growth trigger
(`docs/FINDINGS.md`, finding C, fourth instance). A claim that dates itself is discounted for
its own date; a claim that does not is not guessed at.

| Age | Multiplier |
|---|---|
| 0-24 months | full |
| 24-36 months | half, integer floor |
| over 36 months | 0 |

`CONTRACTION` scoring zero rather than negative is intentional. A shrinking distributor is a
worse growth story and a better cost story; the report models exactly that for SnugZ USA and
Gemline [notes section 10]. The brief's framing changes; the account is not punished.

---

## 8. C6 - Evidence quality (0-10), and why it is uncomfortable

| Factor | Pts |
|---|---|
| Independent source domains (1 each, max 4) | 0-4 |
| 6+ tier-1/2 facts | 3 |
| 3-5 tier-1/2 facts | 2 |
| 1-2 tier-1/2 facts | 1 |
| All evidence dated, and the oldest item under 12 months old | 2 |
| All evidence dated, and the oldest item under 24 months old | 1 |
| Any component corroborated by 2+ independent domains | 1 |

Capped at 10. "Independent" means distinct registrable domains; two pages of one company site
count once.

"All evidence dated" is strict: one undated item means the freshness bonus is not earned,
because a bonus that says every claim is fresh cannot be granted while some claim's age is
unknown. (The first implementation keyed this bonus off the youngest item, which would have
granted it on a single fresh quote; it never fired only because no evidence carried a date
before the quote-year rule in section 7 existed.)

**The honest problem.** Under hard rule H1, an account with thin evidence already scores low on
C1-C5, because unsourced signals contribute nothing. Adding C6 on top double-counts research
effort. Keeping it is a deliberate choice for two reasons: it preserves the rubric this project
was asked to start from, and public operational transparency is itself weakly informative - a
company that publishes its order process is a company whose operations you can have a
conversation about. But it *is* double-counting, and the findings memo says so rather than
pretending the rubric is clean.

**Mitigation - a separate evidence grade**, not a score component:

| Grade | Condition |
|---|---|
| A | 3+ independent domains, 5+ tier-1/2 facts, every scored component sourced |
| B | 2+ independent domains, 3+ tier-1/2 facts |
| C | 1+ tier-1/2 fact |
| D | no tier-1/2 facts |

Grade D sets flag `LOW_EVIDENCE`, and the brief reports the score as a **band of +/- 8**
rather than a point value. A number presented with false precision is worse than a range.

---

## 9. Output, banding and ranking

```python
ScoreResult:
  total: int                    # 0-100
  components: dict[str, int]    # c1..c6
  contributing_signals: dict[str, list[SignalRef]]   # which signal -> which points
  evidence_grade: Literal["A","B","C","D"]
  band: Literal["PRIORITY","INVESTIGATE","WATCH","DEPRIORITIZE"]
  flags: list[str]
  reported_as: Literal["point","range"]
  range: tuple[int,int] | None
```

`contributing_signals` is the audit trail: for any point in the total, the brief can say which
signal produced it and which evidence backs that signal. A score you cannot decompose is a
score nobody should act on.

| Band | Range | Meaning |
|---|---|---|
| `PRIORITY` | 80-100 | Worth a researched approach now |
| `INVESTIGATE` | 65-79 | Worth 20 more minutes of human research |
| `WATCH` | 50-64 | Revisit on a trigger |
| `DEPRIORITIZE` | 0-49 | Not now |

**Deterministic tie-break order** for ranking:

1. `total` descending
2. `evidence_grade` (A > B > C > D)
3. scale band proximity to `SWEET_SPOT`
4. boundary count of the top workflow hypothesis, descending
5. company name ascending

Step 5 guarantees a total order, so two runs over the same corpus produce byte-identical
rankings.

---

## 10. What the score is not

- **Not a probability of closing.** It has never been fitted to an outcome, because no outsider
  has Trelium's outcome data.
- **Not a measure of pain.** It measures observable process surface area and buying-trigger
  proxies. Whether anything is actually manual is unknown and is what the validation questions
  are for.
- **Not comparable across segments.** A supplier at 82 and a decorator at 82 are not equivalent
  opportunities; the workflows differ.
- **Not stable across corpus versions.** Add a source and the score moves. Every brief records
  the corpus hash it was scored against.

---

## 11. Validation plan

Calibration against real outcomes is impossible from outside. Three things are possible, and
all three are cheap:

**V1 - Rank correlation against an independent human judgment.** The research report
independently selected five accounts to deep-dive: Concord, Stran, Overture, Goldstar, Ball Pro
[notes section 10]. That selection was made by a human, from the same public universe, without
reference to this model. Compute Spearman correlation between the model's ranking and the
report's priority ordering over the 30 accounts. This is not ground truth - it is a second
opinion - but a model that ranks those five in the bottom half needs explaining.

**V2 - Component ablation.** Recompute the ranking six times, zeroing one component each time,
and report how far the top 10 moves. If zeroing a 15-point component changes nothing, that
component is decorative and should be cut or reweighted. This is a two-hour experiment that
tells a GTM leader more about the model than the rubric table does.

**V3 - Manual claim audit on the top five.** Every fact in those five briefs checked by hand
against its source. Report claim precision as a fraction, list every correction, and keep the
corrections in the repo. The single most credible number the project can produce is "of N
extracted facts in the top five briefs, M survived manual verification."

**V4 - Negative control.** Run five deliberately out-of-ICP companies through the full
pipeline: a law firm, a SaaS vendor, a restaurant group, a staffing agency, a regional bank.
Gate G1 should exclude all five with status `OUT_OF_ICP`. Any that reaches `WATCH` or above
means the segment classifier is broken, and that is worth discovering before anyone trusts a
ranking. Twenty minutes, and it turns "the model discriminates" from a claim into a result.

All four results go in `docs/VALIDATION.md` and are summarised in the findings memo,
**including if they are unflattering.**

---

## 12. Workflow coverage analysis

A by-product of scoring 30 accounts that is worth reporting on its own.

For each of the nine taxonomy workflows, count how often it appears as a hypothesis across the
portfolio, at what confidence, and concentrated in which scale bands and segments. Written to
`docs/COVERAGE.md`.

The output answers a question Trelium can act on: **which of its published agents can be
targeted from public evidence, and which cannot.** A workflow that is hypothesised for 26 of 30
accounts at `low` confidence is not a targeting signal - it is a description of the industry. A
workflow hypothesised for 6 accounts at `high` confidence is a campaign.

This also functions as a check on the taxonomy. If two workflows always co-occur, they are one
workflow for targeting purposes, whatever the product does.

---

## 13. Deduplication policy (scoring side)

Points are awarded per **distinct identity**, never per signal row. `signals.derive_signals`
merges duplicates before scoring (`EVIDENCE_MODEL.md` section 9); `_score_c3_stack` additionally
re-groups by normalised system name so a hand-built or externally supplied `SignalSet` cannot
inflate C3 by repeating a name. C2 dedupes by sub-signal enum, C5 by trigger type (with
`OPS_HIRING:<n>` counting distinct role titles), and C6's tier-1/2 fact count is a count of
distinct claims. Regression tests: `tests/test_signals_integrity.py`.

Before this policy a system named on two pages scored as two systems (6 + 2 instead of 6). That
bug shipped in the first 30-account run; no account in that run happened to trigger it, but it
was real. Recorded in `RESCORE_COMPARISON.md`.

## 14. Contradiction policy (scoring side)

Full policy in `EVIDENCE_MODEL.md` section 10. The scorer's part:

| `SignalSet.segment_conflict` | C1 effect | Flag |
|---|---|---|
| `none` | as section 3 | — |
| `resolved_by_tier` | as section 3, no penalty | `SEGMENT_CONFLICT_RESOLVED_BY_TIER` |
| `unresolved` | `(points * 4) // 5` | `SEGMENT_CONFLICT_UNRESOLVED` |

`SignalSet.scale_conflict` adds `SCALE_CONFLICT`; C4 is unchanged because the band already
follows the evidence hierarchy. Both conflicts always produce a research gap on the brief. The
scorer never sees the losing candidates' content, only the recorded conflict state, so it
remains a pure function of the `SignalSet`.
