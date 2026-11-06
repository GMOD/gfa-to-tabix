# The format 7 writer against arbiter A's converter, 2026-11-05

gfa-to-tabix 4.0's `--walks` (branch `format7-writer`) built HPRC v2.1
Minigraph-Cactus chr22 and HPRC release 2 pggb chrY on GRCh38 on ada. Each
file was checked with arbiter A's release checks,
[`verify7.mjs`](../arbA/scripts/verify7.mjs), and compared unit by unit
with the converter's output for the same graphs
(`~/work/arb-arbA/out/{mc22,pggbY}/s7.walks.gz`, built by `build.mjs`,
`sfinal.mjs` and `s7.mjs` from gfa-to-tabix 3.0.0's files). The inputs are
`~/work/arb-format-opus/in/{mc22,pggbY}.gfa`, the GFAs those 3.0.0 files
were built from.

## Results

- **Release checks:** both files pass, with the unit and line counts the
  ADR gives for the converter: 3,837 units and 1,958,554 lines on MC, 1,492
  units and 3,126,030 lines on pggb (`results/final.*.verify7.txt`)
- **Same lines:** on pggb every unit is the converter's, line for line. On
  MC every tile, departure block and header is too; the detail units are
  the same 2,468 up to their names (`results/final.*.compare.txt`,
  `final.*.detailnames.txt`)
- **Detail names:** the converter names a detail unit by the path its
  `abridged` row names, so two records of one path in one tile, one per
  contig, take the same name. On MC chr22, 355 of the 2,468 detail numbers
  that `abridged` rows name reach, in the converter's file, a unit holding
  another path's rows or no unit; in the writer's, none
  (`results/final.mc22.abridged.txt`). pggb chrY has none in either. The
  writer numbers records as the tile makes them, as ADR 0010 says (`cs:d`)
- **Sizes:** the writer's files are 58.49 MB on MC and 186.82 MB on pggb,
  against the converter's 59.31 MB and 187.92 MB (`results/final.sizes.txt`).
  The two hold the same blocks: 9,013 and 25,514 of them, cut at the same
  bytes, with uncompressed sizes that differ only by the detail names and
  the tables' digits. Deflated again by one zlib (1.2.11, level 6), the
  writer's and the converter's files come within 0.3 KB of each other on
  both (`results/final.*.reblock.txt`). The difference is the compressor:
  Node's bundled zlib (`results/zlib-versions.txt`) for the converter,
  zlib-rs for the writer
- **Compression level:** at level 6, zlib-rs wrote 60.05 MB on MC and
  196.58 MB on pggb (`results/first-run.txt`), larger than the converter.
  Level 7, zlib-rs's first on `deflate_slow`, wrote 58.49 MB and 186.82 MB;
  level 8 184.60 MB on pggb in 138 s against level 7's 118 s; level 9
  189.58 MB on pggb (`results/levels.txt`). The writer takes level 7. The
  machine is shared, so the times are rough
- **Time and memory:** MC chr22 in 58 s at a 3.9 GiB peak, pggb chrY in
  102 s at 6.7 GiB, on ada's 24 cores (`results/final.*.build.log`)
- **The test GFAs and fuzz graphs** (`results/local-compare.tsv`,
  summarised in `results/local-compare.summary.txt`): the writer and
  gfa-to-tabix 3.0.0 plus the converter, on every walk test GFA in four
  option sets and on 60 fuzz graphs in four, each also run with the
  generator's 0 bp nodes made 1 bp:
  - test GFAs: 63 of 64 builds identical, 1 differing only in detail names
    (walks-records.gfa at `--tile 7 --abridge-bytes 1`)
  - fuzz graphs with no node of 0 bp: 225 of 240 identical, 15 differing
    only in detail names
  - fuzz graphs with 0 bp nodes: 47 of 240 identical; the rest differ in
    departure lines, and some in detail names too. For an end on a node of
    0 bp, the converter takes the extent of the reference node that ends or
    starts at the breakpoint, and the writer that of the end step's own
    node, as the ADR words it ([walks-format.md](../../walks-format.md#departure))

## Scripts

- `scripts/final-run.sh`: the writer at the branch's head on both graphs,
  `verify7.mjs`, and every comparison below; `results/final.*`
- `scripts/first-run.sh`: the same at fbc5f6b, the first commit, which
  wrote at level 6; `results/first-run*.txt`
- `scripts/levels-setup.sh`, `levels.sh`, `levels-mc.sh`: fbc5f6b with the
  level read from `$LEVEL`, built at levels 7 to 9 on pggb and 6, 7 and 9
  on MC; `results/levels.txt`
- `scripts/compare7.py`: two format 7 files unit by unit
- `scripts/detailnames.py`: whether two files hold the same detail units up
  to their names
- `scripts/abridgedcheck.py`: whether each abridged row's `cs:d` unit holds
  its path's walk rows
- `scripts/reblock.py`: a BGZF file's size with each block deflated again
  by Python's zlib, boundaries kept
- `scripts/local-compare.sh`, `both.sh`, `summarize.py`: the test GFA and
  fuzz comparison, run locally with gfa-to-tabix 3.0.0 and graph-walks
  5.0.2's `src/`, which the converter imports
