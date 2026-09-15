# CLAUDE.md - Permanent project rules

Rules for all future work in this repository. They are not style preferences. Each one exists
because breaking it destroys the project's central claim: that this tool's output can be
trusted without re-checking it.

Read alongside `docs/PROJECT_SPEC.md`, `docs/EVIDENCE_MODEL.md` and `docs/SCORING.md`.

---

## 1. Truthfulness

**R1. Never fabricate company information.** No invented revenue, headcount, system names,
customers, quotes, executives, locations or dates. If a fact is not in the evidence corpus, it
does not exist. An empty field is a correct output; a plausible guess is a defect.

**R2. Never represent a workflow hypothesis as a known fact.** "Stran manually enters purchase
orders" is forbidden. "Inbound PO to order entry is worth investigating at Stran, because X and
Y" is correct. This is the distinction the whole project exists to demonstrate.

**R3. Preserve source provenance.** Every fact carries at least one evidence id resolving to a
committed snapshot with a URL, a retrieval date and a verbatim quote. A fact that loses its
provenance is deleted, not repaired.

**R4. Never let an inference become a fact.** Not by rewording, not by summarising, not by
promoting a high-confidence inference. The one-hop rule holds: inferences derive from facts,
never from other inferences.

**R5. Never invent evidence to satisfy a schema.** If a required field has no support, emit the
gap. Do not write a placeholder quote, a synthetic URL or a stand-in date to make validation
pass.

**R6. Do not soften uncertainty in prose.** Research gaps, low evidence grades and rejected
claims are published output, not blemishes to be tidied.

---

## 2. Separation of model and code

**R7. LLM interpretation and deterministic scoring stay separate.** The model produces
evidence-linked signals. `score()` is a pure function of those signals. The model never sees
point values and never emits a score, a rank or a band.

**R8. The scorer stays pure.** No I/O, no network, no model calls, no clock reads, no
randomness, no floats. Integers only. If a change to `scoring.py` requires any of those, the
change is wrong.

**R9. `model_confidence` is recorded and never read by scoring.** It exists so validation can
measure the model's calibration. A test asserts that mutating it changes no score.

**R10. No unsourced signal scores.** Hard rule H1 in `docs/SCORING.md`. A signal with empty or
unresolvable evidence contributes zero, enforced at construction and re-checked at scoring time.

**R11. The workflow taxonomy is closed.** Nine workflows, in `taxonomy.py`, each mapped to a
published Trelium agent. The model selects from it and cannot extend it. Adding a workflow is a
human decision that updates `docs/ICP.md` first.

---

## 3. Testing

**R12. Tests cover deterministic business logic.** Scoring, ranking, evidence verification,
signal derivation, schema invariants and the hedging linter. Every component boundary and both
sides of every threshold.

**R13. Do not write tests that call the LLM.** Model behaviour is measured in the validation
pass, not asserted in unit tests. Tests must pass offline with no API key.

**R14. Invariants are tests, not comments.** F1, F2, F3, I1, I2, I3, E1, E2, H1, H2, H3 from
`docs/EVIDENCE_MODEL.md` and `docs/SCORING.md` each have a test that fails when violated.

**R15. A scoring change requires a test change in the same commit.** Numbers that drift
untested are numbers nobody should act on.

---

## 4. Scope

**R16. Prefer useful GTM output over interface complexity.** Time spent on a brief's substance
beats time spent on its appearance, every time.

**R17. Keep the project small and finishable.** Never build: authentication, users, billing,
organisations, a database, a CRM or CRM sync, chat, a web server or API, a scheduler, a React
or Next.js app, a vector store or RAG layer, contact enrichment, multi-tenancy, Docker, CI,
telemetry. The list in `docs/PROJECT_SPEC.md` section 8 is exhaustive and closed.

**R18. Do not add features because they are technically impressive.** Impressiveness is not the
evaluation criterion. Whether a founder can act on a brief is.

**R19. Every major feature must support the application experiment.** If a change does not make
a brief more trustworthy, more actionable or more reproducible, it does not belong.

**R20. Consult the cut list before adding anything under time pressure.**
`docs/IMPLEMENTATION_PLAN.md` fixes what gets cut and in what order. Phase 1 tests, the E2
substring check, the hedging linter, the manual audit and the research gaps section are never
cut.

---

## 5. Data collection

**R21. Public sources only.** No logins, no paywalls, no credential use, no circumvention of
any access control.

**R22. Respect robots.txt and rate limits.** One request at a time, descriptive user agent. If
a site blocks automated access, record the gap and move on. Never route around a block.

**R23. No personal contact data.** Roles and titles only. No personal emails, phone numbers or
direct messages collected, stored or inferred. Per the research report [notes section 12].

**R24. Third-party figures stay attributed.** PPAI 100 numbers are cited as PPAI-reported 2025
promotional-products revenue, never as verified corporate revenue, and never reproduced in bulk.

**R25. Snapshots store extracted text, not full site mirrors.** With URL and retrieval date, for
verification only.

---

## 6. Outbound and real-world safety

**R26. The codebase must contain no capability to contact anyone.** No email sending, no form
submission, no messaging integration, no webhook that could reach a prospect. This is a design
constraint, not an unimplemented feature.

**R27. Never send outbound to Trelium's prospects.** Not as a test, not as a demonstration, not
"just one". The research report prohibits it explicitly [notes section 12] and it would damage
a company the author does not work for.

**R28. Every brief carries the CRM de-duplication banner.** The tool cannot know Trelium's
pipeline. The banner is non-removable and unconditional.

**R29. Do not generate fake Trelium customer data, fake testimonials or fake case studies.**
Not for fixtures, not for demos. Test fixtures use obviously synthetic company names such as
`ACME_TEST_DISTRIBUTOR`.

**R30. Never claim or imply endorsement by Trelium, PPAI or any named company.** This is an
unaffiliated application project and says so in the README.

---

## 7. Framing

**R31. This is an internal-style GTM research utility, not a Trelium product replica.** Do not
build agent execution, integrations or workflow automation. The report warns against appearing
to replicate Trelium [notes section 11].

**R32. Hypotheses about accounts stay hypotheses in every artifact.** README, memo, demo script
and commit messages included.

**R33. No AI-generated flattery in any output.** No "doing amazing things in promotional
products." Outreach angles state a hypothesis and a question, nothing else.

**R34. Report results faithfully, including bad ones.** If claim precision is 71%, publish 71%.
If the ranking correlates poorly with the report's independent picks, publish that and explain
it. An honest negative result is the most credible thing this project can produce.

**R35. Do not claim proficiency in prose.** No "excellent with Claude Code" anywhere. The
artifact is the claim [notes section 12].

---

## 8. Working conventions

- Python 3.13, pydantic v2, pytest, argparse. No new runtime dependency without a reason
  recorded in the commit message.
- Pure functions in `scoring.py`, `ranking.py`, `signals.py`, `evidence/verify.py`. Side effects
  confined to `collect.py`, `llm_cache.py`, `render/` and `cli.py`.
- LLM responses are content-addressed by prompt hash and committed, so the pipeline runs offline
  with no API key.
- Docs lead code. Changing the ICP, the taxonomy or the rubric means editing `docs/ICP.md` or
  `docs/SCORING.md` in the same commit.
- Commit messages describe the decision, not just the change.
- Do not commit an `OPENAI_API_KEY` or any credential.
