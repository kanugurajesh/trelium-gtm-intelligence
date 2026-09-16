# Account notes: five accounts, by hand, from a second data source

A manual pilot of the next experiment proposed in `docs/FINDINGS.md`: read sources the pipeline
cannot reach (job postings, SEC filings, trade-press rankings, press releases) for five accounts,
and hold the result to the pipeline's own standard. Every claim below is a verbatim quote with a
URL and a retrieval date. Every quote the script could reach was re-checked against the live page
by `scripts/verify_hand_quotes.py` (source list in `data/hand_research_quotes.json`). Anything
that could not be verified that way is labelled, and anything seen only in a search-engine
snippet is kept in a separate "unverified leads" list and should be treated as a rumour.

All retrievals: 2026-09-16. Workflow ideas are hypotheses to test on a call, not findings about
how these companies operate. Revenue figures are ASI Counselor-reported promotional-products
revenue or the company's own filing, as labelled, never independently verified.

> **Before any outreach:** none of these accounts has been checked against Trelium's CRM or
> active pipeline. This document has no visibility into existing customers, prospects or
> in-flight conversations. De-duplicate before contacting anyone.

Why these five: three are the highest-scoring accounts from the pipeline run (Showdown Displays,
Stran, HALO), so the tool's brief and the hand research can be read side by side. Two are from
the nineteen accounts whose sites blocked automated collection outright (Geiger returned HTTP
403; Hit Promotional Products disallows crawling in robots.txt), to see what a second source
recovers when the company's own site gives nothing. For those two the company domain was not
fetched at all, by hand or otherwise; the pipeline respected the block and so does this.

---

## 1. Showdown Displays (supplier)

**What the pipeline found** (`output/briefs/showdowndisplays_com.md`): fit 39/100, the highest
of the run. Two facts from the about page, no named system, no trigger, and no workflow
hypothesis generated at all. The 12 scale points rest on "Their dedicated team of 185
professionals operate out of two primary European locations", which on re-reading describes the
company's European arm, not the group. The pipeline's segment-word guard accepted it because the
sentence is on the company's own about page. That is a scale figure the score should probably
not be leaning on, and it is recorded here rather than quietly fixed.

**What one job posting found.** An "Order Entry Associate" posting on ZipRecruiter (the listing
showed "Until 10/17/2026" as its closing date)
([link](https://www.ziprecruiter.com/c/Showdown-Displays/Job/Order-Entry-Associate/-in-Minneapolis,MN?jid=751140d7cc2b27a4)):

| Quote | Verification |
|---|---|
| "Same day data entry of customer purchase orders into the system" | read via fetch tool; ZipRecruiter robots.txt disallows automated re-check, open the link |
| "Order receipt can come in the form of e-mail, or phone" | same |
| "Provide same day order confirmations and clarify order discrepancies" | same |
| "Support order status requests, limited processing of return material authorizations" | same |
| "Contact customers for needed or missing information via email or phone" | same |
| "Obtain 100% accuracy entering customer Purchase Orders" | same |
| "Ability to interpret complex business documents including customer purchase orders" | same |

**Why it matters.** This is the canonical pattern Trelium's own order-entry page describes:
"Orders spread across emails and attachments become clean ERP records" (trelium.com, verified).
Six pages of the company's site, read by the pipeline, produced zero operational-complexity
points. One job posting describes a full-time role whose stated duties are email-and-phone
purchase orders keyed into "the system" by hand, with a stated accuracy target and a same-day
turnaround. That is the strongest single piece of workflow evidence found on any of the 30
accounts, and it was not on the company's domain.

**Hypothesis worth investigating.** Inbound distributor PO to order entry (`WF_PO_ORDER_ENTRY`)
at a supplier, with order status (`WF_ORDER_STATUS`) as the second candidate since the same role
handles status requests. Confidence: medium. Persona to ask: whoever owns customer service or
order operations (COO / VP Operations at this size).

**Validate before outreach.** What share of PO volume arrives as email or phone rather than
EDI or punch-out, and what is "the system"? Kills the hypothesis if most volume is already
structured and the posting covers the residue.

---

## 2. Stran Promotional Solutions (distributor, public company)

**What the pipeline found** (`output/briefs/stran_com.md`): fit 32/100, two facts (Magento-based
platform; page title calling Stran a "Promotional Product Supplier"), one generic supplier-
purchasing hypothesis, no scale, no trigger. Note the site title says supplier while the press
release below is about the ASI Counselor "Top 40 Distributors List"; the dataset's distributor label is the
one the second source supports.

**What filings and press releases found.** All verified by script against the live page.

| Quote | Source |
|---|---|
| "We have also invested in an internal commercial Enterprise Resource Planning (ERP) system, Oracle/NetSuite's NetSuite ERP, which is expected to enhance the process of gathering and organizing the business data of our company through an integrated software suite, and was launched in the first half of 2025." | [FY2025 Form 10-K, filed 2026-03-25](https://www.sec.gov/Archives/edgar/data/1872525/000121390026034104/ea0282261-10k_stran.htm) |
| "NetSuite combines accounting, order management, inventory, CRM, and presentation functionality." | same |
| "We believe that this ERP will reduce inefficiencies, expenses and headcount, automate current manual processes, and potentially contribute to growing net revenues." | same |
| "Additional NetSuite phases will be planned and rolled out in the future as necessary." | same |
| "As of March 13, 2026, we employed 154 full-time employees, 2 part-time employees and 15 independent contractors." | same |
| "We identified material weaknesses in our internal control over financial reporting as of December 31, 2025." | same |
| "Sales increased $33.5 million, or 40.6%, to $116.2 million for the year ended December 31, 2025" | [Press release, 2026-03-25](https://ir.stran.com/news-events/press-releases/detail/112/stran-company-reports-40-6-year-over-year-revenue-growth) |
| "sales of our SLS segment (which consists of the former Gander Group business) increased 242.6%, or $24.1 million, to $34.1 million" | same |
| "it has been ranked No. 21 on the 2026 ASI Counselor" [Top 40 Distributors list], "advancing two positions from its No. 23 ranking in 2025" | [Press release, 2026-07-24](https://ir.stran.com/news-events/press-releases/detail/119/stran-company-advances-to-no-21-on-asi-counselor-top) |
| "utilizes cutting-edge technology, including efficient ordering and logistics technology to provide order processing, warehousing and fulfillment functions" | same |
| Open roles on the careers page: "Solutions Marketing Lead", "Strategic Account Executive", "Senior Vice President, Sales" | [stran.com/careers](https://www.stran.com/careers) |

**Why it matters.** A single SEC filing supplies what the pipeline's rubric calls a named
system (NetSuite, tier-1 source), a scale figure (154 full-time employees; $116.2M 2025 sales),
and two triggers (an ERP rolled out in 2025 with further phases planned; an acquired business
line that grew 242.6% and is being run as a separate segment). The filing says in the company's
own words that the ERP is expected to "automate current manual processes", which is a statement
of intent, not evidence that those processes are still manual today. The careers page shows
only sales and marketing roles, so there is no operations-hiring signal.

**Hypothesis worth investigating.** Inbound PO to order entry into NetSuite (`WF_PO_ORDER_ENTRY`)
and invoice matching (`WF_INVOICE_MATCHING`), on the reasoning that a mid-rollout ERP with
"additional phases" is the moment a workflow layer either gets bought or gets built into the
implementation. Confidence: medium. The material-weakness disclosure is noted because Trelium's
own positioning includes "auditability" and "human review gates" (trelium.com, verified), but
it is a finance-controls statement and should not be read as an operations finding. Persona to
ask: CFO or COO; this is a public company with a stated controls remediation.

**Validate before outreach.** Which NetSuite phases are live, and does order entry run through
NetSuite's order management today or through the Magento-based platform the site describes?
Kills the hypothesis if the NetSuite rollout already covers PO intake end to end.

---

## 3. HALO (distributor)

**What the pipeline found** (`output/briefs/halo_com.md`): fit 28/100, five facts including a
list of punch-out connections the site names (GEP, PerfectCommerce, SciQuest, Oracle, SAP,
Ariba) which the pipeline correctly declined to score as HALO's own systems, two generic
hypotheses, no scale, no trigger.

**What press and trade press found.** All verified by script.

| Quote | Source |
|---|---|
| "the $1B brand experience and merchandise company" | [HALO press release, 2026-06-04](https://halo.com/halo-announces-new-technology-investments-and-strategic-growth-initiatives-at-house-of-halo/) |
| HALO Atlas, described as built to "help users quickly find information, summarize content, draft responses, and access guidance across HALO systems" | same |
| "We're investing in the tools, expertise, and infrastructure to help our account executives, clients, and suppliers build these brand worlds at scale" | same |
| "Print-on-demand storefront capabilities" (listed among new capabilities) | same |
| A new "chief product and technology officer to lead platform modernization"; "That includes platform modernization and the development of tools that support sellers, clients and partners" | [ASI Central, 2026-03-31](https://members.asicentral.com/news/industry-news/march-2026/halo-adds-3-executives-as-part-of-growth-strategy/) |
| "Based on 2024 North American promotional products revenue of $964.7 million, HALO Branded Solutions ranks second" (ASI Counselor-reported) | same |
| Remote roles listed: "Director Supplier Network", "Proposal Specialist" | [Remote Rocketship](https://www.remoterocketship.com/company/halo-2/) |

**Why it matters.** Two triggers the pipeline could not see: a new product-and-technology
executive hired in 2026 with "platform modernization" as the stated brief, and an internal
AI assistant launched in June that reads "across HALO systems". The second cuts both ways. It
is evidence that HALO is investing in exactly the layer Trelium sells, and it is evidence that
HALO may be building that layer itself. The stated Atlas capabilities are retrieval and drafting
("find information, summarize content, draft responses"), not executing transactions in systems
of record, which is the distinction Trelium's homepage draws ("route exceptions to humans",
"deterministic workflow steps, system updates", verified).

**Hypothesis worth investigating.** Whether a platform-modernization programme at a company of
this size has a workflow-execution gap between the new internal assistant and the order, PO and
invoice transactions it summarises. Candidates: `WF_ORDER_STATUS` and `WF_SUPPLIER_PURCHASING`,
given the "Director Supplier Network" hire. Confidence: low. Persona to ask: the chief product
and technology officer's organisation, not operations; and this is the account where the
non-monotonic scale rule in `docs/SCORING.md` applies, a $1B firm may be above where a
founder-led sales team should spend time.

**Validate before outreach.** Does Atlas take actions in HALO's order and finance systems, or
only answer questions about them? Kills the hypothesis if execution is already in scope for the
in-house platform team.

---

## 4. Geiger (distributor) — site blocked the pipeline (HTTP 403)

**What the pipeline found**: nothing. Zero facts, insufficient evidence, no score.

**What trade press found.** All verified by script. The company domain was not fetched.

| Quote | Source |
|---|---|
| "Based on 2024 North American promotional products revenue of $364.6 million, Geiger ranks 10th on Counselor's most recent list of top distributors in the industry" (ASI Counselor-reported) | [ASI Central, 2026-04-08](https://members.asicentral.com/news/industry-news/april-2026/geiger-expands-to-austria-with-acquisition-of-nowak-werbeartikel/) |
| "The announcement comes just months after Geiger GmbH, the distributor's German subsidiary, acquired two promotional products distributors" | same |
| "To date, Geiger has acquired at least seven distributors in the United Kingdom and four in Germany" | same |
| "all employees will be retained as part of the acquisition" | same |

**Unverified leads** (search-engine snippets of Indeed and ZipRecruiter listings; Indeed
returned 403 and ZipRecruiter's robots.txt disallows fetching, so none of this was read on the
page). An "Accounts Payable Specialist" listing is described in snippets as processing
"invoices, credit memos, debit memos, and reimbursements to sales reps" with "data entry into
Glinx or Vision360". If accurate, Vision360 is an accounts-payable automation product, which
would mean AP is already partly automated. Treat as a lead to confirm in a browser, not a fact.

**Why it matters.** A distributor (family-owned, per the PPAI note in `data/prospects.csv`) that has bought at
least twelve companies in three countries and retains their staff is, on its face, running several inherited
order and finance processes at once. That is a hypothesis about integration load, not a
finding about manual work; the article says nothing about systems.

**Hypothesis worth investigating.** Invoice matching or supplier purchasing across acquired
entities (`WF_INVOICE_MATCHING`, `WF_SUPPLIER_PURCHASING`), with the unverified AP-automation
lead as the thing most likely to kill it. Confidence: low. Persona to ask: CFO or VP Finance.

**Validate before outreach.** Are acquired European distributors on Geiger's order and AP
systems, or on their own? Kills the hypothesis if AP already runs through an automation
product and the acquisitions are kept on separate stacks by design.

---

## 5. Hit Promotional Products (supplier) — site blocked the pipeline (robots.txt)

**What the pipeline found**: nothing. Zero facts, insufficient evidence, no score.

**What trade press found.** All verified by script. The company domain was not fetched.

| Quote | Source |
|---|---|
| "2025 Revenue: $683.0" [million], "2024 Revenue: $655.1" [million], "Year-Over-Year Difference: 4.3%" (ASI Counselor-reported, ranked No. 4 supplier) | [ASI Central, 2026-07-22](https://members.asicentral.com/news/awards/july-2026/counselor-top-40-suppliers-2026-no-4-hit-promotional-products) |
| CEO quoted: "In addition, we continued advancing technology across the business," ... "including the implementation of AI-driven tools to enhance efficiency, service and decision-making." | same |
| "its new Ohio facility, scheduled to be up and running by Q4 this year and will allow for greater fulfillment across the Midwest" | same |

**Unverified leads** (Glassdoor snippet only, not read on the page): a "Domestic Purchasing
Specialist" opening.

**Why it matters.** Two triggers, both dated 2026: a second fulfilment facility opening in Q4,
and a CEO statement that AI-driven tools are being implemented. As with HALO, the AI statement
is also a counter-signal, and it is unspecific: "efficiency, service and decision-making" does
not say which workflows. A supplier at this scale is the party on the receiving end of
distributor POs and order-status requests, which is where Trelium's supplier-side agents sit.

**Hypothesis worth investigating.** Order status (`WF_ORDER_STATUS`) across two fulfilment
sites, on the reasoning that a second facility multiplies "where is my order" lookups.
Confidence: low. Persona to ask: VP Operations or customer service leadership.

**Validate before outreach.** Which functions the "AI-driven tools" cover, and whether order
status is exposed to distributors through the supplier API and portals Trelium's materials
already describe. Kills the hypothesis if status is already self-serve for the large
distributors that make up most volume.

---

## What this pilot says about the method

| | Pipeline (company site, up to 6 pages) | Hand research (filings, trade press, job boards) |
|---|---|---|
| Accounts with any operational-complexity evidence | 0 of 30 | 1 of 5 (Showdown, one job posting) |
| Accounts with a named system of record | 1 of 30 (Stran, Magento) | 1 of 5 verified (Stran, NetSuite) + 1 unverified lead (Geiger) |
| Accounts with a dated 2026 trigger | 0 of 30 | 4 of 5 (Stran, HALO, Geiger, Hit) |
| Accounts with a sourced scale figure | 3 of 30 | 5 of 5 (ASI-reported or filing) |
| Time per account | seconds, automated | roughly 20-30 minutes, by hand |
| Quotes byte-verified by a script | all | 44 of 51; 7 sit behind a robots.txt rule |

Three things follow. First, the memo's prediction held: the evidence Trelium's rubric needs
exists in public, but not on the company's own domain. Second, the two blocked accounts became
researchable through trade press alone, so "site blocks crawlers" should not mean "no score".
Third, job boards are where the workflow evidence is, and they are the hardest source to
collect ethically at scale: the two most useful postings here sit on sites whose robots.txt
disallows fetching. A production version of this tool would need a licensed job-postings feed,
not a crawler. That is a cost line, and it is the honest price of the one signal that
actually describes manual work.

The most useful single finding for the scorer is negative: the top-scored account's scale
points rest on a subsidiary headcount. That is a defect in the extraction guards, it is now
recorded, and it belongs in the next hardening pass with a test.
