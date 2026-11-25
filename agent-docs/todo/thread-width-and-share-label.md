---
name: thread-width-and-share-label
description: A thread fold's lit lanes are as thick as 12.8 px for 137 haplotypes and 14.4 px for 304, and no figure setting reaches that width. The owner found them distracting on the jb2hubs HPRC page and asked for thinner lanes, or a number giving the share of haplotypes on each path.
metadata:
  repo: bandage-core
---

# Thread lane width and a share label

On 25 November the owner said of jb2hubs' folded HPRC renders: "the thick paths are distracting. having a number that says proportion that pass this path could be alternative... thickness could be used also if dialed down a bit".

## What is true now

- `countLaneWidthPx` in `src/nodeWidths.ts` is `COUNT_LANE_PX` (3) + `COUNT_LANE_LOG_PX` (2) × ln(count), so a lit lane is 3 px for 1 haplotype, 12.8 px for 137 and 14.4 px for 304.
- No `FigureSettings` field reaches it. `contigThickness` thins only the grey nodes.
- The graph key draws its lane swatches from the same function (`graphKey.ts`).

## Asked for

- **A named setting for lane width**, in the spirit of `trackFit`: a scale or cap, so that a host can draw about 3 to 6 px across 1 to 464 haplotypes. A mock at a flat 5 px read well on the CFH, HP, GSTM1 and FCGR windows.
- **Optionally, a share label** on each thread or kept branch where it leaves the reference, such as "30%" or "137 of 464", placed like the size labels. `threadEvents` already carries the haplotypes per branch.

## Questions before building

- Should the lighter width become the default in every reader, or only a setting? A default change is a visual change, and needs BEFORE/AFTER pairs.
- Does a share label fit "encode in marks, not sentences", and how does it hide at overview zoom?

## The mock

- `~/src/walks8-evidence/sessions-20261125/thread-width-mock/` holds four HPRC windows folded at 1 kb with HG00097 lit: cfhrWin, fcgrWin, hpWin and gstm1.
- `<name>_now` is 14.6.0 at its defaults.
- `<name>_lane5px_contig3` is `contigThickness` 3 with the lit lane's stroke width set to 5 by hand. Gaps in label backgrounds along the lit lane come from that hand edit, not from the drawing.

jb2hubs ships with `contigThickness` 3 until a core release offers either.
