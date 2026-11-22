---
name: lanes-ribbons-against-reference
description: A lanes track fed from a walk file draws each lane's ribbons against its neighbour because the plugin's adapter declares a capability that turns the display's against-the-anchor mode off; its records against the reference come from a chain search and not from the placement the walk file stores. Three reviews on 2026-11-22 put ribbons against the reference first.
metadata:
  repo: jbrowse-plugin-graphgenomeviewer
---

# Walk-fed lanes read against the reference

## What is true

- **The display has the mode.** `MultiWaySyntenyDisplay/sourceShape.ts`,
  `rowsReadAgainstAnchor`, draws every lane against the anchor, and the
  PAF-fed track uses it; that is its "vs hg38" badge.
- **The walk adapter opts out.** `WalkTabixSyntenyAdapter/index.ts` declares
  `lanePairsOnAnchor`, so the display fetches neighbour pairs and drops any
  pair that holds the anchor. No track or display setting overrides it.
- **The records against the reference are already fetched,** for the first
  fetch, the headers and the top lane's band (`anchorFeatures`).
- **They are not a lookup.** `anchorAligner` in `walkLanes.ts` runs
  gbz-base's weighted longest common subsequence of the haplotype's steps
  against the reference fragment, and pair chaining where enough is turned.
  It keeps one pass and loses HG00128's reversed 29 kb at amylase.
- **The walk file stores the placement.** graph-walks gives every step of a
  fragment its position on the reference (`refStarts`, `against`). Nothing
  in the plugin reads them.
- The paper session asked for lanes against hg38 for Figure 5 on 2026-11-22.

## The prototype, 2026-11-22

Branch `lanes-from-placement`, 42b4f504, in
`~/src/jbrowse-plugin-graphgenomeviewer-placement`, on 10.4.4, not pushed.
Results are on ada in `~/work/synteny-extract-1122/placement-1122/` and
pictures in `~/src/walks8-evidence/sessions-20261122/takeover/placement/`.

- **The rule.** A record is a maximal run of a fragment's placed steps, all
  with the reference or all against it, each at or past the end of the one
  before. Unplaced steps between two of them are an insertion and the
  reference between their places a deletion. A turn, or a step back onto
  reference already passed, starts the next record.
- **On 55 Minigraph-Cactus windows** its matched bases equal the diagonals
  of the PAF unpacked from the same graph, with every placed base under
  exactly one record. It holds all that today's aligner finds and about a
  sixteenth more, most of it at SMN, TBC1D3 and `chr14:19.2M`, and
  HG00128's reversed 29 kb at amylase has a record. Three planted faults
  each fail the checks.
- **It takes about a tenth of the time** in Node, the cut aside.
- **Pictures** at CFH, amylase, SMN and TBC1D3 with every lane against the
  reference: CFH draws the same ribbons; amylase gains its reversed
  ribbons; SMN and TBC1D3 are true to the file and a tangle no single
  ribbon can be followed in.
- **pggb chrY is not ready.** Where the reference passes a node several
  times the stored place hops between copies, and at TSPY five lanes break
  into 4,000 records, 1,565 of them under 100 bp. Today's aligner pairs
  1.75 Mb there with a pass other than the stored one.
- **Given up or left open:**
  - Ribbons between two haplotypes, with the switch on.
  - A haplotype's own sequence at a record break lies under no record,
    about 75 kb a lane at amylase.
  - No smallest record size.
  - Four lanes at amylase still end at their first reversed record; that
    is the display's, fixed on jbrowse-components branch
    `lanes-fit-at-inversions`.

## What is left

- Make it a setting of the track, named as the plugin's other settings
  are: ribbons against the reference by default, between neighbours as they
  ship today (`ideas/waiting-on-a-call/lanes-between-two-haplotypes.md`).
- A stated rule for a reference that passes a node more than once, so a
  pggb array draws as one band with its passes and not as shreds.
- Say what lies at a record break: `todo/lanes-say-what-lies-between-fragments.md`.
- Then land it by the usual gates, with the display's fit fix.
