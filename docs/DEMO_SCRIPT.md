# Demo Script (60-90 seconds)

Recording is outside what I can produce directly; this is the script and the exact commands
to run live, timed to the structure the research report recommends
(`docs/TRELIUM_RESEARCH_NOTES.md` section 11).

---

**0:00-0:10**

"I saw Trelium was hiring someone who could independently execute GTM experiments, so instead of
only sending a resume, I built one."

**0:10-0:25** — show the input and a rejected claim live

```bash
trelium brief --company "Stran Promotional Solutions" --domain stran.com
```

"It fetches the company's own pages, and only keeps a claim if it's an exact quote from the
page. Watch — this one gets rejected." *(show a rejection in the terminal output / rejection log,
or point to a `research_gaps` line like "1/7 extracted claims failed verbatim-quote verification
and were discarded")*

**0:25-0:45** — show the output

Open `output/briefs/stran_com.md`. Walk through: fit score and component breakdown, the ranked
workflow hypothesis with its confidence and validation question, the numbered evidence with
source URLs and retrieval dates, the research-gaps section, the CRM de-duplication banner.

"Score, evidence, and hypothesis are three separate sections because they're three different
kinds of claim, and the renderer literally cannot put a hypothesis in the facts section — they're
different types in the code, not just different headings."

**0:45-1:00** — show the deterministic core

```bash
trelium score --from output/briefs/stran_com.json
```

"Same number, every time, computed from stored signals with zero model calls. I use the model
for messy interpretation and keep scoring, evidence verification, and the workflow taxonomy
fully deterministic — the same reasoning-versus-execution split Trelium's own materials describe
for their agents."

**1:00-1:20** — show the scale of the run and the validation

"I ran this across 30 real candidate accounts from independent industry research, plus a
negative-control batch of five companies that are obviously outside the ICP — a law firm, a SaaS
company, a bank — to check the model doesn't falsely qualify them. It didn't: 5 for 5."

"The most useful thing I found wasn't a good lead. It was that public homepage content alone
failed to collect anything usable for about two-thirds of these accounts — mostly sites blocking
automated access — and when it did work, it almost never surfaced Trelium's own core PO-to-order
-entry pattern from a homepage alone. That's a finding about the method, and it's in the README."

**1:20-1:30**

"Repo, findings memo, and the two bugs I found and fixed while manually auditing the output are
all in the readme. Thanks for reading this far."

---

## Backup timing (if something doesn't load live)

Have these three files open in tabs beforehand:
- `output/briefs/stran_com.md` (or whichever account scored highest in the final run — check
  `docs/RANKING.md`)
- `docs/FINDINGS.md`
- `docs/VALIDATION_V4.md`
