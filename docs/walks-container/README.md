# Evidence for ADR 0010: the walk file's container

The reviews, arbitrations and measurements behind
[ADR 0010](../adr/0010-walks-unit-table.md), from 2026-11-05.

- `reviews/brief.md`: the brief four independent reviewers shared
- `reviews/history.md`, `native.md`, `cleansheet.md`, `reader.md`: their
  proposals. Each built its own harness, so their baselines for the shipped
  file differ (87 to 98 KB per 1 kb window); treat their numbers as the
  leads the arbiters re-measured. Their scripts are not committed
- `arbitration-brief.md`: the brief two independent arbiters shared,
  including the Heng Li lens and the candidates
- `arbA/decision.md`: arbiter A's decision (S, then S7), its cross-
  examination of arbiter B's design and the S7 spec and measurements.
  `arbA/scripts/` holds its harness (`measure.mjs`), the builders
  (`build.mjs`, `sfinal.mjs`, `s7.mjs`), the release checks
  (`verify7.mjs`), the cut check (`cutcheck.mjs`) and the summarisers;
  `arbA/results/res*/` the per-window results each table was summarised
  from (`res4/` and `res5/` are S7's), `win/` the seeded windows
- `arbB/decision.md`: arbiter B's decision (T64, then T64b), its cross-
  examination of S and its acceptance of S7 (`## S7 check`).
  `arbB/harness/` holds its HTTP range-logging server and measurer,
  `arbB/scripts/` its builders (`build_s7.py`, `build_t64b.py`,
  `csi_write.py`), `arbB/results/` its per-window results
- `prior-art-review.md`: an independent prior-art and failure-mode review
  of S7, whose changes S7 took
- `writer/`: gfa-to-tabix 4.0's format 7 writer checked against arbiter A's
  converter and `verify7.mjs` on MC chr22, pggb chrY, the test GFAs and
  fuzz graphs, and its compression level measured
  ([writer/README.md](writer/README.md))

The candidate files themselves are on ada under `~/work/arb-arbA/out/` and
`~/work/arb-arbB/`; the inputs were the gfa-to-tabix 3.0.0 builds of HPRC
v2.1 Minigraph-Cactus chr22 (`~/work/rel3/mc22.GRCh38.walks.bed.gz`) and
HPRC release 2 pggb chrY (`~/work/pggbY.GRCh38.walks.bed.gz`), both on
GRCh38.
- `freeze-review/`: two cases from the format 8 freeze review, each a GFA
  and what graph-walks cut from its walk file with every haplotype loaded,
  by `cut.mjs` (`node cut.mjs <walks.gz> <sequence> <start> <end>`):
  `g4/`, built with `--refs R --tile 20`, whose cut of `R#0#chr:0-20` and
  of 40-60 lacks GFA links at loaded nodes, and `zero/`, built with
  `--refs R --tile 100`, whose cut lists a link `1+>3+` the GFA lacks
  where a 0 bp segment is dropped. The walk files were built before the
  `#walks` line named its graph; neither cut depends on that
- `header-tags/`: the evidence of ADR 0015. `same-bytes.txt` compares
  walk files built with and without `graph:Z:` and `leftout:i:`.
  `leftout.c` counts, from GFA text alone with no writer code, the W and P
  lines with a step that visit no node of the reference, the count
  `leftout:i:` states; `fixture-compare.tsv` holds its count beside the
  writer's for each fixture and reference. Built with `gcc -O2 -o leftout
  leftout.c`, on the whole-genome graphs it
  was run as `vg convert -f <graph>.gbz | leftout <reference> pending.tmp
  names.txt`, each GBZ streamed in once, giving `ada-result.txt`
- `genome/`: the genome-wide check of the prototype on GRCh38 and CHM13
  by the session deploying the walk files: `report.md`, `summary.md`, its
  scripts and `res/` (copied from ada `~/work/s7-genome/res/`; the report's
  paths name that directory)
