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

## Arrays and the setting, 2026-11-22

Plugin branch `lanes-from-placement`, bbe6670a; jbrowse-components branch
`lanes-read-against-anchor` in `~/src/jbrowse-components-againstanchor`.
Checks and scripts are on ada in `~/work/synteny-extract-1122/arrayrule-1122/`,
the plan and pictures in `~/src/walks8-evidence/sessions-20261122/takeover/`
(`array-rule-plan.txt`, `placement2/`).

- **The array rule.** Where a turn or a step back falls beside a node the
  reference passes more than once, the reference between the two steps'
  places is an array stretch of that lane. A run of placed steps inside one
  stretch is one array record: both extents, no alignment, a strand by
  majority, and how often each side walks its nodes. With no such node
  there is no stretch, so the 55 Minigraph-Cactus windows are unchanged,
  row for row.
- **On pggb chrY** TSPY goes from 4,000 records to 174 with no false
  deletion of 10 kb or more and every placed base under one record;
  P1/DAZ has 201 and the palindrome 15. Seven planted faults each fail.
  Making the records takes 57 ms at TSPY where today's aligner takes a
  second.
- **The setting** is the adapter slot `laneRibbons`: `reference`, the
  default, or `neighbours`. Capabilities are fixed per adapter type, so the
  adapter's header says which, and the display reads it in
  `rowsReadAgainstAnchor`. A jbrowse-web without that condition draws
  neighbours as today.
- **Pictures:** TSPY is one fan a lane where it was a thicket under headers
  such as "89 kb deletion, 89 kb deletion, 71 more".

## What is left

- The display does not know an array: at the chrY palindrome a lane is
  headed "400 kb insertion" over an array, at P1/DAZ an array is named an
  inversion from its majority strand, and stacked bands show only as
  darker paint. A laptop session is teaching the display its wording and
  paint on the same jbrowse-components branch.
- With `neighbours`, amylase's HG00128 lane ends 94 kb earlier than it does
  on 10.4.4; not yet explained.
- Whatever the rule, pggb lanes come in many fragments (163 at TSPY), bands
  pile 13 to 36 deep, and a window at chrY:20.0M is refused at the
  browser's departure budget.
- Say what lies at a record break: `todo/lanes-say-what-lies-between-fragments.md`.
- Then land both by the usual gates, as the plugin release after 10.5.0.
