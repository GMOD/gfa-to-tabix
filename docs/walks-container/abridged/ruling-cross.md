# Cross-examination of rulings P and Q, 2026-11-11

A third blinded Fable reviewer, given both rulings, the criteria and the
code, re-measured the facts each depended on and ruled. Its report, as
returned:

## Ruling

Adopt format 8 with exact per-piece blocks, as Q ruled, but in a separate
`blocks` unit per abridged tile, not a column on `abridged` rows. Keep P's
rule that expansion reads only detail units whose extent overlaps the
window; don't build P's auto-load budget. Gated on a real build. Q's
column fails Q's own reversal test on the hosted CHM13 file (one tile grows
40×), and P compared the wrong pair.

## Factual disputes

- P's 2 MB auto-load coverage, verified: from every unit table, 1 kb
  windows over abridged tiles load fully in 93.6% / 91.5% (GRCh38 /
  CHM13), 93.2% / 90.9% with the reader's 1 kb context; in over-budget
  windows 35% / 26% of units stay "not loaded"; at 100 kb windows only
  83.9% / 75.8% load fully
- Latency and memory of loading, Q verified and P's understated:
  all-haplotype 1 kb cuts with every unit loaded took 1.9-2.9 s at
  near-median windows (P: 0.9 s plain); chr2:91,409,000, 1.2 MB of detail
  and inside P's budget, took 6.9 s and 1.5 GB RSS; the median read is
  +300 KB over about 75 units, one request each today
- Q's byte figures, median verified, worst wrong by 15×: 160 / 157 B per
  piece and +11.5 / +9.4 KB per abridged tile at the median on Q's sample;
  about 12-15 MB per file. Built exactly on nine targeted tiles, the
  column adds 1,578 KB to CHM13 chr2:92,012,544 (40 KB today), 474 KB to
  GRCh38 chr2:91,422,720, 327 KB to GRCh38 chr14:19,398,656, 113 KB to
  GRCh38 chr2:91,357,184 and 9 KB to the largest-detail tile, GRCh38
  chr21:8,257,536. Multi-piece tiles cost about 1.5× per piece, and Q's
  sample held almost none
- The viewer drawing from blocks, prototyped: loaded cuts with every run
  of off-reference steps collapsed into one step of its bp, through
  bandage-core's row builder, gave 2,344 of 2,344 rows identical in bp,
  gaps, completeness, readout and runs over five all-haplotype windows,
  including chr2:91,409,000 and a multi-piece CHM13 tile. Trimming blocks
  to the window was not prototyped
- Cut speed on the worst pieces, verified: the worst tile's 14.9 MB of
  text with 1.97 M blocks gunzips in 20 ms and parses in 200 ms
- Nothing false from blocks found: block lengths plus own bp equal `bp`
  for 6,201 targeted pieces (1,092 beyond their end steps, 3,393 in
  multi-piece units) and Q's 9,013. Forms key on departure geometry, not
  node identity (code read). Residual: 0.3% of piece-windows look
  identical from blocks but carry different own nodes, so a view must
  never say "same sequence" for unloaded rows
- Keeping by detail-unit extent misses nothing (0 of 9,013)

## Weighing

P weighed format additions as add-ons to auto-load, so they mattered only
in the 6-8% of windows it left over, and never tested exact blocks as a
replacement. Q weighed blocks as a replacement, which the criteria call
for: criterion 2 rewards what is shown without loading, and auto-load is
loading, whose cost belongs under criterion 3. Truth ties; blocks place
every unloaded piece exactly where unchanged-format options place none;
blocks read +11 KB and one request at the median against +300 KB, about
75 requests and 2-7 s; the format change loses on cost of change, which
ranks fourth. The only mixed point, the worst-case read, the separate unit
removes.

## Gate

Proceed if, over all 461 + 563 abridged tiles: `blocks` units total at
most 2% of each file; the largest is at most 2 MB and no 1 kb
all-haplotype window reads more than 4 MB; zero pieces fail Σlen + Σown =
`bp`; zero rows differ between blocks-built and loaded cuts on the earlier
failure windows plus 1,000 random abridged-tile windows per file.

## What would reverse it

Any gate number failing (then P's ruling); the owner wanting unloaded rows
to show own-node identity, which blocks can't give; window trimming from
blocks disagreeing with loaded contained cuts.
