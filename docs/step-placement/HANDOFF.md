# Handoff: step placement and `--stay`

Status on 2026-10-20: gfa-to-tabix 1.2.0 writes walk format 4 with nearest-pass
placement and the gated, guarded stay (default 311), and @jbrowse/graph-walks
3.0.0 reads format 4 only. [ADR 0001](../adr/0001-step-placement.md) records
the criteria, the measurements and the decision;
[walks-format.md](../walks-format.md) states the rules.

- **Decided by:** six independent reviews and a final one, then pggb chr22
  builds of four stay variants and genome-wide Minigraph-Cactus (MC) builds
- **MC GRCh38:** rows at stay 311, at stay 0 and in the hosted 1.1.0 file are
  byte-identical
- **pggb chr22:** 8.6 (GRCh38) and 16.8 (CHM13) pieces per haplotype-chunk
  pair, against 45 and 52 at stay 0, with strict recall within 0.03 point of
  stay 0

## Follow-ups

1. **Readers of the hosted sets: done 2026-10-20.** Every reader pins
   graph-walks 3.0.0 and names the `-f4` URLs, and jbrowse.org no longer
   hosts the `-f2` or `-f3` sets. graph-walks refuses any walk file but
   format 4
2. **Giant windows.** [ADR 0003](../adr/0003-long-node-lookback.md) removed
   the ones `maxnode`'s lookback caused. What remains on pggb chr22 is 25
   GRCh38 and 23 CHM13 windows over 8 MB, satellite and rDNA arrays pggb
   collapses into looping nodes, at most 168 MB. Next: explain them in the
   reader (what the region is, that zooming won't help, a way to load
   anyway), then decide whether a format should summarize them
3. **Fragmentation on pggb.** The guard turns away runs over nodes passed once
   that lie beyond the lookback; 38% of the runs a guard on every node turned
   away stayed within the lookback in the other direction. Filing a piece
   under the earliest chunk its absorbed steps touch would admit those, but a
   walk row names positions on its own chunk's R, so this changes the format
4. **Criterion 3 per region.** The per-region check at *L* = 1 lacks a
   first-visit row. Score first-visit pggb chr22 at *L* = 1 with
   `--regions scripts/walks-truth-regions.tsv`
5. **Reconcile revisit counts.** The ADR context says genome-wide MC CHM13
   revisits 209,578 nodes; an earlier build log says 512,386 nodes are visited
   in more than one chunk
6. **Rescan cost.** `stay_home` (`src/walks.rs`) can rescan a stretch about
   stay ÷ shortest-reference-node-length times where chunk changes are dense.
   The pggb chr22 builds ran faster than 1.1.0, so measure before changing
7. **Docs.** Add the revisit table's memory (16–24 bytes per pass) to the
   Scale section of `docs/walks.md`
8. **Fuzz test.** An earlier session's `fuzz-walks.rs` (`fuzz_rebuilds`) found
   no defect in 12,400 graphs; promote it into `tests/` if it should run in CI

## Where things are

- **ada, `~/nearest-main/gated/`:** `gated.sh` and `unique.sh` (pggb chr22
  variants, scored), `genome.sh` and `genome2.sh` (genome-wide MC), with their
  `.out` files
- **ada, `~/nearest-main/`:** `walks-truth.py`, the earlier sweep in `stay/`,
  and the regions and lift tables the scoring reads
