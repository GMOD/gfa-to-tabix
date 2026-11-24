---
name: plugin-lanes-cutter-drift
description: The plugin's own copy of clipFeatureToRegion has drifted from the host's in three ways, so lanes on hosted data depend on the host re-cutting every piece. Once the host's cut lands, the copy should go, the lanes then cut by host code only, and the fetch-window guard needs clipWindow stamped.
metadata:
  repo: jbrowse-plugin-graphgenomeviewer
---

# The plugin's piece cutter, after the host re-cuts

Found 2026-11-24 by a Fable investigation of the false "deletion" and "insertion" lane labels; the host-side fix rides on jbrowse-components branch `lanes-truth-l1-l5`.

## What the code holds

- **Cutter copy.** `ComparativeAdapterBase.ts:66` calls the plugin's own `clipFeatureToRegion.ts:92`, which calls `splitSyntenyFeatureAtGaps` from the bundled `@jbrowse/synteny-core` 5.0.0-beta.20. That splitter folds every indel under the gap threshold into the neighbouring piece, so a replacement reaches the lanes as a piece with an unaligned tail and a lane gap of 0.
- **No clipWindow.** The host's `comparative-adapters/src/clipFeatureToRegion.ts:153` stamps `clipWindow`; the plugin's copy never does, so `oneWindow` (`layoutMultiWay.ts:470`) is inert for the plugin. With two fetched regions, a gap across unread anchor can be stated. Read from code, not reproduced on screen.
- **No window-spanning gap piece.** The host's copy has one; the plugin's does not.

## To do

- Have the adapter return whole records with their alignment and let the display's RPC clip and split them with host code, then delete the plugin's copy.
- Until then, set `clipWindow` in the copy.
- Bump the synteny-core pin when a release carries 48e3d77f08; `lanes-splitter-pin` (bbc6167c, worktree `~/src/ggv-splitter-pin`) then stops being a gate.

## Also open from the same investigation

- **Clamped anchor side.** `layoutMultiWay.ts:601-604` starts the anchor side past what earlier pieces reached, so `anchorBp` can be 0 while the raw anchor gap is positive, giving "insertion". The comment at 558-562 says this is meant for copies; nobody has counted how often it fires or whether it is ever false.
- **Pairwise synteny view words.** It names CIGAR ops "insertion" and "deletion" per op (`tables.ts:133-134`, `colorLegend.ts:155-158`), so an adjacent I and D, one replacement, reads as two events.
