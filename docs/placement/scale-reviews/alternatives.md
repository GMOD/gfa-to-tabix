I've read the draft, the five TSVs, the spec sections and ADRs 0004/0010/0012/0016; here is the review.

**Where the draft is wrong or overstated**

- **Missing file:** `runs/scale/warm.query.tsv` does not exist. `runs/scale/t.query.tsv` has one position at 464 and 2000 only, so no 4-haplotype read is measured at 5,000.
- **"About half of every tile's walks move":**
  - At 5,000, 550 of 776 tiles have a blocks unit; at 2,000, 422 do (`scale-files.tsv`).
  - `scale-distinct.tsv` median kept rows per sampled tile are 1,868 of 5,000 (63% moved) and 1,778 of 2,000 (11% moved).
- **1 Mb medians:** over the 32 non-empty positions I get 0.50 / 1.18 / 1.56 MB (default) and 0.51 / 1.56 / 3.46 MB (off), about 8% above the draft's. The 100 kb figures check out.
- **The 4-haplotype read under default budgets is understated:**
  - At 2,000 / 1 Mb, `t.query.tsv` shows haps4 reading 1,576,066 bytes against 1,305,242 expanded, so blocks units are being read.
  - At 5,000 the median blocks bytes per 100 kb (301 kB) exceed the tiles (271 kB). The worst case is about 572 kB, the same as off's 560 kB.
- **Table cost is backwards relative to today:** 39k entries at 8–16 B/entry is roughly 0.3–0.6 MB (my estimate from 13.96 MB / 1.73M entries and 22 kB / 1,369). That is 25–60× off's 22 kB but 20–40× smaller than the default's 14.0 MB.
- **The gain is unmeasured:** no TSV splits tile bytes into shared rows and walk rows, so "4/50 of the walk rows" has no byte figure.
- **Synthetic duplicates flatter in-tile compression:** 43% of kept walk rows at 5,000 duplicate another row, against about 1% for real haplotypes. Real tiles, and per-group units especially, would compress worse.
- **Unmentioned build failure:** the first 5000-off build died with "a step placed at 38417438 is not on the tile's reference path", and the rerun on other CPUs succeeded (`scale-alt-builds.txt`). Explain this before relying on any off-path result.
- **ADR 0011's trigger is not addressed:** ADR 0016 applies it, and it needs an issues-log entry from a consumer on a hosted graph. Synthetic mosaics meet neither condition.

**Alternatives, ranked by what they buy at 5,000 against cost**

- **First: writer policy, abridge outliers only.** Format 8 leaves the budgets and which lines move to the writer (spec, "What a reader relies on"), so there is no reader change and no new format.
  - Two measured builds bracket it:

    | Build | File | Table | Worst tile | Worst 100 kb all-haplotype read |
    |---|---|---|---|---|
    | off | 142 MB | 22 kB | 8.2 MB | 6.8 MB |
    | 4× budgets (s4m) | 778 MB | 1.28 MB | 385 kB | 1.70 MB |

  - Off's worst 100 kb window also gunzips to 42.6 MB of tile text, which is ADR 0012's rejected "no abridging".
  - 4× still abridges 115 tiles into 149,615 detail units.
  - The untested target is a step budget scaled by haplotype count, about 10.8M steps. At 464 the default abridged only 18 tiles.
  - The bytes budget is not what trips: 5000-off median text is about 1.6 MB a tile.
  - Buys: file down about 13×, table down 14 MB → tens of kB. The all-haplotype 100 kb read is unchanged (594 against 615 kB).
  - Costs: the best-case 4-haplotype read doubles, 271 → 560 kB per 100 kb and 1.56 → 3.46 MB per 1 Mb.
- **Second: smaller `--tile`.** It is also writer-only, lowers per-tile steps and narrows 10 kb reads, but it is unmeasured. Each tile still holds all 5,000 walk rows, so this is a test to run, not a recommendation.
- **Third: detail units per tile and group.** A format change; ADR 0012 rejected "spatially indexed detail units" as unmeasured.
  - It targets the real waste: the moved rows cost 1,750 MB as 1.73M units (median 658 B) against about 87 MB in-tile (137 − 50 MB).
  - It is only needed if ordinary tiles stay abridged, which the first option removes.
- **Fourth: paged table.** A format change, since ADR 0010 readers scan one whole table. It fixes the 14 MB open and leaves the 1.75 GB file.
- **Fifth: the draft's per-group tile units.**
  - Against the first option it could cut the 4-haplotype read from 560 kB to perhaps 140 kB per 100 kb. That is my crude estimate, taking shared rows as about 100 kB.
  - Costs: every reader changes, up to k+1 requests per tile, and small-unit compression loss, which the detail units show at 20×.
  - It does nothing for the all-haplotype cut.
- **Last: no change.** 1,885 MB, with 14.0 MB fetched before the first cut (76× hosted chr1's 183 kB table, ADR 0010). Abridging saves the all-haplotype cut nothing, and the 4-haplotype view at most 289 kB per 100 kb.

**Recommendation**

- Build 5,000 with haplotype-scaled budgets and measure haps4 reads at 5,000 before proposing any format change.
- The per-group proposal only has a case if the 560 kB / 3.46 MB 4-haplotype reads prove unacceptable in a consumer.
