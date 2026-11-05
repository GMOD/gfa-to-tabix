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
- **A fact or a safeguard left to every reader.** An abridged row's extent,
  whether an end's pass is a choice, a byte budget: where the file or the
  library leaves each reader to reconstruct or remember it, a reader gets
  it wrong. Rule: when a reader needs a fact to be correct, the file states
  it on the row that needs it, and a safety limit is the library's default
- **A cut justified by a mechanism not yet built.** `leavePasses` went
  for an `mp` tag that was never written. Rule: cut a field only once what
  replaces it is written and read
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
  picture (`mc22.forms-compare-review.txt`). Decided 2026-11-05: the
  forms keep the chain model's reading (the handoff's item 2), and
  HG00126#1's flip is a rare no call folding to the majority state
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
  it. Source: the format's one placement per file. Interim, 2026-11-05:
  host the file as it is with those windows refused; a CHM13-referenced
  graph is the design review's alternative, for the user (the handoff's
  item 2)
- **2026-11-05, the machine.** `/tmp/claude-1001` at its 8 GB quota from
  earlier sessions' scratch files; one command's output lost. Open: the
  user clears it
- **2026-11-05, this author, from the tests review's 28 windows.** A
  site was the union of every overlapping mark, so one haplotype's rare
  long departure merged the sites it crossed for everyone: at chr22
  20.3-20.4 Mb one HG01175#1 departure over 108.7 kb of R, with 126 kb
  of its own, joined two sites of 461 and 460 haplotypes into one of 137
  states (173 haplotypes in `rareCarriers`, against 158 with the sites
  apart). The chain model surfaces far more long departures than
  graph-walks 4's cut saw, so it can happen wherever a rare long
  departure crosses two sites; one of the eight windows compared had
  it. Source: a rule written for marks inside the window, met by the
  chain model's departures over it (the format's limits surfacing in a
  reader). Fixed in graph-walks be081a5: sites come from marks
  `minCarriers` haplotypes share, each covering half of the other, and a
  rarer mark states itself at every site it overlaps without widening
  one. Of eight MC chr22 windows only that one changes, to two sites of
  74 and 24 states at 20338159-20340085 and 20355284-20361765, where
  4.6.0's were 20338159-20343643 and 20355284-20361765
  (`results/minimal/mc22.forms-sites.txt`). Guard: tests "a rare mark
  over two common sites keeps them apart and states itself at each",
  "rare marks overlapping no common site make a site of their own" and
  "a mark shared by minCarriers haplotypes ... makes sites"
- **2026-11-05, logic review of be081a5.** A rare plain mark at a site
  under 1 kb, where plain pieces are summed, still widened that site
  over its whole span and was stated only at the last site it overlapped,
  so the merging be081a5 set out to stop came back there: at chr22
  42.11-42.13 Mb two rare marks made two overlapping sites of one.
  Source: tests shaped by the implementation (the new tests built no
  site under 1 kb), and a lookup (`siteIndex` by the piece's end) kept
  from the old rule without asking what the new one needed of it.
  Fixed in graph-walks edf4acd: a plain piece joins every summed site
  it overlaps, and a summed change widens its site only when no piece of
  it is a rare mark. Guard: tests "a rare plain mark from a summed site
  neither widens it nor merges sites" and "a rare plain mark states
  itself at every summed site it overlaps"
- **2026-11-05, logic review of be081a5.** A form named a rare mark
  spanning two sites twice when the state's median carrier differed
  between the sites, since the dedupe keyed on exact coordinates: net
  -41,980 where about -22,000 was right. Source: a rule written for one
  carrier. Fixed in edf4acd: a mark over several sites dedupes on its
  kind, state key and sites. Guard: test "a form names a rare bridge
  once when its carriers' medians differ by site"
- **2026-11-05, logic review of be081a5.** `commonMarks` compared every
  mark pair and kept a set per mark: 1.4 s and 855 MB on 46k marks, out
  of memory at 184k (a 50 bp floor over a wide window). Source: tests
  and windows too small to show it. Fixed in edf4acd: marks of one
  span compare once and a set stops at `minCarriers`; 0.3 s at 46k and
  0.6 s at 185k (`results/minimal/mc22.forms-sites.txt`). Guard: none
  automated
- **2026-11-05, fact-check of c5ef587.** The CHM13 decision said graph-walks
  5 refuses chr9's repeat windows, but `departureByteBudget` defaults to
  no limit and no caller passes it: `formsCut` had no such option, so a
  Forms read there would fetch about 22 MB per window. The refusal had
  been inferred from gzipped sizes, never run. Source: prose ahead of
  data. Fixed in edf4acd: `formsCut` takes `departureByteBudget` and
  passes it to both cuts; the handoff says plugin 9 and BandageJS must
  pass `WALK_BUDGETS`. Guard: test "throws DepartureReadError past its
  departure byte budget"; plugin 9's own test is still to write
- **2026-11-05, fact-check of c5ef587.** Wordings ahead of the data: the
  user's "open to minimizing" written as confirming each cut; "307
  haplotypes" for a state 304 carry (307 is the form); "173 haplotypes
  folded" by the merge (158 stay in `rareCarriers` without it);
  "back to the two sites 4.6.0 had" (the first ends 3.5 kb earlier);
  "this became common" (one window of eight); "108 kb jump" for a
  departure with 126 kb of its own; "hosted" for a file not yet hosted;
  and HG00126#1 called "no fold artefact" in one doc and "an artefact of
  rare-state folding" in another. Source: prose ahead of data. Fixed in
  the commit after c5ef587. Guard: the rule above
- **2026-11-05, design review.** Folding puts haplotypes in forms they
  don't belong to: at chr22:22.3-22.4 Mb nine haplotypes with 500 to
  740 kb departures over the window show as `ref`, and HG03784#1 and #2
  as "ins 9.1kb +1", a 6.06 kb insertion they lack; a common mark still
  merges every site nested in it. Source: fold and site rules tuned on
  loci without jumps over the window, met by the chain model's. Open:
  sites from the shared relation, a fold guarded by tolerance, measured
  on jb2hubs' gate loci first (handoff item 2)
- **2026-11-05, design review.** No record says whether its end lies on a
  node the reference passes more than once, and `mp` is not written, so
  no reader can tell a hop between copies from a jump, and plugin 9's
  Forms track has nothing to say "placement choice" from. Source: the
  minimal cut of `leavePasses`/`rejoinPasses`, justified by an `mp` tag
  not yet written, which covers ends inside the walk read only. Open:
  the handoff's item 2
- **2026-11-05, arbitration of the forms (Opus and Fable agents,
  independently).** Forms put members in rows their own departures
  contradict: 315 contradicted members on the 28 chr22 windows at the
  auto floor (1,849 at 50 bp) and 417 on the jb2hubs gate, among them
  the 22.3 Mb jump carriers shown `ref`, HG03784 shown "ins 9.1kb +1"
  and HG00126#1's no call shown `inv 48.7kb`. Source: the forms had no
  rule for what a row may say of its members; four fold rules (rare
  state to nearest net, no call to majority, rare form to nearest form,
  majority marks on shared sites) were tuned on loci and scored against
  assemblies with rare carriers set apart, so nothing checked the
  output. Fixed in graph-walks 7601e9e: one tolerance every fold
  passes, no call never folds, `~` and `other` claim nothing, shared
  decided after forming. Guard: `formContradictions` (0 on the 28
  windows and the gate, every floor, folded or not) and its tests;
  numbers in `results/forms-arbitration/`
- **2026-11-05, arbitration of the forms, re-found.** HG00126#1 at 21.4
  Mb, read the same day as "a rare no call folds to the majority" and
  left so, is a no call shown as a call. Source: a decision made ad hoc
  (explaining a rule instead of checking what it claims). Fixed in
  7601e9e: it is in `other`. Guard: test "a rare no call is never shown
  as a call"
- **2026-11-05, arbitration of the forms.** State keys had no place, so
  at CYP2D6 4 haplotypes with a 13.7 kb insertion at 42,134,095 were
  drawn at another carrier's 42,125,923; the same at merged IGL and
  LCR22A sites. Source: a key written for small sites, applied to
  merged wide ones. Fixed in 7601e9e: at a site over 1 kb a change keys
  on its place, from the half-cover relation. Guard: the checker's
  `place` kind and its test. The no-fold branch the Fable agent wrote
  in parallel still showed it, which decided between the two
- **2026-11-05, arbitration of the forms.** A summed change widened its
  site past the span its states were read over: at 50.78 Mb three
  haplotypes' 1 kb insertions in the widened part were stated `ref`.
  Source: widening kept while the read span stayed narrow. Fixed in
  7601e9e: no widening. Guard: test "a site spans the marks it comes
  from"
- **2026-11-05, format arbitration (re-found from the design review).**
  No record said whether an end lies on a node the reference passes more
  than once, so no reader could tell a hop between repeat copies from a
  jump. The 2026-11-04 cut of `leavePasses`/`rejoinPasses` leaned on an
  `mp` tag on `ref` rows that was never written and could not have marked
  a record's far end, which lies outside the walk read for exactly the
  hops in question. Source: a cut justified by a mechanism not yet built
  (a decision made ad hoc). Fixed: `leavePasses` and `rejoinPasses` are
  columns again, `ref` rows carry `passes` and the header `revisited`;
  graph-walks reads them into `WalkDeparture`, the departure table and
  `WalkNode.passes`, computes them for departures inside a piece and
  exports `placementChoice`. Guard: tests "a record states how many times
  the reference passes each end" and the walks-repeat `ref` rows
  (gfa-to-tabix), "a departure computed from steps takes its ends' pass
  counts from the ref rows" and "a record row without pass counts is
  refused, not misread" (graph-walks); `audit6.py` checks every record's
  counts against the `ref` rows and those against the positions the file
  holds, and fails a file with a count off by one (tried by hand)
- **2026-11-05, format arbitration.** An abridged row's `bp` counted its
  moved pieces alone, so every reader had to rebuild the path's extent
  across other chunks' pieces and absorb the departures between them;
  graph-walks got that wrong twice (graph-walks 4's `chains`, then the
  forms rewrite, fixed in 73f2e6b). Source: the format's limits surfacing
  in a reader; a row standing for pieces that are not consecutive. Fixed:
  one `abridged` row per moved piece, with that piece's `hapOffset`,
  `nsteps` and `bp`, sharing the path's detail record; graph-walks reads
  each as an exact net and reads a shared detail record once. What the old
  take-in compensated for, carried over or not: pieces of other chunks
  between moved pieces (now rows of their own, nothing to absorb), the
  departures between moved pieces (now records shown as departures, not
  folded into a net), abutting abridged pieces (still one net), and a
  departure across W lines leaving and rejoining inside two abridged
  pieces (still one net with its missing bp). Guard: the test decoder in
  `tests/walks.rs` checks every abridged row against its detail piece,
  `audit6.py` likewise ("abridged rows unlike the piece their detail
  record holds", tried by hand with a bp off by 12), the forms test on
  `interleaved.R` (net 84 abridged and expanded), and graph-walks tests
  "each abridged piece is a net over its own stretch" and "detail records
  read at once ..." (one read per shared record)
- **2026-11-05, format arbitration.** graph-walks' budgets defaulted to no
  limit, so the CHM13 refusal the handoff promised held only for callers
  that passed `WALK_BUDGETS`, and none did before edf4acd. Source: a safety
  rule placed on every caller instead of the library. Fixed: `cut`'s step,
  byte and departure byte budgets default to `WALK_BUDGETS`, `Infinity`
  lifts one; `formsCut`'s cuts keep at least `FORMS_STEP_BUDGET` steps.
  Guard: test "a cut keeps to WALK_BUDGETS unless its caller lifts them".
  Open: a `TabixSource` without `bytesForRegions` still skips the byte
  budgets; @gmod/tabix has it
- **2026-11-05, format arbitration, diagnosis of the CHM13 chr9 rows.** In
  the GRCh38 graph, CHM13 passes 209,578 nodes more than once by the
  build's count (513,592 counted from the published GBZ by
  `scripts/reference-passes.sh`, not reconciled): its chr9
  pericentromeric copies share nodes. Of 2,241,003 consecutive record pairs
  on chr9, 2,172,351 hop over 1 Mb to the other copy and back, after
  walking a median 257 to 512 bp there and at most 1 kb for 1,698,238 of
  them (`results/arbitration/CHM13.chr9.hops.txt`, by
  `scripts/chm13-chr9-hops.py`): haplotypes alternate between collapsed
  copies every few hundred bp, which no `stay` of 311 bp absorbs, so the
  design review's hypothesis about `stay` refusing once-passed nodes
  explains at most the shortest hops and the cause is the graph, not the
  rule. Source: a file projected onto a reference that was not the
  graph's (evidence on one graph: GRCh38 in its own graph passes no node
  twice). Fixed: the hs1 files come from HPRC v2.1's CHM13-referenced MC
  graph (`hprc-v2.1-mc-chm13`), whose CHM13 passes none of its
  90,761,410 nodes twice; on its chr9 the file holds 70,960 records in
  84,745 rows and the densest window read measured 458 rows. The GRCh38
  graph's CHM13 file is not hosted. Guard: the header's `revisited`, which a host checks before
  publishing a file as exact; results in `results/arbitration/`
- **2026-11-05, the machine.** The inputs on ada the handoff names,
  `~/work/mc/chr22.gfa`, `~/work/pggb/chrY.gfa` and `~/hprc-gbz/`, are
  gone; recut from HPRC's S3 into `~/work/arb-format-opus/in/` by
  `scripts/arbitration-inputs.sh` (pggb chrY gives the port3 counts exactly: 471,497 pieces,
  425,040 records). `/tmp/claude-1001` past its quota again, losing one
  command's output. Open: the user clears `/tmp/claude-1001`
