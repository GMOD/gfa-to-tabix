# ADR 0011: Walk format 7 is frozen, and collapsed repeats stay an open problem

- **Status:** accepted, 2026-11-06
- **Decides:**
  - that walk format 7 ([ADR 0010](0010-walks-unit-table.md),
    [walks-format.md](../walks-format.md)) ships unchanged
  - why no format, 7 or a new one, can place haplotypes truthfully inside
    a collapsed repeat
  - the rules a format change must pass from now on, so the format stops
    being redesigned by reviews
- **Rejects:** the format 8 proposal, which would have placed a step only
  where its reference passes the node once
  ([proposal](../walks-container/reshape/proposal.md), with its
  measurements and the eight reviews of it in
  [reshape/reviews/](../walks-container/reshape/reviews/))

## In short

- **A walk file gives each haplotype step a position on the reference.**
  Where the reference passes a node once, that position is a fact of the
  graph. That holds for every Minigraph-Cactus graph, and every walk file
  we host is one.
- **Where the reference passes a node more than once, the graph doesn't
  say which copy a haplotype took.** pggb graphs collapse repeats this
  way. Format 7 picks a copy by a rule. The rejected format 8 would have
  picked none. Neither draws the truth, because the truth isn't in the
  graph.
- **Format 7 ships.** The two known fixes for collapsed repeats each add
  to format 7, so freezing it blocks neither. They wait until someone asks
  for pggb walk tracks.
- **The format changes again only when a user or consumer hits a real
  problem on a hosted file.** A review's finding goes into
  [open problems](../open-problems.md), not into a new format.

## Three scenarios

### A graph where every position is a fact

GRCh38 walks five 10 bp nodes. HG002 swaps nodes 3 and 4 for its own
5 bp node 6:

```
W  GRCh38  0  chr1  0  50  >1>2>3>4>5
W  HG002   1  chr1  0  35  >1>2>6>5
```

gfa-to-tabix writes one tile:

```
#unit  GRCh38#0#chr1  0  50  tile  0
GRCh38#0#chr1  0  50  ref    GRCh38#0#chr1  0  0  0  5  2,2,2,2,2  10,10,10,10,10  .
GRCh38#0#chr1  0  50  nodes  6  5
GRCh38#0#chr1  0  50  route  4  8  -2
GRCh38#0#chr1  0  50  walk   HG002#1#chr1  0  0  0  4  2  0
```

GRCh38 passes every node once, as the `.` in the `ref` row's last
column says. So HG002's node 2 can only be at 10–20 and its node 5 only
at 40–50, and the drawing follows: HG002 leaves after node 2, runs
through node 6, and rejoins at node 5. Every number in it is a fact of
the GFA. This is the MC case, and format 7 is right here.

### A collapsed repeat: no fact decides

GRCh38 passes node 5 twice, at 10–20 and again at 40–50, as pggb writes
a repeat it has collapsed. HG002 has one copy:

```
W  GRCh38  0  chr1  0  60  >1>5>2>3>5>4
W  HG002   1  chr1  0  30  >1>5>4
```

Two readings fit HG002 equally well:
- **Copy at 10–20:** HG002 follows GRCh38 through 0–20, then skips
  20–50 (nodes 2, 3 and the second copy of 5).
- **Copy at 40–50:** HG002 skips 10–40 (the first copy of 5, then nodes
  2 and 3), then follows GRCh38 through 40–60.

The GFA holds no fact that picks one. HG002 lacks 2, 3 and one copy of
5, and which copy it lacks is unresolved.
- **Format 7 picks by a rule:** the pass nearest the step before, so the
  copy at 10–20. Its `ref` row states the pass counts (`1,2,1,1,2,1`),
  so a reader can tell the choice was made in a repeat. But the drawing
  shows one reading as if it were the only one.
- **The rejected format 8 picks neither.** HG002's node 5 gets no
  position, and HG002 is drawn as skipping 10–50 while carrying 10 bp of
  its own. That's true as far as it goes, but it hides that the 10 bp is
  a copy of a reference node.

### The same thing at scale: pggb chrY

At chrY:23,600,000–23,601,000 GRCh38 passes every node four times: at
21.99, 22.59, 23.60 and 26.07 Mb.
- **Format 7** draws 91 haplotypes through the window, on copies the
  rule chose, plus 6,293 hops between copies. 98% of those hops carry
  0 bp of the haplotype's own. Only about a third of pggb chrY's pieces
  in Yp11 and Yq11 land within 10 kb of where the MC graph places the
  same contig.
- **Format 8** would draw no haplotype through the window. Every
  haplotype becomes a run of hops between copy-specific nodes 1–3.5 Mb
  apart. HG002#1 alone has 561 of them, and a reader draws them as
  alternating 3.5 Mb losses and duplications.
- **What HG002 actually carries** is one arm of the palindrome, whose
  copy-specific variants match one reference arm at one point and the
  other arm at the next.

Measured in
[reviews/biologist.md](../walks-container/reshape/reviews/biologist.md)
and [reshape/out/](../walks-container/reshape/out/).

## Decision

- **Format 7 ships unchanged.** Before the consumers ship, only these may
  change:
  - writer fixes that leave real graphs' bytes unchanged
  - checker fixes
  - spec wording that leaves the rows' meaning unchanged
  - dropping 0 bp segments on read. Neither HPRC graph has one: MC chr22
    has 3,122,495 segments and pggb chrY 4,122,486, none of them 0 bp.
- **Format 8 is rejected.** On MC its rows are byte-identical to format
  7's ([out/results.txt](../walks-container/reshape/out/results.txt)),
  so it gains the hosted files nothing. On pggb it doesn't make collapsed
  repeats true, as the scenarios show, and it:
  - doubles the bytes a 1 kb window fetches, from 589 to 1,070 KB at the
    median
  - drops five chrY contigs silently
  - needed at least six amendments before it could be frozen
- **Collapsed repeats stay an
  [open problem](../open-problems.md#collapsed-repeats-in-pggb-graphs).**
  Both known fixes add to format 7. Either is taken up only when someone
  asks for pggb walk tracks:
  - **Say "copy unresolved" instead of choosing.** Add a table of each
    reference sequence's collapsed runs, and each record's own bp that
    lie on reference nodes. A viewer then draws HG002 in the second
    scenario as present across 10–60 with one copy of 5 unresolved,
    instead of as a deletion.
  - **Bring in the missing fact.** Align each haplotype to the reference,
    and place its steps in repeats from that alignment, which agrees with
    MC 86.5–99.4% of the time. This needs format 7's pass fields, which
    format 8 would have deleted.
- **pggb walk files can be written, but are not hosted.**

## Why we kept redesigning, and the rules that stop it

Between 10-08 and 11-06 the walk format was redesigned eight times
([reviews/fumbling.md](../walks-container/reshape/reviews/fumbling.md)):

| Format | Date | Reached users | Triggered by |
|---|---|---|---|
| 2, 3 | 10-12, 10-16 | yes | chr22 size; the bp between W lines |
| 4, 5 | 10-19, 10-20 | 5 yes | pggb repeats; pggb satellites |
| 6 | 11-04 | no | reviews |
| 7 | 11-05 | no | reviews |
| 8 | 11-06, rejected | no | reviews |

Three causes, each with the rule that answers it:
- **Nothing outside the agents was in the loop after format 5.** Of 124
  issues-log entries, one came from the user and 118 were logged on 11-05
  and 11-06. Reviews find problems at a steady rate for each mechanism,
  so a design driven by reviews never settles.
  - **Ship gate.** There is no ADR for a format 8 until the JBrowse
    plugin and bandage-core have read format 7 from a hosted file.
  - **Trigger.** After that, a format change needs an issues-log entry
    whose source is a user, or a consumer working against a hosted file.
    A finding from a review alone goes into
    [open problems](../open-problems.md).
- **Most of the design work served a graph nobody hosts.** ADRs 0001,
  0003–0006, 0008 and part of 0009 were triggered or measured on pggb's
  collapsed repeats or CHM13's satellites. On MC their mechanisms do
  nothing.
  - **Scope.** A format change is measured on a hosted graph, or on one a
    named user asked for.
- **One session framed, measured and accepted its own proposals.** The
  format 8 proposal was briefed with a figure that turned out to be
  wrong. The measurement was briefed with the proposal itself. The two
  deciders got the same brief, carrying the proposal's numbers. The ADR
  was committed minutes after they reported, citing checkers that had
  been shown that day to pass broken files.
  - **Burden.** A change has to beat shipping the current format
    unchanged, measured against criteria written before the measurement.
    When the evidence is mixed, the format stays.
  - **Briefs.** Whoever briefs a proposal doesn't brief its measurement
    or its deciders. Deciders get the question, the criteria and the
    data, never the proposal's framing.
  - **Checker evidence.** A checker is cited as evidence only alongside
    its recorded failure on a broken writer.

## Applying the rules

- **A review finds that a new row kind would make pggb's 1 Mb windows 20%
  smaller.** No hosted file is pggb and no user asked, so it goes into
  open problems.
- **A writer bug changes the rows of an MC file.** The rows' meaning
  doesn't change, only the bytes that were wrong. Fix it, log it, rebuild
  the hosted files, and keep the format number.
- **Someone hosting pggb chrY reports false inversions across the
  palindromes.** That's a user trigger on a hosted file. Measure the
  "copy unresolved" fix on pggb chrY against shipping format 7
  unchanged, with criteria written first. The result can be an ADR for
  format 8.
- **A reviewer proposes replacing the walk file with GBZ served over
  HTTP.** It goes into open problems. It would need its own trigger from
  a hosted file.
- **A consumer port finds a spec sentence ambiguous.** Clarify the
  wording to match what the writer and reader already do. The rows'
  meaning doesn't change, so neither does the format.

## Consequences

- **Next, in order:**
  - land the writer and checker fixes
  - release-check the MC builds with the repaired checkers
  - port the JBrowse plugin and bandage-core to graph-walks 6
  - host the GRCh38 and CHM13 MC builds
  - look at real windows on them
- **Placement guards come back into scope.** The placement and stay
  mutants that survived, and the GFA-reading placement oracle, guard
  format 7, which is now the format that ships.
- **The detail-table split is not adopted.** It would have cut a
  one-time open of chr9 from 192 to 69 KiB, which doesn't justify
  breaking the freeze.
