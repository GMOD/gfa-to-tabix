# ADR 0001: Where a walk file files a haplotype step

- **Status:** accepted, 2026-10-19
- **Decides:** which reference chunk `--walks` files each step of a non-reference
  path under, when the reference passes the step's node more than once
- **Measured by:** the [success criteria](#success-criteria) below, with
  `scripts/walks-truth.py`. An ADR that replaces this one reports the same
  table on the same data

## Context

- Format 3 (gfa-to-tabix 1.1) gave each node one position, the reference's
  first visit, and filed a haplotype's step on a reference node under that
  position's chunk
- A reference that passes a node twice, megabases apart, splits every
  haplotype through it into a piece per hop. On HPRC release 2's pggb chr22,
  whose references revisit short collapsed nodes, the GRCh38 file has 95.3 M
  walk rows (1.65 GB) and the CHM13 file 165.9 M (2.33 GB). The same chromosome
  from Minigraph-Cactus (MC) v2.1 has 253 k rows in each
- On pggb chr22, 28% of GRCh38's steps and 74% of CHM13's revisit a node. In
  the genome-wide MC graph, GRCh38 revisits none and CHM13 revisits 209,578,
  on chr9, chr14, chr2 and chr5
- The viewers draw every haplotype through a window against the reference,
  to show structural variation

## Success criteria

A window at chunk *c* reads chunks *c − L* to *c*, where *L* is the lookback
from the header's `maxnode`. A piece filed at *f* is visible where its bases
align, at *c*, when 0 ≤ *c − f* ≤ *L*. Truth is impg's all-vs-1 wfmash
alignments of each assembly to the reference.

| # | criterion | measure | pass |
|---|---|---|---|
| 1 | exact round trip | the encoder decodes every row it writes | build succeeds |
| 2 | MC unchanged | files for a reference that revisits no node, at the default stay | rows byte-identical to 1.1.0; the header gains `stay:i:` and `maxnode` counts reference nodes only |
| 3 | strict recall | (haplotype, chunk) pairs with ≥300 aligned bp seen through a piece whose bases align there, at *L* = 1 | within 0.1 point of first-visit filing, overall and in LCR22A, LCR22B–D, the pericentromeric repeats and the control |
| 4 | piece precision | pieces with aligned bases visible where filed, at *L* = 1 | ≥ 90% |
| 5 | fragmentation | pieces per filed (haplotype, chunk) pair | ≤ 1.5 |
| 6 | window cost | windows over 8 MB gzipped or 32 M steps | none outside windows whose steps exceed the budget under every rule |
| 7 | build | wall time and peak memory on pggb chr22 | ≤ 1.5 × main (14:51, 42.8 GB) |

- Criterion 3 excludes the GRCh38 satellite and the CHM13 short arm, where
  the alignments themselves disagree with every graph. The harness reports them
- A contig spanning the chromosome has sequence in nearly every chunk, so a
  misfiled piece is still filed under a chunk the haplotype occupies, and
  precision per (haplotype, chunk) pair scores it as correct. Criterion 4
  scores each piece instead

### How to measure

On chr22 of both references, for the haplotypes CHM13#0, HG00097#1, HG00099#2,
NA19240#1, HG002#1, HG01175#1, HG00280#1, HG005#2, HG01167#2, HG01960#2,
HG02514#1 and HG02984#1:

```sh
s3=s3://human-pangenomics/pangenomes/freeze/release2
aws s3 cp --no-sign-request $s3/impg/pafs/all-vs-1/GCA_000001405.15_GRCh38_no_alt_analysis_set.PanSN.merged.paf.gz .
python3 scripts/walks-truth.py lift GCA_000001405.15_GRCh38_no_alt_analysis_set.PanSN.merged.paf.gz \
  GRCh38#0#chr22 GRCh38#0#chr22_KI2707{31,32,33,34,35,36,37,38,39}v1_random > lift.GRCh38.tsv
python3 scripts/walks-truth.py score lift.GRCh38.tsv out.GRCh38.walks.bed.gz \
  --haps CHM13#0,HG00097#1,... --regions scripts/walks-truth-regions.tsv --lookback 1
python3 scripts/walks-truth.py cost out.GRCh38.walks.bed.gz
```

The pggb graph is `$s3/pggb/gfas/by-chromosome/20251014_hprc25272.p98-k311.chr22.gfa.zst`;
the MC graph is HPRC v2.1's `hprc-v2.1-mc-grch38`.

### Baseline

GRCh38, *L* = 1:

| file | placement, bp once | piece precision | strict recall | pieces per pair |
|---|---|---|---|---|
| MC, main | 98.2% | 99.4% | 97.3% | 1.01 |
| pggb, main (first visit) | 95.4% | 53.5% | 97.2% | 311 |
| pggb, nearest pass | 96.7% | 44.4% | 97.3% | 45 |
| pggb, nearest pass + 4 kb stay | 97.1% | 95.9% | 96.5% | 1.16 |

CHM13, *L* = 1:

| file | placement, bp once | piece precision | strict recall | pieces per pair |
|---|---|---|---|---|
| MC, main | 98.5% | 99.5% | 98.8% | 1.01 |
| pggb, main (first visit) | 86.9% | 37.3% | 94.0% | 476 |
| pggb, nearest pass | 91.4% | 40.8% | 94.0% | 50 |
| pggb, nearest pass + 4 kb stay | 92.0% | 95.7% | 92.6% | 1.18 |

The nearest pass by chunk and by predicted offset differ by at most 0.3 point
on every measure in both tables, and give 50 and 52 pieces per pair on CHM13.
The tables list the chunk rule.

## Results

### Stay sweep

pggb chr22, current code, *L* = 1 except the two window-cost columns, which read
the file's lookback (16 chunks on GRCh38, 31 on CHM13). Criterion 3 compares
with the first-visit rows above (97.2% and 94.0%).

| file | placement, bp once | piece precision | strict recall | pieces per pair | p99 walk rows | windows over 8 MB |
|---|---|---|---|---|---|---|
| GRCh38, stay 311 | 96.8% | 59.7% | 97.1% | 3.60 | 231,827 | 31 |
| GRCh38, stay 1024 | 96.9% | 76.7% | 97.0% | 1.81 | 69,669 | 31 |
| CHM13, stay 311 | 91.6% | 51.2% | 93.8% | 6.34 | 510,775 | 174 |
| CHM13, stay 1024 | 91.9% | 68.3% | 93.3% | 2.45 | 167,446 | 172 |

- At the file's lookback, placement over query bases counted once is 97.2–97.3%
  and strict recall 97.3–98.3%, for both stays and both references
- Criterion 3 passes overall only for GRCh38 at stay 311. Strict recall falls
  0.2 point (GRCh38, stay 1024) to 0.7 point (CHM13, stay 1024) below first
  visit, as it does for the 4 kb stay. The per-region check at *L* = 1 is not
  reported for first visit
- Criterion 7 passes at stay 311: 12:16 and 13.9 GB, against main's 14:51 and
  42.8 GB
- Criterion 2 fails at either stay: on a graph with no revisited node, the
  stay absorbs runs and changes rows. The [gated stay](#gated-stay) fixes this
- Neither stay passes criteria 4, 5 or 6 on pggb. Stay 4 kb passed 4 and 5
  (see [Baseline](#baseline)) but hides real passages
- Stay 1024 cuts the pieces of 311 by 50% on GRCh38 and 61% on CHM13, and
  changes recall by under 0.5 point
- Satellite (GRCh38) and the CHM13 short arm stay weak: 43–46% and 74–76% strict
  recall
- The costliest windows (chr22:12.6–13.0M on GRCh38, the short arm on CHM13)
  stay large under both stays: GRCh38 peaks at 205 MB gzipped, and CHM13 at
  75 MB (stay 311) or 65 MB (stay 1024)

### Gated stay

The sweep above absorbs any run. A gated stay absorbs a run only if it holds
a node the reference passes more than once. A guard further requires that a
window over each chunk the run visits reads the piece's chunk, either for
every node in the run or only for the nodes the reference passes once.

pggb chr22 at stay 311. Precision and the first recall column at *L* = 1, the
second recall column at the file's lookback (16 and 31 chunks):

| file | piece precision | strict recall, *L* = 1 | strict recall, file *L* | pieces per pair | MB | windows over 8 MB |
|---|---|---|---|---|---|---|
| GRCh38, stay 0 | 44.3% | 97.25% | 97.47% | 45.2 | 860 | 44 |
| GRCh38, gate | 59.2% | 97.19% | 97.42% | 4.30 | 688 | 31 |
| GRCh38, gate + guard on every node | 49.3% | 97.25% | 97.47% | 11.95 | 728 | 37 |
| GRCh38, gate + guard on nodes passed once | 53.8% | 97.25% | 97.47% | 8.58 | 710 | 31 |
| CHM13, stay 0 | 41.0% | 93.92% | 98.53% | 52.2 | 580 | 234 |
| CHM13, gate | 51.1% | 93.80% | 98.37% | 6.95 | 317 | 177 |
| CHM13, gate + guard on every node | 41.4% | 93.91% | 98.53% | 29.93 | 460 | 213 |
| CHM13, gate + guard on nodes passed once | 44.7% | 93.89% | 98.50% | 16.78 | 386 | 183 |

- The gate keeps nearly all of the ungated stay's reduction in pieces
- Guarding every node restores stay 0's recall exactly, but triples the
  gate's pieces on GRCh38 and quadruples them on CHM13. Of the runs that guard
  turned away, across both references: 5% visit another sequence, 38% stay
  within the lookback in either direction, 23% within twice the lookback, and
  34% go farther
- 57% of turned-away runs leave the lookback, a megabase or more, and come
  back within 311 bp of reference nodes. Most likely each steps on a collapsed
  node whose nearest pass lies far off, a step with no one true chunk.
  Guarding only the nodes the reference passes once keeps recall within 0.03
  point of stay 0, with 72% (GRCh38) and 56% (CHM13) of the pieces of guarding
  every node

### Genome-wide MC

HPRC v2.1 MC, both references, built without a stay, nearest by predicted offset
against nearest by chunk:

| | predicted offset | chunk |
|---|---|---|
| GRCh38 file | identical to the other column, byte for byte | identical to the other column, byte for byte |
| CHM13 pieces | 24,252,423 | 24,255,105 |
| windows over 8 MB, GRCh38 / CHM13 | 0 / 2 | 0 / 2 |
| windows over 32 M steps, GRCh38 / CHM13 | 4 / 3 | 4 / 3 |

HPRC v2.1 MC at the decided rules, against stay 0 and the hosted 1.1.0
files:

| | stay 0 | stay 311, guard on every node | stay 311, guard on nodes passed once |
|---|---|---|---|
| GRCh38 rows | identical to 1.1.0, byte for byte | identical to 1.1.0 | identical to 1.1.0 |
| CHM13 pieces | 24,252,423 | 24,189,995 | 23,696,899 |
| CHM13 rows | 73,428,204 | 73,366,054 | 72,874,844 |
| windows over 8 MB, GRCh38 / CHM13 | 0 / 2 | 0 / 2 | 0 / 2 |
| windows over 32 M steps, GRCh38 / CHM13 | 4 / 3 | 4 / 3 | 4 / 3 |

1.1.0's CHM13 file, filed by first visit, has 105,863,387 rows.

## Decision

1. **Nearest pass by predicted offset.** A step on a node the reference passes
   more than once takes the pass on the same reference sequence nearest the
   offset that the path's last placed step plus the bp walked since predict.
   On genome-wide MC, nearest by chunk gives the same GRCh38 file and a CHM13
   file with 0.011% more pieces (see [Genome-wide MC](#genome-wide-mc)), so the
   rule the code implements stays
2. **Gated, guarded stay.** A run of steps filed away from the current piece's
   chunk stays in that piece when all of these hold:
   - the path returns to exactly that chunk
   - the run holds at most `--stay` bp on reference nodes (default 311, pggb's
     `-k 311` minimum match; 0 turns it off)
   - one of those nodes is one the reference passes more than once
   - each node in the run that the reference passes once lies on the piece's
     sequence, at most `max(chunk, maxnode) / chunk` chunks after the piece's

   A reference that passes each node once gets the same rows at any stay, and
   a window reads every piece with a step on a node in it that the reference
   passes once. A run that never returns always starts a new piece, and the
   reference's own paths keep filing by their own offsets. Absorbed steps
   become route interior, so a route can hold another chunk's reference nodes.
   The header records the value as `stay:i:`. See [Gated stay](#gated-stay)
3. **Readers place a node at the reference position from a `ref` row of a read
   chunk** whenever one exists, from the row whose path sorts first, at its
   earliest start, when several do; other nodes take haplotype offsets.
   graph-walks implements this from 3.0
4. **`maxnode` counts reference nodes only,** since only they span reference
   coordinates. pggb chr22's longest node, 5.8 Mb, is off both references, and
   the lookback falls from 89 chunks to 16 on GRCh38 and 31 on CHM13
5. **Format 4.** Rules 2 and 3 make a format: the header says `format:i:4`,
   and readers refuse every other format. Nothing reads format 3 any more

## Alternatives

| option | outcome |
|---|---|
| first visit (format 3) | fails 4, 5 and 6 on pggb |
| nearest pass alone | fails 4 and 5: 45 pieces per pair, 44% piece precision |
| nearest by chunk against nearest by predicted offset | within 0.3 point on every chr22 measure; genome-wide MC GRCh38 files identical and CHM13 within 0.011% of pieces; the offset rule stays because the code implements it and the measures do not separate them |
| stay capped at 4 kb away | hides real passages: about 1,300–1,700 per reference between 312 bp and 4 kb align where they went |
| stay without nearest pass | strict recall falls to 90% on CHM13 and 91% in GRCh38's LCR22B–D |
| ungated stay | changes rows on references that pass each node once, and hides real short SVs from their own window |
| gate without a guard | fewest pieces, but files a step on a node passed once where its window cannot read it |
| guard on every node | restores stay 0's recall to the last pair, at three to four times the pieces of guarding only nodes passed once |
| default stay 0, pggb opts in | pggb users get 45–52 pieces per pair unless they know the flag |
| a format 4 marker only in files with an absorbed run | needless with no backward compatibility: every reader refuses format 3 |
| excursion rows for paralog jumps | every lost (haplotype, chunk) pair is filed elsewhere, none absent, so the rows have nothing to add |
| graph preprocessing (chop, unchop, GBZ) | keeps the collapsed repeats |
| placement from impg alignments | a candidate for a later ADR, scored with the same criteria |
| refusing graphs whose references revisit nodes | rejected: pggb graphs are in scope |

## Consequences

- Row syntax is unchanged, but format 3 readers refuse the new files, and
  graph-walks 3 refuses format 3. Hosted files have to be rebuilt
- A window no longer lists a haplotype whose only presence there is a run of
  311 bp or less over nodes the reference passes more than once
- A step on a node the reference passes more than once can lie in a piece
  filed beyond the window's lookback; a step on a node it passes once cannot
- pggb's CHM13 short arm still exceeds the step budget in hundreds of windows
  (516 over 32 M steps at stay 311 and 1024), because filing moves no steps
  out of a chunk
