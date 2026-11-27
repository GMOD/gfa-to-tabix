---
name: stated-hover-position-on-folded-walks
description: Since bandage-core 15.0.0 and plugin 10.14.0, hovering a node on a lifted haplotype of a folded graph gives no position on that haplotype's assembly, and the linear views draw no hover band for it, because the fold's lengths are not the haplotype's. The walk rows state it; read it from them for a one-record thread, and bring back both.
metadata:
  repo: bandage-core
---

# A stated hover position on folded walks

- bandage-core 15.0.0 and plugin 10.14.0 (27 November) stop printing node positions derived from folded lengths. Released 10.13.0 was wrong for 485 of 575 hovers.
- The plugin's linear-view hover band on folded tracks went with them (`nodeAssemblySpans` in `src/launchFromGraph/contributors.ts`, `visits = graph.threadFold ? [] : …`). It was off by the same tens of bp. A stated position brings the band back too.
- The user-view Fable review computed the true one from the walk rows: on HG01960 at GSTM1, the node at GRCh38 chr1:109,683,913 starts at CM088644.1:109,919,836. 10.13.0 printed 109,919,910.
- For a thread of one record, graph-fold or the runs reader could carry each folded node's own offset along that walk, so the hover states it. Threads of several haplotypes stay silent.
- Prove it with `spancheck.mjs`'s hover check, which on 15.0.0 checks nothing (every hover is silent), (ada `~/work/walks8-gates/agents/stated-spans/`) holding every printed position to the rows.
