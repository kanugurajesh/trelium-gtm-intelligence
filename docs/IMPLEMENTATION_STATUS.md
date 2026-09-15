# Implementation Status

Read alongside `docs/PROJECT_SPEC.md` (the plan), `docs/FINDINGS.md` (what running it produced)
and `docs/RESCORE_COMPARISON.md` (effect of the correctness-hardening pass on the committed
dataset). This file records what exists right now.

Last updated: after the CORRECTNESS HARDENING phase (dedup + contradiction policy). 190 tests.

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
| Live web collection | COMPLETE, narrow | `collect.py`: real `httpx` fetches, robots.txt respected, about/careers link discovery | Only 1-3 pages per account; no PPAI/job-board/news/exec-content sources | Deepen source collection (deferred by instruction) |
| OpenAI extraction | COMPLETE, no failure handling | `extract.py`: verbatim-quote-only, E2-verified, taxonomy-constrained, numeric-field guards | No try/except around the API call or `json.loads` | Provider hardening (deferred by instruction) |
| Workflow hypothesis generation | COMPLETE, no failure handling | `hypothesise.py` | Same as extraction | Same |
| Hedging linter | COMPLETE | `lint.py` | None found | None |
| Persona lookup | COMPLETE | `persona.py` | None found | None |
| Rendering (Markdown/JSON) | COMPLETE | `render/`; conflict flags render via the existing flags line, conflict detail via research gaps | No HTML renderer (deliberate cut) | None |
| Pipeline orchestration | COMPLETE | `pipeline.py`; now appends `signals.conflict_gaps` to every brief | One failed source still aborts the whole account | Provider hardening (deferred) |
| CLI | COMPLETE | `cli.py`: `brief`, `score`, `run-all`, `rank` | `brief` lacks the per-account try/except `run-all` has | Provider hardening (deferred) |
| Offline re-score | COMPLETE | `scripts/rescore_existing.py`: re-derives + re-scores committed briefs with no fetch and no model call; deterministic `as_of` from evidence retrieval date | None | None |
| LLM cache (offline reproducibility) | COMPLETE, verified live | `llm_cache.py` | None | None |
| CSV dataset (30 accounts) | COMPLETE | `data/prospects.csv`, domains verified by search | None | None |
| Test suite | 190 tests | `tests/` incl. new `test_signals_integrity.py` (24) and a pipeline conflict test | Still no tests for: provider failures, malformed/non-JSON model output | Provider hardening (deferred) |
| Web UI / server | NOT BUILT | — | N/A | Deliberately out of scope |
| Findings/validation docs | COMPLETE | `FINDINGS.md`, `VALIDATION.md` (rho updated to −0.045), `VALIDATION_V4.md`, `COVERAGE.md`, `RANKING.md` (regenerated), `RESCORE_COMPARISON.md` (new) | None | None |

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
