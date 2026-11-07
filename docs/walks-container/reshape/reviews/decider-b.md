**Decision: B for placement, R3 with the spike's change, R2 rejected.**

**Placement: B.** Place a step only where its reference passes the node once; keep `passes` on `ref` rows and `revisited` in the header; delete nearest pass, `--stay`/`stay:i:`, `@k`/`:k`, `leavePasses`/`rejoinPasses`, "Exact and chosen", claims C2, C21–C24, C53, C62, C70, C120, the Passes part of C79, about 270 lines and 10 tests.

Numbers that decided it (`spike/out/results.txt`, `inspect.pggbY.jsonl`, `deps.*.json`, `docs/open-problems.md`):

- MC is byte-identical. B costs the only graph anyone hosts nothing: every `walksUri` in `jbrowse-components/demos/*/config.json` points at `hprc-v2.1-mc-grch38`; the E. coli pggb track has no walk file.
- A's coordinates in repeats are guesses: 35.6% of Yp11/Yq11 pieces and 50.5% elsewhere on chrY agree with MC's placement of the same contig. A coordinate right half the time, with no mark saying which half, is not a coordinate.
- A's departures are the rule, not the haplotype: 97% end on a revisited node, 87% carry 0 own bp. Under B every record end is once-passed (`revisited_end` 405,985 → 0), own-0 records fall 367,486 → 5,858. Every remaining departure is a fact of the graph.
- What a user sees at chrY:23.6 Mb (node passed at 21.99, 22.59, 23.60, 26.07 Mb): A draws 91 haplotypes on GRCh38 plus 6,333 hops, 98% zero-bp, which the viewer must already caption as "placement choice". B draws all 124 as "no step on GRCh38 across this stretch, median 4.1 kb of its own", and `passes` says the reference holds this node 4 times. Honest and readable, not useless: the haplotype, its order and its sequence are all there; only the unknowable copy is not.
- Windows get cheaper where it hurts: 1 kb p90 246 → 227 KB, 64 kb p90 456 → 365, 1 Mb p90 3,551 → 2,132, p99 5,846 → 3,234. The +26.5% file is all detail units no window reads.
- C refuses a whole file for a per-node problem. pggb chrY under B still places 1.95 Gbp, and at 24.03 Mb and the 14.5 Mb control B's walk rows equal A's (195/200, 117/117). B subsumes C: a file with `revisited:i:0` is exactly the C case.

**R3: adopt with the spike's change.** One `#entry` per sequence table for its detail entries. Median open 86.7 → 69.7 KiB, chr9 192 → 69, CHM13 chr14 116 → 49; chr1 first view 211 → about 144. The directory stays 7.9 KB. henli-fundamental's "chr22 open ≈ 8 KB" was wrong: format 7 already has the root table. B grows pggb's detail units 160 → 216 MB, which makes the split worth more, not less.

**R2: confirm reject.** −1.0% / −1.5% file, 0–4% median, and 37–46% of records still need the pyramid, so one departure is encoded two ways; its one big gain (1 Mb p90 −28%) B already beats (−40%).

**Consequences, as I'd write them:**

- Every position and every departure in a walk file is a fact of the graph. A haplotype's steps on nodes the reference passes more than once are route interior; across such a stretch it shows as a departure record with its own bp, and the `ref` row's `passes` says why nothing is placed there
- MC files are byte-identical. pggb chrY: 31% of haplotype bp and 89% of reference-node steps lose a position, the file grows 26.5% in detail units, p90 window bytes fall at every size
- graph-walks 6 drops the occurrence decoder and its 13 untested rules
- Alignment-guided placement, if ever built, is a later format with its own ADR; no hook is kept for it

**Strongest argument against:** B discards placements continuity makes near-certain, such as the 603 bp node at 18.55 Mb whose other pass is 220 kb away, and on pggb chr22 outside 2.8–26.7 Mb nearest pass agrees with MC 88.7% of the time. B cannot tell those from the Yq11 coin flips and throws all of them out, 865 Mbp on chrY, with no way to add them back short of a new format.