---
name: drawing-faults
description: Small drawing faults in bandage-core and its readers found during the format 8 release, none rechecked at today's heads; triage each with a BEFORE picture first.
metadata:
  repo: bandage-core, jbrowse-plugin-graphgenomeviewer
---

# Drawing faults found during the release

Found between 2026-11-16 and 11-19 and not rechecked since. Take a picture at
today's head before working one; several may be gone.

- The tail tab reads first as a direction head, and its key swatch (two
  triangles) is the reference strip's edge mark. It needs a mark of its own
- With the key no longer resizing the graph view's pane, the "N nodes not
  drawn" line can fall below the pane's edge (rand-chr14-3 zoomed). Proposed:
  frame the pane once for the tallest key its drawing can show
- Links painted over nodes show at sv-19 as a grey broken line whose ends a
  reader cannot find
- Few-bp sites drawn as rings, and a 1 bp node about 85 px long at the chr1
  loop zoomed to 500 bp: the force layout's minimum lengths. The ring fix tried
  in core `loop-sizes` (d8fdb7f, 1384610) broke other windows
- Mid-zoom at amylase and sv-26 stays a small knot under every sizing, and
  zooming in can shrink the drawing when a re-cut's layout curls the reference
  more
- Placeholder lengths sitting on ink ("323 bp" at sv-49), and leaders crossing
  ink
- Gene labels flip above and below the line at each zoom step, and labels are
  cut at the track's left edge
- Edge marks go stale after a node drag, and the fold flickers during the
  morph
- `figureData` fits the full height while `figureSvg` subtracts its key, so
  marks near a threshold differ between the two
- At sv-31 the key's colour range says 6.1 kb where the note says 8.2 kb, and
  ANXA8 shows a 523.8 kb span from RefSeq
- From the cold reads: direction heads grey on dark grey and unkeyed; a dark
  ring round a coloured node, brown dashes in a lifted lane, and the strip's
  steps and ticks unkeyed; spans such as "3–3.9 kb" unexplained; Y-9.3M at
  350 kb unreadable
- Not decided: the lane-head gate rule G2, the key's "9 walks" counting the
  reference, a stub's "N bp" label over a hidden stub, a ramp range setting,
  the nine false crossings and the sv-10/sv-36 fit
- Plugin: `force_kiv2_bubbles`' committed figure, at 10.2.0, draws its
  68.4 kb loop inside the pane, but only because the figure grows its track
  (9dd7f7ba); at the default track height the loop ran past the pane's bottom
  edge, and that has not been looked at since. `force_mhc` curling is the
  seeded FMMM default and stays
- sequenceTubeMap's `--banded-haplotypes` draws haplotype-share bands in
  orange, and since tubemap-core 2.1.0 forward reads are red beside them,
  where blue used to contrast; reads and bands are harder to tell apart
  (`~/work/followup-20261120/gw9-tubemaps/` on ada)
- The force layout lays a not-loaded placeholder's outline loop across the
  reference (sv-48, HG00128#2's 5.1 kb; sv-49, NA20805#1's 591 bp), visible
  at the drawing's scale in sv-48; the drawing gate flags it as a false
  crossing (`~/work/followup-20261121/drawing-gate/work/pictures-129f55b/`
  on ada)
