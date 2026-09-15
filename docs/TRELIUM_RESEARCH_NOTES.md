# Trelium Research Notes

Source: `research/Trelium Deep Research and Application Strategy.pdf` (35 pages).
Page references below are written as `[p.N]` and refer to that PDF's printed page numbers,
which match its physical page order.

> **Epistemic status of this file.** The PDF is itself a research report written by an
> analyst, not a primary source. Everything here is therefore *at best* second-hand.
> This file separates three tiers:
>
> - **[R-VERIFIED]** - the report states this as fact and attributes it to a named public
>   source (Trelium's site, YC, PPAI, a LinkedIn post). Still requires re-verification
>   against the primary source before being used as a project fact.
> - **[R-INFERRED]** - the report explicitly labels this as its own inference,
>   interpretation, or hypothesis.
> - **[R-UNSOURCED]** - the report asserts it without attribution. Treat as opinion.
>
> No claim in this file may be copied into a generated account brief as a `Fact`.
> Briefs draw facts only from the project's own evidence corpus. See `EVIDENCE_MODEL.md`.

---

## 1. What Trelium does

**[R-VERIFIED]** Trelium positions itself as an AI-agent platform that executes repetitive
operational work across email, PDFs, spreadsheets, ERPs, CRMs and browser applications.
Named example workflows: order entry, quotation, invoice matching, customer updates,
approval routing, reporting. [p.1]

**[R-VERIFIED]** The product pattern is described as: unstructured input -> interpretation ->
business rules -> system actions -> exception handling -> audit trail. [p.2]

**[R-VERIFIED]** Trelium's public use-case library lists 29 agents, including business
reporting, company-store-to-ERP sync, invoice follow-up, invoice matching, margin analysis,
distributor order entry, order-status updates, PO creation and PO entry. [p.2]

**[R-VERIFIED]** Workflow catalogue given in the report [p.3]:

| Workflow | Starting point | Trelium action | Outcome |
|---|---|---|---|
| Order entry | Email, PDF, form | Extract SKUs, quantities, decoration/shipping details; enter into order system | Less manual PO transcription |
| Invoice matching | Supplier invoice | Compare invoice to order/PO, flag discrepancies | Finance reviews exceptions only |
| Order status | Customer request | Look up status/tracking, update systems, prepare reply | Less status chasing |
| Quoting | Email/request form | Retrieve product/inventory/pricing, apply rules, build quote | Faster response |
| Reporting | ERP/accounting/CRM | Aggregate and send recurring report | Less report assembly |
| Supplier purchasing | Approved customer order | Validate item/inventory/pricing/supplier rules, create supplier order | Fewer purchasing errors |
| Invoice follow-up | Accounting data | Detect overdue invoices, send contextual follow-ups | Less AR chasing |
| Proposal follow-up | CRM/SAGE/commonsku | Track open opportunities, trigger follow-ups | Less post-quote leakage |

**[R-VERIFIED]** Trelium is selling the workflow layer *between* existing systems, not
replacing them. The SanMar/S&S material is cited as the clearest statement: supplier systems
already expose product, inventory, price, order, invoice and shipment data; the hard part is
connecting those facts into email -> supplier -> quoting -> ERP -> accounting -> customer
communication. [p.3]

### Product philosophy [p.3-4]

- **[R-VERIFIED]** Natural-language workflow construction rather than manual integration programming.
- **[R-VERIFIED]** **Deterministic execution where possible** - Trelium's materials explicitly
  distinguish reasoning from predictable software actions, using AI where judgment is required
  and deterministic steps where it is not. *This is the single most important line in the PDF
  for our architecture. See section 9.*
- **[R-VERIFIED]** Cross-system execution: NetSuite, QuickBooks, Salesforce, SAP, Oracle,
  HubSpot, Printavo, ShopWorks, Gmail, Outlook, Slack; 3,000+ integrations advertised plus
  browser automation where no API exists.
- **[R-VERIFIED]** Human review gates, run history, exception escalation - not unsupervised autonomy.
- **[R-VERIFIED]** Organization-wide workflows, not individual copilots.

---

## 2. Company and stage

**[R-VERIFIED]** San Francisco based, YC Fall 2025, founded 2025. [p.1, p.4]

**[R-VERIFIED]** YC lists Abhimanyu Yadav as CEO and Ritanshu Dokania as co-founder. YC job
pages label Ritanshu CTO; newer Trelium materials list him as COO. The report flags the public
sources as out of sync and advises not asserting an exact title or headcount. [p.2]

**[R-VERIFIED]** Origin: a Sept-2025 launch-era post described Questom/Trelium as AI sales and
support for commercial printing, targeting lost leads and manual follow-up; YC launch material
described inbound B2B sales agents across phone, email, chat and SMS. [p.2]

**[R-INFERRED]** Trajectory reads as *narrow vertical customer problem -> broader workflow
platform*, not a company that stayed an inbound-sales agent. [p.2]

**[R-VERIFIED]** Trelium is a PPAI-recognized solution provider and has said it is starting
close to promotional products, print and custom merchandise before expanding into other
manual-work-heavy industries. [p.2]

**[R-VERIFIED]** Publicly listed customers include Vapor Apparel, Vantage, HPG, Numo, iPromo,
Brand Fuel, Icebox Cool Stuff. [p.5]

**[R-INFERRED]** Current strategy: win one operations-heavy vertical deeply, embed across many
of its core workflows, then expand the platform beyond it. [p.5]

### Business model

**[R-VERIFIED]** Public pricing: Starter about $500/mo, Growth about $1,000/mo, Supreme about
$2,000/mo, plus custom Enterprise. Plans allocate credits consumed by building and running
agents, and correspond roughly to a number of workflows/agents. [p.4]

**[R-INFERRED]** The economic sale is "this recurring process costs more in employee time than
automating it costs", not "buy AI". Trelium publishes workflow-level AI cost/ROI content. [p.4]

> **Project consequence.** A $500-$2,000/month price point is mid-market pricing. This is the
> basis for the non-monotonic scale scoring in `SCORING.md` section 4 - a $1B distributor is
> not automatically a better account than a $150M one for an early-stage company with
> founder-led sales capacity.

---

## 3. ICP as the report frames it

**[R-VERIFIED]** Broad ICP stated on Trelium's site: mid-market and enterprise organizations
with repetitive work spanning email, documents, spreadsheets and multiple systems of record. [p.5]

**[R-INFERRED]** Highest-confidence current vertical ICP: North American promotional-products
distributors, suppliers, decorators, print shops and related merchandise businesses processing
substantial volumes of quotes, POs, orders, supplier interactions, invoices and status requests
across fragmented software. [p.5]

Report's ICP table [p.5-6]:

| Dimension | Working hypothesis | Tier |
|---|---|---|
| Industry | Promotional products first; also manufacturing and other operations-heavy sectors | [R-VERIFIED] targeting, [R-INFERRED] prioritisation |
| Scale | Mid-market and enterprise; enough transaction volume to justify recurring automation | [R-VERIFIED] site language |
| Geography | U.S./Canada safest initial target | [R-INFERRED] |
| Systems | SAGE, commonsku, ShopWorks, Printavo, NetSuite, QuickBooks, Gmail/Outlook, supplier APIs; multiple disconnected systems is a strong fit signal | [R-VERIFIED] system names |
| Work | Quoting, PO intake, order entry, supplier purchasing, status updates, invoice matching, AR, reporting | [R-VERIFIED] |
| Users | Ops, finance/AP/AR, customer service, sales ops | [R-VERIFIED] |
| Buyer | COO/CEO at smaller firms; VP Ops / CFO / technology / transformation leaders at larger ones | **[R-INFERRED]** - the report labels this an inference |

**[R-VERIFIED]** Public testimonials include CFO, CEO and chief-experience leadership. [p.6]

### The strongest pain pattern [p.6]

The report's sharpest analytical point, and the one the scoring model is built around:

> The best Trelium customer probably does not merely have "manual work." Almost every company
> has manual work. The stronger signal is: **a high-volume process that begins with messy or
> unstructured information, crosses several software systems, has repeatable business rules,
> and still requires humans to handle exceptions.**

Canonical example flow [p.6-7]: customer email -> PDF/Excel PO -> extract item, quantity,
artwork, shipping -> check supplier data -> apply pricing/margin/inventory rules -> create
order in ShopWorks/ERP -> attach files -> update spreadsheet/CRM -> confirm with customer.

**[R-VERIFIED]** Trelium publicly describes an active pattern very close to this using incoming
order emails, PDF/Excel attachments, SanMar data, ShopWorks and Google Sheets. [p.7]

**Research question the report derives** [p.7] - adopted verbatim as this project's core question:

> Not "does this company use AI?" but **"where does information cross system boundaries inside
> this company?"**

---

## 4. Buying triggers

**[R-INFERRED]** - the report states plainly that these are its inferences from Trelium's
marketed workflows, not confirmed Trelium qualification criteria. [p.7]

| Trigger | Rationale |
|---|---|
| Rapid company growth | Transaction volume may outgrow operations headcount |
| Acquisition / integration | Duplicate processes and legacy systems |
| New ERP / order platform | Migration exposes process inefficiency |
| High customer-service volume | Repeated status/quote requests become automation candidates |
| Large supplier ecosystem | More inventory/pricing/status checks across systems |
| Hiring ops / order-entry / AP roles | Possible signal of rising manual workload |
| Multiple systems named publicly | Cross-system movement is exactly Trelium's value proposition |
| High quotation volume | Connects automation to revenue, not just cost |
| Complex invoice reconciliation | Measurable labour and accuracy value |
| Margin pressure | Cost reduction easier to justify |

---

## 5. Personas [p.8]

**[R-INFERRED]** throughout. The report's instruction is to identify *roles*, not personal
emails, and to explain why that role is likely to own the workflow.

- **Distributors** - COO / VP Operations; President/CEO at smaller firms; VP Technology; Sales Operations; Finance/CFO.
- **Suppliers** - VP Operations; Customer Experience/Service leadership; Finance/AP; CIO/VP Technology.
- **Decorators / print shops** - owner/CEO; operations manager; production or customer-experience leader.

---

## 6. GTM motion

- **[R-VERIFIED]** Founder-led selling and customer discovery; founders publicly documented
  deciding to attend industry conferences on very short notice to meet customers. [p.5, p.8]
- **[R-VERIFIED]** Frequent vertical-specific content: NetSuite automation, AI workflow ROI,
  SAGE, SanMar/S&S, Claude Cowork, Syncore. **[R-INFERRED]** that this is a deliberate SEO
  program, though the structure is compatible with SEO-led demand generation. [p.9]
- **[R-VERIFIED]** Events and community participation in the print/promo ecosystem. [p.9]
- **[R-VERIFIED]** Public partner motion aimed at implementation firms, integrators and service
  providers. **[R-INFERRED]** that this is a meaningful second route to market. [p.9]
- **[R-INFERRED]** Weak evidence of self-serve PLG. Pricing is public but the conversion flow
  pushes toward a human, including a 30-minute session where Trelium automates one of the
  prospect's real workflows in their real tools rather than presenting slides. Motion reads as
  sales/demo-led. [p.9-10]
- **[R-UNSOURCED / anecdotal]** Referral behaviour exists informally; no public formal referral
  program found. [p.10]

> **Project consequence.** The "we'll automate one of your actual workflows in 30 minutes"
> demo is the conversion event. So the highest-value GTM artifact is not a lead list - it is
> *a defensible guess at which single workflow to put on the table in that 30 minutes.*
> This is the product thesis of the tool. See `PROJECT_SPEC.md` section 2.

---

## 7. Founder and hiring signals [p.10]

- **[R-VERIFIED]** A separate Trelium hiring post sought people who "don't wait to be told what
  to do" and GTM hires willing to try unconventional experiments.
- **[R-VERIFIED]** Founders publicly described abrupt decisions to attend conferences to learn
  and meet customers - speed under incomplete information.
- **[R-VERIFIED]** Ritanshu's product content is concrete and operational (actual print-shop
  quotation behaviour) rather than abstract AI language.
- **[R-VERIFIED]** Ritanshu publicly criticised candidates who no-showed or handled rejection
  poorly. **[R-INFERRED]** that "reliable" in the job post is not filler.
- **[R-VERIFIED]** The YC announcement framed the founders' archetype around stability and
  persistence.

---

## 8. Competitive positioning [p.11-12]

| Alternative | Its strength | Report's read on Trelium's difference | Tier |
|---|---|---|---|
| Zapier | 9,000+ connections, broad no-code automation, AI agents | Trelium emphasises complete operational jobs and vertical workflows over a general toolkit | [R-VERIFIED] (partly Trelium's own comparison page) |
| n8n | Flexible workflow automation, AI agents, human approvals, self-host | Trelium aimed at business operators describing a process, not technical teams assembling one | [R-INFERRED] |
| UiPath | Mature enterprise automation plus agents plus governance | Trelium's edge is speed, simplicity and vertical knowledge for mid-market ops | [R-INFERRED] |
| Salesforce Agentforce | Agents deep inside Salesforce's ecosystem | Trelium is system-agnostic rather than CRM-centred | [R-VERIFIED] positioning, [R-INFERRED] advantage |
| Custom integrations | Maximum control, direct APIs | Trelium argues the recurring cost is the engineering and maintenance burden of turning APIs into complete processes | [R-VERIFIED] via the SanMar/S&S article |

**[R-VERIFIED] caution from the report:** the category is converging. UiPath combines agents
with deterministic workflows, n8n supports human review, Zapier has AI agents. "Trelium has AI
agents and competitors don't" is *not* a defensible thesis. [p.11]

**[R-INFERRED]** The credible differentiation is the combination: business-user workflow
definition + cross-system execution + deterministic controls + human exception handling +
aggressive verticalisation around operational workflows. [p.11-12]

---

## 9. GTM experiments proposed [p.12-13]

Ranked by the report's own judgment, explicitly **not** Trelium's roadmap.

| # | Experiment | Impact | Difficulty | Executable without internal access? |
|---|---|---|---|---|
| 1 | Workflow Opportunity Audit outbound - personalised one-page workflow hypothesis per target | Very high | Medium | Research yes; **sending, no** (see section 12) |
| 2 | **PPAI Account Intelligence Engine - score distributors/suppliers on workflow, stack and growth signals** | Very high | Medium | **Yes** |
| 3 | Five-account video teardown | High | Medium | Yes |
| 4 | SAGE/commonsku/ShopWorks signal outbound | High | Medium | Partially |
| 5 | Partner activation sprint | High | Medium | Yes |
| 6 | "Bring us your worst workflow" clinic | High | Medium | No (needs Trelium to host) |
| 7 | Trigger-based account watchlist | Med-high | Medium | Yes |
| 8 | ROI-first outbound | Med-high | Low | Partially |
| 9 | Customer workflow expansion audit | Very high potential | Medium | **No - needs customer and product data** |
| 10 | Customer proof / referral flywheel | Med-high | Medium | No |

**[R-VERIFIED, report's own words]** "The first two are best for your application because they
require no internal Trelium access." #9 has the highest potential business value but cannot be
genuinely executed pre-hire. [p.13]

### The report's architecture instruction [p.22-23]

**Use the LLM for:** categorising segment, summarising business model, interpreting public
operational clues, inferring likely workflows, producing discovery questions, explaining fit,
generating outreach angles, distinguishing fact from hypothesis.

**Keep deterministic:** "Do not let the LLM arbitrarily produce the final score." Explicit
rubric, then implement rules. Rubric: core vertical fit 25 / operational complexity 20 /
software-ecosystem signals 15 / transaction scale 15 / growth trigger 15 / evidence quality 10.

The report notes this mirrors Trelium's own reasoning-versus-deterministic-execution split
[p.23] and says to point that out in the README. Our critique of the *exact rules* it proposes
is in `SCORING.md` section 1.

### Evidence discipline [p.13, p.25-26]

Source hierarchy, strongest first: company website -> industry associations, filings and
reputable databases -> job descriptions -> executive public content -> reliable third-party
reporting -> search snippets.

Mandated separation, with the report's own worked example:

```
FACT:                Company is a PPAI-ranked distributor.
INFERENCE:           Order-entry automation may be relevant because of its scale/industry.
VALIDATION QUESTION: How are emailed purchase orders currently moved into the
                     order-management system?
```

And the report's warning about its own prospect table [p.20-21]: it does **not** claim "Concord
manually enters every order" - it claims "Concord has characteristics that make order-entry
process scaling worth investigating."

---

## 10. Prospect research [p.14-21]

**[R-VERIFIED] method caveats stated by the report - all of which bind this project:**

1. Trelium's publicly displayed customer logos were screened out first, but the website is
   unlikely to represent every customer or active opportunity. **All accounts must be
   de-duplicated against Trelium's CRM before anyone is contacted.** [p.14]
2. Size figures are **2025 promotional-products revenue reported or estimated in the 2026
   PPAI 100** - not total corporate revenue in every case. [p.14]
3. The priority ranking is the report author's estimate of research attractiveness,
   **not PPAI's rank**. [p.14]

30 candidates are listed, each with segment, approximate promo size, fit hypothesis, workflow
hypothesis and persona angle. Summary [p.14-20]:

- **Distributors (1-15):** Concord Marketing Solutions ~$87M; Stran ~$116M; Overture ~$192M;
  iPROMOTEu ~$372M *(report notes it is distinct from iPromo, which is a public Trelium customer)*;
  American Solutions for Business ~$335M; BDA ~$551M; Geiger ~$370M; HH Global ~$457M;
  Proforma ~$668M; LeaderPromos ~$59M; Nadel ~$225M; G&G Outfitters ~$96M; HALO ~$964M;
  Staples Promotional Products ~$930M (est.); 4imprint ~$1.3B *(report flags likely substantial
  existing automation, so fit is less certain)*.
- **Suppliers (16-30):** Hit Promotional ~$733M; Goldstar ~$98M; Showdown Displays ~$150M;
  Ariel Premium Supply ~$131M; The Magnet Group ~$130M; Hirsch ~$59M; Ball Pro ~$43M
  *(exceptionally high reported growth)*; High Caliber Line ~$50M; Koozie Group ~$358M;
  Gemline ~$143M *(weaker growth, so efficiency angle)*; Logomark ~$131M; SnugZ USA ~$92M
  *(contraction, so cost angle not growth angle)*; PCNA ~$667M; **S&S Activewear** and
  **SanMar** (multi-billion) - the report explicitly flags both as **possible ecosystem or
  integration partners rather than prospects**, low confidence until checked internally. [p.20]

**Report's recommended deep-dive five** [p.21]: Concord Marketing Solutions, Stran, Overture,
Goldstar, Ball Pro. Selection logic: meaningful operational scale plus unusually strong
reported growth, while avoiding the largest enterprises where existing automation programs make
a generic pitch less informative. Growth figures from PPAI; **the selection logic is the
report's inference.**

Per-account manual checklist [p.21]: website -> business model -> products and services ->
operations language -> job postings -> public technology references -> acquisitions and growth
-> likely workflow -> buyer role -> 3 discovery questions.

---

## 11. Application recommendations [p.21-33]

- **Name:** "Trelium GTM Intelligence." Framed as *an internal GTM research utility for
  Trelium*, explicitly not a replica of Trelium's product. [p.21]
- **Input:** company_name, company_domain, optional_industry. [p.21]
- **Pipeline:** public-source research -> company facts, tech-stack clues, buying signals ->
  evidence normaliser -> structured LLM extraction -> ICP rules engine -> workflow hypotheses
  and buyer personas -> confidence checks -> deterministic scoring -> account brief. [p.22]
- **Output schema** [p.24-25]: company, segment{value,confidence}, size{value,evidence},
  fit_score, verified_facts[{claim,source,date}], stack_signals[{tool,confidence,evidence}],
  buying_signals[{signal,evidence,confidence}], workflow_hypotheses[{workflow,reason,confidence,
  validation_questions[]}], buyer_personas[], outreach_angle, **research_gaps[]**.
  The report calls out `research_gaps` specifically: "Most AI lead-research demos try to hide
  uncertainty. You should surface it."
- **Interface** [p.26]: "Do not waste half your day building a beautiful SaaS dashboard." Clean
  CLI or minimal page. A brief layout is sketched: fit score, component ratings, top automation
  opportunity with confidence and reasons, numbered evidence, "validate before outreach"
  questions, persona, outreach angle.
- **Repo shape** [p.27]: `README.md`, `src/{research,extraction,scoring,workflows,output}`,
  `schemas/account.ts`, `examples/*.json`, `data/prospects.csv`, `docs/findings.md`.
- **README sections** [p.27-28]: Problem / What I built / How it works / Why I built it this
  way / What I learned / What I would do next.
- **Deliverables** [p.28-29]: working tool, GitHub repo, 30-account scored dataset, five
  manually verified briefs, one-page findings memo, 60-90s demo, 2-3 sentence email, resume and LinkedIn.
- **Findings memo skeleton** [p.29-30]: Question -> Method -> three findings -> next experiment.
  The three example findings are (A) growth is a useful prioritisation signal, (B) workflow
  specificity beats generic AI personalisation, (C) **evidence quality is the bottleneck -
  public information rarely establishes whether a process is actually manual, so the system
  should generate validation questions rather than treat workflow hypotheses as facts.**
- **Framing** [p.28]: title it "I researched Trelium's ICP and built an account research system
  to find workflows worth automating", *not* "Strategic Growth Plan for Trelium." You are not
  inside the company; pretending to know their GTM better than they do can backfire.
- **Thesis** [p.33]: "You asked for someone who can take an ambiguous GTM/operations problem and
  execute without constant direction. I treated the application as my first assignment."

---

## 12. Explicit prohibitions from the report [p.33]

These are lifted directly into `CLAUDE.md` as permanent project rules.

- No generic RAG chatbot.
- **No fake Trelium customer data.**
- No scraping hundreds of personal emails.
- **No outbound messages sent to Trelium's potential customers without permission.**
- **Never imply that hypothesised operational problems are known facts.**
- No AI-generated fluff personalisation ("Saw your company is doing amazing things in...").
- No six hours on a landing page over shallow research.
- Do not claim "excellent with Claude Code" - let the artifact make the sentence unnecessary.

---

## 13. Open questions the PDF does not settle

Recorded so the project does not silently assume answers.

1. **Is the PPAI 100 data redistributable?** The report uses it freely. We cite individual
   figures with attribution and store them as third-party-reported values, never as verified
   revenue. Not resolved in the PDF.
2. **Which of the 30 accounts are already in Trelium's pipeline?** Unknowable externally. The
   report's answer - dedupe against CRM before contact - is the only correct one, and the tool
   must surface this as a blocking caveat on every brief.
3. **Does Trelium's ICP actually exclude sub-$20M shops?** The pricing tiers suggest a floor,
   but the report never states one. Treated as a scoring assumption, documented in `SCORING.md`.
4. **Is Ritanshu COO or CTO?** Public sources conflict [p.2]. Do not assert either.
5. **What does Trelium's own qualification actually weight?** Every trigger in section 4 is an
   inference. The model is a *hypothesis about qualification*, and the findings memo must say so.
