---
name: labels-probe-harness
description: The drawing gate's labels probe on Y-9.3M has drawn no window since 8df4c07 (V8 out of memory at the default heap) yet exits 0; give it a heap and make a missing window fail the job.
metadata:
  repo: walks8-evidence (fab8f323/drawcheck-merged)
---

# The labels probe draws nothing and passes

- Give `labels-probe` `NODE_OPTIONS=--max-old-space-size=6500` and a cap above
  3G in `caps.tsv`; a run at that heap took about 8,400 s and 4.9 GB
  (ada `~/work/walks8-gates/agents/labels-heap/`)
- Make `run.sh` fail a job whose expected window has no `windows.jsonl` line,
  and prove it by running the old heap
- The checker's `checksMs` on this window grew from 84 s (89a0b3c) to over
  8,000 s; find out why before the next gate
