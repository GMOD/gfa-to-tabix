---
name: graph-track-lanes-button
description: A graph track gives no way to reach the haplotype lanes for the same walk file, and the owner wants a single button. No such action exists; a lanes track is a GraphTrack on the same walk file with a WalkTabixSyntenyAdapter and MultiWaySyntenyDisplay, so the button can derive it with no new host config. It must open a named, capped list of haplotypes, never all of them.
metadata:
  repo: jbrowse-plugin-graphgenomeviewer
---

# One button from a graph track to the haplotype lanes

Asked for by the owner on 2026-11-23: a graph opens as a bandage track and nothing shows that the lanes exist. Designed read-only against plugin origin/main (10.8.0); nothing is built.

## What the code holds

- **No action exists.** Nothing calls `addTrackConf`; `launchFromGraph/launchFromGraph.ts` has `showInLinearView`, `showTrackInLinearView` and `launchSyntenyView` only.
- **The graph track cannot switch display.** `GraphTrack/index.ts` offers the synteny displays only to adapters declaring `headerLanes`; `RgfaTabixAdapter` does not, `WalkTabixSyntenyAdapter` does.
- **The config is derivable.** `walksLocation`, `walksIndex`, `samplesTsvLocation`, `assemblyNameToPanSN` and the two budgets are the same slots in both adapter schemas, and the reference assembly is `graphReferenceAssembly`.

## Design

- **Where:** a "lanes" button beside "highlight" in the pane's HAPLOTYPES row (`GraphGenomeView/components/HaplotypeSwitch.tsx`), and the same item in the track menu's Haplotypes submenu.
- **Click:** build a session track `<sourceTrackId>-lanes` (type `GraphTrack`, one display `MultiWaySyntenyDisplay`, `rows.kept` set to the chosen haplotypes), `session.addTrackConf`, then show it in the linear view that holds the graph track, so the region is the same.
- **Which haplotypes:** at most 8, in order the lifted walks, the pane's cut list, the track defaults. The lanes title says "8 of 463". 8 lanes answer to 5 Mb; all 463 are refused at 1 Mb.
- **Disabled, with the reason,** when the graph has no walk file or this JBrowse has no `MultiWaySyntenyDisplay`.
- **Back to the graph:** core's "Display types" menu already switches the derived track to the graph.
- **Size:** about 150 to 200 source lines plus tests; new `launchFromGraph/lanesTrack.ts`.

## To verify while building

- That `rows.kept` matches a PanSN prefix such as `HG00097#1` to the lane name (`synteny/lanePairs.ts`).
- A JBrowse that does not state `readsLanesAgainstAnchor` draws neighbour ribbons, not reference ribbons.
- A second click with another selection must call the display's `setSelectedLanes`.
- Relative `walksUri` (see plugin-relative-walksuri).
