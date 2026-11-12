# 19 P line names against the pipelines that write them

From the review of [the proposal](proposal.md) by a user of the tools: each
name as vg 1.69.0 or odgi 0.9.4 wrote it at the end of the pipeline in
`origin`, and `truth`, where its line lies on its contig. `A` to `O` are the
proposal's four sets and `M+` the reviewer's own reading; none is the
reading [ADR 0014](../../../adr/0014-p-line-names.md) decided, which
[p-names.tsv](../p-names.tsv) holds. RIGHT is the truth, `local` a reading under
another path name than the truth's, WRONG the true path from a false start.

| name | bp | origin | truth | A today | M mended | T tools | O opaque | M+ |
|---|---|---|---|---|---|---|---|---|
| `H#1#c` | 16 | pggb | `H#1#c@0` | RIGHT `H#1#c@0` | RIGHT `H#1#c@0` | RIGHT `H#1#c@0` | RIGHT `H#1#c@0` | RIGHT `H#1#c@0` |
| `grch38#chr6:31972046-32055647` | 83601 | HPRC v1 pggb + odgi extract (odgi test chr6.C4) | `grch38#chr6@31972046` | RIGHT `grch38#chr6@31972046` | RIGHT `grch38#chr6@31972046` | RIGHT `grch38#chr6@31972046` | local `grch38#chr6:31972046-32055647@0` | RIGHT `grch38#chr6@31972046` |
| `gi|568815592:32578768-32589835` | 11068 | pggb README example, samtools region name | `gi|568815592@32578767` | WRONG `gi|568815592@32578768` | local `gi|568815592:32578768-32589835@0` | local `gi|568815592:32578768-32589835@0` | local `gi|568815592:32578768-32589835@0` | RIGHT `gi|568815592@32578767` |
| `H#1#c#0` | 16 | vg on pggb | `H#1#c@0` | RIGHT `H#1#c@0` | RIGHT `H#1#c@0` | RIGHT `H#1#c@0` | local `H#1#c#0@0` | RIGHT `H#1#c@0` |
| `H#1#c#0[10-16]` | 6 | vg chunk on pggb; MC .og / -gfW clipped piece | `H#1#c@10` | local `H#1#c#0@10` | RIGHT `H#1#c@10` | RIGHT `H#1#c@10` | local `H#1#c#0[10-16]@0` | RIGHT `H#1#c@10` |
| `H#1#c#100` | 14 | MC GBZ -> P (vg convert -f [-W], vg paths -F) | `H#1#c@100` | RIGHT `H#1#c@100` | RIGHT `H#1#c@100` | refused | local `H#1#c#100@0` | RIGHT `H#1#c@100` |
| `K#2#d[7]` | 24 | MC GBZ, reference-sense piece | `K#2#d@7` | RIGHT `K#2#d@7` | RIGHT `K#2#d@7` | RIGHT `K#2#d@7` | local `K#2#d[7]@0` | RIGHT `K#2#d@7` |
| `H#1#c#100[6-14]` | 8 | MC GBZ -> pg -> vg chunk | `H#1#c@106` | local `H#1#c#100@6` | refused | refused | local `H#1#c#100[6-14]@0` | local `H#1#c#100@6` |
| `H#1#c#0:6-14` | 8 | vg P form (MC .og, vg on pggb) -> odgi extract | `H#1#c@6` | local `H#1#c#0@6` | local `H#1#c#0@6` | local `H#1#c#0@6` | local `H#1#c#0:6-14@0` | RIGHT `H#1#c@6` |
| `H#1#c#0[100-114]:6-14` | 8 | MC .og / -gfW -> odgi extract | `H#1#c@106` | local `H#1#c#0[100-114]@6` | local `H#1#c#0[100-114]@6` | local `H#1#c#0[100-114]@6` | local `H#1#c#0[100-114]:6-14@0` | RIGHT `H#1#c@106` |
| `H#1#c#100:6-14` | 8 | MC GBZ -W -> odgi extract | `H#1#c@106` | local `H#1#c#100@6` | local `H#1#c#100@6` | local `H#1#c#100@6` | local `H#1#c#100:6-14@0` | local `H#1#c#100@6` |
| `H#1#c:5-21#0` | 16 | odgi extract -> vg (W form: W H 1 c:5-21 0 16) | `H#1#c@5` | local `H#1#c:5-21@0` | RIGHT `H#1#c@5` | RIGHT `H#1#c@5` | local `H#1#c:5-21#0@0` | local `H#1#c:5-21@0` |
| `H#1#c:6-10:0-4` | 4 | odgi extract twice | `H#1#c@6` | local `H#1#c:6-10@0` | local `H#1#c:6-10@0` | local `H#1#c:6-10@0` | local `H#1#c:6-10:0-4@0` | local `H#1#c:6-10@0` |
| `S1#0#chr1#2` | 70 | vg, VCF-phased, lone third block | `S1#0#chr1@50` | WRONG `S1#0#chr1@2` | WRONG `S1#0#chr1@2` | refused | local `S1#0#chr1#2@0` | WRONG `S1#0#chr1@2` |
| `S1#0#chr1#2[40-56]` | 16 | vg chunk of VCF-phased pg | `S1#0#chr1@90` | local `S1#0#chr1#2@40` | refused | refused | local `S1#0#chr1#2[40-56]@0` | local `S1#0#chr1#2@40` |
| `H#1#c[100-900]` | 16 | stated end wrong | `refuse` | WRONG `H#1#c@100` (end unchecked) | RIGHT `refused` | RIGHT `refused` | local `H#1#c[100-900]@0` | RIGHT `refused` |
| `H#1#HLA:DRB1` | 16 | colon in contig | `H#1#HLA:DRB1@0` | RIGHT `H#1#HLA:DRB1@0` | RIGHT `H#1#HLA:DRB1@0` | RIGHT `H#1#HLA:DRB1@0` | RIGHT `H#1#HLA:DRB1@0` | RIGHT `H#1#HLA:DRB1@0` |
| `[5]` | 16 | suffix alone | `[5]@0` | WRONG (empty path) `@5` | RIGHT `[5]@0` | RIGHT `[5]@0` | RIGHT `[5]@0` | RIGHT `[5]@0` |
| `:5-21` | 16 | suffix alone | `:5-21@0` | WRONG (empty path) `@5` | RIGHT `:5-21@0` | RIGHT `:5-21@0` | RIGHT `:5-21@0` | RIGHT `:5-21@0` |
