I measured all three. R1 is byte-identical on MC as expected, but on pggb it makes the file 26.5% bigger and drops 31% of the placed haplotype bp. R2 saves little and removes no mechanism. R3 is mostly already format 7.

My verdicts: adopt R1 with a change, reject R2, adopt R3 with a change.

How it was measured: a bundle of main (1061737) went into `~/work/reshape` on ada, with worktrees `base` and `r1`. The baseline rebuilds are byte-identical to `~/work/tidy7/new.*`. I rewrote the window harness in Python, `winbytes.py`; on arbA's own s7 files it reproduces all 2,400 windows in `res4/` exactly (29/53, 70/246, 738 KB). KB means 1,000 bytes. Every number below is in `~/work/reshape/out/results.txt`, also copied to `/home/cdiesh/work/review-2026-11-06/spike/out/`.

## R1, placement only on nodes the reference passes once

R1 is a 5-line `visits_along` change (`patches/0002-*`).

| | MC chr22 | pggb chrY, now | pggb chrY, R1 |
|---|---|---|---|
| data file | 58.49 MB, identical (same sha256) | 187.16 MB | 236.83 MB (+26.5%) |
| tile / departures / detail units | — | 12.2 / 14.6 / 160.3 MB | 10.5 / 10.5 / 215.9 MB |
| 1 kb, median / p90 | 28.8 / 52.5, identical | 69.8 / 246.1 | 67.9 / 226.7 |
| 64 kb | 57.8 / 112.9 | 120.6 / 456.1 | 119.3 / 365.3 |
| 1 Mb | 500.5 / 683.9 | 736.7 / 3,551 | 769.3 / 2,132 |
| departure records (0 own bp) | 24,648 (18.7%) | 425,040 (86.5%) | 246,739 (2.4%) |
| haplotype bp placed | 16.25 Gbp, unchanged | 2.815 Gbp | 1.950 Gbp (−30.7%) |
| steps placed | — | 175.5 M | 19.7 M (−89%) |
| copies named | 0 | 284,114 | 0 |
| paths abridged | — | 693 | 1,565 |

- **MC:** the expected result is confirmed. The file is byte-identical, with `revisited:i:0`.
- **Validity:** `verify7.py` passes, and `claims7.py` reports 0 failures on every claim (`r1.*.verify.txt`, `r1.*.claims.txt`).
- **`--stay` does nothing under R1.** Builds at 311 and at 0 differ only in the header tag.
- **Where the file grows:** all of the growth is in detail units, which no window reads. Steps that used to follow R for free are now explicit route interiors.
- **Windows over collapsed repeats** (`inspect.pggbY.jsonl`, `nodeat.py`), each 1 kb with ±1 kb context:

| window | what is there | now | R1 |
|---|---|---|---|
| chrY:23,600,000–23,601,000 | every node, e.g. 369836 (298 bp), passed 4 times: at 21.99, 22.59, 23.60 and 26.07 Mb | 110 KB; 91 haplotypes in walk rows; 6,333 records, 98% with 0 own bp | 74 KB; 0 walk rows; all 124 haplotypes appear only as 2,760 records spanning the window, median 4,095 own bp |
| chrY:18,550,000–18,551,000 | node 419828 (603 bp), passed at 18,550,746 and 18,769,052 | 100 KB; 46 haplotypes in walk rows | 101 KB; 0 walk rows; 121 haplotypes as records |
| chrY:24,030,000–24,031,000 | node 299797 (1,746 bp), passed at 24.03 and 25.64 Mb | 139 KB | 129 KB; walk rows are nearly the same (195 against 200) |
| chrY:14,500,000–14,501,000 (control, no revisited node) | — | 57 KB | 55 KB |

- **What R1 deletes from the spec:** claims C2, C21–C24, C53, C62, C70, C120 and the Passes part of C79. It also deletes the "Exact and chosen" section, `--stay`, the `stay:i:` header tag, `@k`/`:k`, and `leavePasses`/`rejoinPasses`.
- **What it deletes from the code**, about 270 lines:
  - in walks.rs: `stay_home` (33 lines), `rehome` (46), `visit_near` (20), `predict` (8), the pass index inside `index_visits` (about 20), and the `--stay` plumbing (20)
  - in routes.rs: the occurrence helpers (31) and the copy encoding and decoding (about 60)
- **Tests:** 10 tests now fail, each one a deleted rule (`r1.cargo-test.txt`).
- **What R1 loses:**
  - 865 Mbp of haplotype sequence no longer has a position, though in the current file those positions were a placement choice.
  - Every haplotype vanishes from walk rows inside collapsed repeats.
  - The file is 26.5% bigger.
  - The 1 Mb median rises 4%.
- **Verdict: adopt with a change.** Keep `passes` on `ref` rows, or turn it into a collapsed mask. It becomes the only thing that tells a viewer why no haplotype is placed over a stretch. Drop everything else listed above.

### Alignment-based placement
Nothing on ada provides it for pggb chrY. There is no wfmash PAF for HPRC chrY. `~/hprc_multiway/build/hprc_multiway_gfa.paf` covers 8 haplotypes and is derived from the MC graph's shared nodes, with only 63 rows on chrY, so it is MC placement, not an alignment.

wfmash, impg 0.5.0, minimap2 and vg are installed, and `~/work/arb-format-opus/in/grch38.gbz` is there. Two ways to get it:
- **Cheapest:** build chrY from the MC GRCh38 GBZ (vg extract, then `--walks`), which has `revisited:i:0` by construction.
- **For pggb itself:** align each chrY contig with minimap2 `-x asm5` (roughly 1–3 CPU-hours), then add a writer mode that lifts each revisited-node step through the PAF to a pass. That is about 200 lines.
- **Caveat:** palindrome arms are near-identical, so the aligner also picks a copy (MAPQ 0) unless a contig spans the whole palindrome.

## R2, departures as neighbour fields
Simulated by `r2sim.py`: it rewrites every tile and recompresses it the same way (BGZF, deflate level 7) to measure the change.

| | MC | pggb | R1 + R2 on pggb |
|---|---|---|---|
| file | 57.89 MB (−1.0%) | 184.42 MB (−1.5%) | 235.44 MB |
| 1 kb | 27.8 / 49.1 | 68.9 / 247.7 | 65.6 / 226.1 |
| 64 kb | 55.3 / 111.2 | 118.6 / 463.2 | 119.0 / 366.0 |
| 1 Mb | 483.0 / 659.4 | 714.8 / 2,574 | 766.6 / 1,965 |
| records still in the pyramid | 1,095 (4.4%) | 159,124 (37%) | 114,554 (46%) |

- **What R2 removes:** `ownTiles` almost entirely. It names a tile other than the leave piece's in only 34 MC records and no pggb records. R2 also removes the duplicate-line drop for most records.
- **What it keeps:** the `departure` kind, its extent rule (C83), the pyramid (C43, C88, C89) and the duplicate drop all remain for the records a window can reach without reading either piece. So the same departure ends up encoded two ways.
- **Verdict: reject.** It gains 0–4% at the median and removes no mechanism. The only large gain, pggb 1 Mb p90 (−28%), R1 already gets (−40%).

## R3, one table per sequence
Arithmetic in `r3.py`, over `~/work/s7-genome/res/structure.*.json` (the prototype converter's files) and report.md.

| | open now: median / max | open with detail entries split out: median / max |
|---|---|---|
| GRCh38, 24 chromosomes | 86.7 / 192.2 KiB (chr9) | 69.7 / 121.3 KiB |
| CHM13 | 84.8 / 173.7 KiB | 63.8 / 114.8 KiB |

- **Biggest drops in open cost:** GRCh38 chr9 192→69 KiB, CHM13 chr14 116→49 KiB.
- **First view:** GRCh38 chr1 goes from 211 to about 144 KiB, chr22 from 62 to about 36 KiB.
- **Format 7 already has the root table.** The `.idx` is a root table pointing at per-sequence tables. henli-problem's "183 KB of the 211 KB first view is the whole-genome unit table" is wrong: 183 KB is chr1's own table, and the directory is 7.9 KB. So "chr22 open ≈ 8 KB" can't happen; with the split it is about 30 KiB.
- **What it loses:** one more round trip the first time a sequence's detail is expanded.
- **Verdict: adopt with a change.** List the detail table as one `#entry` in the sequence's table, so the directory, which every open reads, doesn't grow.

Everything is in `/home/cdiesh/work/review-2026-11-06/spike/`:
- `scripts/`, including the R1 patch scripts `stats.py` and `r1.py`
- `patches/`, the R1 branch from ada as patches
- `out/`, with `results.txt` as the summary table

Nothing was committed to the local repo. The `claims7` shards on ada were left running.