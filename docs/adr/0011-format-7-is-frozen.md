# ADR 0011: Walk format 7 is frozen until its consumers ship

- **Status:** accepted, 2026-11-06. Walk format 7, as
  [ADR 0010](0010-walks-unit-table.md) and
  [walks-format.md](../walks-format.md) define it.
- **Decides:**
  - that format 7 ships as it is
  - what may change before the consumers ship
  - what it takes to make a format 8
- **Rejects:** the format 8 proposal, which placed a step only where its
  reference passes the node once
  ([proposal](../walks-container/reshape/proposal.md)).

## Context

Between 10-08 and 11-06 the walk format was redesigned eight times.
Formats 2 to 5 were hosted, and each was triggered by real data. Formats
6 and 7 never reached a user, and nor did the proposed 8, which was
triggered and judged by reviews alone.

The "why we keep fumbling" review
([reviews/fumbling.md](../walks-container/reshape/reviews/fumbling.md))
traced the churn to three causes:
- **Nothing outside the agents was in the loop.** Review findings arrive
  at a steady rate for each mechanism, so redesigns driven by reviews
  don't converge.
- **Most design work served pggb's collapsed repeats.** No hosted file
  uses them.
- **One session framed, measured and accepted its own proposal.**

The format 8 proposal was then reviewed four ways, against criteria
written before the reviews
([brief](../walks-container/reshape/reviews/brief.md)):
- **Against it** ([against.md](../walks-container/reshape/reviews/against.md))
- **What a biologist sees** ([biologist.md](../walks-container/reshape/reviews/biologist.md))
- **Hidden traps** ([hidden-traps.md](../walks-container/reshape/reviews/hidden-traps.md))
- **The process** ([fumbling.md](../walks-container/reshape/reviews/fumbling.md))

## Decision

- **Format 7 ships.** On MC, the only graphs hosted, format 8's rows were
  byte-identical to format 7's
  ([out/results.txt](../walks-container/reshape/out/results.txt)), so
  format 8 gains them nothing.
- **Format 8 is not built.** On pggb it doesn't make collapsed repeats
  true: the records that span a repeat are still hops between copies,
  2,693 of 2,760 at chrY:23.6 Mb. It doubles attach fetches (1,070 against
  589 KB at the 1 kb median), and it would need at least six amendments to
  freeze. Format 7 draws the same hops, plus rows the placement rule
  chose. Neither format is true in collapsed repeats. That is recorded in
  [open problems](../open-problems.md#collapsed-repeats-in-pggb-graphs),
  with the two known fixes.
- **The detail-table split is not adopted.** It would cut a one-time open
  of chr9 from 192 to 69 KiB, which doesn't pay for breaking the freeze.
- **What may still change in format 7 before the consumers ship:**
  - writer fixes that leave real graphs' bytes unchanged
  - checker fixes
  - spec wording that leaves the rows' meaning unchanged
  - dropping 0 bp segments on read, since neither HPRC graph has one
    (3,122,495 segments in MC chr22, 4,122,486 in pggb chrY)
- **pggb walk files can be written, but aren't hosted.** Their collapsed
  repeats draw hops between copies.

## The freeze

- **Ship gate.** There is no ADR for a format 8 until the JBrowse plugin
  and bandage-core have read format 7 from a hosted file.
- **Trigger.** After that, a format change needs an issues-log entry whose
  source is a user, or a consumer working against a hosted file. A
  finding from a review alone goes into
  [open problems](../open-problems.md).
- **Scope.** A format change has to be measured on a hosted graph, or on
  one a named user asked for.
- **Burden.** A format change has to beat shipping the current format
  unchanged, measured against criteria written before the measurement.
- **Briefs.** Whoever briefs a proposal doesn't brief its measurement or
  its deciders. Deciders get the question, the criteria and the data,
  never the proposal's framing.
- **Checker evidence.** A checker is cited as evidence only alongside its
  recorded failure on a broken writer.

## Consequences

- **Next, in order:**
  - land the writer and checker fixes
  - release-check the hosted MC files with the repaired checkers
  - port the JBrowse plugin and bandage-core to graph-walks 6
  - host the GRCh38 and CHM13 MC builds
  - view them
- **pggb collapsed repeats stay an open problem.** The two fixes would
  each add to format 7 when someone asks for pggb walk tracks:
  - a table of collapsed runs, plus each record's own bp on reference
    nodes
  - placement from an alignment of each haplotype to the reference

  Format 7 keeps the pass fields both of them need.
