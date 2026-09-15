# Re-score Comparison (offline replay, no fresh research)

> Historical note: this comparison was made on the homepage-only collection pass. Those briefs
> are now archived in `output/briefs_pass1_homepage/`; `output/briefs/` holds the deeper-page
> pass described in `docs/DEEP_COLLECTION.md`.

Re-derived from the facts/evidence already committed in `output/briefs/*.json` after the 
correctness-hardening changes (deduplication + contradiction policy). No pages were 
re-fetched and no model calls were made.

| Company | Old score | New score | Diff | Old rank | New rank | Reason |
|---|---|---|---|---|---|---|
| Showdown Displays | 39 | 39 | +0 | 1 | 1 | no change |
| HALO | 36 | 36 | +0 | 2 | 2 | no change |
| High Caliber Line | 28 | 28 | +0 | 5 | 3 | no change |
| Stran Promotional Solutions | 29 | 28 | -1 | 4 | 4 | evidence quality 4->3; (duplicate claims now counted once) |
| Hirsch | 27 | 27 | +0 | 6 | 5 | no change |
| Concord Marketing Solutions | 29 | 24 | -5 | 3 | 6 | core vertical fit 25->20; new flags: SEGMENT_CONFLICT_UNRESOLVED; (unresolved segment conflict penalty) |
| Nadel | 17 | 17 | +0 | 7 | 7 | no change |
| SanMar | 10 | 10 | +0 | 8 | 8 | no change |
| Ball Pro | 5 | 5 | +0 | 9 | 9 | no change |
| Staples Promotional Products | 3 | 3 | +0 | 10 | 10 | no change |
| LeaderPromos | 2 | 2 | +0 | 11 | 11 | no change |
| 4imprint | None | None | +0 | 12 | 12 | not scored (unchanged) |
| American Solutions for Business | None | None | +0 | 13 | 13 | not scored (unchanged) |
| Ariel Premium Supply | None | None | +0 | 14 | 14 | not scored (unchanged) |
| BDA | None | None | +0 | 15 | 15 | not scored (unchanged) |
| G&G Outfitters | None | None | +0 | 16 | 16 | not scored (unchanged) |
| Geiger | None | None | +0 | 17 | 17 | not scored (unchanged) |
| Gemline | None | None | +0 | 18 | 18 | not scored (unchanged) |
| Goldstar | None | None | +0 | 19 | 19 | not scored (unchanged) |
| HH Global | None | None | +0 | 20 | 20 | not scored (unchanged) |
| Hit Promotional Products | None | None | +0 | 21 | 21 | not scored (unchanged) |
| Koozie Group | None | None | +0 | 23 | 23 | not scored (unchanged) |
| Logomark | None | None | +0 | 24 | 24 | not scored (unchanged) |
| Overture Promotions | None | None | +0 | 25 | 25 | not scored (unchanged) |
| PCNA | None | None | +0 | 26 | 26 | not scored (unchanged) |
| Proforma | None | None | +0 | 27 | 27 | not scored (unchanged) |
| S&S Activewear | None | None | +0 | 28 | 28 | not scored (unchanged) |
| SnugZ USA | None | None | +0 | 29 | 29 | not scored (unchanged) |
| The Magnet Group | None | None | +0 | 30 | 30 | not scored (unchanged) |
| iPROMOTEu | None | None | +0 | 22 | 22 | not scored (unchanged) |

**4 of 30 accounts changed score or rank.**
