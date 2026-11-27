---
name: jb2hubs-rows-and-lit-lanes-disagree
description: On genomes.jbrowse.org's pangenome pages a row, the lane it lights and the graph's node labels give different counts for the same thing; at AMY1 the "94.2 kb deletion" row (52 of 461) lights a lane of 363 haplotypes, most of which re-add the sequence, and at GSTM1 "GRCh38's structure 33%" lights 70.
metadata:
  repo: jb2hubs
---

# Rows, lit lanes and node shares disagree on the pangenome pages

Found by the Fable audit of the live sites on 27 November, on production before any bandage-core 15 deploy. Evidence: `~/src/walks8-evidence/sessions-20261127/hosted-audit/` (`findings.jsonl`, `hubs/results.json`, shots in `hubs/`). The page text for AMY1 and GSTM1 was read back from `results.json`.

- **AMY1, row "94.2 kb deletion":** the row says 52 of 461; the lit lane says "363 haplotypes, HG00099#2 among them" (`hubs/amy1__row2.png`).
  - The 363 is a true count of walks over the link that skips chr1:103620893-103715097. Of the 8 haplotypes the plugin draws, 7 take the skip, and 5 of those then carry 75 to 94 kb of their own sequence.
  - The figure is abridged ("drawn without the nodes of their runs off the reference"), so a haplotype that skips and re-adds the sequence is lit like one that lost it.
- **GSTM1, row "GRCh38's structure" 33% (152 of 461):** the lit lane says 70 haplotypes and the GSTM1 node 16% (`hubs/gstm1__row0.png`).
  - Raw VCF: chr1:109683912 has 18,445 bp to 0 in 391 of 463 called; chr1:109702377 has an 18.4 to 24.4 kb insertion in 86. Only 72 called haplotypes are not deleted. The page's blurb (390, about 80) is right.
  - Likely cause: rows come from vcfwave-realigned states, where the deletion and the adjacent insertion cancel (`website/src/pangenome/pangenomeSvStates.ts:27`). C4 and AMY1 get a "realigned" row for this pattern (`pangenomeWalkForms.ts:80`); GSTM1 does not.
- **Row count against lane count elsewhere:** CFHR 138 and 137; C4 217 and 216, 95 and 96; KIR 263 and 317, 48 and 78; RHD 363 and 349; HP 188 and 166; PGA 8 and 11.
- **Two denominators on one page:** rows are "of 462", graph shares "of the 464 haplotypes drawn" (CFHR 68% in the row, 70% on the node).
- **Direction:** one denominator; a lit lane that is the row's own carriers or carries no count; no lane lit for a deletion row where the page itself classes haplotypes as realigned.
- **Not covered:** 12 of the 18 pages had no VCF check (LPA, HLA, KIR, RHD, HP, FCGR, MNS, PRSS, PGA, FLNA among them).
- A deploy on bandage-core 15.1.0 is not expected to change any of this.
