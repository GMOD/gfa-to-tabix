# Placement scores on pggb, 2026-10-30 to 2026-11-08

Measurements of where the walk writer puts a haplotype's step on a node
the reference passes more than once, on HPRC release 2's pggb chrY and
chr22 on GRCh38. Nearest pass ([ADR 0001](../adr/0001-step-placement.md))
is what gfa-to-tabix writes; the other two placements were built in the
spike of 2026-10-30 and not adopted. The scores have not been rerun since
the review of 2026-11-01, whose caveats are below.

## Three placements against Minigraph-Cactus

Each placement was built on pggb chrY and chr22 and scored by agreement
with Minigraph-Cactus's placement of the same contigs, an independent
projection, within 10 kb ([`agree.py`](scripts/agree.py)). The
alignment-guided placements take HPRC's wfmash all-vs-1 alignments as a
second input; [`primary.py`](scripts/primary.py) first chains each
contig's blocks into one co-linear projection, since 73.5% of chrY's
lifted blocks overlap another block of the same contig.

| | nearest pass | alignment-guided, raw blocks | alignment-guided, primary projection |
|---|---|---|---|
| chrY pieces agreeing with MC, Yp11/Yq11 / elsewhere | 35.6% / 50.5% | 71.1% / 77.3% | 86.5% / 99.4% |
| chrY departures, rows | 572,051, 1,616,957 | 81,978, 146,299 | 35,911, 53,775 |
| chrY rows per 64 kb window, median / p95 / max | 114 / 24,018 / 173,312 | 58 / 391 / 23,650 | 91 / 265 / 1,937 |
| chr22 pieces agreeing with MC, 2.8-26.7 Mb / elsewhere | 38.1% / 88.7% | | 95.9% / 99.9% |
| chr22 departures, rows | 12,458,636, 36,505,261 | | 303,171, 722,740 |
| chr22 departure query bytes p95 / max | 6.2 MB / 73 MB | | 389 KB / 1.4 MB |
| chr22 file over format 5 | +32.6% | | +17.8% |

- The departure rows above are the spike's format, and its chrY maximum
  under the primary projection, 1,937, was an audit error: the spike's
  own file holds 19,933 rows in its densest window
- The 2026-11-03 rebuild of the simplified format 6 gives, on chrY,
  425,836 records in 1,224,800 rows under nearest pass (p95 / max per
  window 18,037 / 104,479) and 30,329 in 43,415 under the projection
  (265 / 18,562); on chr22, 5,333,737 in 17,434,823 under nearest pass
  and 177,475 in 452,672 under the projection (1,070 / 71,905, at most
  988 KB a departure read)
  ([results](results/rebuild/README.md))
- Under ADR 0001's own criteria on chr22, with the raw lift as truth, the
  primary projection takes piece precision from 32.8% to 93.9% and
  pieces per pair from 17.9 to 1.05 outside the repeats, with strict
  recall 98.9% to 97.9%; in LCR22A precision goes 22.5% to 98.0% and
  strict recall 93.5% to 71.5%. The recall lost is sequence the raw
  alignments place at several copies, which nearest pass shows at every
  copy by hopping and the projection at one. The 95.9% agreement with
  MC is over the whole 2.8-26.7 Mb stratum, not LCR22A
- The projection places 45% of chr22's steps on reference nodes off the
  reference, as own sequence, where the contig's alignment does not
  cover them (the chr22 community holds sequence of other acrocentric
  chromosomes); an off step costs more to encode, hence +17.8%
- A chaining rule inside the writer (`--chain` in the spike: stay on one
  copy, pay a penalty per jump, place a step off the reference when
  keeping it would force a hop and back) is exact on the fixtures and did
  not finish chrY in two hours ([chain.txt](results/chain.txt))

## Caveats from the review of 2026-11-01

Until these are fixed and the scores rerun, the agreement figures are not
the gap between the two placements:

- The agreement rows count pieces. Nearest pass hops between copies and
  makes 922,159 scored pieces on chr22 to the projection's 253,591. By
  bp outside the repeats, ADR 0001's placement score is 93.53% for
  nearest pass and 93.22% for the projection
  ([chr22.adr0001-scores.txt](results/chr22.adr0001-scores.txt))
- `agree.py` extrapolates an MC position forward only. That is wrong on
  reverse-strand contigs past 5 kb from an anchor, and it hits nearest
  pass's mid-chunk pieces more than the projection's
- The "2.8-26.7 Mb" stratum is chrY's Yp11/Yq11 bounds reused on chr22,
  with a hole at 10-11 Mb, not chr22's repeats
- The precision gain under ADR 0001's criteria is scored against the
  alignments that guided the projection. The chrY primary build scores
  61% bp placement against its own guide, likely because the scorer ran
  with a lookback of 1 chunk where the header's maxnode implies 16
- `agree.py`'s departure lines count rows, not records.
  `walks-truth.py`'s "lost elsewhere" counts every strict miss, including
  bases in no piece
- MC also picks one copy per contig in repeats, so agreeing with it there
  isn't proof that either placement is right. The UCSC hg38-to-hs1 chain,
  scored on the graph's CHM13 path, would be a more independent check

## CHM13 as the reference of the GRCh38-referenced graph

- In the genome-wide Minigraph-Cactus graph CHM13 passes 209,578 nodes
  more than once, and the format 6 file on CHM13 holds 5.5 M departure
  records in 42.7 M rows against the GRCh38 file's 1.8 M in 2.1 M. 32.4 M
  of the rows are on chr9, where 2.2 M records, 96% with no own bp and
  81% switching strand, hop between copies held 1 to 100 Mb apart, three
  quarters of them 10 to 100 Mb, so a 64 kb window between 38 and 80 Mb
  reads up to 1.7 M rows, 22 MB compressed, and graph-walks 5 refuses it,
  as it does a window at 13.5 Mb of chr14, where 4.2 M rows lie in one Mb
  ([results/minimal](results/minimal/README.md#where-the-chm13-files-rows-are))
- Counted on 2026-11-08: in the CHM13-referenced HPRC v2.1
  Minigraph-Cactus graph, CHM13 passes each of its 90,761,410 nodes
  exactly once, and the 11-07 format 7 build of it has `revisited:i:0`
  and 3.74 M departure lines. The figures above came from another file,
  likely CHM13 as a haplotype of the GRCh38-referenced graph, and are not
  reproduced
- Decided 2026-11-05: the hs1 files come from HPRC v2.1's
  CHM13-referenced graph, which HPRC publishes, and the file above is not
  hosted ([results](results/arbitration/README.md)). The hops are
  haplotypes alternating between the collapsed copies every few hundred
  bp
