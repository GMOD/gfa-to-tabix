# Ruling Q (scripts and data were in the session scratchpad)

**Ruling: format 8 — every `abridged` row gains an exact `blocks` column; both hosted files are rebuilt.** An unloaded piece should carry its exact stretches on the reference, so its row draws like a loaded one with only node identities missing. It beats the best unchanged-format option on the second criterion, ties on Truth, near-ties on read cost, and loses only on cost of change, which ranks fourth. The byte figures are zlib of a prototype encoding, not a writer build, and the viewer drawing from blocks was not prototyped.

## Designs against criteria

Sample: 40 randomly chosen abridged tiles per file (of 461 GRCh38, 563 CHM13), every detail unit read: 5,397 and 3,616 pieces; windows 1 kb every 2 kb across those tiles (1,280 and 1,238). Auto-load read costs from the unit tables, all 7,334 and 8,893 windows at 4 kb steps. GRCh38 / CHM13.

| Design | False statements surviving | True info before loading | Added bytes; read per window | Releases, rebuilds |
|---|---|---|---|---|
| A. Unchanged | shown-with-no-step-there 6,672 of 160,153 kept (4.2%) / 15,848 of 95,925 (16.5%); missed 4 / 21; whole-piece size; end-step strand | steps and bp of the whole piece | 0; median 98 / 104 KB, worst 305 / 317 KB | none |
| B. Keep by detail extent, "not loaded" block clipped to window, no size or strand (cheapest honest) | none if the block claims nothing; 4.3% / 16.8% of blocks cover a window where loading shows no step | no placement, size or strand; median 91 / 41 rows per window (p90 295 / 200) are blank blocks | 0; same read as A | graph-walks, bandage-core, plugin |
| C. B plus auto-load of every overlapping detail unit (best unchanged) | none once loaded | everything, but by loading | 0; +298 / +340 KB median (4×), +1.6 / +1.8 MB p90, +14.6 / +12.0 MB worst; cuts timed on GRCh38: 2.3 s median and p90, 15 s and 3.1 GB RSS at p99, 17 s worst | as B |
| D. Row states its true span (format 8) | as B | as B; the unit extent already gives it | ~0 | all, plus rebuilds |
| E. Tolerant blocks, gaps under 100 bp merged (format 8) | none observed in 76k / 39k pairs at 50 bp windows; small departures hidden, sizes approximate | placement and strand; forms still can't use unloaded pieces | +8.5 / +10 B per piece, file +0.6 / +0.7 MB; tiles +1% | all + rebuilds + a header parameter |
| F. Exact blocks (ruling) | none: every stretch, strand, size and departure ≥1 bp exact | everything the row view draws; contained cuts and forms can use unloaded pieces | +160 / +158 B per piece, file +11.9 / +10.3 MB (0.76% / 0.59%); per abridged tile +11.5 / +9.4 KB median, +132 / +102 KB worst sampled; none on the other 99% of tiles | all + rebuilds; one column, no parameter |
| G. Spatially indexed detail units (richest) | not measured | — | — | redesign; open problems |

- C fails on cost: it needs a budget, which leaves B's blank blocks in the heaviest ~10% of windows.
- D gains nothing over B: 12,997 of 74,053 and 8,595 of 65,396 pieces share a multi-piece unit, where B draws one block per W line.
- F over E: E needs a tolerance parameter and leaves forms and sizes approximate; F's extra cost is about 11 KB on a 98 KB read, in 1% of the genome.
- Sample caveat: uniform tile sampling under-represents multi-piece units and pieces stepping beyond their span (1 and 7 sampled, against 1,279 and 469 genome-wide); F is exact for those by construction.

## Changes
- Spec (`format:i:8`, new ADR): row `seq start end abridged path fragStart hapOffset piece nsteps bp start[@k] end[@k] detail blocks`. A block is a maximal run of consecutive steps on R, each starting where the last ended, in one direction, with no step off R between; `blocks` lists them in path order, comma-separated, as `<d><+|-><len>[:<own>]`: `d` the signed distance from where the previous block ended on R (in path order) to where this one begins, the first from 0; `+` along R, `-` against; `len` its bp; `own` the haplotype's bp between the previous block and this, omitted when 0. Leading `start end` become the span of all blocks. Guarantees: Σlen + Σown = bp, first block begins on `start`'s node and last ends on `end`'s, blocks equal those the detail walk row decodes to.
- Writer: emit blocks from the placed steps; extend the decode assertion; checker claim with a recorded failure on a broken writer.
- Reader: parse blocks; keep a piece when a block overlaps the drawn stretch; trim blocks to the window with exact hap offsets; departures between consecutive blocks computed as between steps; forms and gaps read blocks; refuse any format but 8.
- Viewer: on-reference runs from blocks, own runs from `own`; drop the single abridged block and `estimated`; stepless only with no step and no block in the window; draw unloaded runs in loaded geometry in the amber style, readout with exact size plus "steps not loaded".
- Plugin: load action on every row with an unloaded run; `EXPAND_NAMED_MAX` stays 64; forms adapter uses block departures.
- Rebuild both hosted files on ada; graph-walks major, bandage-core, plugin and other consumers green on exact versions; swap the hosted pair with the plugin release.

## What would reverse it
- The real build adds over ~2% to a file, or pushes a window's read past roughly twice today's worst (305 KB): rule E.
- The row view needs own-node identities blocks can't state.
- Cuts in abridged tiles slow materially from block decoding (worst sampled piece 12,159 blocks).
- The rebuild is refused: rule B, with unloaded haplotypes excluded from forms and said so.
