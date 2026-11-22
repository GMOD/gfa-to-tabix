---
name: lanes-headers-and-fit-at-inversions
description: At amylase the lanes' headers name a 94 kb deletion and a 94 kb insertion over sequence minimap2 aligns to the same 94 kb reversed, the walk-fed and PAF-fed tracks head the same haplotypes differently, and a lane with a reversed record against the anchor ends there and loses its far flank; all three are in JBrowse's multi-way display.
metadata:
  repo: jbrowse-components
---

# Lane headers and lane fit where a stretch is inverted

Found 2026-11-22 at `chr1:103,500,000-103,800,000` with the eight haplotypes
of `demos/hprc`. Pictures and scripts are on ada in
`~/work/synteny-extract-1122/` (`shots/`, `verify.sh`).

## What is true

- **The header names two events where the sequence shows one.** The
  walk-fed lanes head HG00133.1, HG01109.1, HG01123.1, HG01960.1 and
  HG02055.1 "94 kb deletion, 94 kb insertion". For HG01123.1, minimap2
  aligns the "inserted" stretch (`CM089081.1:103,972,366-104,066,525`) to
  the "deleted" one (`chr1:103,620,893-103,715,097`) on the reverse strand,
  over all of it, at mapq 60. The other four were not aligned; their records
  are alike.
- **The graph does not hold it as a reversal.** Of that stretch of
  HG01123's walk, about four fifths is on nodes GRCh38 does not step in the
  window, and the rest is on GRCh38's nodes either side of the "deleted"
  stretch, stepped the other way. So a reader of the walks sees 94 kb of
  the reference replaced by 94 kb of other nodes.
- **Both sides have bases, so by this project's own wording rule it is "94
  kb replaced by 94 kb",** not a deletion and an insertion. The label is
  built in `MultiWaySyntenyDisplay/layoutMultiWay.ts` (`laneIndelsOf`).
- **The two published tracks disagree.** The PAF-fed lanes head four of the
  same haplotypes "110 kb inversion, 94 kb deletion, 1 more"
  (`shots/pif/lanes_amylase_pif.png`).
- **A lane ends at its first reversed record.** In the PAF-fed picture, and
  in the walk-fed one once its records against the anchor are complete
  (`shots/after`), four lanes draw about 261 kb, stop near AMY1B and leave
  the band blank to the right, while their header still says "449Kbp,
  squeezed 1.5×".
- **A break in a walk is headed an insertion.** The review found
  HG00097.1's walk in two fragments 49 kb apart in the window, where its
  lane says "49 kb insertion". Whether that is Minigraph-Cactus clipping was
  not checked against the GFA.

## What to do

- Fit a lane across a reversed record instead of ending at it, and make the
  header's span agree with the range drawn.
- Head a stretch with bases on both sides as one replaced by the other, and
  print no event name where the only fact is that no node is shared.
- Add to the tutorial's "Limits of the lanes": identical sequence that the
  graph keeps on separate nodes draws as a gap beside unmatched sequence,
  an inverted stretch among them; and a break in a clipped walk is not an
  insertion.
- The tutorial's part 3 says HG00133.1 "has GRCh38's three AMY1 copies and
  its length"; its lane heads it with a deletion and an insertion.
- Until the fit is fixed, walk-fed lanes keep today's records against the
  anchor (`todo/lane-aligner-leftover-stretches.md`).
