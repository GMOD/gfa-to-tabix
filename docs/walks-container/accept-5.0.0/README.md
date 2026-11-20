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
- **graph-walks 730e752,** the 7.0.0 candidate, on the same bytes
  ([README](730e752/README.md)): release-check 28 of 28 on both genome
  files, and the worst windows cut to the same counts as at 4b14ee3
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
- **A 0 here is a 0 within a run's sequences, not across the file,** for
  the two claims about a node, N2 and N3: each run holds a node's passes
  and its length to its own sequences' rows. So N2 at 0 in both
  `claims.txt` says that no route interior of a run's sequences holds a
  node those sequences pass once, and nothing of an interior that holds a
  once-passed node of another run's sequence. `claims7.py` now prints
  that under `--seq`
- **Not checked this way:** a node's length across two sequences (N3),
  and the `--own` checks of each record's own steps

## The whole file, on the hosted bytes

[ADR 0016](../../adr/0016-format-8-is-frozen.md) rests on two properties
of a whole file that the runs above could not see: no route interior, on
any sequence, holds a node the reference passes once, and each `ref`
row's `passes` is the number of `ref`-row steps on its node in the file.
`verify7.py` checks both as it streams a file, and `spec8.py`, written
from the page alone, on a file that fits in memory.

- [whole-file/](whole-file/README.md), written by
  [table.py](whole-file/table.py) from the runs' own output
  ([results.jsonl](whole-file/results.jsonl)): the hosted GRCh38 and
  CHM13 files and the hosted chr6 file with sequences pass both, and pggb
  chrY on GRCh38, which is not hosted and has revisited nodes, passes
  them too
- **The files checked are the hosted bytes,** the builds with ADR 0015's
  header, not the builds the runs above read, which differ from them in
  the `#walks` line and the offsets after it: each local file's length,
  its S3 multipart ETag and its `.idx` are held to the hosted URL's
  ([identity.tsv](whole-file/identity.tsv), by [run.sh](whole-file/run.sh))
- **What it would catch:** [broken-matrix.txt](whole-file/broken-matrix.txt)
  lists the checkers that fail each planted file, the one a review built
  by hand among them ([craft/](whole-file/craft/)), and that pass the
  unbroken files
- `spec8.py` did not read the genome files: it holds a file's every
  piece in memory

## Not covered by any run on the genome files

- graph-walks' release-check cuts 28 windows, all on chr22
- The read scan against `bytesFor` samples the start, middle and end of
  each abridged tile
