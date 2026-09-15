# Implementation Status

Read alongside `docs/PROJECT_SPEC.md` (the plan), `docs/FINDINGS.md` (what running it produced)
and `docs/RESCORE_COMPARISON.md` (effect of the correctness-hardening pass on the committed
dataset). This file records what exists right now.

Last updated: after the DEEPER COLLECTION pass (`docs/DEEP_COLLECTION.md`). 224 tests.

---

## Status table

| Component | Status | Implementation | Problems | Next action |
|---|---|---|---|---|
| Typed schema (Fact/Inference/Evidence/Signal/Brief) | COMPLETE | `models.py`; `SignalSet` now also carries `segment_candidates`, `segment_conflict`, `scale_candidates`, `scale_conflict` | None found | None |
| Workflow/segment/scale/trigger taxonomy | COMPLETE | `taxonomy.py`, frozen data, closed enums | None found | None |
| Deterministic scorer | COMPLETE | `scoring.py`, pure function, 44 tests + integrity suite | **Fixed this phase:** C3 counted a system named on two pages as two systems. Now groups by normalised name defensively (SCORING.md §13). C1 applies the unresolved-conflict penalty (§14) | None |
| Deterministic ranking | COMPLETE | `ranking.py`, 5-step tie-break | None found | None |
| Evidence store + E1/E2 verifier | COMPLETE | `evidence/store.py`, `evidence/verify.py`, 19 tests | `append_index_record`/`load_index` still unused dead code (unchanged, harmless) | Wire in or delete, low priority |
| Signal derivation | COMPLETE | `signals.py`, rewritten: one merged signal per normalised identity, provenance = sorted union, explicit contradiction policy, order-independent | **Fixed this phase:** first-seen-wins on conflicting segments; per-fact (not per-identity) signals inflating C2/C3/C5/C6 | None. Known limit: no fuzzy aliasing by design (EVIDENCE_MODEL.md §9) |
| Live web collection | COMPLETE | `collect.py`: real `httpx` fetches, robots.txt respected, token-based link discovery for about / careers / technology-integrations / press-news / services pages (up to 6 requests per account, spaced), content-addressed snapshots (`src_<url>_<content>.txt`, a changed page never overwrites an earlier brief's snapshot), homepage fetched once and reused by the pipeline | Same-domain only; no PPAI / job-board / exec-content sources; JS-rendered and bot-protected sites still fail (19 of 30) | A second data source, not more crawling (`docs/FINDINGS.md` finding D) |
| OpenAI extraction | COMPLETE, no failure handling | `extract.py`: verbatim-quote-only, E2-verified, taxonomy-constrained; deterministic post-checks for revenue, headcount, quote-dated recency (`published_at` from the latest year the quote names), whose-system context (punch-out / second-person framing) and segment role-word support | No try/except around the API call or `json.loads` | Provider hardening (deferred by instruction) |
| Workflow hypothesis generation | COMPLETE, no failure handling | `hypothesise.py` | Same as extraction | Same |
| Hedging linter | COMPLETE | `lint.py` | None found | None |
| Persona lookup | COMPLETE | `persona.py` | None found | None |
| Rendering (Markdown/JSON) | COMPLETE | `render/`; conflict flags render via the existing flags line, conflict detail via research gaps | No HTML renderer (deliberate cut) | None |
| Pipeline orchestration | COMPLETE | `pipeline.py`; appends conflict gaps, collection failures and zero-yield pages ("Read <url>: no extractable claims") to every brief; accepts prefetched sources; spaces live requests | One failed source still aborts the whole account | Provider hardening (deferred) |
| CLI | COMPLETE | `cli.py`: `brief`, `score`, `run-all`, `rank`; `brief` pins the company name to `data/prospects.csv` when the domain matches, so a one-off run reproduces the batch's cache keys; `--delay` applies between page requests | `brief` lacks the per-account try/except `run-all` has | Provider hardening (deferred) |
| Offline re-score | COMPLETE | `scripts/rescore_existing.py`: re-derives + re-scores committed briefs with no fetch and no model call; deterministic `as_of` from evidence retrieval date | None | None |
| LLM cache (offline reproducibility) | COMPLETE, verified live | `llm_cache.py` | None | None |
| CSV dataset (30 accounts) | COMPLETE | `data/prospects.csv`, domains verified by search | None | None |
| Test suite | 224 tests | `tests/` incl. `test_collect.py` (discovery, E1 preservation across passes), `test_recency.py`, `test_system_context.py`, `test_segment_support.py` | Still no tests for: provider failures, malformed/non-JSON model output | Provider hardening (deferred) |
| Web UI / server | NOT BUILT | — | N/A | Deliberately out of scope |
| Findings/validation docs | COMPLETE | `FINDINGS.md` (finding D added), `VALIDATION.md` (re-run on pass 2), `VALIDATION_V4.md`, `COVERAGE.md`, `RANKING.md`, `DEEP_COLLECTION.md` (pass 1 vs pass 2), `RESCORE_COMPARISON.md` (historical) | None | None |

---

## Effect of the correctness-hardening pass on the committed 30-account dataset

Re-scored offline from committed facts/evidence (`docs/RESCORE_COMPARISON.md`):

| Account | Old | New | Why |
|---|---|---|---|
| Concord Marketing Solutions | 29 | 24 | Its own pages claim both "distributor" and "supplier" at equal tier → `SEGMENT_CONFLICT_UNRESOLVED`, C1 25→20, gap emitted. Rank 3 → 6 |
| Stran Promotional Solutions | 29 | 28 | Duplicate tier-1 claims (same statement from two URL variants of one page) now count once for C6 (4→3). Rank unchanged |
| High Caliber Line / Hirsch | unchanged | unchanged | Moved up one rank each (5→3, 6→5) purely because Concord dropped |
| All other 26 | unchanged | unchanged | — |

V1 rank correlation with the report's independent priority order moved from 0.182 to −0.045:
the report's #1 pick is the account with the contradiction. V2 ablation unchanged (c1: 1,
c6: 1, others 0). Workflow hypotheses and coverage untouched (no model calls were made).

---

## Effect of the deeper-collection pass on the 30-account dataset

Full data in `docs/DEEP_COLLECTION.md`; interpretation in `docs/FINDINGS.md` finding B and D.
Homepage-only briefs are archived in `output/briefs_pass1_homepage/`.

| Measure | Homepage-only | Deeper pages |
|---|---|---|
| Accounts scored / insufficient evidence | 11 / 19 | 11 / 19 |
| Pages read | 16 | 44 |
| Verified facts | 33 | 50 |
| Accounts with a workflow hypothesis | 3 | 6 |
| Scored accounts with c2 (ops complexity) or c5 (trigger) > 0 | 0 | 0 |
| Highest score | 39 | 39 |
| Rank correlation with the report's order (n=11) | −0.045 | 0.400 |
| Claim precision, top five briefs, audited by hand | 8/10 (top three) | 22/26 |

Four extraction defects were found on this pass and fixed in code with tests, each one a
verbatim quote whose meaning was misread: a 2015 headline scored as a live growth trigger
(recency now derives from a year the quote names); a list of customers' punch-out systems
scored as the company's own ERP stack (whose-system context guard); segment labels attached to
quotes that never state the role (role-word guard, which is what `docs/SCORING.md` section 3
had specified all along); and one sentence rendered six times (fact-level dedupe). The
segment guard moved four accounts out of the top ten (SanMar 35→10, Ball Pro 30→5, Staples
28→3, High Caliber Line 28→3) — those scores had rested on unsupported segment claims.

---

## Remaining correctness risks (not addressed in this phase, by instruction)

1. **Provider failures / malformed model output** are unhandled at the two OpenAI call sites.
2. **Semantic mis-support** (a verbatim quote that does not actually support its claim, e.g.
   Concord row 7 in `VALIDATION.md` V3) is detectable only when it produces a *contradiction*;
   a single unsupported claim with no competing claim still passes.
3. **Exact-match normalisation** will treat spelling variants of one system as two systems
   until an alias is added to the taxonomy — a false negative on deduplication, never a false
   positive.
4. **Scale conflicts are flagged but not penalised**; if both figures are wrong the flag is the
   only signal.
