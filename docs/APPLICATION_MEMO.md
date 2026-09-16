# I researched Trelium's ICP and built an account-research system to find workflows worth automating

One page. Repo: github.com/kanugurajesh/GTM. Everything below is either a verbatim quote with a
source or labelled as my reading. Workflow ideas about named companies are hypotheses to test on
a call, not claims about how those companies operate.

## What I understood about Trelium

Trelium's homepage describes "an AI agent-building platform for mid-market and enterprise teams
that need repetitive operational work completed across the software they already use", and
positions the product as "an execution layer for repeatable business processes where teams need
deterministic workflow steps, system updates, auditability, human review gates, and
organization-wide agent sharing" (trelium.com, retrieved 2026-09-16). The order-entry page puts
the whole thesis in one line: "Orders spread across emails and attachments become clean ERP
records."

My reading: the product is the layer between systems a promotional-products business already
runs, and the buyer is whoever owns a high-volume process that starts unstructured, crosses
systems and still needs a human for exceptions. So the GTM question is not "who uses AI" but
"where does information cross system boundaries inside this company", and the scarce resource
for an early team is knowing that before the discovery call. The line I kept coming back to is
Trelium's own split between reasoning and deterministic execution. I built the research tool on
the same split.

## What I built, and what it found

A pipeline that reads a company's public pages, keeps a claim only if it is a verbatim quote
from a stored snapshot, derives signals in code, scores fit with a pure integer function the
model never sees, and generates hedged workflow hypotheses from Trelium's nine published
agents, each with a question that would falsify it. Every brief lists what it could not find.

Run on 30 candidate accounts, twice, it answered its own question with a no:

- 19 of 30 sites blocked or defeated automated collection. Deeper crawling cannot help a site
  that blocks the homepage.
- 11 accounts scored. None above the deprioritise band. The two rubric components that describe
  Trelium's actual pain pattern, operational complexity and buying triggers, scored zero on
  every account.
- 22 of 26 facts in the top five briefs survived a by-hand audit. Six extraction defects were
  found by that auditing and each is now a deterministic check with a test.

The finding is about the market, not the prompt: public websites in this vertical do not say
how work gets done. Details in `docs/FINDINGS.md` and `docs/VALIDATION.md`.

## Five accounts by hand, held to the same standard

The memo proposed a second data source as the next experiment. I ran it manually on five
accounts, three the tool scored and two whose sites blocked it, using SEC filings, trade press
and job boards, and re-verified every quote against the live page with a script. Full notes with
sources in `docs/ACCOUNT_NOTES.md`.

| Account | Tool | Second source found | Worth probing |
|---|---|---|---|
| Showdown Displays (supplier) | 39/100, no hypothesis | Job posting: "Same day data entry of customer purchase orders into the system", "Order receipt can come in the form of e-mail, or phone" | Inbound PO to order entry |
| Stran (distributor, public) | 32/100 | 10-K: NetSuite ERP "launched in the first half of 2025", "Additional NetSuite phases will be planned", 154 full-time employees; a segment up 242.6% after an acquisition | PO entry into NetSuite; invoice matching |
| HALO (distributor) | 28/100 | New chief product and technology officer "to lead platform modernization"; internal AI assistant "across HALO systems" | Execution gap next to an in-house assistant; may be a build-not-buy |
| Geiger (distributor) | blocked, no score | At least twelve acquisitions in three countries, staff retained; unverified lead that AP already runs on an automation product | Invoice matching across acquired entities |
| Hit Promotional (supplier) | blocked, no score | Second fulfilment facility opening Q4 2026; CEO cites "AI-driven tools" | Order status across two sites |

Scorecard for the method: the site pass found operational-complexity evidence on 0 of 30
accounts; twenty minutes of hand research found it on 1 of 5, a dated 2026 trigger on 4 of 5,
and a sourced scale figure on 5 of 5. The two blocked accounts became researchable through trade
press alone. It also found a defect in my own tool: the top-scored account's scale points rest
on a subsidiary's headcount. That is recorded, not hidden.

## What I would do next

A licensed job-postings feed rather than a crawler, since the two most useful postings sit
behind robots.txt rules the tool honours; a stated prediction for what it does to the trigger
component; then a frontier deep-research product on the same five accounts, held to the same
verbatim-quote standard, with the two precision numbers published side by side.

## Caveats

None of these accounts has been checked against Trelium's CRM; de-duplicate before anyone is
contacted. ASI revenue figures are ASI Counselor-reported, not verified corporate revenue. This
is an unaffiliated application project and says so in its README.
