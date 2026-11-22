---
name: lanes-ribbons-against-reference
description: A lanes track fed from a walk file draws each lane's ribbons against its neighbour, with no setting for every lane against the reference; the paper's Figure 5 wanted that.
metadata:
  repo: jbrowse-components
---

# Lanes have no setting for ribbons against the reference

- `MultiWaySyntenyDisplay` draws neighbour against neighbour. A walk-fed
  track has records of every lane against the reference already
  (`WalkTabixSyntenyAdapter.anchorFeatures`), so the data is there.
- The paper session asked for it for Figure 5 on 2026-11-22 and was told it
  is a display change.
- A setting in the display, named as the other lane settings are, with
  neighbour against neighbour staying the default.
