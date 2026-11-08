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
  implementation, no fixture with adjacent leave chunks. The mechanism:
  the attach fetch for chunk `cs` reads from the chunk before, so it
  decodes chunk `cs − chunk` under its own records' names and marks it
  done, and the fetch for a record leaving in `cs − chunk` then skips it;
  either order loses one record's steps, and which one depends on which
  read returns first. Fixed on graph-walks' format7-reader branch before
  the port: `decode` remembers the name filters each chunk was decoded
  under and decodes again for names none of them took, and an attach
  fetch is skipped only when the chunk was decoded for that record's
  name. Format 7 keeps both rules, keyed by unit. Guard: test "two records
  whose leave pieces lie in adjacent chunks both get their own steps" on
  `test_data/attach.GRCh38.gfa`, which fails on 5.0.2 (HG003#1's `>21`
  missing)
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
- **2026-11-05, the format 7 writer, replacing format 6's Tabix filing.**
  What format 6's mechanisms made up for, and where each went:
  - **`#long`:** a reader widened its read for a reference node longer
    than a chunk. Now a tile's extent runs to its longest node's end, so a
    read by extent reaches it
  - **`maxnode`:** widened every departure and attach read. Now a
    departure line's extent covers its end nodes, and the pyramid files it
    in every block of that cover
  - **The one-base key and the chunk-before rule:** only a reader that
    rounded to chunk starts got rows. Now the key is gone, and every line
    states its stretch
  - **`seq~cs` detail sequences at `DETAIL_SPACING`:** one record per
    Tabix leaf bin, so a query for a record read no other. Now each record
    is its own `detail` unit with exact bytes, and `DETAIL_SPACING` is
    gone
  - **`seq~departure` rows clipped to bin-sized blocks:** each row sat in
    a bin no larger than itself. Now each block is a unit, and the record's
    line in it is whole and the same in every block
  - **The `.csi` fallback past 512 Mb:** the unit table has no coordinate
    limit
  - **Holding a sequence's detail records on disk until its main rows are
    written:** Tabix needed each sequence's rows together. Kept, since a
    table lists its units in file order
  - **`bed::Writer`'s `.partial` name and rename, and its removal of the
    partial files when a build fails:** kept, as `.tmp-<pid>` for both
    files, the data file renamed before the directory is written. The
    first commit dropped the removal; the test "a failed write leaves no
    temporary file" guards it

  The `maxnode` test is gone with the header line. Source: rewrites that
  drop what the old code compensated for. Guard: `tests/walks.rs`'s
  `verify`, the release checks of `verify7.mjs`, runs on every file the
  tests build
- **2026-11-05, the format 7 writer.** Arbiter A's converter (`build.mjs`,
  `s7.mjs`) keys detail records by path name. It names a `detail` unit
  `cs:d` by looking up the path's last `abridged` row, so two records of one
  path in a tile (two of its contigs abridged there) both take the last
  number. On walks-records.gfa at `--tile 7 --abridge-bytes 1`, unit `0:2`
  appears twice and `0:1` never. On MC chr22, 355 of the 2,468 detail
  numbers that `abridged` rows name reach, in the converter's file, a unit
  holding another path's rows or no unit
  ([walks-container/writer/](walks-container/writer/README.md)). So the
  converter's files, `~/work/arb-arbA/out/` and the genome-wide build from
  the same scripts, can't test expanding an abridged piece. Found by
  comparing the writer's output with the converter's on every test GFA
  and on fuzz graphs. Source: evidence on one graph (the converter checked
  on MC and pggb, and pggb has no such tile).
  Fixed in the writer, which numbers records as `routes.rs` makes them.
  Guard: `verify` refuses two tiles or two detail units of a sequence
  with one name. The 'abridged' tests build walks-records.gfa at a byte
  budget of 1
- **2026-11-05, the format 7 writer.** The writer first gave each `ref`
  row its own stretch. The ADR's table gives `ref` rows the tile's
  extent, as rows of the tile's dictionary; the two differ only in a tile
  with several `ref` rows. Found by the same comparison, on fuzz graphs
  whose reference has holes. Source: tests shaped by the implementation,
  since every hand-written fixture has one `ref` row per tile. Fixed before
  the first commit. Guard: `verify` checks that each `ref` row states its
  unit's extent and that the extent is the union of the ref rows'
  stretches and the pieces' spans
- **2026-11-05, the format 7 writer.** For a departure whose end step is
  on a node of 0 bp, the converter takes the extent of the R node that
  starts or ends at the breakpoint, a neighbour. The writer takes the end
  step's own node, as the ADR words it ("its first end node"), widened by
  the breakpoint stretch. Every departure line agrees between the two on
  fuzz graphs with no 0 bp node. Source: a spec read two ways. Decided:
  the ADR's reading, stated in walks-format.md. Guard: none needed in
  readers, which keep lines overlapping their window either way
- **2026-11-05, the format 7 writer.** ADR 0010's file sizes (59.31 MB on
  MC chr22, 187.92 MB on pggb chrY) are the converter's, compressed by
  Node's bundled zlib. The writer at zlib-rs level 6, the level the walk
  writer had always used, wrote 60.05 and 196.58 MB from the same blocks;
  deflated again by one zlib, the two files agree within 0.3 KB. Source: a
  format choice made without measurement, the compression level, never
  measured for walk files. Fixed: walk files at zlib-rs level 7, its first
  on `deflate_slow`, 58.49 and 186.82 MB in the same time
  ([walks-container/writer/](walks-container/writer/README.md)). Guard: the
  writer's results list sizes by compressor and level, so a later change
  of crate or level is measured against them
- **2026-11-05, the format 7 writer.** `audit6.py`'s reach rule for a
  departure inside a piece at one point (leave and rejoin breakpoints
  equal) asked that a window one base either side read the piece's chunk.
  In format 7 a tile whose reference nodes all have 0 bp has an empty
  extent, `[p, p)`, which the read rule's overlap fetches only for a
  window holding bases on both sides of `p`; a fuzz graph (seed 10) has
  one. Source: a rule carried from a mechanism (the chunk-before read) that
  format 7 removes. Fixed in `audit7.py`: every window over the stretch
  reads the tile, the window over a point being one that holds bases on
  both sides. Guard: `fuzz7.sh` over 300 seeds; walks-format.md states
  the empty extent
- **2026-11-05, the genome-wide format 7 check (CHM13 chr14 13.20 Mb).**
  A departure record's own steps can lie in the rejoin's tile, where the
  ADR and the spec send an attach fetch to the tile holding the leave base.
  NA19185#2#CM087748.1 leaves at 13,472,637 at the end of one W line and
  rejoins at 13,135,857 in the next. That line starts with its own steps,
  which take the tile of the first reference step after them, the
  rejoin's (13,107,200); format 6's chunk-before read happened to hold
  them. Within one W line, own steps after the leave take the leave's tile;
  across lines, the next line's lead takes the rejoin's, and both can.
  Source: a reader rule written from where own steps usually are, not
  from the placement rules. Fix: each record names the tiles holding its
  own steps on its sequence, in a column `ownTiles`, and the spec says
  which they are. Guard: a test with a jump back across W lines, one
  within a line and one with own steps on both sides; `audit7.py` checks
  every record's `ownTiles` against the tiles its decoded own steps lie in
- **2026-11-05, the genome-wide format 7 check.** CHM13's file is 1.78 GB,
  and the prototype scripts read whole files, which Node refuses past
  2 GiB; `verify7.mjs` is one of them, and `walks-truth.py cost` read
  whole files too. Source: scripts sized on chromosome files. Fix: a
  streaming `verify7.py` with the release checks, which `fuzz7.sh` runs;
  `walks-truth.py cost` reads units by offset. The writer streams through
  the BGZF writer and keeps offsets as u64. Guard: a unit test writing a
  unit file whose blocks start past 2^32, checked through its table and
  directory
- **2026-11-05, the genome-wide format 7 check.** The converter's detail
  name collisions reach 10,993 of 66,981 detail units on GRCh38. `verify`
  in the tests refuses duplicate unit names, but `audit7.py`, which runs
  on real files, didn't check. Source: a guard placed only where the
  fixtures are. Fix: `audit7.py` and `verify7.py` count tiles and detail
  units sharing a name. Guard: both fail a file with any
- **2026-11-05, the format 7 verifier (F1).** The spec's departure extent
  clipped each breakpoint stretch to S, which leaves a record whose ends
  are 0 bp nodes at S's end with an empty extent and no block, findable by
  no reader. The writer clamps the base beside the breakpoint into S and
  files it at `[|S| − 1, |S|)`. Source: the spec written from the ADR's
  words, not from `step_end`. Fix: the spec states the clamp. Guard: a
  test with such a record (the verifier's zerotile.gfa)
- **2026-11-05, the format 7 verifier (F2).** A tile whose reference nodes
  all have 0 bp had the empty extent `[p, p)`, which the overlap rule
  fetches for no window starting or ending at `p`, against ADR 0010's
  guarantee that every placed step is in a tile whose extent overlaps
  it; a detail unit of only such steps likewise. Source: a choice made to
  keep the converter's lines, documented instead of checked against the
  ADR. Fix: a unit whose stretches cover no base takes the base beside
  `p`, `[p, p + 1)`, or `[p − 1, p)` at S's end, as a departure's
  breakpoint stretch does; `audit7.py` asks again that a window over
  either base beside a point reads its tile. Guard: the zerotile test;
  `verify` in the tests and `verify7.py` accept an empty union only as
  that base
- **2026-11-05, the format 7 verifier (F3, F4).** The spec used S, R,
  "file order", "dictionary rows", "the leave base", "attach fetch", span,
  stretch and extent before or without defining them, called a departure
  record a record in the abridged section, and said pieces' spans widen a
  tile's extent, which they can't: every placed step is on R. Source:
  prose written section by section. Fix: a terms list ahead of the rows,
  and the sentences corrected. Guard: the verifier's read
- **2026-11-05, the format 7 verifier (F5).** A `#` in a W line's sample
  or haplotype column makes the path's PanSN name split differently from
  its columns, so `#haplotype` names `H#x` for path `H#x#1#ctg`. Older
  than format 7; PanSN forbids it. Fix: the build refuses a W line whose
  sample or haplotype holds `#`. Guard: a test
- **2026-11-06, graph-walks 6's measurements (the reader's entry on
  `format7-reader-log`, c69c9bc, holds the bytes).** The spec's line "an
  own step of a piece the tile abridged lies in its detail unit", beside
  "an attach fetch reads the tiles `ownTiles` names", led the reader to
  expand every abridged piece an attach fetch decoded; graph-walks 5 never
  did. ADR 0010's reading rule puts the two clauses side by side the same
  way. Source: a true statement of where steps are, read as a rule for
  when to fetch them. Fix: the spec and the ADR say that an attach fetch
  takes the own steps the named tiles hold, that an abridged piece there
  stays abridged, and that its own steps come only when a viewer expands
  that path's `detail` unit. Guard: graph-walks 6 (17ed0a6) expands only
  on request, with its test
- **2026-11-06, the format 7 verifier (W1).** The spec defined a record's
  own steps twice: for `ownTiles` as the steps between its leave and its
  rejoin, for the attach fetch as the path's steps in `[hapStart,
  hapStart + ownBp)`. They disagree on a 0 bp own step: path G of the
  verifier's `jumpback.gfa` (`>1>2>3>4>9>1`, node 9 of 0 bp) has `ownBp`
  0 and `ownTiles` 10, where the bp range is empty. The writer, `audit7.py`
  and graph-walks 6 follow the steps. Source: a bp range written as
  shorthand for a run of steps. Fix: the spec says the own steps are the
  steps strictly between the leave step and the rejoin step, a 0 bp step
  included, which start at `hapStart` and span `ownBp`. Guard: a writer
  test for path G, `ownBp` 0 and `ownTiles` 10
- **2026-11-05, porting graph-walks to walk format 7.** graph-walks 5.0.2's
  attach fetch was skipped when the chunk holding the leave base had been
  read, though a leave step on a node straddling the chunk boundary files
  its piece under the chunk before: on `header.GRCh38` a cut of 2100-2600
  reads chunks 1000-2000, HG002#1's record leaves at 1200 (base 1199,
  chunk 1000, node 2 at 600-1200 filed under chunk 0) and came back with
  no own steps. Source: tests shaped by the implementation; the attach
  test's leave node sat inside one chunk. Fixed in graph-walks 6 by format
  7's addressing: an attach fetch reads every tile whose extent holds the
  leave base, and tile 0's extent is 0-1200. Guard: test "a cut reads the
  tiles and departure blocks its window overlaps, in one read where they
  touch, and fetches the tile holding a leave base" (HG002#1 with `>7`)
- **2026-11-05, porting graph-walks to walk format 7.** What graph-walks
  5's read rules compensated for, and where each went (ADR 0010 removes
  the rules):
  - the chunk-before rule (`chunkQueryStart`, one chunk at least): a node
    straddling a chunk boundary, filed under the chunk of its start, is
    now in the extent of the tile holding it; the detour a walk takes into
    the window's first node, now the departure record over the window and
    its attach fetch; the stay guard, gone since format 6. Not carried: a
    reference node the window's tiles hold only as a route interior, whose
    reference pass lies in a tile outside the window, is placed off R in
    that walk's coordinates (the `stays` fixture at 16-32 placed node 2 at
    4 by reading the chunk before; the test now cuts 12-32, which reaches
    that tile). It lies outside the drawn stretch, so the cut does not draw
    it on the reference either way, and arbiter A's comparison found the
    shipped rule's extra nodes came from this habit
  - `maxnode` lookback (`lookbackChunks`) and `#long` widening
    (`walkQueryStart`): a node longer than a chunk, filed chunks back, is
    now inside the extent of its tile. Guard: test "a node longer than a
    tile is read from the tile whose extent holds it" (`maxnode.GRCh38`)
  - the departure read's reach, the drawn stretch ± `maxnode`: walkCut
    keeps records over the nodes on the window, which can run a node past
    the context; a departure line now states its end nodes' whole extents,
    so a record ending on such a node overlaps the drawn stretch
  - the `seq~departure` sibling and the `seq~cs` detail sequences at
    `d × 16384`: Tabix needed a sequence and a leaf bin for each; now the
    `departures` units and the `detail` unit named `cs:d`
  - `bytesForRegions`' estimates for the byte budgets: now the table's
    exact unit lengths
  - the attach fetch's read from the chunk before the leave base's: now the
    tiles whose extents hold the base (the entry above)
  - `checkRange` stays: a NaN window would select no unit and return an
    empty cut without saying why
- **2026-11-05, porting graph-walks to walk format 7.** A fragment's
  `trimmedBefore` and `trimmedAfter` count the bp of its walk the cut read
  and left out, so they shrink when a cut reads less: without the chunk
  before, a fragment starting on the window's first tile now says 0 where
  graph-walks 5 said up to a chunk. bandage-core's `gapParts` labels a
  gap's trimmed bp from these, so some bp it labelled trimmed it now
  labels elsewhere. The return shape is unchanged. Source: a value whose
  meaning depends on the read, documented as "the bp the cut read". Open
  for the consumer ports: check the walk-row gap labels on a window that
  starts a tile. Guard: graph-walks' tests now expect the format 7 values
- **2026-11-05, the genome-wide format 7 check.** The attach fetch reads the
  tile whose extent holds a record's leave base, but a record's own steps
  can lie at its rejoin side: NA19185#2's jump back on CHM13 chr14 (leave
  13,472,637, rejoin 13,135,857) has them in tile 13,107,200, and own steps
  that lead a W line take the tile of the first step after them. Source: a
  read rule written from where format 6 usually files steps, not from the
  writer's rule. graph-walks 6 keeps the rule in one function,
  `attachTiles`, for the field naming the tile of a record's own steps that
  the writer is adding. Two cases: where the cut lacks the leave piece,
  `attachTiles` naming that tile fixes it (tried by hand); where the cut
  holds the leave piece and not the rejoin piece, `walkCut` reports nothing
  unattached, so it must also report a record whose own steps it did not
  find. Fixed with gfa-to-tabix's `ownTiles` column (format7-writer
  a921511): `attachTiles` returns the tiles a record's `ownTiles` names,
  `walkCut` reports a record lacking its leave piece or its rejoin piece,
  and own steps in an abridged piece come only for a walk the cut
  expands, as in graph-walks 5: reading the detail units on every attach
  fetch, as the spec's reader rule has it, took pggb chrY's 1 kb windows
  from 1,348 to 26,951 KB at p90 with attach fetches, and up to 112
  requests (`docs/walks-container/reader/results-own/`). Guard: graph-walks tests "a
  jump back whose own steps lie in the rejoin piece gets them attached" at
  50-60 (neither piece read) and 80-90 (the leave piece read) on
  `test_data/jumpback.GRCh38.gfa`, each failing on the leave-base rule; "a
  record's own steps come from its leave and rejoin pieces, and a record
  lacking either is asked for"; "an attach fetch reads an abridged piece's
  own steps where the cut expands the walk" on `ownends.R`
- **2026-11-05, the genome-wide format 7 check.** CHM13's format 7 file is
  1.78 GB, and Node refuses a buffer over 2 GiB, so any reader of a whole
  file fails on a larger one. graph-walks 6 reads the data file only by
  byte ranges, one unit run at a time, parses offsets as numbers checked
  `Number.isSafeInteger`, and `pnpm release-check` opens files through
  `WalkReader.open`. Guard: graph-walks test "a file past 4 GiB is read at
  its exact offsets" (units past 2^32)
- **2026-11-05, graph-walks 6's real-data cut check.** Against graph-walks
  5.0.2 over format 6's rows for the same units, graph-walks 6's cut on the
  writer's MC chr22 and pggb chrY files differs only where 5.0.2's
  attach-decode bug dropped own steps, and, against 5.0.2 with that bug
  fixed, only where 5.0.2's attach read (the chunk before and the leave
  chunk) holds more pieces of the attached walks, which join two fragments
  through steps outside the drawn stretch or attach steps whose leave node
  straddles a tile; rerun with 5.0.2's attach extent, every such window is
  identical. Source: the ADR's attach rule reading less than graph-walks 5,
  as the genome-wide check also found for the lookback chunk. Counts,
  windows and scripts: `docs/walks-container/reader/`. Guard: the
  scripts there, rerun on each release candidate
- **2026-11-06, the format 7 verifier (R1).** `walkCut` took the drawn
  stretch from the graph's node map, which holds one placement per node, so
  where the reference passes a node twice inside the window the other pass
  did not widen it: on `walks-loop.gfa` (R `>1>2>3>2>3>4`, 6 bp nodes,
  node 2 at 6-12 and 18-24) a cut of 8-20 kept R's fragment at 6-18 and
  dropped its step at 18-24, trimmed the walks there likewise, and left out
  F's record at 24 (its own node 5 after that pass). graph-walks 5.0.2 on
  the format 6 build at `--chunk 10` gives the same cut (R `>2>3` at 6-18,
  no F record), so the bug predates format 7. Source: tests shaped by the
  implementation: no fixture passed a node twice inside one window.
  Fixed in graph-walks 6: `walkCut` widens the stretch by every step of
  the cut's runs placed on the window and its context, each at its own
  pass, as well as by the nodes on it. Guard: graph-walks test "a cut's
  drawn stretch takes every pass over the window, not one per node" on
  `test_data/loop.R.gfa`, which fails before the fix
- **2026-11-06, the format 7 README figures, three drawings of the
  format.** A departure block's `#unit` line named the block by its size,
  which its `start end` already gives, so `name` meant two things: the key
  `ownTiles` and `abridged` rows point at a unit by, and for departure
  blocks a copy of `end − start`. Source: a column filled because it was
  there. Fix: the writer names a departure block `.`, as a table already
  was; the spec's Units table and ADR 0010 say `name` is the key other
  lines point at a unit by, `.` where nothing does. `verify7.py`,
  `verify7.mjs` and `compare7.py`, which read the size from the name, take
  it from `start end`. graph-walks 6 never reads the name; on
  `format7-reader-tidy` (97f857b) its fixtures are rebuilt with this
  writer, its test writer names a block `.`, and its tests label a block
  by its start. Guard: writer test "a departure block is named dot and
  every other name is unique", and `verify()` in `tests/walks.rs` and `verify7.py` refuse any
  other name
- **2026-11-06, the format 7 README figures, three drawings of the
  format.** ADR 0010 guaranteed every unit's name unique within its kind
  and sequence, but every departure block of one size shared that size as
  its name, and the checks (`verify()` in `tests/walks.rs`, `verify7.py`)
  exempted the `departures` kind rather than the name. Source: a guarantee
  written for the units readers look up by name and stated for all.
  Fix: with departure blocks named `.`, ADR 0010 and the spec say every
  name other than `.` is unique within its kind and sequence, and both
  checks exempt `.` instead of a kind. Guard: writer test "a departure
  block is named dot and every other name is unique", on a build with
  several tiles and detail records per tile, and the two checks
- **2026-11-06, the format 7 README figures, three drawings of the
  format.** The spec ("What the writer guarantees") and ADR 0010 said every
  line lies within its unit's `start end`. A departure line goes in every
  block of its cover and runs past each, so the statement was false for
  departure blocks, and `verify()` and `verify7.py` skipped those lines
  rather than check what does hold. Source: a guarantee written for tiles
  and stated for every unit. Fix: both say every tile and detail line lies
  within its unit's `start end`, and every departure line overlaps each
  block it is in. The writer has no build-time check of either: a unit's
  extent is the union of its lines' and a record's blocks are its cover,
  so both hold by construction. Guard: `verify()` in `tests/walks.rs`, run
  on every file the tests build, and `verify7.py` check within for tile
  and detail lines and overlap for departure lines
- **2026-11-06, the format 7 README figures, three drawings of the
  format.** The spec's Readers section and ADR 0010's Consequences named
  graph-walks 6's constructor `WalkReader.fromFilehandles({ data, table })`;
  graph-walks 6 (`src/walkReader.ts`) takes `{ data, directory }`, the
  data file and its `.idx`, since a reader finds each sequence's table
  through the directory. Source: an API named in the ADR before it was
  written and copied into the spec. Fix: both say `{ data, directory }`.
  Guard: none in this repository; graph-walks' README states the same
  signature its code exports
- **2026-11-06, the format 7 README figures, three drawings of the
  format.** `--help` described `--stay` and `--abridge-steps` in format 6's
  word, a path's piece kept "in its chunk" and "a chunk's costliest
  paths", where format 7, `--tile` and the spec say tile; a panic message
  said "home chunk" too. Source: help text left when `--chunk` became
  `--tile`. Fix: the help strings and the message say tile; the spec's
  option table already did. Guard: writer test "help says tile not
  chunk"
- **2026-11-06, the format 7 README figures, three drawings of the
  format.** The spec's Example named its reference sample `R`, so its
  lines read `R#0#chr` beside prose where R is the defined term, a tile's
  reference path. Source: a test fixture's
  one-letter sample quoted into the spec. Fix: `walks-two-refs.gfa` and
  its P-line twin name the sample GRCh38, the tests that build them say
  `GRCh38#0#chr`, and the Example's lines are regenerated from the tool.
  Guard: writer test "the spec's example quotes the tool's lines", which
  reads the Example from `docs/walks-format.md` and finds each line in the
  build
- **2026-11-06, the format 7 README figures, three drawings of the
  format.** Findings the drawings raised that format 7 keeps as costs, not
  fixed, each with where it was decided or measured. ADR 0010 does not
  justify three of them, the routes' storage, a record for a bubble across
  a tile edge and the header's missing `#unit` line, and their items say
  so:
  - route rows chained by deltas, so a row is not readable alone: ADR 0010
    keeps the route dictionary and the delta ids inside a tile, and
    measured the alternative, self-contained lines (Srel, Sabs), at 3.1×
    and 4.5× the bytes on MC (Alternatives rejected)
  - departure lines copied into every block of their cover: ADR 0010's
    `departures` units and its genome-wide check, lines repeated 2.12× and
    2.14×, 3.3% to 3.6% of the file (Genome-wide); the alternative without
    the pyramid, O, read 281 against 70 KB at pggb 1 kb (Alternatives
    rejected)
  - the `.idx` → table → unit hops: ADR 0010's Files and Reading a window;
    measured at 48.6 KB in 2 round trips at open on MC against T64b's
    87 KB in 1, and at most two round trips per window against three (Size
    and open cost, Bytes per window, Genome-wide)
  - routes stored the way round whose handles sort first, so the leave
    side of a route with no exit reads reversed: not ADR 0010's choice,
    which keeps format 6's columns and decoding rules unchanged (Decides),
    and no ADR records why routes are stored that way round or measures it
  - a departure line's extent covering both end nodes while its leave →
    rejoin stretch is narrower: ADR 0010's Lines table decides it, in
    place of format 6's reach of `maxnode` (Context, Supersedes); arbiter
    A measured filing over end nodes against reach widening at 292 → 187
    KB, pggb 1 kb median (`walks-container/arbA/decision.md`, "The 2.7×";
    its second table says 288, see the entry on the two medians below)
  - a bubble across a tile edge becomes a departure record, where inside a
    tile it is a route: not ADR 0010's choice. ADR 0009 decides that a
    departure inside one piece has no record and one between pieces does,
    and rejects records for departures inside a piece; ADR 0001 cuts
    pieces at tiles. No ADR measures how many records are bubbles across
    a tile edge
  - the header unit has no `#unit` line, and `#walks` appears both in the
    `.idx` and in the header: ADR 0010's Files and Units decide both. The
    copy lets a reader refuse a directory and data file from different
    builds (Reading a window). No reason is given for the header lacking a
    `#unit` line, and neither is measured

  Guard: none; each stands until the ADR named reopens it
- **2026-11-06, the format 7 claims audit (claims 105 and 115).** The
  spec's Scale, the README and `--help` said `--walks` reads the GFA
  twice; `first_pass` reads it a third time when a path line comes before
  an S line it uses, to visit the paths it deferred. Source: performance
  prose from format 5's docs (200c0a5), carried through two rewrites and
  never checked. Fix: the help, the stdin message, the spec and the
  README say twice, three times when a path line comes before an S line
  it uses. Guard: claims C105 and C115, checked by the test "records of a
  contig that overlap or share a start are refused", which builds a GFA
  whose path lines come first
- **2026-11-06, the format 7 claims audit (claim 97).** The spec said
  `tests/walks.rs` checks every record's `ownTiles` against the tiles its
  decoded own steps lie in; the test took own steps by the bp range
  `[hapStart, hapStart + ownBp)` (`tests/walks.rs:721`), the definition
  W1 replaced, and compared the tiles sorted. The two differ on 5,735 fuzz
  records, and the fixtures have no 0 bp end in another tile, so the test
  still passed. Source: W1 (108bab7) changed the spec's definition and not
  the test's. Fix: the test finds each record's leave step, the path's
  step on S ending at `hapStart` at `leavePos` and `leaveStrand`, and its
  rejoin, the next step on S, and compares `ownTiles` in order with the
  tiles of S holding the steps strictly between. Guard: the test itself,
  on every file `decode_file` reads, and `claims7.py`'s O1 on the fuzz
  batch
- **2026-11-06, the format 7 claims audit (claim 8).** The spec said
  `--abridge-bytes` moves a tile's costliest paths until the rest compress
  to at most that many bytes. The writer moved them by an estimate, each
  path's raw bytes times the tile's whole compression ratio, and never
  compressed what it kept, so 1 of 1,600 fuzz files kept walk rows at 306
  bytes against a budget of 300; and it entered the rule only where the
  rows' raw length passed the budget, which a tile whose deflated rows
  outgrow it never does. The test beside the rule said the estimate could
  leave a path. Source: 200c0a5, format 5's docs, written from the
  intent while the code took an estimate; carried through two rewrites.
  Fix: the writer deflates the rows it keeps, as `abridgebytes` measures
  them, and moves the next costliest path until they fit or no walk row is
  left, and it compresses any tile whose rows could deflate past the
  budget; the spec states the measure, the tile's rows other than its
  `abridged` rows from `kind` on, at level 6 in 65,280-byte blocks. Guard:
  the test "a tile that keeps walk rows fits its budgets", which fails on
  the old writer, and `claims7.py`'s B1 on the fuzz batch
- **2026-11-06, the format 7 claims audit (claim 93).** "The tool checks
  each of these as it writes" introduced the spec's list of writer
  guarantees; the build checked only the walk and abridged rows' spans and
  the `#` refusal. The partition, the tables, the extents, containment,
  the cover, `ownTiles` and the names held by construction and were
  checked only by `verify()`, `verify7.py` and `audit7.py`. Source:
  86d1006, the format 7 rewrite: the sentence introduced a list that grew,
  and each bullet was checked by tests, so it read true. Fix: the writer
  now fails the build where a unit or table does not start where the last
  one ended or the EOF block does not follow the last table; where a
  table would list a unit out of file order or of 0 bytes; where two units
  of a kind and sequence share a name other than `.`; where a tile or
  detail line leaves its unit's extent; where a departure line is written
  to a block outside its cover, not overlapping it, or twice; and where a
  sequence gets fewer or more departure lines than its records' covers
  hold. The spec's writer guarantees say which of them the build checks
  and which only the tests, `verify7.py` and `claims7.py` do (the spec
  pass below). Guard: the checks themselves, and claim C93's row naming
  each
- **2026-11-06, the format 7 claims audit (unstated: `|S|`).** A table's
  `#unit` line ended at the largest end of its sequence's units, which a
  reader computes from the entries anyway, and which a departure block
  pushes past the sequence's end; `|S|`, on which the extents at the
  sequence's end depend, was in no line, so graph-walks took it from the
  largest tile end. Source: ADR 0010's table, written before anything
  needed `|S|`. Fix: a table's `#unit` line runs from 0 to `|S|`, where
  the sequence's last line ends. Guard: `verify()` and `verify7.py` check
  it equals the end of the sequence's last `ref` row's stretch
- **2026-11-06, the format 7 claims audit (claim 17).** The spec said the
  tool refuses two W lines of a contig that overlap or start at the same
  base; `first_pass` never recorded a W line with no steps, so two empty
  lines starting at one base, or an empty line where a line with steps
  starts, were built without a word. An empty line of the reference
  sample still named a sequence, which then had a table and no units, and
  stretched `|S|` to its start. Source: c5d388c; the refusal test used
  lines with steps, and no fuzz graph had an empty line. Fix: a W or P
  line with no steps is skipped once its end column is checked, the
  reference's included, and the spec says so and limits the overlap
  refusal to lines with steps. Skipping, not refusing: the line covers no
  base, so no row, record or own bp changes, and refusing would turn away
  graphs `vg convert` writes. Guard: the test "a W line with no steps is
  skipped", which builds with and without four empty lines and compares
  the files; the widened fuzz generator writes empty lines
- **2026-11-06, the format 7 claims audit (claims 42 and 111).** The
  point rule gave a unit covering no base `[p, p + 1)`, or `[p − 1, p)`
  at `|S|`; where `|S|` is 0 neither exists, and the tile came out
  `[0, 0)`, which no window selects, while the spec and ADR 0010 said
  every window over the base beside a point reads it. A departure on such
  a sequence came out `[0, 1)`, a base S doesn't have. `verify()` and
  `verify7.py` accepted `[0, 0)` because they took a unit whose extent
  equals its rows' hull before testing the point rule. Source: the F2
  amendment (1a0646f) and ADR 0010's, written for a 0 bp tile on a
  sequence with bases; no fixture or fuzz graph had a sequence of 0 bp.
  Fix: no invented coordinate. On a sequence of 0 bp the units, the table
  and the departure lines state `[0, 0)`, a departure line goes in the
  block of the tile holding 0, the cover reaching at least that tile, and
  the spec says that `D`, which starts at 0 or later, selects none of
  them, so no window shows a sequence with no base. Guard: the test "a
  sequence of 0 bp states 0 0"; `verify()`, `verify7.py` and
  `claims7.py` accept `[0, 0)` only where the table states `|S|` 0; the
  widened fuzz generator writes sequences of 0 bp
- **2026-11-06, the format 7 reader audit (graph-walks a1dc38a).** An
  attach fetch decoded the fetched tile into the cut's rows, so every
  piece of the walk there joined its fragment: a cut of MC chr22 at 18.16
  Mb returned a fragment running to 20.36 Mb and 452 computed departures
  there, and a fragment depended on `attachFetches` and on which other
  walks the cut kept. Source: the reader audit,
  [rules7.md](walks-container/reader/rules7.md) (Failing inputs); the
  decode came in with graph-walks 5's attach fetch (43910ec) and the spec
  sentence "takes the own steps those tiles hold" was written for detail
  units without looking at the rows downstream. Fix: a1dc38a, walkCut
  takes a fetched tile's rows as attach runs, indexed for records' leave
  and rejoin pieces alone. Guard: graph-walks test "a tile fetched to
  attach gives its record the own steps and nothing else"
- **2026-11-06, the format 7 reader audit (graph-walks 7afced7).** walkCut
  attached own steps only to records with `ownBp` above `missingBp`, so a
  record with a 0 bp own step and `ownBp` 0, which W1 decided is an own
  step and `ownTiles` names, never got it. Source: the reader audit
  (rules7.md, Failing inputs); W1's entry said graph-walks follows the
  steps, which held for `ownTiles` and not for the gate. Fix: 7afced7,
  every record within `attachBp` looks for its own steps between its
  leave and rejoin. Guard: graph-walks test "a 0 bp own step is attached",
  on the `ownzero.R` fixture, W1's path G
- **2026-11-06, the format 7 reader audit (graph-walks 5b9cba6).** walkCut
  returned a record only where its stretch overlapped the reference nodes
  over the window or touched a fragment's edge, so a window inside a
  `#hole` lost the record over it; and it kept a computed departure inside
  a fragment's span or at its edge far outside the window. Source: the
  reader audit (rules7.md); the spec's reading rule was written from ADR
  0010, not from `walkCut` (86d1006). Fix: 5b9cba6, a cut returns every
  record read over D and computes departures over the drawn stretch only.
  Guard: graph-walks tests "a cut returns every record whose line overlaps
  its window, in a hole too" and "a cut computes no departure outside its
  drawn stretch, even inside a fragment", on `hole.R` and `excursion.R`
- **2026-11-06, the format 7 reader audit (graph-walks 6236988).**
  `referenceNodes` kept one pass per node, so on `loop.R` a region of 0-36
  lacked node 2 at 18-24 and node 3 at 24-30; the JBrowse plugin calls it.
  Source: the reader audit (rules7.md); R1's one-pass pattern in a
  function the R1 fix didn't touch. Fix: 6236988, it returns every pass
  whose node overlaps the region. Guard: graph-walks test "referenceNodes
  gives every pass of the reference over the region"
- **2026-11-06, the format 7 reader audit (graph-walks 5e7db36).**
  `canonicalLink` wrote each link with the smaller first handle, so a
  walk `>7>3` gave `L 3 - 7 -` and Bandage drew the figure cuts' arrows
  backwards. Source: the reader audit (rules7.md, Links); format 1's links
  file rule (c4ff08d), never revisited. Fix: 5e7db36, a link goes the way
  round with more `+` ends, by the old rule on a tie; the spec's Readers
  says so. Guard: graph-walks test "a cut's links run the way a walk along
  the reference takes them"
- **2026-11-06, the format 7 reader audit (graph-walks 55dfdc8).** 13 of
  37 mutations of graph-walks' format 7 rules passed every test: `:k`,
  `@k`, `start@k`, the `@k` tie, an abridged row's default end, R's
  `hapOffset` order, path-first placement, the hole squeeze, records kept
  by their text, the `#unit` refusal, the departure-line filter and the
  length-0 skip, though pggb chrY's file uses the copies on 109,697 walk
  rows. Source: the reader audit (rules7.md, `rules7-mutate.py`); no
  graph-walks fixture had ever held a walk row with `@` or `:`. Fix:
  55dfdc8, fixtures `copies.R`, `copyends.R`, `zerostep.R` and
  `holetile.R` and tests for each; the mutation score goes from 24/37 to
  37/37. Guard: those tests. With all six fixes, graph-walks' cut matches
  the reference cut on ada in every set:

  | Set | Windows | Differences before | Now |
  |---|---|---|---|
  | MC chr22 1 kb | 100 | 0 | 0 |
  | MC chr22 100 kb | 100 | 452 | 0 |
  | MC chr22 1 Mb | 30 | 49, plus 7 unchecked | 0 |
  | pggb chrY 1 kb | 100 | 55 | 0 |
  | pggb chrY 100 kb | 100 | 28,940 | 0 |
  | pggb chrY 1 Mb | 30 | 5,192 | 0 |
- **2026-11-06, the format 7 claims audit (claim 4).** The spec said every
  walk file lists the same paths; a path with no step on a node of a
  reference has no rows in that reference's file, and never had. Source:
  200c0a5, 2026-10-21, merging walks.md into the spec: the same commit's
  page said a path off the reference is left out, and the sentence
  survived formats 5, 6 and 7 because no check compared two references'
  files. Fix: the spec says a file lists every W or P line with a step on
  a node of its reference, that a line with none has no rows there while
  its contig's other lines keep theirs, and that a reader lists the
  haplotypes with rows in the file. Guard: claim C4's row in claims7.md,
  checked on the two-reference fixtures and the widened fuzz graphs
- **2026-11-06, the format 7 claims audit (claim 76).** The spec and ADR
  0010 said a path's moved pieces in one tile share one detail record,
  "one per contig"; the writer writes one per W line, `(path,
  fragStart)`, and MC chr22 has 170 tile and path pairs where a contig's
  W lines give two or three records in one tile. Source: 86d1006, the
  format 7 rewrite, which added "one per contig" to format 6's sentence;
  `abridged_groups` had grouped by W line since a57515d, and no check
  counted records per path and tile. Fix: one record per W line, which is
  the unit of contiguity, stated in the spec's `abridged` rows and Terms
  and in ADR 0010's `detail` unit. Guard: claim C76's row
- **2026-11-06, the format 7 claims audit (claim 85).** The spec said an
  own step on no reference node takes the leave's tile; `assign_chunks`
  gives it the tile of the last step before it with a position on any
  sequence of the reference, so after a step on another sequence it lies
  in that sequence's tile. Source: c4caa2f, `ownTiles`: the fuzz graphs
  had one reference sequence, so no path crossed sequences, and the test
  compared `ownTiles` against the writer's own placement. Fix: the spec's
  placement rule and `ownTiles` bullets say so, and that a W line with no
  step on the reference has no tile. Guard: claim C85's row, on fuzz
  graphs with several sequences
- **2026-11-06, the format 7 claims audit (claim 91).** ADR 0009 said R
  holds one node ending at a `+` leave's or `-` rejoin's breakpoint and
  one starting at the other kind's; with 0 bp nodes several do, at 11,029
  ends in the fuzz batch. Source: f672193, an explanatory sentence never
  treated as a guarantee, written while 0 bp nodes on the reference were
  already legal and tested. Fix: the spec and ADR 0009 say "a node", and
  that with 0 bp nodes several can. Guard: claim C91's row
- **2026-11-06, the format 7 claims audit (claim 102).** The spec said a
  detail record holds a `nodes` row, then `route` and `walk` rows;
  `emit_rows` writes `nodes` only where a route has an interior step, so
  5,309 fuzz detail units and 44 on the fixtures have none. Source:
  c00c433, format 5's docs, carried through three rewrites, and no check
  read a detail unit's row kinds. Fix: the spec says a record holds at
  most one `nodes` row, one exactly when its routes have an interior
  step. Guard: claim C102's row
- **2026-11-06, the format 7 claims audit (claim 109).** ADR 0010's
  Lines table gave an `abridged` row's `start end` as "the moved piece's
  stretch on the reference path", which reads as the span of all its
  placed steps; the writer and walks-format.md give the span of its
  first and last steps on R, which is narrower on 70,765 of pggb chrY's
  110,886 abridged rows. Source: 2b0f7a5, the ADR written before the
  writer and never re-read against it, while ADR 0009's final review had
  already defined the span by the end steps. Fix: ADR 0010's table says
  what the spec says. Guard: claim C56's row, shared by both pages
- **2026-11-06, the format 7 claims audit (claim 112).** ADR 0010's
  writer guarantees said each line's `start end` is checked at build
  against its decoded steps, "on every row"; the build decodes walk and
  abridged rows only, and no `ref`, `nodes`, `route` or departure line
  has a build check of its extent. Source: 2b0f7a5, "every row" written
  for the rows a decoder checks. Fix: the spec and ADR 0010 say the walk
  and abridged rows are checked at build, and that the other rows'
  extents are checked by the tests and `verify7.py`. Guard: claim
  C112's row
- **2026-11-06, the format 7 claims audit (the ambiguous claims 1, 10,
  21, 40 and 107, 87, 114).** Six sentences held under one reading and
  not another: a reader rebuilds every path "from the tiles whose
  extents overlap" the window (it also needs attach fetches and detail
  units); a walk row's span runs "from its first step on R to its last"
  (its placed steps span more on 170,648 pggb chrY rows; the span is over
  all of them); "the first pass" when a sequence has none (the pass of
  the reference line whose name sorts first in bytes, at its lowest
  offset); a tile's extent is "the union of its ref rows' stretches"
  (the hull: 166 fuzz tiles' stretches leave a gap inside it); own
  steps on other sequences "are not listed" (nor are they in any tile
  an attach fetch reads); and the README's "one unit per tile and per
  departure block" (also a header, detail units and a table per
  sequence). Source: each written from the common case, where the
  readings agree. Fix: each sentence says the one reading the writer
  has (claims C1, C10, C21, C40, C87, C114). Guard: their rows
- **2026-11-06, the format 7 claims audit (arbiter A's 292 and 288
  KB).** `walks-container/arbA/decision.md` gives F6p's pggb 1 kb median
  as 292 KB in its first table and 288 in its second, and this log cited
  288. The committed results (`arbA/results/res/pggbY.f6p.jsonl.gz`,
  300 windows) sort to 288.9 KB at index 149 and 292.4 at index 150;
  arbiter A's `summarize.py` and `summarize2.py` both take index 150,
  so 292 is the figure its rule gives, and 288 is the lower middle value
  of the same windows. Source: a number typed from one summary into a
  second table. Fix: this log says 292 and where 288 came from; ADR 0010
  already said 292; the arbiter's record is left as written. Guard: none
  beyond the rule in Sources, no number in prose without the file and the
  script that wrote it
- **2026-11-06, the format 7 claims audit (the costs with no ADR).** The
  review of the format drawings (above, 2026-11-06) found four choices
  no ADR had decided or measured: routes stored the way round whose
  handles sort first, the header unit's missing `#unit` line, bubbles
  across a tile edge becoming departure records, and the cost of the
  build-time checks. Each is now measured on MC chr22 and pggb chrY and
  decided in ADR 0010's Costs decided: the orientation is kept, the two
  files differing by 0.10% one way and 0.53% the other against a
  first-walk orientation; the header keeps no `#unit` line, since one
  would carry a made-up coordinate; the records stay, costing 1.5% of
  MC chr22's file and 7.8% of pggb chrY's; the checks cost nothing the
  timing can see. Guard: the ADR's section, which claims C30 and C68
  cite
- **2026-11-06, the format 7 claims audit (the mechanism).** Two audits
  of format 7, one of the spec against the writer (claims7.md: 115
  claims, 15 false, 7 ambiguous, 34 with no check of any kind) and one
  of the reader against the spec (rules7.md), gave the same five causes.
  The prose was written from the design and the checks from the code, so
  a check restating the writer's formula could not catch a sentence the
  code contradicts; checks exempted the cases they could not state
  instead of failing on them; a definition changed in the spec and not
  in the checks (W1 and the ownTiles test); the fuzz graphs had one
  reference sequence, one reference and no empty W line; and rewrites
  carried old sentences forward unread (the format 7 rewrite was 514
  lines in one commit). Fix: every normative sentence of walks-format.md
  and ADR 0010 carries a claim ID (`<!-- C76 -->`), and claims7.md keeps
  one row per ID naming the check behind it, written from the sentence;
  `scripts/check-claims.py` fails CI on an ID with no row, a row with no
  check that exists, or a sentence saying every, each, never, always,
  only, unique or exactly with no ID; `claims7.py` checks each claim
  with no exemption; `fuzz7.sh` writes several sequences, two references,
  empty and abutting W lines and sequences of 0 bp; and
  `scripts/check-walks.sh` runs the file checks on every fixture and a
  fuzz batch in CI. Guard: CI, on every push
- **2026-11-06, the reader squad review.** graph-walks refused a
  directory that did not match its data only in `header()` and `cut()`.
  `units`, `referenceSequences`, `sequenceFor`, `sequenceLength`,
  `bytesFor` and `referenceNodes` read the table directly and returned
  data from a stale `.idx` beside a re-uploaded data file, the case C122
  exists for. Source: a test shaped by the implementation, since C122's
  test called `header()` alone. Fixed in graph-walks 569c2c8: every entry
  point waits on the header check. Guard: the C122 test runs all 8 entry
  points against a changed `bytes`, a changed `#walks` line and a
  directory with no `bytes`; on the old code 6 of the 8 returned data
- **2026-11-06, the reader squad review.** graph-walks read a corrupt
  table or unit silently. It checked only that a unit began `#unit\t`, so
  a table length that ended partway through a unit dropped H's piece
  `>3>4` from window [12,24) with no error, and two tiles with their
  byte ranges swapped returned nothing for [0,6). Source: a reader rule
  the spec never stated. Fixed in graph-walks 05b7ddd. A unit's `#unit`
  line must state its `#entry`'s seq, start, end, kind and name, and its
  text must end in a newline. Each row must be its sequence's and of a
  kind its unit holds. A table must start with its own `#unit` line, and
  every other line of it must be an `#entry`. Guard: eight tests that
  failed on the old code, each check broken once to see a test fail. A
  table entry left out entirely is still not detectable
- **2026-11-06, the reader squad review.** A unit cut partway through a
  gzip member failed with Gunzip's bare `TypeError` rather than a
  `WalkFormatError`. Fixed in graph-walks 852948c. Guard: a test on a
  truncated unit
- **2026-11-06, the reader mutation run.** 10 of 59 mutants of the
  format 7 reader survived its tests. Seven of them gave a wrong cut or
  accepted a bad file:
  - a contig whose W lines joined each other's pieces
  - a route leaving from the last copy of its entry node instead of the
    first one reached
  - an abridged piece at the window's edge returned as a walk
  - a tag read as an abridged piece's detail-unit name
  - an unknown unit kind decoded as a tile
  - a directory with no `bytes` accepted
  - a piece joined with no `fragStart`

  Source: tests shaped by the implementation. Fixed in graph-walks
  585a838: a test for each, which fails on its mutant. Guard: the
  mutants' patches in ~/work/review-2026-11-06/scratchpad/isolated/gw-mutants/
- **2026-11-06, the format 8 "why we keep fumbling" review.** ADR 0011
  (walk format 8) was accepted by the process it was meant to end. One
  session wrote the brief behind the proposal, which planted a wrong
  figure: "183 KB" for the whole-genome table, which is really chr1's own.
  The same session briefed the spike with the proposal it was to
  measure, and gave the two deciders byte-identical briefs: the
  proposer's persona, a list of B's numbers, and option C labelled
  "loses pggb". It committed the ADR minutes after they reported. The
  ADR's validity evidence was "passes verify7.py and claims7.py" on the
  day those checkers were shown to pass broken files. Source: one session
  owning proposal, measurement and verdict, on a format with no outside
  user since format 5. Fix: the ADR is withdrawn to
  [a proposal](walks-container/reshape/proposal.md) until the owner
  has read the evidence. Guard: none yet. The review's rules are an open
  question for the owner:
  - **Ship gate:** no ADR for format N+1 until a consumer has read format
    N from a hosted file
  - **Scope gate:** a trigger must be measured on a hosted graph, or one a
    named user asked for
  - **Split briefs:** whoever briefs a proposal doesn't brief its
    measurement or deciders
  - **Overnight acceptance:** an ADR is accepted no earlier than the next
    session, after the owner has read the briefs
  - **Checker evidence:** an ADR may cite a checker only alongside that
    checker's recorded failure on a broken writer
- **2026-11-06, the nine-reviewer bug hunt (0 bp segments).** Six of the
  nine reviews traced defects to segments of 0 bp. The build aborted on
  two departures of H with the same text, `0 0 0 0 + 1 20 + 1 .`, because
  every step between them was 0 bp (writer-vs-spec.md, `dup.gfa`). R
  passed node 2, of 0 bp, at offset 4 on both strands, and H's `<2` took
  one pass in its records and the other in its walk row, so the records
  stated a strand switch the rows don't show (cleanroom.md, `min/z2.gfa`).
  A reference line of 0 bp at 20 after R's last base removed the hole
  10-20, and one at 15 inside the hole 10-20 split H's step across it into
  two records (units.md, `hole-trailing`, `hole-inside`). A tile holding 2,
  of 0 bp, at 5 and 3 at 7-9 had the extent 5-9, wider than C40 said, and
  a 0 bp line at 5 inside a line 0-9 of the same contig was refused as an
  overlap (placement.md, `zmix`, `zgap`, `ov2`, `ov3`, `ov5`). The spec
  carried rules for 0 bp alone: a point extent, a sequence of 0 bp stating
  `[0, 0)`, a breakpoint stretch wider than the end nodes, a cover widened
  to a whole tile, a 0 bp own step. Source: a degenerate input the format
  kept every rule for, though HPRC's Minigraph-Cactus chr22 (3,122,495
  segments) and pggb's chrY (4,122,486) have none
  (walks-container/writer/results/zero-bp.txt). Fix: the tool drops every
  0 bp segment as it reads the GFA, its steps leaving every W and P line,
  a line left with no steps skipped as C118 says, a sequence left with no
  bases given no units (C152). Deleted with it: claims C42 and C121, the
  0 bp clauses of C11, C43, C81, C83, C89, C91, C132 and C137, the
  breakpoint stretch (`End::beside`), the point extents in `unit_of`, the
  cover's widening to a tile, the hole filter for 0 bp lines, the point
  case of the block overlap check, the clamps in `step_end` and the scan
  over equal offsets in `index_at`. A tile's extent now comes from its
  `ref` rows alone, so `unit_of`'s check that every piece lies inside it
  can fail, where it compared the extent with the spans it was built from.
  What the old mechanisms compensated for: a 0 bp step had no base to
  file, overlap or bound a block by, and each rule gave it one; with no 0
  bp step there is nothing left to compensate. Every tests/data and
  docs/figures GFA builds to the same bytes before and after (126 builds
  under six option sets), and on fuzz7-gen seeds the new writer on each
  graph gives the bytes the old one gives on the graph with its 0 bp
  segments removed. Guard: one test per repro, each asserting the files
  equal those of the same graph with its 0 bp segments removed by hand,
  each failing on the old writer
- **2026-11-06, the nine-reviewer bug hunt (memory by largest id).** The
  walk writer held about 31 bytes per id up to the largest, used or not:
  `lengths` grew to `id + 1`, and each reference's placement, offset and
  bit arrays matched it. A 6-line GFA with segment 2147483647, which the
  spec allows (C126), needed about 66 GB, and a reviewer's uncapped run
  of it is the likely cause of the session's OOM kill (cold.md,
  placement.md, `bigid.gfa`). MC chr22's ids run from 120,283,403 to
  127,929,432 over 3,122,495 segments (walks-container/writer/results/zero-bp.txt),
  so it paid for 128 million slots. Source: arrays indexed by GFA id, a
  shortcut that holds for ids numbered densely from 1 and for nothing
  else. Fix: the first read numbers the segments densely (`node_ids.rs`,
  a paged map of 1024 ids a page, allocated where an id falls), renumbers
  them in id order once every S line is read, so handles sort as ids do,
  and maps an index back to its id only where a row writes it. A second S
  line for one id is now refused, where the last one won. Every fixture
  and fuzz7-gen seeds 1-60 build to the same bytes as before, plain and
  with their ids spread 7,919 or 97 apart and their S lines shuffled, half
  after the path lines. Guard: the test
  `a_node_id_near_2_to_the_31_costs_no_more_memory_than_a_small_one`,
  which builds that graph in a 512 MB address space and fails on the old
  writer with "memory allocation of 8589934592 bytes failed". On ada, MC
  chr22 with `--refs GRCh38` went from 52.5 s and 4.07 GB peak to 52.0 s
  and 1.11 GB, the files byte-identical
  (walks-container/writer/results/node-ids.mc22.txt)
- **2026-11-06, the nine-reviewer bug hunt (`--abridge-bytes` moved too
  many).** C100 says a tile moves its costliest W lines' pieces until the
  rest are within the byte budget, measured by deflating them. The writer
  estimated how many to move from `40 + 4 × choices` bytes a path and the
  tile's compression ratio, then only ever added to that count: on 60
  haplotypes with long contig names over one tile it moved 40 paths at
  600 bytes where 29 fit, and 15 at 900 where 10 fit (writer-vs-spec.md,
  `long.gfa`). Source: a check of the upper bound only (B1, B2 and
  `a_tile_that_keeps_walk_rows_fits_its_budgets`), so an overshoot passed.
  Fix: `write_chunk` starts from the estimate and, where the kept rows fit,
  puts paths back one at a time while they still fit, down to the count
  the step budget needs; where they don't, it moves more as before.
  Fixtures and fuzz seeds 1-60 build to the same bytes. Guard: the test
  `a_tile_over_its_byte_budget_moves_the_fewest_paths_that_bring_it_within`
  on that graph (now tests/data/walks-abridge-bytes.gfa) at 300, 600 and
  900 bytes, which deflates the kept rows to at most the budget and, with
  the last moved path's walk row put back, to more; it fails on the old
  writer
- **2026-11-06, the nine-reviewer bug hunt (NUL in a path name).** A W
  line whose sample was `H\0X` panicked the writer at `routes.rs:74`,
  index out of bounds: the sort keys a piece by its name and a NUL
  terminator, so `Piece::read` cut the name at the NUL and read every
  later field from the wrong place (cold.md, `f_nul.gfa`). Source: a name
  check that knew `#` and tab but not the byte the writer's own sort
  reserves. Fix: `named` refuses a path name holding a NUL byte, W or P,
  as it refuses one starting with `#`; C95 says so. Guard: the test
  `a_nul_byte_in_a_path_name_is_refused`, which fails on the old writer
- **2026-11-06, the nine-reviewer bug hunt (option values that wrap).**
  `--tile` of 2^55 or more made `cover`'s 512-tile block `512 × tile`
  wrap to 0, so it never advanced and filled memory, with the same wrap at
  `start + tile` in `rehome`; `--abridge-steps` of 2^62 or more wrapped to
  0 when counted in quarter steps, so every path was over budget and
  abridged (units.md). The header also states `tile`, `stay`, `abridge`
  and `abridgebytes` as typed, which a reader holding numbers as doubles
  rounds above 2^53. The cold review's other suspect, the u32 global
  tile index under tiny tiles, is already refused: `Chunks::new` fails a
  build of 2^32 tiles or more ("use a larger --tile"). Source: options
  taken as any u64 into u64 arithmetic. Fix: one bound for every walk
  option, at most 2^40 (`WALK_OPTION_MAX`), refused by the CLI: a block
  of 512 tiles past any position the tool reads, below 10^19, stays below
  2^64, four times the step budget does too, and every header value is
  exact as a double (C153). Guard: the test
  `each_walks_option_takes_at_most_2_to_the_40`, which runs each option
  just over the bound in a 512 MB address space and expects the CLI's
  refusal; on the old writer `--tile` 2^55 died there on memory
- **2026-11-06, the nine-reviewer bug hunt (segment length message).** A
  segment of 4,294,967,295 bp was refused as "longer than 2^32 bp", which
  it isn't: the writer kept u32::MAX in `lengths` to mean no S line
  (cold.md, x12). Source: a sentinel's limit reported as the format's.
  Fix: since segments are numbered densely (a989245) `lengths` holds no
  sentinel, so a segment of up to 2^32 − 1 bp builds, and one longer is
  refused as "longer than 2^32 − 1 bp". Guard: the test
  `a_segment_of_2_to_the_32_bp_is_refused_and_one_less_builds`; the old
  writer refuses 2^32 − 1 with the old message
- **2026-11-06, the nine-reviewer bug hunt (reader rules the spec
  lacked).** The spec review found no rule for a unit whose `#unit` line
  differs from its table entry, or for a unit cut short, and the graph-
  walks reader fixes made since refuse five kinds of corrupt file that no
  claim named: a `#unit` line not stating its entry's seq, start, end, kind
  and name; a unit not ending in a newline; a row of another sequence or
  of a kind its unit doesn't hold; a table not starting with its own
  `#unit` line; a table line that isn't an `#entry` (spec.md, the
  coordinator). The spec sentence "`#reference` names the reference
  sample" also had no ID, though the checker now checks it (H3). Source:
  reader behaviour written in code and tests, not in the spec. Fix: claims
  C154 to C156 beside C49 and C123, which also say a table missing a
  unit's entry can't be told, and C157 on `#reference`;
  graph-walks-tests.txt regenerated from graph-walks main, with C34's and
  C122's rows naming the two tests it renamed. Guard: the rows' graph-walks
  tests, which check-claims.py requires to exist
- **2026-11-06, the nine-reviewer bug hunt (ADR facts).** ADR 0010's C98
  said files pass 2 GiB, though the largest built is CHM13's at 1.78 GB;
  its C112 named `verify7.py` as checking departure extents from their
  ends, which `claims7.py`'s D6 does; its Costs decided gave sizes,
  departure-block bytes, bubble counts and timings with no data file in
  the repository, only `~/work/tidy7/` on ada; ADR 0009 read as in force
  for format 6's filing, header and extension rules; and "units, by start"
  could mean a unit's `start` column or a tile's name, where the writer
  orders tiles by name (spec.md, cleanroom.md). Source: prose written from
  memory of the data, and an ADR left unmarked when a later one replaced
  part of it. Fix: C98 states the 1.78 GB; C112 names D6; the Costs
  decided numbers are in walks-container/writer/results/costs-decided.txt,
  each recomputed on ada from the files and logs there; ADR 0009's status
  names the sections ADR 0010 replaced and the ones still in force; C32
  says a tile's name and a block's start. Guard: none beyond the rule in
  Sources, no number in prose without a committed data file
- **2026-11-06, the format checker's B3 (a budget no checker can
  reproduce).** The checker's new B3, which puts back the last moved W
  line and fails if the tile still fits, failed on
  `walks-abridge-bytes.gfa` and on fuzz seeds 1 and 3 under
  `--sequences`, the overshoot fixed above; and it found the same tile
  deflating to 300 bytes under the writer's zlib-rs and 301 under zlib
  1.3.1, so `--abridge-bytes`, defined as deflated size, could put B1 and
  B3 a byte off the writer (the coordinator). Source: a budget defined by
  one library's output. Fix: the budget counts the kept rows' bytes
  uncompressed, from `kind` on with their newlines (C100, ADR 0010's
  amendment); `deflate_bound`, `compressed_len` and the ratio estimate are
  gone. On ada MC chr22 is unchanged and pggb chrY moves 15 more paths
  from two tiles over 3,000,000 bytes of rows, 0.07% more file
  (walks-container/writer/results/abridge-bytes.txt), and with the
  minimality fix and the deflated budget neither graph's byte budget
  bound at all. Guard: `a_tile_that_keeps_walk_rows_fits_its_budgets` and
  `a_tile_over_its_byte_budget_moves_the_fewest_paths_that_bring_it_within`
  count raw bytes, which any checker can count the same
- **2026-11-06, the checker bug hunt (verify7's header).** verify7.py
  checked the directory's `#header 0 <length>` only when a gzip member
  started exactly at that length, so a directory stating `#header 0 100`
  over a header ending at byte 139 passed all three checkers, and so did
  one whose `#walks` line differed from the data's. Source: the spec
  review's corrupted files `hdr-len-idx-only` and `walks-differ-len100`.
  Fix: verify7 fails when the stated length ends inside a member or runs
  past the units. Guard: verify7, on every fixture; both files now fail
- **2026-11-06, the checker bug hunt (claims7 G1, dead code).** claims7's
  walk-row order check sat inside `if kind == 'detail'` and tested `kind
  == 'tile'`, so it never ran; mutant O1, `piece` sorted ahead of
  `fragStart` and `hapOffset`, changed nearly every fuzz file and passed.
  Source: the spec review (`g1-walk-order`, H's and D's rows swapped in
  tile 0) and the mutant run. Fix: G1 runs on every tile. Guard: claims7
  G1; O1 now fails check-walks.sh
- **2026-11-06, the checker bug hunt (claims7 U2).** U2 read a tile's
  name with `int()`, so `tile 010` passed. Source: the spec review's
  `u2-leading-zero`. Fix: U2 requires `0` or a decimal with no leading
  zero. Guard: claims7 U2
- **2026-11-06, the checker bug hunt (audit7's pass counts and exit
  status).** audit7 kept one stated pass count per node, the first, so a
  second ref row of node 2 in walks-repeat stating 3 where the first
  states 2 gave only the tally "one node with two pass counts", which
  fuzz7.sh's grep did not match; and fuzz7.sh ignored audit7's exit
  status, failing on whatever its grep of the output matched. The grep
  compensated for audit7 printing counts with no exit status. Source:
  the spec review (`passes-second-row`). Fix: audit7 checks every count
  each ref row states against the positions holding the node, prints
  each check that must find nothing as `(must be 0)` and exits 1 when
  one finds something; fuzz7.sh and check-walks.sh fail on its exit
  status. Guard: audit7; a writer that restates one missingBp one lower
  per file fails 54 of 54 fuzz runs of seeds 1 to 6 and passed main's
  fuzz7.sh
- **2026-11-06, the checker bug hunt (audit7's "steps unseen").** audit7
  excused any record whose missingBp was below the gap it recomputed, so
  G's record in walks-records restated from 18 to 5 passed. The excuse
  compensated for one real case: a W line with no step on the reference
  has no rows in the file (C4), so the bp it covers between two lines
  that do look missing to a reader of the file alone (H's `>5>6` line at
  20 to 26 in walks-records). Source: the spec review
  (`missing-understated-G`). Fix: audit7 takes `--gfa`, the graph, and
  counts as missing only the bp no W or P line of the contig covers;
  with it no understated missingBp is excused, and without it the case is
  printed as unverified, not passed. check-walks.sh and fuzz7.sh pass the
  graph. Guard: audit7 `field mismatch`; the file now fails
- **2026-11-06, the checker bug hunt (audit7 not run on fixtures).**
  check-walks.sh ran audit7 only inside fuzz7.sh, so a record stating
  leavePasses 2 in a `revisited:i:0` file passed every fixture check.
  Source: the spec review (`record-leavepasses`). Fix: check-walks.sh
  runs audit7, given the fixture, on every fixture file, and claims7 H2
  also fails a record stating passes above 1 under `revisited:i:0`.
  Guard: both; the file fails each
- **2026-11-06, the checker bug hunt (holes, C52).** claims7 G5 checked
  the `#hole` lines' order only, so a hole at GRCh38#0#chr 3 to 5, over
  bases the ref rows cover, passed; and audit7 removed a hole only from
  positions past its end, the writer's own rule, so it could not see the
  writer's records 10 to 15 and 15 to 20 over a 0 bp line inside the
  hole 10 to 20. Source: the spec review (`hole-bogus`) and the units
  review (`hole-inside.gfa`, `hole-trailing.gfa`). Fix: G5 requires the
  holes of each sequence to be exactly the stretches before `|S|` that no
  ref row covers; audit7 squeezes a position inside a hole to the hole's
  start. Guard: claims7 G5 fails `hole-bogus` and the writer's missing
  hole 10 to 20 beside the 0 bp line at 20; audit7 fails the records
  inside the hole. Both writer cases are 0 bp lines, which the writer
  fix dropping 0 bp segments removes
- **2026-11-06, the checker bug hunt (a point departure line).** verify7
  and claims7 U7 accepted a departure line `[p, p)` anywhere in its
  block, since `a == b` stood in for overlap; only a line `[0, 0)` on a
  sequence of 0 bp may sit in a block it does not overlap, at the
  block's start. Source: the spec review. Fix: a point line must lie at
  its block's start. Guard: verify7 and claims7 U7 fail a copy of I's
  record at 5 5 in the block 0 to 10
- **2026-11-06, the checker bug hunt (check-claims' test: checks).**
  `exists()` accepted `test:f` from `src/`, against claims7.md's legend,
  so C98 and C106 named unit tests of `src/` as tests of
  `tests/walks.rs`. Source: the spec review. Fix: `test:f` must be in
  tests/walks.rs and a new `unit:f` names a `#[test]` function of `src/`;
  both rows use it. Guard: check-claims.py fails both rows written as
  `test:`
- **2026-11-06, the checker bug hunt (walks-truth.py).** `score` read
  only walk rows, so an abridged piece counted nowhere, and gave a W
  line's last piece `nsteps × 30` bp or its record's mean bp per step.
  Source: the spec review. Fix: it decodes every walk row, a detail
  record's against its tile's R, and sums its steps' lengths; its new
  `pieces` command fails a W or P line with rows whose pieces' bp differ
  from its length in the GFA. Guard: check-walks.sh and fuzz7.sh run
  `pieces` on every file; main's piece reading fails it on all 4 lines of
  walks-two-refs at `--abridge-bytes 1`, reading none of them, and on all
  6 of walks-loop at `--tile 7 --abridge-steps 2`
- **2026-11-06, the checker bug hunt (extents, C41, C137, C43).** The
  build's out-of-extent check takes the extent from the same spans it
  tests, and verify7 widened a tile's extent by its pieces' spans too,
  so a walk row and its tile both widened past R passed. C43's
  `test:cover` copies `departures::cover`, and verify7's cover was the
  same algorithm. Source: the writer-vs-spec review. Fix: verify7 takes
  a tile's extent from its ref rows alone and a detail unit's from its
  pieces; it checks a record's blocks against the sentence, aligned
  pyramid blocks tiling the stretch with no larger aligned block fitting
  at a block's start, not by rebuilding them. Guard: verify7 fails tile 0
  of walks-two-refs widened from 0 12 to 0 15; mutant Y3 (blocks of 256
  tiles) fails it on the new fixture walks-long-jump.gfa, whose H
  departs over 600 tiles of 10 bp
- **2026-11-06, the checker bug hunt (abridging stops at the fewest
  lines, C100 and C7).** claims7 B1 and B2 checked only that a tile's
  kept rows fit, so a writer moving more W lines than needed passed:
  mutant B1 (`>=` for `>`) abridged walks-loop's one tile at a cost of
  exactly 1, and the writer moves 40 of 60 lines of
  walks-abridge-bytes.gfa at `--abridge-bytes 600` where, with the last
  one put back, the kept rows deflate to 437 bytes. Source: the mutant
  run and the writer-vs-spec review. Fix: claims7 B3 puts the
  last-numbered detail record back, re-encodes the tile's routes, nodes
  and walk rows by the spec's rules (a tile re-encoded with nothing put
  back is byte-identical to the writer's on all 248 files of the
  fixtures and 25 fuzz graphs), and fails where it would fit both
  budgets, or where a kept line costs more than a moved one. Guard: B3,
  on the fixture walks-abridge-bytes.gfa and fuzz option set `i`. It
  fails on the current writer until the writer measures instead of
  estimating; mutant B1 and a cheapest-first writer fail it
- **2026-11-06, the checker bug hunt (coverage).** No fixture had a
  departure over 512 tiles (mutant Y3 survived), or three or more
  sequences out of byte order and holes needing a sort (mutants O2 and
  H4 were caught from fuzz seed 5 by HashMap order alone); the fuzz
  generator wrote reference lines forward only, no P lines, no bases and
  0 bp nodes by default; and `#reference` was checked by nothing (a file
  naming CHM13 passed). Source: the mutant run, the writer-vs-spec review
  and the spec review (`reference-wrong`). Fix: fixtures
  walks-long-jump.gfa and walks-sequences.gfa (ten sequences, chr9 to
  chrY in no order, each with a hole 8 to 12); fuzz7-gen.py writes
  reverse and mixed-strand reference lines, P lines named with `[start]`,
  `[start-end]`, `#start` and `:start-end`, bases on every segment, one
  to three W lines per contig, and 0 bp nodes only with `--zero`;
  fuzz7.sh adds an option set with `--sequences`; claims7 H3 checks
  `#reference` against every ref row's sample, and audit7 checks each
  `SQ:Z:` against the GFA. Guard: check-walks.sh. Nodes shared across
  reference sequences wait for the placement decision
- **2026-11-06, the checker bug hunt (deflate is not one size).** The
  spec's "deflate at level 6" does not fix a size: tile 128 of Q in fuzz
  seed 8 (`--zero`, `--tile 64 --abridge-bytes 300`) deflates to 300
  bytes under the writer's zlib-rs and 301 under zlib 1.3.1, which
  claims7 uses, so B1 fails a tile the writer measured as fitting. Source:
  this hunt. Fix: none yet; the spec has to name the deflate the measure
  uses, and the writer and claims7 use it. Guard: B1 and B3 measure with
  zlib; no fuzz seed of 1 to 80 without `--zero` sits on that byte
- **2026-11-06, the checker bug hunt (proofs that left with the
  session).** Each repaired check above was shown failing on a corrupted
  file under the reviewers' scratch folders, outside the repo, so nothing
  would show a later edit had made it pass again. Source: this hunt.
  Fix: the 37 broken files, with the corruption each holds, are in
  docs/departures/scripts/broken/, and broken.sh fails unless every
  checker cases.tsv names fails each by its exit status with no
  traceback. Main's checkers pass 11 of them. Guard: check-walks.sh runs
  broken.sh first
- **2026-11-07, the fundamentals review (no consumer on known truth).**
  Nothing ran the real reader on the writer's output over a known graph:
  graph-walks' unit tests read hand-packed files, its release-check reads
  hosted data with no GFA, and check-walks.sh's checkers read the file
  alone or recompute the writer's rules in Python. Source: the
  fundamentals review. Fix: scripts/graph-walks-rebuild.mjs imports
  @jbrowse/graph-walks 6's sources, builds every fixture under
  check-walks.sh's option sets, cuts each reference sequence whole with
  every budget lifted and every abridged walk expanded, and demands every
  fragment be a run of whole steps of its GFA line with the GFA's handles,
  every step on a reference node back exactly once over all sequences,
  every placed step at a pass of its sequence, and in a revisited:i:0
  file every departure as the GFA states it, with the header's holes and
  haplotypes, the nodes' placements and the bases besides. All 50 fixture
  builds pass. walk-span-wrong, wide, u2-leading-zero, table-S-wrong,
  nodes-extra, owntiles-wrong, passes-second-row, g1-walk-order,
  block-misaligned, empty-block and abridged-nsteps pass it and stay with
  the file checks: a whole cut never reads a walk row's `start end`, a
  tile's name or extent, a table's `|S|` or a record's `ownTiles`; the
  reader takes a `nodes` row's extra node, a walk row's order, a block's
  extent and an empty block as they come, keeps the first ref row's
  `passes`, and expands the abridged piece whose `nsteps` lies. Guard: the
  `rebuild` job of push.yml, on GMOD/graph-walks at c0d8a23; the script
  first requires 26 of the broken files to fail it
- **2026-11-07, the fundamentals review (no step-for-step rebuild on a
  file).** The only check that rebuilt a line from a file against the GFA
  was `tests/walks.rs`'s decoder, on ten fixture builds. On any file,
  `walks-truth.py pieces` summed each line's bp, so a wrong node of the
  same length, a flipped strand or a swapped choice passed it, and passed
  verify7, claims7 and audit7, which read the file alone; audit7's "every
  base in one piece's stretch or one record's own bp" is a bp cover too.
  No real-data run had ever compared the file's steps with the GFA's.
  Source: the fundamentals review, after the user asked for fundamentals
  over edge cases. Fix: `walks-truth.py rebuild WALKS GFA [--shard I/N]`
  decodes every walk row and detail unit by the spec's rules, hashes each
  piece's handles (and a ref row's lengths), and compares each line's
  pieces in order with the GFA's steps, 0 bp segments dropped, the set of
  lines included; the decoder also refuses a step off the end of R, where
  it wrapped to R's last position. `broken/corrupt.py` repacks a file from
  edited text so a broken file is reproducible. Guard: check-walks.sh and
  fuzz7.sh run it on every build; broken.sh on `interior-flipped`,
  `detail-interior-flipped` and `ref-strand-flipped`, which every other
  checker passes, and on five older broken files; the release check on
  ada (`writer/scripts/release-check.sh`) runs it in shards on MC chr22
  and pggb chrY, which has not yet run: ada refused ssh all day
- **2026-11-07, the fundamentals review (thread count).** Nothing had
  shown the bytes independent of the machine: MC chr22 was compared across
  commits on one host. Source: the fundamentals review. Fix: none needed;
  95 files from the ten walk fixtures under five option sets and five fuzz
  graphs under three, built at 1, 2 and 16 threads, are byte-identical.
  Guard: none in CI; `docs/handoff/2026-11-07-fundamentals.md` records
  the run
- **2026-11-07, the release check on ada (claims7 on a chromosome).**
  `claims7.py --own` had never completed on a real graph: no result for it
  exists under writer/results, only fixtures and fuzz. On MC chr22 with 24
  shards, each shard holds every tile of the file and 18 to 26 GB, six of
  eight died under a 20 GB cap in nine minutes, and under 28 GB none of
  four finished in an hour, since the O2 and L1 checks rescan a path's
  steps for each own step. Source: the first release-check run. Fix: none
  to the checker yet; `release-check.sh` runs claims7 only with
  `CLAIMS7=1`, and audit7, which checks `ownTiles` and own bp by its own
  route, ran unsharded under 60 GB on MC chr22 with the GFA and passed.
  Guard: none; a claims7 that streams and indexes a path's steps once is
  owed before its O and L claims count as checked on real data
- **2026-11-07, the consumer ports (a departure hidden behind its flanks).**
  bandage-core 13.0.1 drew a haplotype whose departure spans the window, with
  a step within the cut's context on each side, as an empty row with no sign
  of the departure: on the `skip` fixture (HG002#1 `>1>2>9>10`, leaving at
  20 and rejoining at 80) at chr1:31-60 with graph-walks' default 1000 bp
  context, the row read `0.0 kb (−30 bp)` with no runs, while the same
  window at context 0 read "no step on GRCh38 across 60 bp · 0 bp of its
  own". A lone flank beside a departure crossing the window read "goes on"
  likewise. On a real graph that is any haplotype with a deletion wider than
  the window and steps within 1 kb of it. Source: the JBrowse plugin's port
  to graph-walks 6, whose fixture test asserted the empty row. Fix:
  bandage-core `818a1c6`, a row is stepless when the slice between its
  flanks holds no step and one of its departures crosses the reference's
  bar, whatever the context. Guard: two tests in bandage-core's
  `src/gfa/graphWalks.test.ts` at context 1000, shown failing first, and the
  plugin's `walkFiles.test.ts` skip test, which asserts the departure row
- **2026-11-07, the consumer ports (`bytesFor` on a range that is not
  finite).** graph-walks 6's `bytesFor` returned 0 for a NaN or infinite
  bound, where `cut` and `referenceNodes` refuse the range first, so a byte
  gate fed such a window would pass it and the cut after it would throw.
  Source: the plugin port, which guards the range itself. Fix: graph-walks
  `e7259ee`. Guard: the finite-range test runs over `cut`, `referenceNodes`
  and `bytesFor`
- **2026-11-08, graph-walks release-check on the genome-wide CHM13 file.**
  On `hprc-v2.1-mc-chm13.CHM13.walks.gz` (writer 1e698f4, verify7 clean)
  graph-walks e7259ee's `release-check` passes 25 of its 28 chr22 windows
  and fails three (chr22:18.9-19.0 Mb, 19.0-19.1 Mb, 12.345-12.395 Mb): an
  abridged walk read unexpanded differs from the same walk expanded; at
  18.9-19.0 Mb HG00097#2 covers `[18877346,18898973],[18950922,19077990]`
  with net 387,953 bp expanded but `[18950922,19077990]` with 388,284 bp
  unexpanded, so the unexpanded read lacks the walk's first piece in the
  window. The GRCh38 file passes all 28 (`results/genome7.release-check-*`).
  Source: the first release check on a CHM13 build. Fix: none yet; not
  diagnosed (writer, reader, or the check's own assumption on a sequence
  the reference revisits). Guard: the release check itself; do not host
  the CHM13 file until this is explained

