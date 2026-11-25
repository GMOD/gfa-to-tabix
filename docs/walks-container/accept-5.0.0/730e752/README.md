# The reader's acceptance runs again, at graph-walks 730e752

graph-walks main 730e752, the 7.0.0 candidate, reading the bytes
[4b14ee3's runs](../4b14ee3/README.md) read: the 5.0.0 genome files that
gfa-to-tabix main 9e46a46 built with ADR 0015's header (the hosted `-f8`
files), and the pggb chrY GRCh38 file that run rebuilt. On ada on
2026-11-18 ([run.sh](run.sh), [log](run.log)), from 11:12 to 12:49.
graph-walks 7.0.0 is b0d8378, one commit later, in which a contig on two
haplotypes of the reference sample throws instead of resolving to the last.
graph-walks has 22 commits since 4b14ee3, and the release document asks
for release-check again when the reader changes. Each file's sha256 is
the one [identity.tsv](../whole-file/identity.tsv) holds for it
([sha256.txt](sha256.txt)). The memory caps, `nice` and order are
4b14ee3's: each command under a cap with no swap and `/usr/bin/time`,
whose line of wall time and peak memory ends its file, or for the harness
its line in the log; release-check and the worst windows alone, the read
scans and the harness together. Other agents' jobs shared ada through the
harness, at a load average of up to 27 on 24 cores. Every count is in the file its line
links.

## What changed in the reader, and what these runs see of it

- Most of the 22 commits add `reader.counts` and its tests and README
  sections (638de51 to 2d43528, a4b0834). No run here calls it, and
  release-check, `blocks-equality.ts` and the two scripts are the same
  files as at 4b14ee3, so the counts' change to lower bounds on files
  without `revisited:i:0` (2d43528) shows in nothing below. Both genome
  files state `revisited:i:0`
- 581302a gives a placed node its strand, "at no read more": the cuts
  read the same bytes and keep the same nodes below
- 6ce85e0, 13b4f1e and 730e752 change the words and the advised window
  of a refusal by the budgets. Every cut here lifts the budgets or keeps
  under them, and none was refused
- 364ccb0 changes which walks `abridgedWalks` lists; 378b884, 8df8f81,
  bcd4fe4 and 8fd27e8 refactor or tighten the row reading the cuts share

## release-check

- 28 of 28 on [GRCh38](release-check-grch38.txt) and
  [CHM13](release-check-chm13.txt), the same tests as at 4b14ee3, in
  73 s and 80 s against 109 s and 93 s

## The worst windows, every haplotype

[cut-cost.ts](cut-cost.ts), 4b14ee3's copy: three cuts in one process,
unloaded and loaded with graph-walks 730e752 on the format 8 file, and the
same with graph-walks 6.2 on the hosted format 7 file.

- **GRCh38 chr2:91,409,000-91,410,000** ([cost-grch38.txt](cost-grch38.txt)):
  the same bytes, reads, fragments, departures, gaps and nodes kept as
  4b14ee3's cuts in both modes. The unloaded cut is 0.34–0.45 s and
  567 MB peak (4b14ee3 0.37–0.49 s, 567 MB), the loaded one 0.87–1.04 s
  and 833 MB (0.93–1.11 s, 850 MB); graph-walks 6.2's loaded cut on
  format 7 took 3.4–3.6 s and 2,084 MB
- **CHM13 chr2:92,078,080-92,079,080** ([cost-chm13.txt](cost-chm13.txt)):
  the same counts as 4b14ee3's in both modes; unloaded 1.35–1.55 s and
  1,183 MB (1.39–1.57 s, 1,176 MB), loaded 12.0–13.4 s and 5,529 MB
  (13.0–13.9 s, 5,557 MB), against graph-walks 6.2's 35–42 s and
  8,368 MB loaded on format 7
- The loaded cuts hold every fragment (457 and 522, none with unloaded
  pieces), as graph-walks 6.2's do

## The 4 MB read scan

- [read-scan.ts](read-scan.ts) on [GRCh38](read-scan-grch38.txt) and
  [CHM13](read-scan-chm13.txt): no 1 kb window's unloaded cut of every
  haplotype reads over 4,000,000 bytes, and the 20 that read most each
  read what `bytesFor` says. Both files' counts and lists are 4b14ee3's
  line for line

## The equality harness

graph-walks' `scripts/blocks-equality.ts`, as
[0350375/run.sh](../0350375/run.sh) ran it.

- [pggb chrY on GRCh38](eq-pggbY.out), 24 windows: no difference from the
  loaded cut, and the 72 reference nodes and 111 links set aside by
  design are the ones [pggbY/notes.md](../../pggbY/notes.md#where-a-loaded-and-an-unloaded-cut-differ)
  describes. The file is 4b14ee3's output byte for byte
- **The genome files,** 1,000 windows of seed 1 on each in two runs, 64
  haplotypes a cut: neither differs anywhere,
  [GRCh38 1–500](eq-grch38.0.out), [501–1,000](eq-grch38.1.out),
  [CHM13 1–500](eq-chm13.0.out), [501–1,000](eq-chm13.1.out). Each file
  is 4b14ee3's output byte for byte, so the bytes read, fragments,
  departures, gaps, reference nodes and links compared are the same
- The runs took 1,550 s for pggb chrY and 4,572–5,424 s for the genome
  runs, against 1,754 s and 4,739–5,533 s at 4b14ee3, at the same peak
  memory within 0.1 GB

## Not run again

- The writer's runs read nothing through graph-walks, and the writer and
  the files are unchanged since 4b14ee3's: against-format7.py on each
  genome file, byte identity across thread counts, and the pggb chrY
  rebuild with its header diff. Their results are
  [4b14ee3's](../4b14ee3/README.md)
