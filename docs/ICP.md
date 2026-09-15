# ICP Definition

This is the operational ICP the scoring engine implements. It is a **hypothesis about
Trelium's qualification criteria**, derived from public evidence, not a statement of Trelium's
internal criteria. Every section marks what is grounded and what is assumed.

Grounding references point to `TRELIUM_RESEARCH_NOTES.md`, which in turn page-references the
research PDF.

---

## 1. The unit of qualification

Most ICP models qualify a **company**. This one qualifies a **company-workflow pair**.

That is a deliberate departure, and it is the core product decision of the project.

Trelium's conversion event is a 30-minute session where it automates one of the prospect's
actual workflows in their actual tools [notes section 6]. The scarce resource in that motion is
not a list of companies. It is **a defensible guess about which single workflow to put on the
table.** A brief that says "Stran is a good account" is worth much less than one that says
"for Stran, the first workflow to probe is inbound PO to order entry, and here are the three
questions that confirm or kill that hypothesis in under two minutes of a discovery call."

So the output record is:

```
Account  ->  ranked workflow hypotheses  ->  per-hypothesis evidence and validation questions
```

The fit score ranks accounts. The workflow hypotheses are what makes a brief usable.

---

## 2. Segment tiers

Grounded in [notes sections 1, 3]. Tier assignment is deterministic from an LLM-extracted
segment label plus keyword evidence; see `SCORING.md` section 3.

| Tier | Segment | Definition | Grounding |
|---|---|---|---|
| **A** | Promotional-products distributor | Sells branded merchandise to end clients, sources from suppliers, runs company stores or programs | Trelium's named use cases include "distributor order entry"; customer logos are largely distributors |
| **A** | Promotional-products supplier | Manufactures or imports branded goods, sells to distributors, receives distributor POs | Trelium's supplier-facing content (SanMar, S&S, PromoStandards) |
| **A** | Decorator / print shop | Screen print, embroidery, DTG, commercial print, signage | Named explicitly [notes section 1]; Printavo, ShopWorks integrations |
| **B** | Adjacent branded-merchandise business | Corporate gifting platforms, kitting and fulfilment providers, uniform and workwear programs, packaging converters | Report says "related merchandise businesses"; adjacency is our inference |
| **C** | Operations-heavy non-promo | Wholesale distribution, light manufacturing, field services with PO and invoice volume | Trelium's broad ICP language covers this, but the vertical wedge does not |
| **X** | Out of ICP | Everything else: pure software, agencies, retail-only D2C, professional services | Assumption |

**Disqualifier, not a low score.** A Tier X company should not receive 40/100 and sit in the
middle of a ranked list. It exits the pipeline with status `OUT_OF_ICP`. See `SCORING.md`
section 2.

---

## 3. Scale band

Grounded in [notes section 2, business model].

The naive rule in the research PDF is ">$50M relevant revenue: +15" [notes section 9], which
makes scale monotonic - bigger is always better. **We reject that.** Reasoning:

1. Trelium's published pricing tops out at roughly $2,000/month before custom Enterprise
   [notes section 2]. That is mid-market pricing.
2. The report itself flags 4imprint (~$1.3B) as *less* certain fit because of likely existing
   automation, and recommends deep-diving Concord (~$87M) and Ball Pro (~$43M) over HALO
   (~$964M) [notes section 10].
3. An early-stage company with founder-led sales has limited capacity for 9-month enterprise
   procurement cycles.

So scale scores on a **band with a peak**, not a ramp:

| Band | Promo-relevant revenue | Read |
|---|---|---|
| `SWEET_SPOT` | $50M - $500M | Enough transaction volume to justify recurring automation; small enough to buy on a founder's demo |
| `LOWER_MID` | $20M - $50M | Plausible; may be price-sensitive against a $500-$2,000/mo floor |
| `LARGE` | $500M - $1B | Real volume, but longer cycles and more incumbent tooling |
| `ENTERPRISE` | > $1B | Needs a narrowly scoped workflow POC, not an ICP pitch |
| `SMALL` | $5M - $20M | Likely below the pricing floor. Assumption, flagged in notes section 13 |
| `MICRO` | < $5M | Out of range |
| `UNKNOWN` | no sourced figure | Scores zero, raises a research gap |

**Caveat that must appear on every brief using PPAI figures:** these are 2025
promotional-products revenue reported or estimated by PPAI, not audited total corporate
revenue [notes section 10].

---

## 4. Systems and ecosystem

Grounded in [notes sections 1, 3]. Presence of *named, disconnected* systems is the single
most direct evidence that Trelium's value proposition applies, because Trelium sells the layer
between systems [notes section 1].

| Class | Examples | Why it matters |
|---|---|---|
| Industry order/business systems | SAGE, commonsku, ShopWorks, Printavo, DistributorCentral, Syncore, AIM, Shopworks | Directly named in Trelium's content; strongest single stack signal |
| ERP / accounting | NetSuite, SAP, Oracle, QuickBooks, Acumatica, Dynamics | Named Trelium integrations; the destination side of order entry |
| CRM | Salesforce, HubSpot | Named integrations; quote and proposal follow-up |
| Supplier data | PromoStandards, SanMar API, S&S Activewear API, alphabroder | The source side; Trelium's clearest published example |
| Commerce / company stores | Shopify, custom company-store platforms, OrderMyGear | Company-store-to-ERP sync is a named Trelium agent |
| Generic office | Gmail, Outlook, Google Sheets, Excel, Slack | Weak alone; **strong when combined with any system above**, because that is a boundary crossing |

**Scoring principle:** a spreadsheet mentioned alongside an ERP is worth more than either
alone. Cross-class combinations are the signal, not system count. See `SCORING.md` section 3.

---

## 5. Workflow taxonomy

Nine workflows, mapped one-to-one onto Trelium's own published agents [notes section 1] so a
brief names a workflow Trelium can actually demo, not an invented category.

| ID | Workflow | Trelium agent it maps to | Typical trigger evidence |
|---|---|---|---|
| `WF_PO_ORDER_ENTRY` | Inbound PO or email to order entry | Order Entry / PO Entry agent | Distributor or supplier segment, order system named, high order volume |
| `WF_QUOTING` | Quote request to priced quote | Quoting agent | Quote request forms, "fast turnaround" language, SAGE or commonsku |
| `WF_ORDER_STATUS` | Customer status request to answer | Order Status agent | Customer service team size, status portal, high SKU or order count |
| `WF_SUPPLIER_PURCHASING` | Approved order to supplier PO | Supplier purchasing agent | Large supplier network, PromoStandards or supplier API evidence |
| `WF_INVOICE_MATCHING` | Supplier invoice to PO match | Invoice Vouching / matching agent | AP roles, ERP plus accounting split, high invoice volume |
| `WF_INVOICE_FOLLOWUP` | Overdue invoice to AR chase | Invoice follow-up agent | AR roles, accounting system named |
| `WF_PROPOSAL_FOLLOWUP` | Open opportunity to follow-up | Proposal follow-up agent | CRM plus SAGE or commonsku, sales team |
| `WF_REPORTING` | Source systems to recurring report | Business Report agent | Multiple systems, finance or ops analyst roles |
| `WF_COMPANY_STORE_SYNC` | Company store order to ERP | Company-store-to-ERP sync agent | Company store or program business evidence |

Each hypothesis carries a **boundary count** - how many system boundaries the workflow crosses
given that account's observed stack. Higher boundary counts rank higher, because that is the
report's strongest pain pattern [notes section 3].

**Hard rule:** a workflow hypothesis is never phrased as a finding about the company. It is
phrased as a hypothesis with attached validation questions. See `EVIDENCE_MODEL.md`.

---

## 6. Buying triggers

Grounded as inferences in [notes section 4]. Implemented as a fixed enumeration so the LLM
cannot invent new trigger types.

`GROWTH_HIGH`, `GROWTH_MODERATE`, `CONTRACTION`, `ACQUISITION`, `SYSTEM_MIGRATION`,
`OPS_HIRING`, `AP_AR_HIRING`, `NEW_FACILITY`, `LEADERSHIP_CHANGE_OPS`, `MARGIN_PRESSURE`,
`SERVICE_VOLUME`.

`CONTRACTION` deliberately scores zero rather than negative, and instead flips the brief's
angle from growth-scaling to cost-efficiency. The report models exactly this for SnugZ USA and
Gemline [notes section 10].

---

## 7. Personas

Grounded as inferences in [notes section 5]. Deterministic mapping from segment and scale band,
because persona selection is a lookup, not a judgment.

| Segment | Scale band | Primary persona | Secondary |
|---|---|---|---|
| Distributor | SWEET_SPOT and below | COO or VP Operations | President/CEO, Sales Operations |
| Distributor | LARGE / ENTERPRISE | VP Operations or VP Technology | CFO, Digital Transformation lead |
| Supplier | any | VP Operations | Customer Experience lead, Finance/AP, CIO |
| Decorator / print | any | Owner or CEO | Operations manager, production lead |
| Adjacent / non-promo | any | VP Operations | CFO |

Each brief must state **why** that role plausibly owns the hypothesised workflow. Per the
report, naming the role and its rationale is the GTM reasoning; a list of names from a
prospecting database is not [notes section 5].

---

## 8. Exclusions and flags

| Flag | Trigger | Effect |
|---|---|---|
| `PUBLIC_CUSTOMER` | Company appears in Trelium's public customer list | Excluded from ranking; brief still generated for reference, clearly labelled |
| `ECOSYSTEM_AMBIGUOUS` | Company is a supplier whose data Trelium already integrates (SanMar, S&S Activewear) | Not ranked as a prospect; flagged as possible partner or infrastructure [notes section 10] |
| `NAME_COLLISION` | Confusable with a different company | Requires a human disambiguation note. Live example: **iPROMOTEu is not iPromo**, and iPromo is a public Trelium customer [notes section 10] |
| `CRM_DEDUPE_REQUIRED` | Always set, on every brief | Non-removable banner: the tool cannot know Trelium's pipeline [notes section 10] |
| `OUT_OF_ICP` | Segment tier X | Exits before scoring |
| `LOW_EVIDENCE` | Evidence grade D | Score reported as a band, not a point |

---

## 9. What this ICP deliberately does not model

- **Whether a process is actually manual.** Public sources essentially never establish this.
  The system produces validation questions instead. This is finding C in the report's own memo
  skeleton [notes section 11] and it is the honest limit of the method.
- **Intent data.** No visitor tracking, no technographic vendor feeds, no purchased signals.
- **Individual contacts.** Roles only. No personal emails, per [notes section 12].
- **Non-North-American accounts.** Geography is an inference [notes section 3] and the PPAI
  frame is North American. Out of scope rather than mis-scored.
