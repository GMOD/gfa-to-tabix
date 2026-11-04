# The port of walk format 6, 2026-11-04

The writer in `src/` after the port (gfa-to-tabix 3.0, not released), built
on ada on the rebuild's graphs under nearest-pass placement: HPRC v2.1
Minigraph-Cactus chr22 (`mc22`) and HPRC release 2 pggb chrY (`pggbY`) and
chr22 (`pggb22`), on GRCh38, at the default options. Format 5 is the same
graphs built by 552b9c1, the commit before the port.

## Files

- `NAME.build.log`: the port's builds, with each phase's time and the
  process's peak memory so far
- `NAME.format5.build.log`: format 5's

## The port against the prototype and format 5

| | MC chr22 | pggb chrY | pggb chr22 |
|---|---|---|---|
| file | 59.43 MB | 196.6 MB | 1.68 GB |
| format 5 | 59.14 MB | 179.8 MB | 1.41 GB |
| against format 5 | +0.48% | +9.3% | +18.9% |
| rows differing from the prototype's, its cuts aside | 0 | 0 | 0 |
| build, s / peak GB | 56 / 4.1 | 115 / 8.0 | 693 / 22.4 \* |
| format 5 build, s / peak GB | 70 / 4.1 | 169 / 6.5 | 581 / 20.1 |
| the prototype's build, s / peak GB | 52 / 4.1 | 132 / 12.5 | 587 / 36.3 |

\* While other jobs loaded ada; the port's first build of pggb chr22, before
the memory changes below, took 508 s.

- The comparison with the rebuild's prototype (`out6/` on ada) sorts both
  files' rows after taking out what the port cut: the prototype's `pg`,
  `pr`, `ng` and `nr` tags (it had already dropped `pv` and `nx`), its
  abridged rows' `pages` column and `detail` by first page, and its detail
  rows' page positions. The headers differ only in `page:i:`
- With abridging off, MC chr22's `ref`, `nodes`, `route` and `walk` rows
  are the same in format 6 as in format 5, neighbour tags aside. GRCh38
  passes no MC node twice, so no row takes `@k` or step counts it did not
  take before, and the stay keeps nothing
- With the neighbour tags kept, the first build of the port was 59.77 MB on
  MC chr22 and 197.2 MB on pggb chrY: the tags cost 0.31 MB and 0.70 MB.
  On pggb chr22 they also moved 805 more paths to detail records, since
  they count toward the chunk byte budget

## Memory

- The build phase, which cuts the paths and files the departure records
  through an external sort, peaks at 1.1 GB on pggb chrY and 1.3 GB on pggb
  chr22 (2.83 billion steps). The rest is the encoding of the chunks, which
  the densest ones set: pggb chrY on 4 cores peaked at 10.2 GB against 11.7
  GB on 24, before the changes below
- A walk piece's positions are read from the sort straight into positions
  in the chunk's reference path, 4 bytes a step, never held as offsets;
  each route is held once; and a chunk over budget drops its whole-chunk
  encoding before encoding what it keeps. These took pggb chrY from 11.7 GB
  to 8.0 GB and pggb chr22 from 35.8 GB to 22.4 GB
- Format 6 still holds more than format 5: a step's position in the sorted
  rows, and more pieces, since the bounded stay keeps fewer runs home
  (5,569,569 pieces on pggb chr22 against 4,882,682)

## Checks

- `cargo test`: the walk tests check format 6 rows by hand, including
  departure records between pieces, across W lines, at contig ends, across
  reference sequences (`xb`), over a step on a 0 bp node between abutting W
  lines, and across a hole in the reference; `@k` and step counts where
  positions need them; and the bounded stay
- `audit6.py` over every walk fixture and five hand-made graphs in five
  option modes, and `fuzz6.sh` over 450 random graphs in six modes, which
  now draw references with holes and contigs whose W lines abut: no
  failures
- Extending the fuzz found one fault of the prototype, a departure missed
  across abutting W lines over a step on a 0 bp node (adjacency checked
  `ownBp` and not `ownSteps`), and two of the audit, both fixed: it took a
  run along R's bp from the reference's span, holes included, and it took
  a contig's unseen last W line for a field mismatch when no bp lay
  between
