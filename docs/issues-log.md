# Issues log

Every bug, gap and review finding on the walks stack, with where it came
from, how it was fixed and what now guards it, oldest first. Append an
entry before committing a fix; mark an entry **re-found** when it repeats
an earlier one, since that is the circle this log exists to break. The
handoffs hold the state of the work and the ADRs the decisions; this holds
the mistakes.

## Sources

Where the findings have come from so far, and the rule each gives:

- **The format's limits surfacing in a reader.** An abridged row's `bp`
  counts the moved pieces alone, so every reader must grow its extent by
  what lies between them; one placement per file means a repeat the
  reference passes many times files a departure at every hop. Rule: when a
  reader meets a format summary, write down what it leaves out before
  reading it
- **Tests shaped by the implementation.** Unit inputs with the reference
  forward, every node passed once, pieces consecutive and own bp equal to
  the attached steps cannot tell the rule from the wrong one. Rule: for
  each rule in the code, one test input where the wrong rule gives a
  different answer; cover reversed reference handles, repeated nodes,
  non-consecutive pieces
- **Evidence on one graph.** MC chr22 on GRCh38 never shows a reversed
  reference handle, a node the reference passes twice or a hop between
  copies; pggb and CHM13 do. Rule: a real-data check runs on MC and pggb
  before a claim about "every" case
- **Prose ahead of data.** Numbers typed into docs from terminal output, or
  summaries that generalise from the windows measured. Rule: no number in
  prose without a committed data file and a script that wrote it; no "the
  rest reads fine" without a measurement of the rest
- **Rewrites that drop what the old code compensated for.** The old chains
  grew an abridged walk's extent by each absorbed run; the rewrite took a
  max and the review re-found the case the same day, through a test the
  rewrite had deleted. Rule: before replacing a mechanism, list what the
  old one compensated for and carry each item over or log why not; read a
  file whole before replacing it and diff its test names
- **Decisions made ad hoc mid-implementation.** Whether own steps beside
  an abridged net join it flipped twice in one session. Rule: when two
  readings both pass the tests, state the rule in the doc comment first
  and pick by it
- **A wrong word on screen.** "deletion" for a stretch the haplotype has no
  step on. Rule: state the facts the file holds
- **The machine.** Memory kills on ada, the laptop's /tmp quota. Rule: check
  before starting, keep outputs small, record in the handoff's gotchas

## Entries

- **2026-10-30, the user.** The viewers called any skipped stretch a
  deletion. Source: a wrong word. Fixed in bandage-core 12.6.0 (1f53c24),
  jbrowse-components cfbebd84cf and plugin a00b1af, which state the
  stretch and the haplotype's own bp; the graph-view arc label is parked
  ([handoff](handoff/2026-10-31-departures.md)). Guard: the rule in the
  handoff's decisions
- **2026-10-30, measurement.** graph-walks 4.6.0's crossing fragments
  depended on which other haplotypes were kept, and the synteny mate span
  with them. Source: format 5 held no record of a departure. Fixed by walk
  format 6's records ([ADR 0009](adr/0009-departure-records.md)) and
  graph-walks 5 (43910ec), whose fragments run from a walk's own first
  step on the window to its last. Guard: ADR 0009's reader promise, audited
  by `departures/scripts/audit6.py`
- **2026-10-31, review.** The bypass prototype's `order` column was the
  reference's order, not the haplotype's: reverse-strand contigs going
  forward counted as backward jumps. Source: a column defined from the
  wrong side. Fixed: ADR 0009 derives direction from the two ends' strands
  and breakpoints. Guard: the format defines the kinds from the ends
- **2026-11-01, review of the spike.** Sizes quoted from a narrower
  record; filing choices never weighed; chrY's rows per window missing
  from the results; the `dep.rs` check left out 414 mismatches. Source:
  prose ahead of data. Fixed by the 2026-11-03 rebuild, read back by an
  independent audit ([ADR 0009 History](adr/0009-departure-records.md#history)).
  Guard: `audit6.py` over every build, `fuzz6.sh`
- **2026-11-01, review of the placement scores.** `agree.py` extrapolates
  forward only, reuses chrY's strata on chr22, counts rows not records;
  the chrY maximum of 1,937 rows was an audit error (19,933 in the file).
  Source: prose ahead of data. Open: the caveats are in
  [open-problems](open-problems.md), the scores not rerun
- **2026-11-04, measurement at the port.** The prototype had dropped the
  `pv` and `nx` tags unrecorded, so its sizes left them out (0.35 to 0.5%).
  Source: prose ahead of data. Fixed: measured, then removed with the user.
  The port also recorded a departure over a 0 bp node between adjacent
  steps, which the prototype missed; the minimal record then defined
  adjacency by bp, the other way. Source: a decision made ad hoc. Guard:
  the format doc states the rule; `audit6.py` and the tests agree with it
- **2026-11-05, this author's comparison.** In the forms-cut rewrite a
  reversed rejoin ran into a forward fragment of the same contig and the
  haplotype lost every departure in the window (HG00097#2 at LCR22A).
  Source: unit inputs with no contig visiting the window twice. Fixed in
  graph-walks 1132859 (chains, each read in its own orientation). Guard:
  `results/minimal/mc22.forms-compare.txt`, the old cut's departures
  reproduced on six windows
- **2026-11-05, logic review.** An abridged group's contig extent stayed
  at `hapOffset + bp`, which leaves out the pieces of other chunks between
  the moved ones, so a departure leaving the last moved piece was counted
  twice and split the chain. Source: a rewrite dropping what the old
  chains compensated for; **re-found**, graph-walks 4's `chains` had it
  and the rewrite deleted the test that covered it. Fixed in 73f2e6b, the
  test back in 3574904. Guard: tests "abridged pieces with another chunk's
  piece between them count its bp in their net" and "keeps an abridged
  walk's net exact when a piece of it lies in another chunk"
- **2026-11-05, logic review.** A fragment's ends took their strand from
  the handle and their position from the node, wrong where the reference
  holds a node reversed or passes it twice; graph-walks 4 had read every
  step so, and MC chr22 never shows either. Source: tests shaped by the
  implementation, evidence on one graph. Fixed in 73f2e6b: `WalkFragment`
  carries `refStarts` and `against`. Guard: tests "a walk along R through
  a node R holds reversed stays on R" and "a fragment's ends lie where
  their pass does"
- **2026-11-05, logic review.** A departure leaving the abridged pieces'
  last step was folded into their net with only the steps the cut held,
  losing own bp in pieces outside the read. Source: a decision made ad
  hoc (the inclusive edge, chosen to match the old merged output). Fixed
  in 73f2e6b: a departure at the pieces' edge stays exact. Guard: test "a
  departure leaving abridged pieces' last step keeps its own bp whole"
- **2026-11-05, tests review.** `walkDepartures` compared every pair of a
  path's items and rebuilt arrays on every add: 109 s on a 900 kb IGL
  window with 976,347 departures. Source: tests and comparison windows
  too small to show it. Fixed in 3574904, one sweep in contig order: 0.6
  s. Guard: none automated yet; the timing is in
  [results/minimal](departures/results/minimal/README.md#the-forms-cut-on-mc-chr22)
- **2026-11-05, tests review.** "The forms are identical outside LCR22A"
  generalised six windows; on 28 the forms differ in 12, wherever jumps
  over the window appear, by the chain model's design, and once by a
  rare-state fold (HG00126#1 at 21.4 Mb, `ref` to `inv 48.7kb`). Source:
  prose ahead of data. Fixed: the results README states the 28-window
  picture (`mc22.forms-compare-review.txt`). Open: what forms should say
  in such windows, in the handoff's "To decide"
- **2026-11-05, tests review.** The rewrite deleted two tests it should
  have kept, the interleaved-piece net and the byte budget, and three
  tests could not tell their rule from the wrong one. Source: a file
  replaced without being read whole. Fixed in 3574904. Guard: the rule
  above
- **2026-11-05, fact-check review.** The chr14 one-Mb count and the
  window-read table had no data file; "the rest of the file reads as the
  GRCh38 one" was false for six chromosomes; 4.3 M was chr14's total and
  4.2 M its one Mb; several ranges and summaries were tighter than the
  data. Source: prose ahead of data. Fixed in 72e704e, the script now
  writing every number's file. Guard: the rule above
- **2026-11-05, measurement.** The CHM13 file's chr9 and chr14 hops: a 64
  kb window reads up to 2.0 M departure rows and graph-walks 5 refuses
  it. Source: the format's one placement per file. Open: the handoff's
  "To decide"
- **2026-11-05, the machine.** `/tmp/claude-1001` at its 8 GB quota from
  earlier sessions' scratch files; one command's output lost. Open: the
  user clears it
