---
name: span-label-end-from-folded-length
description: In the plugin figure force_gstm1_three_ways, each haplotype's span label takes its end as start plus the folded length rather than the haplotype's real end, so HG01960's label ends about 64 bp past its true end (109,960,754). Plugin 10.12.0 and 10.13.0 both show it. A false label in production; unverified beyond the release agent's check.
metadata:
  repo: bandage-core
---

# A span label's end is computed, not read

- Found by the release agent while comparing figures for plugin 10.13.0 against 10.12.0 on 26 November (ada `~/work/walks8-gates/agents/release-1013/compare/`). 10.13.0 does not make it worse, so it did not hold the release.
- The label should give the haplotype's real start and end on its own contig, from the walk data. Find where the end is derived from the folded length and read it instead.
- First confirm it independently against the walk file and the VCF, with a checker that fails on the released code. It belongs in `claims-inventory.md`: a number on a label with no stated condition.
