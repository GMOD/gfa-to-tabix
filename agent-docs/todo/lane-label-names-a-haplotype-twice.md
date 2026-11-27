---
name: lane-label-names-a-haplotype-twice
description: A lane label on genomes.jbrowse.org reads "70 haplotypes, HG00128#1, HG00128#1 among them"; bandage-core's threadLabel joins the host's picks without dropping repeats, and the website passes one twice.
metadata:
  repo: bandage-core
---

# A lane label names one haplotype twice

- Seen on production on 27 November: GSTM1 "70 haplotypes, HG00128#1, HG00128#1 among them", LPA "85 haplotypes, HG00140#1, HG00140#1, HG00290#2 among them", CFHR "314 haplotypes, HG00097, HG00097 among them" (sample names without the haplotype). Shots and text: `~/src/walks8-evidence/sessions-20261127/hosted-audit/` `hubs/`.
- `threadLabel` (`bandage-core/src/threadKey.ts`) writes `picked.join(', ')`; the line is the same in 15.1.0.
- Not traced: why the website passes a pick twice, and where the `#1` is dropped.
