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

The candidate files themselves are on ada under `~/work/arb-arbA/out/` and
`~/work/arb-arbB/`; the inputs were the gfa-to-tabix 3.0.0 builds of HPRC
v2.1 Minigraph-Cactus chr22 (`~/work/rel3/mc22.GRCh38.walks.bed.gz`) and
HPRC release 2 pggb chrY (`~/work/pggbY.GRCh38.walks.bed.gz`), both on
GRCh38.
- `genome/`: the genome-wide check of the prototype on GRCh38 and CHM13
  by the session deploying the walk files: `report.md`, `summary.md`, its
  scripts and `res/` (copied from ada `~/work/s7-genome/res/`; the report's
  paths name that directory)
