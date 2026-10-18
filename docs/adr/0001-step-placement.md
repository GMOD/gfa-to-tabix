# ADR 0001: Where a walk file files a haplotype step

- **Status:** proposed, 2026-10-18
- **Decides:** which reference chunk `--walks` files each step of a non-reference
  path under, when the reference passes the step's node more than once
- **Measured by:** the [success criteria](#success-criteria) below, with
  `scripts/walks-truth.py`. A later proposal that replaces this one reports the
  same table on the same data

## Context

- Format 3 gives each node one position, the reference's first visit, and
  files a haplotype's step on a reference node under that position's chunk
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
| 2 | MC unchanged | files for a reference that revisits no node | byte-identical to main |
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

## Decision (proposed)

1. **Nearest pass.** A step on a node the reference passes more than once
   takes the pass on the same reference sequence nearest the path's last
   placed step: nearest its chunk, or nearest the offset predicted from it
   plus the bp walked since. The genome-wide MC CHM13 comparison picks between
   the two
2. **Stay.** A run of steps filed away from the current piece's chunk stays in
   that piece when the path returns to exactly that chunk and the run holds at
   most 311 bp on reference nodes (pggb's `-k 311` minimum match). A run that
   never returns always starts a new piece, and the reference's own paths keep
   filing by their own offsets. Absorbed steps become route interior, so a
   route can hold another chunk's reference nodes
3. **Readers place a node at the reference position from a `ref` row of a read
   chunk** whenever one exists; other nodes take haplotype offsets.
   graph-walks commit 79634c3 implements this, and it must ship before any file
   written under rule 2
4. **`maxnode` counts reference nodes only,** since only they span reference
   coordinates. pggb chr22's longest node, 5.8 Mb, is off both references

## Alternatives

| option | outcome |
|---|---|
| first visit (format 3) | fails 4, 5 and 6 on pggb |
| nearest pass alone | fails 4 and 5: 45 pieces per pair, 44% piece precision |
| nearest by chunk against nearest by predicted offset | equal on every chr22 measure; chosen by the genome-wide MC CHM13 comparison |
| stay capped at 4 kb away | hides real passages: about 1,300–1,700 per reference between 312 bp and 4 kb align where they went |
| stay without nearest pass | strict recall falls to 90% on CHM13 and 91% in GRCh38's LCR22B–D |
| excursion rows for paralog jumps | every lost (haplotype, chunk) pair is filed elsewhere, none absent, so the rows have nothing to add |
| graph preprocessing (chop, unchop, GBZ) | keeps the collapsed repeats |
| placement from impg alignments | a candidate for a later ADR, scored with the same criteria |
| refusing graphs whose references revisit nodes | rejected: pggb graphs are in scope |

## Consequences

- Row syntax is unchanged, so format 3 readers parse the new files. A reader
  without rule 3 draws absorbed reference nodes at haplotype offsets
- A window no longer lists a haplotype whose only presence there is a run of
  311 bp or less of reference nodes
- pggb's CHM13 short arm still exceeds the step budget in 12–14 windows,
  because filing moves no steps out of a chunk
