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
- **A format choice made without measurement or an ADR.** Format 6 files
  every row of a chunk at `seq cs cs+1` because one commit said a full-span
  row shares a Tabix bin with its neighbour; nobody measured it, and plain
  `tabix` queries on the file return nothing. Rule: every format choice gets
  an ADR with the alternatives measured, and a column means what its name
  says
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
  on chr9, 2,172,351 jump over 1 Mb twice in a row, the second leaving
  near where the first landed, and 2,064,356 of those rejoin within 100
  kb of where the first left, a hop to the other copy and back (the
  return was checked only after the review of the landed work); they
  walk a median 257 to 512 bp on the far copy and at most 1 kb for
  1,698,238 (`results/arbitration/CHM13.chr9.hops.txt`, by
  `scripts/chm13-chr9-hops.py`): haplotypes alternate between collapsed
  copies every few hundred bp, which no `stay` of 311 bp absorbs, so the
  design review's hypothesis about `stay` refusing once-passed nodes
  explains at most the shortest hops and the cause is the graph, not the
  rule. Source: a file projected onto a reference that was not the
  graph's (evidence on one graph: GRCh38 in its own graph passes no node
  twice). Fixed: the hs1 files come from HPRC v2.1's CHM13-referenced MC
  graph (`hprc-v2.1-mc-chm13`), whose CHM13 passes none of its
  90,761,410 nodes twice; on its chr9 the file holds 70,960 records in
  84,745 rows and a 64 kb window's departure read at most 848 rows over
  the audit's windows (chm13-chr9.audit.txt; 458 was the one window
  sampled at 45 Mb, misquoted as the densest until the review of the
  landed work). The GRCh38
  graph's CHM13 file is not hosted. Guard: the header's `revisited`, which a host checks before
  publishing a file as exact; results in `results/arbitration/`
- **2026-11-05, the machine.** The inputs on ada the handoff names,
  `~/work/mc/chr22.gfa`, `~/work/pggb/chrY.gfa` and `~/hprc-gbz/`, are
  gone; recut from HPRC's S3 into `~/work/arb-format-opus/in/` by
  `scripts/arbitration-inputs.sh` (pggb chrY gives the port3 counts exactly: 471,497 pieces,
  425,040 records). `/tmp/claude-1001` past its quota again, losing one
  command's output. Open: the user clears `/tmp/claude-1001`
- **2026-11-05, the format arbitration (Fable agent).** `fuzz6.sh` resolved
  its own path and the writer's after `cd` into the scratch directory, so
  a relative invocation failed every seed with a build error ("no S
  lines" or no binary). It failed loudly, not silently, so no fuzz result
  was wrong. Source: a script only ever run with absolute paths. Fixed:
  paths resolved before `cd`, and a seed whose graph has no `S` line
  reports itself. Guard: run relative, and with `GFA_TO_TABIX=/bin/false`
  every seed reports a build failure
- **2026-11-05, review of the landed work.** Doc claims the committed
  files contradicted: "the densest window read 458 rows" on the CHM13
  graph's chr9 (458 was the 45 Mb sample; the audit's 64 kb windows
  reach 848 on chr9, 1,328 on chr14, 902 on chr22); "hop to the other
  copy and back" for 2,172,351 pairs whose return the script never
  checked (2,064,356 return within 100 kb once checked); "the same
  bytes on Minigraph-Cactus" for a pass-count tag against columns that
  cost 124,956 bytes of MC chr22's departure text; `combined.txt` saying
  every budget was lifted while the committed `dump.test.ts` lifted
  none; the handoff still saying the budget was off by default and
  listing the record without its pass counts. Source: prose ahead of
  data, and a script edited locally but committed unedited. Fixed in
  the commit after 0c8d428, `chm13-chr9-hops.py` now counting the
  return and refusing records with pass counts, whose columns it would
  misread. Guard: the rule above
- **2026-11-05, review of the landed work.** `audit6.py` checked an
  abridged row's offset, steps and bp against its piece but not that the
  piece lies in the detail record the row names, that `start` and `end`
  are the piece's first and last nodes on R, or that every detail piece
  has a row; no writer test had a node the reference passes on two
  sequences; `fuzz6.sh` broke a writer named by `PATH`. Source: tests
  and audits shaped by the implementation. Fixed in the same commit:
  the three audit checks, each shown to fire on a hand-tampered copy of
  graph-walks' `abridged.R` fixture and to pass on the three abridged
  fixtures; the test "a pass count counts every sequence of the
  reference"; `command -v` before `readlink`. Guard: `fuzz6.sh` fails on
  any nonzero "must be 0" line, which the new checks print
- **2026-11-05, review of the landed work.** walkDepartures gave an
  unexpanded abridged piece the wrong net when a departure left or
  rejoined inside it: the departure kept only its missing bp and the
  steps the cut held, so own bp in pieces the cut never read or past
  `ATTACH_BP` was lost or moved into the piece's net (HG03453#1 +227,316
  unexpanded against +2,382 expanded; 11 haplotypes over 29 MC chr22
  windows), and a piece whose handles both run against R read as along
  it. Source: tests shaped by the implementation (pieces whose own bp
  the cut always held). Fixed in graph-walks 277fa44: the departure
  keeps its whole `ownBp` and the piece's net drops the overlap, using
  the per-piece extent the format now states. Guard: unexpanded equals
  expanded, in seven tests that fail on ec8ecd9 (checked) and the
  `ownends.R` fixture; all 463 haplotypes match on 29 windows
- **2026-11-05, review of the landed work.** Forms places came from
  union-find over every mark, so one haplotype's mark could merge two
  common changes' places or name one (CYP2D6 placed at 42,125,912 by a
  single +1.6 kb replacement). Source: a relation (half-cover) assumed
  transitive. Fixed in ec8cad4 and ea95ac0: a place is a set of common
  spans that all half-cover each other, filled most carried first, and
  a rarer mark's place is its own span. Guard: tests that fail on
  ec8ecd9
- **2026-11-05, review of the landed work.** `formContradictions` was
  built from the code it checked (it imported six of structuralForms'
  functions), compared marks that merely touched, and looked only
  around the stated marks, so it missed contradictions; rewritten, it
  found 5 to 30 place contradictions per setting in ec8ecd9's forms on
  the 28 windows (same-size places sharing a start shared a key, as at
  LCR22A's +61 bp; a state's carriers not all half-covering the one it
  showed; folding matching places by key). Source: a checker written
  by the author of the rules it checks. Fixed in ea95ac0: the checker
  recomputes each member's changes from its departures and pairs them
  one-to-one under half-cover, sharing only `agrees`, and
  structuralForms meets it by construction. Guard: a test that fails if
  the checker imports more of structuralForms, hand-edited wrong
  results for every kind, and `results/forms-arbitration/strengthened.txt`
  (0 on the 28 windows, every floor). Open: the checker reads a form's
  keys, not the `marks` and `net` that `describeForm` draws; the gate
  table in `structural-forms.md` was not rerun
- **2026-11-05, review of the landed work.** The reader accepted a pass
  count of 0 and refused rows of the earlier format 6 writer without
  saying to rebuild; its README claimed a caller passing no budget never
  fetches an unbounded read, false for a source without
  `bytesForRegions`, detail reads (bounded by steps only) and attach
  fetches. Source: prose ahead of the code. Fixed in dd6986c. Guard: the
  row-refusal tests
- **2026-11-05, final review before release.** An `abridged` row's
  `hapOffset` and `bp` cover its whole piece, own steps before its first
  step on S or after its last included, where no departure record
  covers them (a contig's start or end, a move onto another sequence),
  so an unexpanded piece netted them as a change: on a hand-made graph
  built with `--abridge-bytes 1`, L and M net +30 unexpanded and 0
  expanded; pggb's satellite paths at contig ends are the main case.
  Source: the format's limits surfacing in a reader, again: a row stating
  less than the reader needs. Fixed in gfa-to-tabix 1a74b3e: the row's
  `hapOffset` and `bp` run from where its `start` step begins to where its
  `end` step ends, as a reader trims a walk row's piece. `nsteps` stays the
  whole piece's, the steps its detail record decodes, which graph-walks'
  expansion budget sums; a count of the stretch alone would let a
  satellite's own steps at a contig end past that budget. Every record
  leaves at a piece's last step on S and rejoins at a piece's first, so
  none ends inside the stretch, and graph-walks d2058b5 drops 277fa44's
  `ownTrimmed`. What it compensated for, each now impossible: a record
  leaving a piece with own steps after its leave (the row ends at the
  leave), one rejoining a piece with own steps before its rejoin (the row
  starts at the rejoin), both across W lines (the record's own bp hold
  both lines' ends), and a move onto another sequence and back (the steps
  before the move trail the leave). The contig's own ends, which it never
  covered, were this bug. A file from the earlier writer reads wrong
  without it and no reader can tell, so every format 6 file is rebuilt;
  none was released. Guard: the decoder in `tests/walks.rs` checks each
  abridged row against its piece's stretch, steps and end positions and
  strands, and that every base of a path from its first step on a
  sequence to its last lies in one piece's stretch or one record's own
  bp, which fails on main's writer, on `walks-two-refs.gfa` too; test "an
  abridged row spans its piece from its first step on R to its last" on
  `walks-contig-ends.gfa`, the graph above; `audit6.py` the same two
  checks, shown firing on main's `ownends.R` and `abridged.R` fixtures and
  on a record's `ownBp` off by one, clean on every fixture and `fuzz6.sh 1
  100`; graph-walks test "reads each haplotype to the net and coverage its
  walks give in full when an abridged piece holds its contig's first or
  last steps" on `contigends.R` (+30 on main's reader and writer). Not
  checked on real data: the local MC chr22 file comes from the earlier
  writer and no graph could be built on this machine
- **2026-11-05, final review before release.** `audit6.py`'s new check of
  an abridged row's ends compared node ids only, so a `start` or `end`
  pointing at another occurrence (`@k`) or strand passed while
  graph-walks read another stretch. Source: a check written to the
  common case. Fixed in gfa-to-tabix cba70b5: each end resolves as the
  format says, `start` at its `@k` or R's first occurrence, `end` at its
  `@k` or the occurrence nearest `start`'s position, the later on a tie,
  and compares its position in R and its handle with the detail piece's
  first and last steps on R. Guard: it fires on the review's `X#1#c` row
  with `6@1` rewritten `6`, and with `start` or `end` on the other strand,
  all three of which main's audit passes, and is clean on every
  graph-walks fixture and `fuzz6.sh 1 100`
- **2026-11-05, final review before release.** Forms place sets were
  filled in an order that ties in carriers and start left to input
  order, which differs from window to window: two orders of three
  equal-sized replacements gave different forms, and the checker passed
  both. Source: an unordered tie. Fixed in graph-walks 52557ed: spans
  fill places by carriers, start and end, and a span joins the place with
  the most carriers, then the earliest start and end; a span is one
  place's first at most, so both orders are total. Two more ties left
  to input order, fixed in the same commit: a state's median carrier
  among equal net changes, which picks the marks a form draws (`repl
  6kb->11kb` or `repl 10kb->15kb` for the same members), found by the
  shuffling test, and a rare form fitting two common forms of one size,
  found reading the rest of `structuralForms`.
  Guard: tests "forms are the same for every order of the haplotypes
  where places tie in carriers and start" (six orders and their
  reverses) and "a rare form that fits two common forms of one size joins
  the same one for every order of the haplotypes", both failing on
  dd6986c
- **2026-11-05, the machine, during the final review's fixes.**
  `/tmp/claude-1001` at its quota again: a full graph-walks run failed to
  load seven test files with no message, and a scratch file was written
  empty. `fuzz6.sh` was committed without its executable bit, so running
  it by path is refused. Source: the machine; a script only ever run
  through `bash`. Fixed: the checks ran with `TMPDIR` under the worktree,
  and `fuzz6.sh` is executable. Open: the user clears `/tmp/claude-1001`
- **2026-11-05, the 3.0.0 release workflow.** CI's `scripts/figures.py
  --check` failed: its walk-row parser still read format 6's earlier
  `end` column, dropped by 76c9223, so it ran off the row. No session's
  checks ran it since; the release stopped at its tests and published
  nothing. Source: a check left out of the local runs (the session ran
  `cargo test`, clippy and fmt, not the whole CI job). Fixed: the
  parser decodes by `nsteps` as the spec does, and the README figure
  redrawn with format 6 rows. Guard: run every step of `push.yml`'s
  "Format, lint and test" job before a release push
- **2026-11-05, the handoff's list, porting bandage-core to graph-walks
  5.** A row for a haplotype that jumps over the window (`skipRowOf`)
  stated `offReferenceBp: 0`, claiming nothing off the reference however
  much sequence of its own the haplotype carried there. Source: a fact
  format 5 did not hold (a skip row had no own bp), hard-coded rather than
  left unstated. Fixed in bandage-core 240b9e8 (13.0.0): a stepless row's
  `offReferenceBp` is its departures' `ownBp`, and its readout states it
  ("no step on GRCh38 across 2.5 kb · 4 kb of its own"). Guard: tests "a
  haplotype with no step in the window draws its departure under it" and,
  on graph-walks 5's own cut of `follow.GRCh38`, "a stepless row states
  the own bp between the departure's ends"
- **2026-11-05, ADR 0009's consequences, porting bandage-core.** The
  hand-off `GraphTables.skips` was optional, so graph-walks 5 under
  bandage-core 12 drew no departure and raised no error. Source: an
  optional field for a fact the viewer must show. Fixed in bandage-core
  240b9e8 (13.0.0): `departures` is required, a source with none passes
  `departureTable()`, and bandage-core's `GraphTables` mirror is held
  identical to graph-walks 5's by `typecheck/graphWalks.ts`, both ways and
  optional fields included. Guard: `tsc` fails on that file when the
  pinned graph-walks changes the tables' shape (checked by adding a field
  and by making `departures` optional, each of which failed)
- **2026-11-05, reading graph-walks 5.0.0's README for the port.** Its
  "Contained cuts" and "How a cut works" sections still describe format
  5's follow rounds ("follows each haplotype ... until it rejoins", "reads
  on to that chunk, in up to three rounds", `pv:`/`nx:` tags), which 5
  removed; "Fragments" and "Changes in 5" say the opposite. Source: a
  rewrite that left sections it did not touch. Open: fix in graph-walks'
  README at its next release
- **2026-11-05, porting BandageJS to graph-walks 5.** A cut read chunks
  from the window's start to its end, not over the drawn stretch with its
  `context`, so context past the window's last chunk was dropped: on
  `skip.GRCh38` (chunk 10) a cut of 32-38 with context 5 kept R to 40
  where 27-43 with none keeps it to 50; at HPRC's 64 kb chunks and 1 kb
  context about 1.5% of BandageJS windows lost up to 1 kb on the right.
  Source: a rewrite dropping what the old mechanism compensated for,
  **re-found** as a class: graph-walks 4's follow rounds read past the
  window and hid it, and 43910ec removed them without listing that.
  Fixed in graph-walks 3d9889a (5.0.1): the read runs from the chunk before
  the drawn stretch's start through its end. Guard: test "a cut reads the
  chunks under its context, not only under its window", both sides, which
  fails on 5.0.0; unexpanded still equals expanded on the release check's
  seven MC chr22 windows
- **2026-11-05, porting the tube map to graph-walks 5.** `WalkGraph.tables`
  took `departures` with a default of none, so a caller still making
  graph-walks 4's two-argument call compiled and drew no departure at
  all, which ADR 0009's required hand-off exists to prevent. Source: a
  default kept from a migration step, the hand-off required on
  `GraphTables` but not on the call that fills it. Fixed in graph-walks
  5.0.2: the parameter is required. Guard: a typecheck test whose
  two-argument call must be a type error. Also from the ports: bandage-core
  13's `laidOutGraph` takes GFA text only, so ggbandage repeats its
  layout calls for tables (open)
- **2026-11-05, porting jb2hubs to graph-walks 5.** The page's converter
  (`pangenomeWalkForms.ts`) turned the `other` form, `*` at every site and
  no marks, into a form with no marks, which the panel counts as GRCh38's
  structure and gives a lane. Source: a reader of the forms' states that
  listed the states it drew (`.`, `~`) and dropped the rest silently.
  Fixed on jb2hubs `format6`: the form is marked `other`, gets no lane,
  and counts in the "other forms" row. Guard: test "the walks' other form
  gets no lane and is not the reference's structure", which fails with
  either half of the fix removed
- **2026-11-05, porting jb2hubs to graph-walks 5.** The page keyed a
  change by site, kind and size (`changeKey`), so graph-walks 5's
  `-2000@1000` and `-2000@2500`, one size at two places in a site over
  1 kb, merged into one change with both forms' carriers. Source: an
  identity rebuilt from a mark's fields where the library's state key
  already is the identity. Fixed on `format6`: a walk mark's key adds its
  state. Guard: test "one size deleted at two places in a site is two
  changes"
- **2026-11-05, porting jb2hubs to graph-walks 5.** `formsCut` gained
  default byte and departure budgets, which the page's sidecar fallback
  did not catch, so a refused window would have shown an error rather
  than the callset's forms; `generatePangenomeLocusGenes.ts` cut with no
  budget, which 5's 4 M step default refuses at MHC class II (11 M steps
  expanded), and `generatePangenomeGeneModels.ts`'s `...WALK_BUDGETS`
  started carrying a departure budget its catch did not expect. Source:
  callers that relied on "no option means no limit". Fixed on `format6`:
  `WalkFormsTooLarge` covers `RegionTooLargeError` and
  `DepartureReadError`; the locus generator lifts every budget and the
  gene-model one the departure budget. Guard: test "a read past
  graph-walks' budgets falls back to the callset, and nothing else does";
  the generators have none (build-box scripts)
- **2026-11-05, porting jb2hubs to graph-walks 5.** `scoreForms.py`
  scored the `other` form's members as rare carriers claiming no change.
  Source: as above, a reader that did not know the new form. Fixed on
  `format6`: `printWalkForms.ts` writes `other: true` and the scorer counts
  its members as "no claim: other form". Measured on the 3.0.0 MC chr22
  file at the gate's cyp2d6 and gstt1 windows against `truth2.tsv`: the
  rare line read 3 of 5 (auto floor) and 19 of 27 (50 bp) with them, 2
  of 2 without; every other line unchanged (801/801, 779/779, 814/814
  unfolded)
- **2026-11-05, porting jb2hubs to graph-walks 5.**
  `checkPangenomeAssets.mjs`, the check that every url a pangenome config
  names resolves, read `adapter.uri` only, so the lane track's
  `walksUri` (the HPRC walk file) was never probed and a config naming a
  missing walk file passed. Source: a url field the check's adapter list
  did not know. Fixed on `format6`: `<walksUri>.walks.bed.gz` and its
  `.tbi` are probed. Guard: the check FAILs on the `-f6` url until it is
  uploaded. Also: `structuralForms` takes `floorBp: NaN` without
  complaint and returns forms (170 haplotypes in `other` at cyp2d6);
  `printWalkForms.ts` now refuses a floor that is not a number (open in
  graph-walks)
- **2026-11-05, porting the JBrowse plugin.** bandage-core 13 marks a
  walk row whose fragment ends at the window's edge as "contig ends inside
  the window" (`walkRowRuns.ts` sets `contigEnds` from whether the last
  step is on the reference, true for every format 6 fragment), even where
  a departure record says it goes on and rejoins: `walks6_rejoin` at
  chr1:1000-1500, HG002#1 leaving at 1500 with 4 kb of its own. Source: a
  rule written for format 5, where a fragment running off R meant the
  contig went on, met by format 6's fragments that end on R. Fixed in
  bandage-core 23169a2 (13.0.1): a side's contig ends only where its last
  step is on R with no departure at it and no trimmed bp past it;
  otherwise `WalkStop.goesOn` names the departure and the readout says
  "goes on near … · … of its own". Guard: `graphWalks.test.ts` on
  `rejoin.GRCh38` at chr1:1000-1500 and 4000-4500 with context 500, and
  `records.GRCh38` HG002#1 as the control that truly ends
- **2026-11-05, fixing the contig-ends bug.** Two more format 5
  assumptions in bandage-core 13: with no context, `flanked` takes every
  walk as whole, so a walk departing at the window's edge reads complete
  with a length change ("0.5 kb (−500 bp)", read as a measured deletion)
  and its departure unmentioned; and a walk whose only step on the cut is
  a flank gets no direction from `partialSide` and draws the flank,
  outside the window, as a "partial walk", not saying it departs. Source:
  rules written for format 5's fragments, which ran off R. Fixed in
  bandage-core 899ee29 (13.0.1): with no context the reference's
  outermost nodes in the cut stand in for flanks, so a walk-file walk
  that departs or ends inside reads "goes on near …" or "contig ends
  inside the window"; a walk with no trim and no departure, as GFA
  extracts give, stays whole (a pggb test showed odgi-extract pieces end
  on R wherever the subgraph clips them); and a lone flank takes its
  direction from a departure's strand at that step, else the side
  trimmed alone, reading "goes on near …" with 0 bp in the window.
  Guard: `graphWalks.test.ts` on `rejoin.GRCh38` and `records.GRCh38` at
  context 0 and 500, with true-whole and true-end controls. Left: a
  contig that starts at a flank and runs off R toward the window for
  good reads "contig ends at the window", since `GraphPath` has no step
  strands
- **2026-11-05, porting the JBrowse plugin.** The plugin adjusted its
  tests to graph-walks 5.0.0's missing right-hand context (the reference
  ending at 3200, not 3800, in `walks6_maxnode`), reading the README as
  saying so; 5.0.1 fixed the read. Source: a port fitted to its target's
  bug. Fix: below, with the plugin on `^5.0.2`
- **2026-11-05, porting the JBrowse plugin.** Open: graph-walks 5 calls
  `expand(name)` with the name alone, so the plugin cannot replace its
  64-name `EXPAND_NAMED_MAX` cap by a per-row threshold; and the forms'
  departures carry no pass counts, so the Forms track cannot say
  "placement choice". Both are graph-walks features for a later minor
- **2026-11-05, ggbandage's final pass on the 13.0.1 candidate.**
  bandage-core 899ee29 keeps "a walk with no trimmed bp and no departure"
  whole, meant for GFA extracts, so on a walk file a contig ending inside
  the window with no departure reads as a whole walk shorter than R ("0.3
  kb (−200 bp)", `linked` true), while one with an unrelated departure
  reads "contig ends inside the window": repro `clip.REF.gfa`, REF
  `>1>2>3>4>5`, CLIP `>1>2>3`, CLIPSNP `>1>6>3`, 100 bp nodes, chr1:1-500.
  Source: a rule keyed on the absence of facts, where a walk file states
  them (trimmed bp 0 means the contig ends) and a GFA extract does not.
  Fixed in bandage-core e4e5c10 (13.0.1): the source decides; walk-file
  tables state trimmed bp, 0 kept on the path, so a side with no trim and
  no departure is a contig end, and GFA text and gbz-base extracts, which
  state none, stay whole. Guard: `graphWalks.test.ts` on `clip.REF`
  (ggbandage's repro) at chr1:0-500 (context 0, 100) and 50-450, with
  `rejoin.GRCh38` HG002#2 and the pggb whole-reference test as controls
- **2026-11-05, the tube map's final pass.** Its paths panel found a walk
  file's sequence length by probing chunk starts upward from 0, assuming
  rows start at 0 and a `.tbi` can tell chunks apart; the shipped E. coli
  slice (rows from 1,004,500) and any file with chunks under 16 kb listed
  length 0. Older than the port, hidden because the hosted HPRC files
  satisfy both. Source: tests and fixtures in one 64 kb chunk. Fixed in
  sequenceTubeMap 81f867f: it asks whether rows lie at or past a 16 kb
  step and reads that step's rows. Guard: test "the E. coli file lists
  K12#1#chr at length 1,004,961"; the departures fixture rebuilt with
  `--chunk 100` so its windows cross chunks, which fails on graph-walks
  5.0.0; a 3,279-window sweep over 16 files at chunks of 10 to 5,000 bp
  found nothing on 5.0.2 and caught 5.0.0's undrawn steps (not committed)
- **2026-11-05, the format review (four reviewers, on reading S6's real
  rows).** Walk format 6 files every row of a chunk at its first base,
  `seq cs cs+1`, so `tabix file chr1:15-35` returns no rows (98 of 100
  1 kb windows on MC chr22), and only a reader that rounds to chunk starts
  gets any. Adopted in 3953bb1 on 2026-10-08, the day after 10d3ae1 filed
  whole spans, with no numbers; 842a19b then made readers query from the
  chunk before. The spec's reason, bin sharing, holds for @gmod/tabix and
  not for htslib. The tube map's chunk-length probe (above) is the same
  key misleading a consumer. Source: a format choice made without
  measurement or an ADR. Decided in [ADR 0010](adr/0010-walks-unit-table.md):
  walk format 7 drops the key, and every line states its true stretch.
  Open until gfa-to-tabix 4.0 writes it. Guard: the writer checks each
  line's extent against its decoded steps, and `verify7.mjs`'s release
  checks become tests
- **2026-11-05, the format review.** graph-walks 5.0.2's `decode` drops a
  chunk already decoded under another attach fetch's name filter, so of
  two departure records whose leave chunks are adjacent, one loses its own
  steps (chr22:22865052, NA18608#2). Source: tests shaped by the
  implementation, no fixture with adjacent leave chunks. Open: fixed in
  graph-walks 5.0.3 if ADR 0010 keeps format 6, else in the format 7
  reader. Guard: a test with two records whose leave chunks are adjacent
- **2026-11-05, the format review.** graph-walks sizes its departure and
  attach reads from the file-wide `maxnode` instead of the `#long` passes
  that need them. On pggb chrY, where `maxnode` is 1 Mb, a 1 kb window
  fetches 4.0 MB in about 10 requests and 24 of 100 windows hit the budget
  and are refused; sized from `#long`, 1.0 MB and 1 of 100. Departure
  reads are about 95% of a pggb window's bytes. Source: evidence on one
  graph (MC, `maxnode` 1,024). Open: with the item above
- **2026-11-05, the format review.** Every read starts one chunk before
  the window. The rule came with the one-base key (842a19b) and later
  backed the stay guard; format 6 removed that need, since a stay can no
  longer absorb a node the reference passes once, and the rule stayed. On
  MC (`maxnode` ≤ chunk, no `#long`) it doubles a small window's walk read
  (96 KB against 64 KB for 1 kb); graph-walks' own cut matched on 232 of
  240 windows without it, the rest each gaining one departure's own
  steps. Source: rewrites that drop what the old code compensated for, in
  reverse: a mechanism kept after its reason went. Open: with ADR 0010
- **2026-11-05, the format review.** @gmod/tabix fetches one BGZF block
  past each read's last chunk, about 30 KB, because no chunk starts on a
  block boundary, so a 1 kb window pays for its own chunk, the chunk before
  and most of the chunk after. Source: a container behaviour nobody
  measured. Open: with ADR 0010 (block-aligned chunks in the writer, or an
  index giving exact ends)
- **2026-11-05, the format review.** For two 22q11 windows, graph-walks
  5.0.2 gave a different cut in a 240-window batch than when each window
  ran alone; the narrower read was stable. Cause not found. Source: unknown.
  Open: reproduce with the review's scripts before graph-walks 5.0.3 or the
  format 7 reader
