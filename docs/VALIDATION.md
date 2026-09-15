# Validation Results

Total briefs: 30 | Scored: 11 | Excluded/insufficient: 19

## V1 — Rank correlation against the research report's independent priority order

The report ranked these 30 accounts by its own judgment, from the same public universe, without reference to this scoring model (docs/TRELIUM_RESEARCH_NOTES.md section 10). This is a second opinion, not ground truth — no external party has Trelium's actual win data (docs/SCORING.md section 10).

**Spearman's rho: 0.182**

Model ranking (scored accounts, best first): Showdown Displays, High Caliber Line, HALO, Stran Promotional Solutions, Concord Marketing Solutions, LeaderPromos, Hirsch, Nadel, SanMar, Ball Pro, Staples Promotional Products

Report priority order: Concord Marketing Solutions, Stran Promotional Solutions, Overture Promotions, iPROMOTEu, American Solutions for Business, BDA, Geiger, HH Global, Proforma, LeaderPromos, Nadel, G&G Outfitters, HALO, Staples Promotional Products, 4imprint, Hit Promotional Products, Goldstar, Showdown Displays, Ariel Premium Supply, The Magnet Group, Hirsch, Ball Pro, High Caliber Line, Koozie Group, Gemline, Logomark, SnugZ USA, PCNA, S&S Activewear, SanMar


## V2 — Component ablation (top-10 movement)

Each row zeroes one score component and reports how many of the original 
top-10 accounts fell out of the top 10 once that component is removed.

| Component zeroed | Accounts that fell out of top 10 |
|---|---|
| c1 | 1 |
| c2 | 0 |
| c3 | 1 |
| c4 | 1 |
| c5 | 0 |
| c6 | 0 |

## V4 — Negative control

See scripts/run_negative_controls.py output (run separately; not part of 
the 30-account prospect batch).


## V3 — Manual claim audit

Not computed by this script — see docs/FINDINGS.md for the manual audit 
results on the top-scored briefs.

