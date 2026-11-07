**Decision: B for placement, R3 with the spike's change, R2 rejected.**

**Placement: B.** Place a step only on a node its reference passes once. Keep `passes` on `ref` rows (already `.` on MC, so byte-identical there). Delete nearest pass, `--stay`, `stay:i:`, `@k`/`:k`, `leavePasses`/`rejoinPasses`, "Exact and chosen", about 270 lines and 12 claims.

The numbers that decided it:

- A's rows in collapsed repeats are not information. Only 35.9% of pggb pieces land within 10 kb of MC's placement of the same contig (open-problems.md). At chrY:23.6 Mb, A draws 91 haplotypes along a reference that passes every node there four times, plus 6,333 departure records, 98% with 0 own bp: arcs to 21.99 and 26.07 Mb no haplotype makes. That is a fake coordinate with a jump drawn to justify it.
- B's windows are honest and not empty. The same window: 124 haplotypes, all present as records spanning it, median 4,095 own bp, 74 KB against 110 KB. `passes` tells the viewer why: "reference passes this stretch 4 times; unplaced". Records with 0 own bp fall from 367,486 to 5,858, so a departure record now almost always states real sequence.
- B keeps what is exact. 1.950 of A's 2.815 Gbp placed survive, and at chrY:24.03 Mb (one node passed twice) B is 195 walk rows against A's 200. C would throw away 69% exact placement to avoid writing 31% guessed placement, and needs a refusal rule where B needs none: B is the MC code path with nothing added.
- Bytes that a window reads fall: p90 1 kb 246→227 KB, 64 kb 456→365, 1 Mb 3,551→2,132. The +26.5% file is all detail units no window reads.
- `--stay` is inert under B (r1stay0 differs only in the header tag).
- Hosted demos: no pggb walk file exists. `demos/hprc`, `hprc_multiway`, jb2hubs `hprc-grch38.json` name only `hprc_v2_1_walks` (MC) and its hs1 twin; `ecoli_pangenome` hosts pggb as graph index, untangle, PIF and VCF tracks, no walks. Neither B nor C costs a user today.

**R3: adopt, one `#entry` for the detail table inside the sequence's table.** Open median 86.7→69.7 KiB, GRCh38 chr9 192→69, CHM13 chr14 116→49; chr22 first view 62→36. The directory every open reads does not grow. It matters more under B, where detail is 91% of pggb's file. Cost: one round trip the first time a sequence's abridged path is expanded, a rare click.

**R2: reject.** −1.0% MC, −1.5% pggb, 0–4% at the median, and 37–46% of records still need the pyramid, so one departure is encoded two ways. It adds a mechanism; it removes none.

**ADR Consequences:**

- A position in a walk file is a fact of the graph: a step is placed only on a node its reference passes once. On a reference that passes every node once (`revisited:i:0`, all MC graphs on their own reference) the file is byte-identical to format 7.
- On a reference that revisits nodes, haplotypes crossing those nodes appear as departure records spanning the stretch, whose `ownBp` is sequence the file does not place, not sequence the reference lacks. `passes` on `ref` rows says where and why. Viewers draw the span; they must not label it an insertion.
- pggb chrY: file 187→237 MB, all detail; window p90 lower at every size; 31% less haplotype bp placed, 89% fewer steps.
- Deleted: `--stay`, `stay:i:`, `@k`/`:k`, `leavePasses`/`rejoinPasses`, ADR 0001's rule, claims C2, C21–C24, C53, C62, C70, C120, C79's Passes part, 10 tests.
- Placement in collapsed repeats, if wanted, comes from an alignment as writer input, recorded in the header; it changes no row kind.

**Strongest argument against:** pggb is the only graph with HPRC's chrY palindromes and acrocentric arms, and B shows a user zoomed there nothing but spanning bars for 865 Mbp of haplotype sequence; A at least shows which haplotypes carry the repeat. The reply: A showed that too, as records, and the rows it added were right about a third of the time.