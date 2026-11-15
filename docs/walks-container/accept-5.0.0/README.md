# Reader and claims checks on the 5.0.0 genome files

HPRC v2.1's Minigraph-Cactus graph, built for CHM13 and GRCh38 by
gfa-to-tabix 5.0.0 at d7ef618, and pggb chrY on CHM13, checked on
2026-11-13. Every count is in the file its line links.

## The equality harness

graph-walks' `scripts/blocks-equality.ts` cuts each window with every walk
expanded and with none, and prints every difference between the two cuts.
Each genome file: 1,000 windows of seed 1 in two runs, 64 haplotypes a
cut. pggb chrY: 24 windows.

- **graph-walks 8e3d397** ([run.sh](8e3d397/run.sh)): CHM13 differs in one
  window, by links only the expanded cut holds
  ([windows 1–500](8e3d397/eq-chm13.0.out),
  [501–1,000](8e3d397/eq-chm13.1.out),
  [that window alone](8e3d397/w457-fresh.out)); GRCh38 nowhere
  ([1–500](8e3d397/eq-grch38.0.out), [501–1,000](8e3d397/eq-grch38.1.out));
  [pggb chrY](8e3d397/eq-pggbY.out) in most windows, the same way
- **graph-walks 0350375,** which links the routes of the pieces a cut builds
  and no other ([run.sh](0350375/run.sh), [log](0350375/run.log)): neither
  genome file differs anywhere
  ([CHM13 1–500](0350375/eq-chm13.0.out),
  [501–1,000](0350375/eq-chm13.1.out),
  [the window alone](0350375/w457.out),
  [GRCh38 1–500](0350375/eq-grch38.0.out),
  [501–1,000](0350375/eq-grch38.1.out)), over the same fragments,
  departures and links as before; [pggb chrY](0350375/eq-pggbY.out) keeps
  the differences [open-problems.md](../../open-problems.md#pggb-chry-in-walk-format-8)
  describes
- **graph-walks 4b14ee3,** the release head, on the 5.0.0 files with
  the header ([README](4b14ee3/README.md)): neither genome file differs
  anywhere, nor pggb chrY on GRCh38, beside the rest of ADR 0012's
  acceptance runs, all passed
- **What it would catch:** 8e3d397 is the broken reader here, and the
  harness fails it on the window above. The same difference is a test of
  graph-walks, on `unbuilt.R.gfa`, that fails without the change
- [probe-why.ts](probe-why.ts) names the detail unit, the route and the
  piece behind a CHM13 link; [probe-pggb.ts](probe-pggb.ts) does the same
  for the links pggb chrY keeps

## claims7.py, a sequence at a time

`claims7.py` holds more than ada's memory on a genome file, and had
finished on neither. With `--seq` it checks one sequence's units and reads
of the others what the claims about a whole line, the `#haplotype` list
and `SQ:Z:` take ([scripts](../../departures/README.md#scripts)).

- [claims-genome.sh](claims7/claims-genome.sh) runs it on every sequence a
  file's directory lists, under a memory cap sized from
  [CHM13 chr22](claims7/calib-chr22.txt), and fails unless every run exits
  0 with every claim at 0
- **CHM13:** [summary](claims7/chm13/summary.txt),
  [each claim's count](claims7/chm13/claims.txt),
  [each run](claims7/chm13/runs.txt), [its sequences](claims7/chm13/runs.tsv)
- **GRCh38:** [summary](claims7/grch38/summary.txt),
  [each claim's count](claims7/grch38/claims.txt),
  [each run](claims7/grch38/runs.txt),
  [its sequences](claims7/grch38/runs.tsv)
- The runs' abridged rows add up to the rows the step-for-step rebuild
  counted in each file
- **What it would catch:** `broken.sh` holds the per-sequence runs to every
  broken file `claims7.py` fails whole, three of them broken across
  sequences, and [a chr22 file with one wrong `hapBp`](claims7/broken-hapbp.txt)
  fails here
- **Not checked this way:** a node's length and passes across two
  sequences (N2, N3), which each run holds to its own sequences' rows, and
  the `--own` checks of each record's own steps

## Not covered by any genome-wide run

- graph-walks' release-check cuts 28 windows, all on chr22
- The read scan against `bytesFor` samples the start, middle and end of
  each abridged tile
