---
name: reference-walk-unstated-start
description: A reference W line with "*" for its start anchors every node at positions counted from an assumed 0, so GFA text read in BandageJS or the plugin prints node locations, pins genes, opens JBrowse spans and writes ruler and ramp-key ranges on a contig coordinate nobody stated; walk files always state coordinates.
metadata:
  repo: bandage-core
---

# Node coordinates from a reference walk with an unstated start

- Found on 27 November by the implementer of the walk-row axis fix (bandage-core 15.1.0), which left this untouched. Confirmed there: with a reference `W` line whose start is `*`, node `a` gets start 0 and `c` 1000 on `ref#0#chr`.
- Nodes walked only by a `*` walk off the reference are anchored the same way.
- The assumed coordinates feed:
  - node locations in BandageJS's node hover and details, and the plugin's own-location hover band;
  - BandageJS's node link and region search, and the span the plugin band opens in JBrowse;
  - genes pinned onto backbone nodes from a bound gene track, which land on the wrong nodes;
  - the tube-map ruler, the reference-ramp key's range text and coordinates in deletion text.
- The stated-spans rule removes all of these: no contig location, link, pinned gene, ruler number or ramp-key range for a node on a `*` reference.
- What stays true: bp along the reference walk's own steps. Backbone order, distances and the ramp's colours already use them. A ruler or key could read "bp along `ref#0#chr`" from the walk's first step.
- GFA text only. Hosted walk files state coordinates.
