# Ruling P (scripts and data were in the session scratchpad)

**Decision: no format change; walk format 7 and both hosted files stay as they are.** Fix the readers (candidate C): an unloaded piece is kept by its detail unit's `start end` from the table, drawn only as "not loaded", and loaded automatically under a byte budget. Two format additions measured and rejected under ADR 0011's burden.

## Measurements

- Whole file, from every per-sequence table: 461 of 47,140 GRCh38 tiles and 563 of 47,579 CHM13 tiles have detail units (about 1%). A detail unit is 3.9 / 6.1 KB median, 115 / 106 KB max. All detail units of one abridged tile: median 363 / 466 KB, p90 1.8 / 2.3 MB, worst 14.9 / 12.1 MB, against a median tile of 91 / 101 KB.
- Sample: 40 random abridged tiles per file, every detail unit decoded with graph-walks (capped at 1.5 MB per tile; 3 and 5 tiles capped): 5,006 GRCh38 and 3,273 CHM13 pieces, 800 random windows per size per file.
- Unit extent equals the hull of the decoded on-reference steps for 8,279 of 8,279 pieces, so it is a safe keep rule.
- 18.5% of GRCh38 and 57.1% of CHM13 pieces have a hole of 1 kb or more; exact coverage is a median 131 / 181 intervals per piece.
- End-step strand differs from the majority strand in 0 / 2 pieces; 149 CHM13 pieces are mixed.
- The whole-file version of the sample needs all 399 + 544 MB of detail units decoded (sample.ts over all 1,024 tiles on ada).

## Scores (1 kb windows, GRCh38 / CHM13)

| Candidate | Truth | Seen before loading | Read cost | Change cost |
|---|---|---|---|---|
| A. Nothing | Fails: 3.2% / 17.8% of kept piece-windows drawn present with no step; size charged 65× / 73× the true bp at the median; 336 of 437 haplotypes absent at chr2:91,409,000 | False blocks | 0 | 0 |
| B. Keep by unit extent, draw "not loaded" with no size, strand or net | Passes: 0 missed of 90,563 / 44,689 true piece-windows; 3.4% / 18.1% of markers have no step in the window, acceptable because they claim only "unloaded steps within the unit's extent" | Nothing about where or how big | 0 | graph-walks, bandage-core, plugin; no rebuild |
| C. B plus auto-load by extent, smallest first, 2 MB of detail | As B | Everything, in 93.7% / 91.6% of 9,220 / 11,260 windows of abridged tiles (whole-file, from tables); B's marker for the rest | Median +294 / +335 KB, capped at 2 MB, in 1% of tiles; 0 elsewhere | As B plus one budget; the plugin's 64-name rule goes |
| D. C plus per-1,024 bp presence and bp tags on `abridged` rows | As C; a bin is still "somewhere in 1 kb" | Leftover markers with no step fall to 0.4% / 2.3%, only in the 6–8% of windows C leaves unloaded | As C plus 2.4% / 1.5% on abridged tiles | Est. +1.31 / +1.17 MB per file; presence alone +0.02 / +0.05 MB; two spec mechanisms, writer release, both files rebuilt, every consumer |
| E. C plus exact intervals | Exact presence, no size | As D, at any zoom | Abridged tiles +14% / +9%, worst +88% | Est. +7.7 / +7.2 MB; rebuild |
| F. Always load everything, or stop abridging | Passes | Everything | Up to 15 MB per window | Reader only, or a rebuild with 15 MB tiles |

Timings (single runs, network included): a fully loaded cut 1.6 s against 0.9 s at chr22:46,500,000 (148 units, 493 KB) and 6.2 s against 0.8 s at chr2:91,409,000 (420 units, 1.2 MB).

Burden: D beats C only in the 6–8% of windows of 1% of tiles that C leaves partly unloaded, and there refines "maybe" for 3–18% of markers: mixed evidence at best, so the smaller move wins.

## Changes
- graph-walks (major): `abridgedSpan` keeps an abridged run when its detail unit's `start end` overlaps the window, extent carried on `Abridged` from the table, one unloaded fragment per unit with no `refStarts`, `against` or bp-derived `hapEnd`. `expand` defaults to every kept name, reading only detail units whose extent overlaps the window plus context, smallest first, within a new `expandByteBudget` of 2,000,000 and `stepBudget` (today `expand` reads every unit of the tile: 12.7 s and 20,622 nodes at chr21:8,300,000 where no unit overlaps the window). Departures, gaps, forms: drop the `abridged` net event; an unloaded unit breaks the chain and lists its haplotype as not assessed; contained cuts return it as unloaded.
- bandage-core: unloaded unit drawn as a marker clipped to window ∩ extent with zero bp; readout "N steps not loaded"; never stepless; always offers load. Render before/after.
- Plugin: delete `EXPAND_NAMED_MAX`; `expandByteBudget` slot; "Load" on any row with an unloaded unit, and "load all (N MB)".
- gfa-to-tabix: no writer change; spec wording; an ADR; record C37's checker failing on a broken writer.

## What would overturn it
- A hosted graph where 2 MB loads far fewer windows, or auto-load latency forcing the budget down: then adopt D (presence tag under 1 byte per row).
- A user needing where unloaded rows step in over-budget windows.
- A piece outside its unit's extent: a writer bug, fixed in format 7.
