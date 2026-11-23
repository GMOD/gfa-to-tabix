---
name: rgfa-track-after-graph-truth
description: Four graph-track changes from the 23 November audit apply only to graphs with walks, so the rGFA segments track the paper's figures use is unchanged. Whether they should also reach the rGFA track needs its own BEFORE/AFTER pictures.
metadata:
  repo: bandage-core
---

# Should the graph-truth changes reach the rGFA track?

The graph-track fixes (`../handoffs/2026-11-23-hosted-audit.md`, bandage-core
branch `graph-truth`) apply four changes only where the graph has walks:

- skips drawn at their walk count's width, not 2.2 times the connector;
- no length labels on reference nodes;
- the fold measured in bp at the reference's px per bp, not in drawn length;
- short skips drawn as low dashed arches.

On the rGFA segments track the fold by drawn length can hide a large site
that FMMM lays short, and labels on reference nodes there say as little as
on walk files. But the paper's figure windows (CFH, the MHC, chr17) are drawn
on that track, and no picture of the change there has been taken.

To do:

- **Shoot** the paper's rGFA windows and a sample of audit windows on that
  track, BEFORE and AFTER, with the four changes enabled for it.
- **Judge** every changed mark against the VCF.
- **Decide with the owner.** Show the pairs and let the owner decide,
  remembering that a figure change after submission needs a caption and
  letter line.
