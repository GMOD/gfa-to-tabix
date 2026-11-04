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
  42.7 M rows, a third of the file. The audit of its chr22 is in
  `CHM13.chr22.audit.txt` once run
