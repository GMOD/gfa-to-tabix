# ADR 0012's acceptance runs at the release heads

graph-walks main 4b14ee3 reading the 5.0.0 genome files that gfa-to-tabix
main 9e46a46 built with ADR 0015's header (the bytes of the hosted `-f8`
files), on ada on 2026-11-15 ([run.sh](run.sh), [log](run.log)). Each
command ran under a memory cap with no swap and `/usr/bin/time`, whose
line of wall time and peak memory ends its file, or for the harness its
line in the log; all but the read scans and the harness ran alone. The
format 7 side is the hosted file, `~/work/genome7/` on ada, whose
GRCh38 copy has the URL's length. Every count is in the file its line
links.

## release-check

- 28 of 28 on [GRCh38](release-check-grch38.txt) and
  [CHM13](release-check-chm13.txt) (colour codes removed)

## The worst windows, every haplotype

[cut-cost.ts](cut-cost.ts), as `genome-accept/cost.sh` ran it: three cuts
in one process, unloaded and loaded with graph-walks 4b14ee3 on the
format 8 file, and the same with graph-walks 6.2 on the hosted format 7
file.

- **GRCh38 chr2:91,409,000-91,410,000** ([cost-grch38.txt](cost-grch38.txt)):
  the unloaded cut takes as long as graph-walks 6.2's on format 7 and
  peaks a little above it, and holds every fragment 6.2's needs a loaded
  cut for; the loaded cut is a quarter of 6.2's time, under half its
  memory and a sixth of its bytes
- **CHM13 chr2:92,078,080-92,079,080** ([cost-chm13.txt](cost-chm13.txt)):
  the unloaded cut is half graph-walks 6.2's time on format 7 in less
  memory, reading more bytes, as many as `bytesFor` says; the loaded cut
  is a third of 6.2's time in two thirds of its memory
- The loaded cuts keep fewer nodes than graph-walks 6.2's, and than the
  branch measured on 2026-11-11 in ada's `genome-accept/out/cost-*.txt`,
  over the same fragments, departures and gaps; on GRCh38 fewer than the
  unloaded cut keeps

## Against the hosted format 7 file

`against-format7.py`, as
[genome-blocks.sh](../../abridged/genome-blocks.sh) ran it, on each
genome file:

- [GRCh38](against-format7-grch38.txt) and
  [CHM13](against-format7-chm13.txt): every hosted `abridged` row
  recomputed from the format 8 rows, and no line differing in abridged
  rows, elsewhere or in length; the one header line that differs is the
  `#walks` line with ADR 0015's `graph:Z:` and `leftout:i:`, which ADR
  0012's comparison leaves out. The script exits 1 on it

## Byte identity across thread counts

- [threads-chr22.txt](threads-chr22.txt): MC chr22 built with
  `--walks --refs GRCh38` on all 24 cores and under `taskset -c 0`, where
  the writer finds one; the `.walks.gz` and `.idx` are the same bytes

## pggb chrY on GRCh38

- Rebuilt by the writer at 9e46a46 ([log](pggbY-build.GRCh38.log)), it
  differs from the 5.0.0 build in `~/work/blocks/pggbY-5.0.0/` only by
  ADR 0015's header tags ([walks-header-diff.py](pggbY-header-diff.txt))
- [The equality harness](eq-pggbY.out), 24 windows: no difference from
  the loaded cut; the reference nodes and links set aside by design are
  the ones [pggbY/notes.md](../../pggbY/notes.md#where-a-loaded-and-an-unloaded-cut-differ)
  describes

## The 4 MB read scan

- [read-scan.ts](read-scan.ts) on [GRCh38](read-scan-grch38.txt) and
  [CHM13](read-scan-chm13.txt): no 1 kb window's unloaded cut of every
  haplotype reads over 4,000,000 bytes, and the 20 that read most each
  read what `bytesFor` says

## The equality harness on the genome files

graph-walks' `scripts/blocks-equality.ts`, as
[0350375/run.sh](../0350375/run.sh) ran it: 1,000 windows of seed 1 on
each file in two runs, 64 haplotypes a cut.

- Neither file differs anywhere:
  [GRCh38 1–500](eq-grch38.0.out), [501–1,000](eq-grch38.1.out),
  [CHM13 1–500](eq-chm13.0.out), [501–1,000](eq-chm13.1.out)
