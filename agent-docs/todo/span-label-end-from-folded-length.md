---
name: span-label-end-from-folded-length
description: Confirmed 26 November - on any folded graph, bandage-core derives a walk's stated end and its node hover positions by summing drawn node lengths, so released 14.10.0 / plugin 10.13.0 print false haplotype ends (53 of 55 one-haplotype labels, by up to 1,341 bp), labels for several-haplotype threads that are true for no member, and false hover positions. Fix in progress on `stated-spans` branches.
metadata:
  repo: bandage-core
---

# Positions derived from folded lengths

## Confirmed

- A read-only Fable diagnosis (ada `~/work/walks8-gates/agents/span-label-diag/`) checked 80 random windows over the hosted file, seed 20261126. The released code got these wrong:
  - 165 of 250 key labels;
  - 53 of 55 one-haplotype labels (median 34 bp, up to 804 bp; up to 1,341 bp on cut folds);
  - 112 of 115 several-haplotype labels, true for no member;
  - 485 of 575 node hover positions.
- The VCF agrees with the walk file, not the labels.
- In `force_gstm1_three_ways`, HG01960#1's label ends at 109,960,817, where the walk file has 109,960,754.
- Cause: `walkHighlight.ts` `extentOf` and `threadFold.ts` `foldedGraph` take the end as start plus drawn length. `GraphPath` carries no end, though `tablePath` has `w.ends[p]`. A several-record thread takes its first record's name, contig and start.
- Affected readers:
  - the key (`walkKey.ts`, `graphKey.ts`);
  - SVG figures (`figureScene.ts`, `figure.ts`) and exported figure data;
  - the plugin's node hover on a lifted walk and its assembly band;
  - jb2hubs' figure, by inference from its code.
- BandageJS never folds to threads, so it is believed exact.

## The rule for the fix

A position is printed only when the data states it. It is read from the walk data, never derived from drawn lengths, and nothing is said where the data does not state it.

The checker `spancheck.mjs` (random windows) must fail on released code and pass on the fix.
