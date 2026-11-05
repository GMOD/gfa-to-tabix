# The minimal record, 2026-11-04

The writer at 76c9223, with ADR 0009's minimal record and one copy
mechanism on walk rows, built on ada on HPRC v2.1 Minigraph-Cactus chr22
(`mc22`) and HPRC release 2 pggb chrY (`pggbY`), on GRCh38, under
nearest-pass placement at the default options, and read back by
[`audit6.py`](../../scripts/audit6.py). The port of the same morning is the
same writer before the cuts ([results/port/](../port/README.md)); format 5
is the same graphs built by 552b9c1.

## Files

- `NAME.build.log`: the build, with each phase's time and the process's
  peak memory so far in GiB, and `/usr/bin/time`'s peak in KiB, which the
  table gives over 10^6, as the port's does
- `NAME.audit.txt`: the audit, as the rebuild's README describes it
- `sizes.txt`: each file's bytes against the port's and format 5's

## Results

| | MC chr22 | pggb chrY |
|---|---|---|
| file | 59.17 MB | 190.4 MB |
| the port, before the cuts | 59.43 MB | 196.6 MB |
| format 5 | 59.14 MB | 179.8 MB |
| against format 5 | +0.04% | +5.9% |
| records, rows | 24,648, 31,239 | 425,040, 1,224,004 |
| the port's records, rows | 24,777, 31,368 | 425,836, 1,224,800 |
| copies named on walk rows | 0 | 299,916 |
| departure rows a 64 kb window returns, p95 / max | 310 / 893 | 18,034 / 104,479 |
| departure read, requests max, bytes p95 / max | 1, 81 KB / 115 KB | 5, 569 KB / 1.05 MB |
| build, s / peak GB | 57 / 4.1 | 102 / 7.6 |
| audit, s / peak GB | 493 / 13.8 | 386 / 5.9 |

- The records lost against the port are the one-ended ones, 129 on MC
  chr22 and 796 on pggb chrY. Every record left matches a departure the
  audit recomputes from the decoded rows, in every field; none is missing
  and none lacks a departure; every departure inside a piece lies within
  the walk read's reach; every base of every record's stretch lies under
  one of its rows
- On MC chr22, 9 departures across a contig's W lines run over a W line
  with no step on the reference, which has no rows: the audit counts that
  line's bp as between lines, the record as in the graph, and the audit
  reports them apart
- The walk rows: MC chr22 names no copy, since GRCh38 passes none of its
  nodes twice. pggb chrY names 299,916, `:k` and `@k` together, where the
  port wrote `@k` on some rows and step counts on every token of 119,749
- The departure rows a window returns are the port's: the one-ended
  records it lost were one row each, and the cuts change no other filing

## The genome-wide graph

The hosted graph, HPRC v2.1 Minigraph-Cactus on GRCh38, with `--refs
GRCh38,CHM13`, built by the same writer on ada from
`~/hprc-gbz/walks/hprc-v2.1-mc-grch38.W.gfa.gz` (`genome.build.log`);
format 5 is the hosted `hprc-v2.1-mc-grch38-f5s` build of 2026-10-28:

| | GRCh38 file | CHM13 file |
|---|---|---|
| file | 1.55 GB | 1.99 GB |
| format 5 | 1.55 GB | 1.46 GB |
| rows | 95,409,901 | 131,233,956 |
| format 5 rows | 93,368,633 | 88,516,941 |
| pieces | 19,933,602 | 23,760,739 |
| departure records, rows | 1,797,769, 2,066,063 | 5,537,747, 42,748,799 |
| copies named on walk rows | 0 | 65 |
| paths abridged, detail walk rows | 66,981, 74,053 | 38,504, 518,746 |
| build, s / peak GB | 4,928 / 13.1 (both files) | |
| format 5 build | 8,703 / 13.1 | |

- GRCh38 passes no node twice, so its file writes no copies and holds
  about as many bytes as format 5's, the records in place of the skip rows
- CHM13 passes 209,578 nodes more than once, and under nearest-pass
  placement its paths depart at those copies as pggb's do: 5.5 M records in
  42.7 M rows, a third of the file
- `genome/`: chr22 of each file audited with `audit6.py --seq`
  (`CHM13.chr22.audit.txt`, 630 s and 15.3 GB; `GRCh38.chr22.audit.txt`,
  435 s and 13.9 GB), the departure rows of each file by sequence, and
  CHM13 chr9's records broken down by `scripts/chm13-chr9-departures.sh`

### chr22 of each file

Every record matches a departure recomputed from the decoded rows and
every base of every record's stretch lies under one of its rows, on both
files. CHM13's chr22 has 94 `#hole` lines, stretches no line of the
CHM13 reference covers, and the audit reads across them as the format
says.

| | GRCh38 chr22 | CHM13 chr22 |
|---|---|---|
| departure records, rows | 24,648, 31,239 | 23,740, 32,480 |
| across a record gap, matched / over a W line with no row | 549 / 9 | 446 / 28 |
| departure rows a 64 kb window returns, p95 / max | 310 / 893 | 271 / 881 |
| departure read bytes, p95 / max | 82 KB / 115 KB | 78 KB / 117 KB |
| walk read bytes, p95 / max | 173 KB / 426 KB | 162 KB / 540 KB |

### Where the CHM13 file's rows are

The GRCh38 file's departure rows spread over the chromosomes, at most
170,660 on one (chr2). The CHM13 file's 42.7 M lie in a few places:

| CHM13 sequence | departure rows |
|---|---|
| chr9 | 32,413,649 |
| chr14 | 4,278,254 |
| chr2 | 2,048,353 |
| chr16 | 1,039,235 |
| chr8 | 572,669 |
| chr21 | 511,449 |
| chr4, chr5 | 390,751, 336,946 |
| every other sequence | under 170,000 |

On chr9, 2,241,594 records make the 32.4 M rows. 2,151,415 of them
(96%) carry 0 own bp, 1,818,332 (81%) switch strand, 233,393 jump
forward and 184,517 back; 1,680,736 span 10 to 100 Mb of CHM13 chr9 and
496,029 span 1 to 10 Mb. Their leave breakpoints cluster at 38 to 44 Mb
(1,339,179 records) and 76 to 79 Mb (841,477), and the stretches between
make the rows: every Mb from 50 to 75 Mb holds a row of 1,680,735
records. These are paths hopping between copies of sequence that CHM13
holds tens of Mb apart there. chr14's rows lie in one Mb, at 13 Mb
(4,215,785 of them).

A 64 kb window's departure read on the CHM13 file:

| window | rows | text | gzipped |
|---|---|---|---|
| chr9:30,000,000 | 4 | 448 B | 198 B |
| chr9:39,000,000 | 473,088 | 51.4 MB | 5.3 MB |
| chr9:45,000,000 | 1,680,736 | 182.7 MB | 22.4 MB |
| chr9:60,000,000 | 1,680,736 | 182.7 MB | 22.4 MB |
| chr9:78,000,000 | 1,255,166 | 136.5 MB | 15.9 MB |
| chr9:85,000,000 | 1 | 114 B | 109 B |
| chr22:19,000,000 | 750 | 88 KB | 11 KB |

graph-walks 5 refuses a departure read over `departureByteBudget`, 2 MB
compressed, so on the CHM13 file every window between about 38 and 80
Mb of chr9 gets its DepartureReadError, which names a collapsed repeat
as the usual cause; the GRCh38 file has no such stretch. The placement
question of [open-problems](../../../open-problems.md#placement-of-steps-on-nodes-the-reference-passes-more-than-once)
applies to CHM13 as a reference of this graph, not only to pggb.

## The forms cut on MC chr22

`mc22.forms-compare.txt`: graph-walks 1132859's `formsCut` on the format
6 file against 4.6.0's on the format 5 file (`f5/` and `port3/` on ada),
six windows, every haplotype, `partial: false`. In every window every
departure the old cut found over the window the new one finds too, and
the forms are identical outside LCR22A. At chr22:18.6-18.68 Mb the new
cut adds, for 377 of 463 haplotypes, departures the old one could not
see: contigs that leave the reference before the window and rejoin after
it, or jump over it whole, which the records hold and a cut of the
window's chunks never reached. The forms there change from groups on a
65.5 kb replacement to groups on those jumps (624 kb replaced by 130 kb
for 114 haplotypes, 400 kb by 159 kb for 70); one window at 21.5 Mb adds
one such departure. The new cut takes 1.9 s at LCR22A to the old 5.2 s.
