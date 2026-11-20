---
name: reader-deviations-refresh
description: reference/reader-deviations.md is the 2026-11-15 audit; deviations found since (ggbandage faceted exons and pass-bar axis, the plugin's missing plain-GFA track adapter, others) are not in it, and some it lists are fixed.
metadata:
  repo: gfa-to-tabix (agent-docs), all readers
---

# Refresh the reader deviations audit

Re-audit at today's heads of BandageJS, ggbandage, the plugin, jb2hubs, tube
map and ggtubemap. Known since 11-15:

- fixed: core supplies the heads swatch; ggbandage's notch comes from
  columns; BandageJS's `swatchHtml` is gone
- unchecked: ggbandage's faceted exons and pass-bar axis; the plugin has no
  track adapter for a plain GFA (the syng graph opens only in its own view)
- the `links` setting is now one default in every reader (walked), so drop any
  links entry
