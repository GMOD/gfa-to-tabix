# The format arbitration, 2026-11-05

The writer of branch `arb-format-opus`: departure records with
`leavePasses` and `rejoinPasses`, `ref` rows with `passes`, the header's
`revisited`, and one `abridged` row per piece ([ADR 0009](../../../adr/0009-departure-records.md#pass-counts)).
Built on ada by [`arbitration-builds.sh`](../../scripts/arbitration-builds.sh)
from inputs [`arbitration-inputs.sh`](../../scripts/arbitration-inputs.sh)
cut from HPRC's S3, since the inputs the handoff names were gone from ada;
main's writer (the port3 binary, 76c9223, no writer change since) built
the same inputs by [`arbitration-base.sh`](../../scripts/arbitration-base.sh).

## Files

- `mc22.*`, `pggbY.*`: HPRC v2.1 Minigraph-Cactus chr22 and HPRC release 2
  pggb chrY on GRCh38, each build's log and its `audit6.py` audit;
  `base-*.build.log` main's writer on the same input
- `sizes.txt`: each file's bytes and its rows and text bytes by kind,
  against main's writer
- `chm13-chr9.*`, `chm13-chr14.*`, `chm13-chr22.*`: chr9, chr14 and chr22
  of HPRC v2.1's CHM13-referenced Minigraph-Cactus graph (`vg chunk
  --contig` from `hprc-v2.1-mc-chm13.gbz`), built with `--refs CHM13`: the
  build logs and each file's `#walks` header line
- `chm13.windows.txt`: what a 64 kb window's departure read returns at the
  windows `../minimal/README.md` measured on the GRCh38 graph's CHM13 file
- `CHM13.chr9.hops.txt`: by [`chm13-chr9-hops.py`](../../scripts/chm13-chr9-hops.py)
  from the GRCh38 graph's CHM13 chr9 records, `chr9.records.txt` on ada
- `*.passes.txt`, when present: nodes each reference passes more than once
  over the whole graph, by [`reference-passes.sh`](../../scripts/reference-passes.sh)
  from the GBZs

## The format on MC chr22 and pggb chrY

Both audits are clean: every record matches a recomputed departure in
every field, pass counts included (24,639 on MC chr22, 549 across a record
gap and 24,090 within one, and the same 9 over a W line the file holds no
row of as before; 425,040 on pggb chrY); the `ref` rows' counts equal the
passes the file's `ref` rows hold; every abridged row equals the piece its
detail record holds; no base of any stretch is uncovered.

| | MC chr22 | pggb chrY |
|---|---|---|
| file, this writer / main's | 59,174,381 / 59,170,079 B | 192,199,564 / 190,420,488 B |
| change | +0.007% | +0.93% |
| `revisited` | 0 | 107,467 |
| abridged rows, this writer / main's | 2,572 / 2,468 | 110,886 / 669 |
| walk read bytes p95 / max, this writer | 172 KB / 411 KB | 139 KB / 1.72 MB |
| walk read bytes p95 / max, main's (`../minimal/`) | 168 KB / 411 KB | 138 KB / 1.31 MB |

- Walk, route and nodes rows have main's counts and text bytes in both
  files (`sizes.txt`); `ref` rows grow by their `passes` column, departure rows by
  two counts, abridged rows by one per moved piece
- On pggb chrY the abridged rows go from 669 to 110,886, one per moved
  piece, as many as the detail walk rows; the densest window's walk read
  rises from 1.31 to 1.72 MB, under the 8 MB budget

## CHM13 from its own graph

Over the whole of each published GBZ (`*.passes.txt`), CHM13 in its own
graph passes none of its 90,761,410 nodes twice, and GRCh38 none of its
83,303,684 in its own; CHM13 in the GRCh38 graph passes 513,592 nodes more
than once. ADR 0001 and `../minimal/` give 209,578 for the last, from the
genome-wide build's GFA, which is no longer on ada; the two counts are not
reconciled, and the hosting decision does not depend on which is right.

| | GRCh38 graph, CHM13 file (`../minimal/`) | CHM13 graph |
|---|---|---|
| chr9 departure records, rows | 2,241,594, 32,413,649 | 70,960, 84,745 |
| chr14 departure records, rows | 1,060,530, 4,278,254 | 63,332, 79,938 |
| chr22 departure records, rows | 23,740, 32,480 | 38,451, 60,545 |
| copies named on walk rows | 65 genome-wide | 0 on each |
| `revisited` | (not written; CHM13 passes 209,578 nodes twice or more) | 0 on each |

`chm13-chr9.audit.txt` audits the CHM13 graph's chr9 file clean: of its
70,960 records 70,894 match a recomputed departure in every field and 66
run over a W line the file holds no row of, as on MC chr22; every pass
count is 1; no base of any stretch is uncovered. chr14
(`chm13-chr14.audit.txt`: 63,212 match, 120 over a W line with no row)
and chr22 (`chm13-chr22.audit.txt`: 38,223 match, 228 over a W line with
no row) are clean the same way.

A 64 kb window's departure read (`chm13.windows.txt`, rows and text):

| window | GRCh38 graph | CHM13 graph |
|---|---|---|
| chr9:30,000,000 | 4 | 4, 464 B |
| chr9:39,000,000 | 473,088 | 19, 2.2 KB |
| chr9:45,000,000 | 1,680,736 | 458, 57 KB |
| chr9:60,000,000 | 1,680,736 | 405, 51 KB |
| chr9:78,000,000 | 1,255,166 | 206, 24 KB |
| chr9:85,000,000 | 1 | 1, 118 B |
| chr14:13,000,000 | 6 | 14, 1.7 KB |
| chr14:13,500,416 | 2,004,750 | 1,084, 131 KB |

- In the GRCh38 graph's file, CHM13 chr9 from 44,972,986 to 76,978,318 is
  a `#hole` (`CHM13.grch38-graph.chr9-holes.txt`), so the windows at 45
  and 60 Mb there have no CHM13 sequence; HPRC's v2.1 README says a
  graph's reference is never clipped, and in CHM13's own graph those
  windows read 458 and 405 rows; over the audit's 64 kb windows the
  read is at most 848 rows on chr9, 1,328 on chr14 and 902 on chr22
  (`chm13-*.audit.txt`)
- chr22 has more records in CHM13's graph than in the GRCh38 graph's
  CHM13 file, 38,451 to 23,740; not looked into
- Why the GRCh38 graph's file hops: of 2,241,003 consecutive record pairs
  of one path on chr9, 2,172,351 jump over 1 Mb twice in a row, the
  second leaving within 100 kb of where the first landed, and 2,064,356
  of those rejoin within 100 kb of where the first left: a hop to the
  other copy and back, walking a median 257 to 512 bp there (`CHM13.chr9.hops.txt`). The two
  copies share nodes in that graph, and each haplotype's path alternates
  between nodes CHM13 holds at one copy and at the other every few hundred
  bp. No `stay` near its 311 bp would absorb most of these. A placement
  rule could pick one copy per haplotype and count the other copy's nodes
  as its own sequence, but which copy is a choice the graph does not make;
  in CHM13's own graph the copies are separate nodes and the question does
  not arise
