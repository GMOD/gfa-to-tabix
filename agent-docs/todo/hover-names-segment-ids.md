---
name: hover-names-segment-ids
description: Reference-node hovers in the plugin lead with GFA segment ids joined by `~` (8469182~8470855) and end the coordinate line with "(rank 0)"; both are in-house terms a user cannot read. Fold-made names were removed from hovers on 26 November; these remain, as in plugin 10.12.0.
metadata:
  repo: jbrowse-plugin-graphgenomeviewer
---

# Segment ids and "(rank 0)" in reference hovers

- Seen in the CFH shots of 26 November (`~/src/walks8-evidence/sessions-20261126/plugin-runs-pairs/cfh-line/`), in 10.12.0 and in the fold-runs build alike. Both Fable reviews of the hover fix named it.
- A fold-made node is now named by its length (bandage-core bfb93a6, plugin b1188e7c). A reference node still opens with its segment ids.
- Decide what a user needs as the hover's title (the gene, the GRCh38 stretch, the length) and drop "(rank 0)" or say it in plain words. Segment ids may stay in the node details widget for someone matching the GFA.
- Part of `claims-inventory.md`'s list of hover text.
