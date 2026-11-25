# pggb chrY, walk format 8, notes

ada dir: ~/work/blocks/pggbY (src = bundle of blocks-unit 1440c39; gw = snapshot of graph-walks-blocks 676a0dd)
writer: ~/work/blocks/src/target/release/gfa-to-tabix (e3e49de; src/ identical to 1440c39)
GFA: ~/work/arb-format-opus/in/pggbY.gfa (1053 P lines; GRCh38#0#chrY, GRCh38#0#chrY_KI270740v1_random, CHM13#0#chrY)

## Builds
- GRCh38: 98.4 s, 6,888,408 KB peak, 193,514,603 B (+210 B idx); 3,245,676 lines, 1,518 units
  (399 tile, 424 departures, 684 detail, 11 blocks). format 7 release build was 187,082,886 B, 3,132,876 lines, 1,507 units
- CHM13: 134.6 s, 3,929,340 KB peak, 188,280,064 B; 11,104,925 lines, 4,001 units (559/819/2566/57)

## Stats: see stats.GRCh38.json, stats.CHM13.json

## Results (all on ada under ~/work/blocks/pggbY)
- checkers: verify7/expand7/claims7/audit7(--gfa; CHM13 in 2 shards)/spec8/rebuild(24 shards) pass on both files: *.out, *.time, *.rc
- windows: win1.GRCh38.log, win2-5.GRCh38.log, win.CHM13.log (all haplotypes, equality), four.*.log (4 haplotypes, default budgets)
- once-passed-node.tsv: the drawing check's rows for node 408455, which GRCh38 passes once at 9,394,014 and seven haplotypes walk inside the TSPY copy near 9,482,842, its link drawn as no 88.8 kb skip (bandage-core drawcheck, window Y-9.3M)
- stay: stay0.GRCh38.walks.gz, staydiff.out (1,785,011 steps moved, 0.36%; pieces 618,112 -> 471,098)
- fixture coverage: fixcov/*.json (maxK 7, passes 11, abridged/tile 51, bin lines 29)
- harness fault reduced: tiny/revref.gfa (reference walking 1-,2-,4-; link-missing in both cuts)
- by-design difference: 20.15M window, HG00642 1 bp step on node 195169 (17 passes) off this tile's R; loaded keeps it at 20,055,206

## What the build shows, 2026-11-12 and 11-13

HPRC release 2's pggb chrY, built in format 8 on 2026-11-12 for GRCh38 and
CHM13 at the default options. All six file checkers and
`walks-truth.py rebuild` pass on both files, and `spec8.py`, the reader
written from the spec alone, disagrees nowhere.

- The rules no hosted file exercises fire throughout: 81% and 95% of the
  reference's steps lie on nodes it passes more than once, and a walk
  row's `k` reaches 3,346 and 3,756 where the fixtures reach 7. No row
  needed a change
- **What a reader gets,** graph-walks 676a0dd over 1 kb windows
  ([four haplotypes on GRCh38](four.GRCh38.log),
  [on CHM13](four.CHM13.log), every haplotype on
  [GRCh38](win1.GRCh38.cuts.txt) and [CHM13](win.CHM13.cuts.txt)): off
  the satellites a cut of four haplotypes is a few range requests.
  GRCh38's densest tile is refused at the default budgets with every
  haplotype, and CHM13's Yq12 windows are refused even for four: the
  attach fetches or the departure read pass the reader's budgets
- **`blocks` units outgrow [ADR 0012](../../adr/0012-abridged-blocks.md)'s
  limits here,** which were set for the hosted graphs: 3.5% and 5.7% of
  the file, the largest 2.58 MB, and a unit can be several times its tile

## Where a loaded and an unloaded cut differ

- **Where a run off the reference holds a node the reference passes
  elsewhere.** At GRCh38 20.15 Mb a haplotype's 1 bp step inside a run is
  on a node passed 17 times; the loaded cut keeps that node and its links
  95 kb away, the unloaded cut shows a 1 bp run. The format page says a
  run can hold another tile's reference node
  ([blocks](../../walks-format.md#blocks)); it can't happen where
  `revisited` is 0
- graph-walks' equality harness, not its reader, read a `+` leave as the
  node's right end, which is wrong where the reference passes the node
  reversed ([revref.gfa](revref.gfa)). graph-walks cbca728 reads the
  strand from the tile's `ref` rows, and sets the difference above aside
  by name where `revisited` is above 0
- With both mended, ten links still differed over seven GRCh38 windows,
  at 11.56 and 20.08 Mb: each joined two reference nodes, only the loaded
  cut held it, and no fragment or departure of either cut walked it. That
  was graph-walks cbca728 on the file built before `hapBp`
- **The cause, traced on the files gfa-to-tabix 5.0.0 built**
  ([outputs](../accept-5.0.0/)): a detail unit holds every moved piece of
  one W line in its tile, and a cut that expanded the walk linked each
  route of the unit, whichever of its pieces it built. A piece it stated
  as bp alone so gave it links between reference nodes that other walks'
  steps kept, and the cut that expands nothing held none of them.
  graph-walks 8e3d397 shows it on Minigraph-Cactus too: 6 links in 1 of
  1,000 windows of HPRC v2.1's CHM13 file, at chr1 16.39 Mb
  ([probe](../accept-5.0.0/probe-why.ts)), none in 1,000 of its GRCh38
  file, and 660 over 24 windows of pggb chrY on CHM13
- graph-walks 0350375 links the routes of the pieces a cut builds and no
  other. Both genome files then differ nowhere over the same 1,000
  windows each, and pggb chrY in 4 links over 2 of its 24 windows
- Those 4 are the first difference above where no step shows it: a piece
  the cut builds takes a route through a node the reference passes
  elsewhere, on steps the cut trims off its fragment
  ([probe](../accept-5.0.0/probe-pggb.ts)). It can't happen where
  `revisited` is 0
- One window differs otherwise, and is untraced: at CHM13 chrY 28.84 Mb
  the loaded cut walks links with an end off the reference 7,298 times
  and the unloaded one 7,294
- Since then graph-walks gained a `links` setting, `walked` (the default,
  the links a cut's steps take), `between` or `none` (`src/walkReader.ts`,
  7592122); neither difference has been rerun under it
