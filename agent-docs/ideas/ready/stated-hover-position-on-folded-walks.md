---
name: stated-hover-position-on-folded-walks
description: Once the stated-spans fix ships, hovering a node on a lifted haplotype of a folded graph gives no position on that haplotype's assembly, because the fold's lengths are not the haplotype's. The walk rows state it; read it from them for a one-record thread.
metadata:
  repo: bandage-core
---

# A stated hover position on folded walks

- The stated-spans change (bandage-core `stated-spans`, 26 November) stops printing node positions derived from folded lengths. Released 10.13.0 was wrong for 485 of 575 hovers.
- The user-view Fable review computed the true one from the walk rows: on HG01960 at GSTM1, the node at GRCh38 chr1:109,683,913 starts at CM088644.1:109,919,836. 10.13.0 printed 109,919,910.
- For a thread of one record, graph-fold or the runs reader could carry each folded node's own offset along that walk, so the hover states it. Threads of several haplotypes stay silent.
- Prove it with `spancheck.mjs`'s hover check (ada `~/work/walks8-gates/agents/stated-spans/`) holding every printed position to the rows.
