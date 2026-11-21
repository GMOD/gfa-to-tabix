**Verdict**

- No, not on these numbers. Every cost that grows faster than the haplotype count comes from the default abridge budgets, which is writer policy. A per-group split touches none of those costs.
- The split does cut one cost a lot: tile bytes for a few-haplotype view. That cost is small in absolute terms and was never measured at 5,000.

**Costs that grow with haplotypes (464 → 2000 → 5000; `scale-files.tsv`, `scale-alt-files.tsv`)**

- **File size, default budgets:** 59.1 → 463.9 → 1,885.3 MB, 32x for 10.8x the haplotypes. Detail units are 66.5% / 87.5% / 92.8% of it. A split does not reduce this.
- **Detail-unit overhead:** tiles are 137.2 MB with abridging off and 50.1 MB by default at 5,000. So about 87 MB of rows became 1,750 MB of detail units, 20x (13x at 2,000).
- **Sequence table:** 46,338 → 1,937,087 → 13,955,363 B, about 8 B per unit, all detail entries. With abridging off it is 21–22 kB. A split does not reduce it and adds 38,800 entries.
- **Blocks units:** 0.6 → 15.5 → 66.7 MB, default budgets only. A split does not reduce them.
- **Tile bytes per 100 kb window, abridging off:** 80 → 243 → 560 kB, 7x. This is the only cost a split reduces, and only for few-haplotype views.
- **Departures:** 3.3 → 8.1 → 16.9 kB per 100 kb window. Negligible, and unaffected.
- **All-haplotype cuts:** irreducible by any split. They already hit `NodeLimitError` at 2,000 haplotypes and 100 kb (`runs/scale/t.query.tsv`).

**What the split would buy**

- I gunzipped three tiles of `alt/mc22.5000.off2.GRCh38.walks.gz` (20512768, 35454976, 46661632). Walk rows are 146–209 kB of each 166–235 kB tile, about 88%.
- The shared rows (ref, nodes, route) compress to 3.4–5.1 kB alone and are identical at 464, 2,000 and 5,000.
- So 4 of 50 groups is roughly 20 kB per tile instead of about 200 kB, before the loss from compressing small units. The draft's gain is right in direction; these are the numbers it lacks.
- Against that, the added table entries cost about 0.3–0.6 MB at the 8–16 B per entry seen today, fetched whole before the first cut. That is about what the split saves on one 100 kb window (560 → ~60 kB).

**Where the draft's reading is wrong or overstated**

- **"About half of every tile's walks move":** the build logs give 223,030 of 1,083,462 walk rows at 2,000 (21%) and 1,740,726 of 2,702,989 at 5,000 (64%). My three default tiles at 5,000 have 3,141–3,360 abridged rows of about 5,000.
- **Mixed medians:** the 100 kb figures match medians over the 29–30 non-empty positions (79.8 / 211.0 / 270.7 kB; off 79.8 / 243.0 / 560.1; blocks 0 / 36.9 / 301.0). The 1 Mb figures are medians over all 40, including about 11 empty ones. Non-empty 1 Mb is 0.51 / 1.18 / 1.57 MB default and 0.52 / 1.59 / 3.58 MB off.
- **Missing comparison:** at 5,000 and 100 kb, `bytes_for` is 614.5 kB default against 593.5 kB off. A 4-haplotype view with any kept walk abridged reads 271 + 301 = 572 kB against 560 kB off. Default abridging buys nothing per median window at 5,000, for 13x the file and 630x the table.
- **`warm.query.tsv` is absent:** only a 3-line `warm.query.log` exists. `t.query.tsv` has one position, one run, load about 9, and no 5,000 rows. "A 4-haplotype view reads the same tiles" is measured only at 464 (85,979 B for both) and 2,000 (205,774 against 266,596 B at 100 kb).
- **Synthetic data flatters growth:** distinct walk rows are 98.7% of rows at 464, 69% at 2,000 and 57% at 5,000 (`scale-distinct.tsv`, 30 tiles). The 7x tile growth is partly this; a real cohort could be nearer 10.8x, about 0.85 MB per 100 kb.
- **"By haplotype count alone":** consistent with the data but not checked against the writer. Steps per tile are about 0.8M / 3.5M / 8.7M, and tile text at 5,000-off is about 1.6 MB, under the 3 MB byte budget.
- **Unmentioned build failure:** the first 5,000-off build exited 1 with `SYN1288#1#c2: a step placed at 38417438 is not on the tile's reference path` (`scale-alt-builds.txt`). The identical command rerun on other CPUs succeeded. The off numbers rest on a writer that failed once, unexplained.

**What abridging is actually for**

- Outlier tiles, which barely depend on haplotype count: the largest tile with abridging off is 4.3 / 7.2 / 8.2 MB, against 0.29 / 0.16 / 0.17 MB by default.
- The 4x budgets at 5,000 give 778 MB and a 1.28 MB table, which is still poor.
- This points to the draft's own alternative, abridging only outlier walks, as the first thing to measure, before any format change.

**Gaps before anyone decides**

- A 4-haplotype query at 5,000, default and off, at more than one position.
- The row-kind breakdown in the outlier tiles; I only checked median ones.
