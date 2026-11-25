# ADR 0016: Walk format 8 freezes as it is, and a file with no revisited node promises its reference nodes

- **Status:** accepted, 2026-11-16, before the paper freezes the walk
  format
- **Decides:**
  - walk format 8 ([walks-format.md](../walks-format.md)) freezes with no
    byte changed: every unit, row, column and tag stays as it is, and the
    hosted files stay the bytes they are
  - none of the six additions a study put forward is taken
  - the page gains wording only: C27 as an invariant of a file that
    states `revisited:i:0`, the meaning of a `ref` row's `passes`, and
    seven statements the page had left unsaid
- **Rejects:** a `links` unit, a site decomposition, stored haplotype
  counts, stored layout coordinates and a pairing rule in the walk file;
  C27 as an invariant of every format 8 file; C27 as a `#walks` tag; C27
  left as this writer's property alone
- **Applies** [ADR 0011](0011-format-7-is-frozen.md)'s trigger, scope and
  burden, which stand for format 8 as they stood for format 7

## Context

- **A reader leaned on a rule the page never stated.** graph-walks'
  counting call marks a count exact where a `ref` row states `passes` 1,
  and every window read returns the lines that step the window's
  reference nodes. Both hold only where no route interior holds a node
  the reference passes once (C27) and where `passes` counts the `ref`
  rows of the whole file (C62). C27 stood in
  [ADR 0009](0009-departure-records.md) and
  [claims7.md](../departures/claims7.md) as a consequence of this
  writer's placement, and nowhere in the page
  ([issues log](../issues-log.md), 2026-11-16)
- **A file can break it and read as valid.** A review of the counting
  call built one by hand
  ([craft/](../walks-container/accept-5.0.0/whole-file/craft/)): line A
  walks the reference's four nodes, and its steps on the last two are
  written as a route interior of the first tile. A read of the second
  tile returns the reference and B and no A. Of the six file checks only
  `claims7.py`'s N2 failed it
- **N2 had run a sequence at a time on the genome files,** 25 runs for
  each, where it holds a run's nodes to that run's own rows
  ([README](../walks-container/accept-5.0.0/README.md)). A route interior
  in one sequence holding a once-passed node of another was never looked
  for, and no run compared a `ref` row's `passes` with the `ref` rows of
  another sequence
- **A study had put six additions forward,** written to a standard fixed
  before it measured, against a baseline of changing nothing
  ([writeup.txt](../walks-container/format-study/writeup.txt),
  [its records](../walks-container/format-study/records.jsonl)). Three
  reviews, each with criteria written before it opened the write-up, ruled
  on them apart: whether each is needed before the freeze
  ([review-need.txt](../walks-container/format-study/review-need.txt)),
  by which route a reader would get it
  ([review-routes.txt](../walks-container/format-study/review-routes.txt)),
  and whether its text and checks are complete
  ([review-spec.txt](../walks-container/format-study/review-spec.txt))

## The candidates

Need is graded by the study's standard: demonstrated, where no set of the
file's rows holds the fact; cost-only, where the file serves it at a
measured price; not demonstrated. Every number is the write-up's, on
chromosome builds of the hosted Minigraph-Cactus graph, chr22 and chr6,
and on pggb chrY.

| Candidate | Need | The three reviews | Why it is not added now |
|---|---|---|---|
| Baseline: change nothing | | | The format as it ships: a 1 kb window of chr22 reads a median 29,426 bytes in one request |
| Complete adjacency, a `links` unit | Demonstrated for links that only left-out lines walk, 32,347 of chr22's 4,737,114 and none of chr6's; cost-only for the rest | later; nothing; later | No reader's view was shown to change, and 150 random 1 kb windows of chr22 hold no such link. It is a unit kind or a side file, so waiting closes nothing. Its text leaves absence undefined and its example's bytes are on disk nowhere |
| Site decomposition, a `sites` unit | Cost-only | later; reader only; never in the walk file | The rows already give it: chr22's 430,246 site intervals are the same from walked links alone. It is one definition among several, flat where the model it follows is nested, and 11.03% of chr22's file and 40.04% of chr6's |
| Haplotype counts, a `counts` unit or tag | Cost-only | later; reader only; later | On reference nodes the reader counts at no byte, given C27: 0 wrong on reference nodes in 211 probed windows, with a reader from before its counting call. Off the reference the prototype leaves out the left-out lines, which visit 50,890 chr22 nodes, so its number is not the graph's either, and M is not derivable from the header |
| Stored layout coordinates | Not demonstrated | never; nothing; never | A coordinate is a tool's output, not a fact of the graph: two runs with the same options share 0 of 51,126 points, and chr22 took 10 h 03 min and 49.0 GB against the writer's 45.7 s |
| Pairing rule for a side file | Not demonstrated on a hosted file | later, with the first side file, from all three | No side file exists, and the walk file needs nothing for one. The rule as prototyped pairs by `bytes:i:`, which the compressor sets |
| C27 as a guarantee | Not demonstrated on a hosted file; shown on the hand-built file | add now, scoped to `revisited:i:0`; add now, for every file; add now, for every file | Taken, as wording, in the scoped form: [the ruling](#the-ruling-on-c27) |

- **None of the five additions changes what a row means,** and each is a
  unit kind, a tag or a file that the page's additions rule already lets
  a reader skip. Freezing closes none of them
- **Only C27 as an invariant is tied to the freeze.** It narrows what
  format 8 is, so it is stated before the format is cited or not at all;
  as a tag it would change every hosted file's header, every `#entry`
  offset, the `.idx` and the checksum
- **Each stays an [open problem](../open-problems.md)** with what the
  study measured, stated as a problem

## The ruling on C27

- **C27 is an invariant of a format 8 file that states `revisited:i:0`.**
  No route interior, of a tile or of a detail unit, on any sequence of
  the file, holds a node the reference passes once. So the tiles a
  window's read selects hold a row of every line of the file that steps a
  reference node over the window
  ([What a reader relies on](../walks-format.md#what-a-reader-relies-on))
- **`passes` is stated beside it, unscoped,** as the meaning of a column:
  the number of steps on the node in the `ref` rows of the whole file
- **A file with revisited nodes, or one that states no `revisited`, is
  promised nothing of its once-passed nodes** by the format. The page
  says so
- **This writer keeps the rule on every file it writes,** revisited or
  not, and the page says that under
  [What the writer guarantees](../walks-writer.md#what-the-writer-guarantees),
  with the reason a reader can't use it: the header names no writer
- **Why the scoped form:**
  - it covers every hosted file: both hosted graphs' references pass no
    node twice
  - pggb is not hosted, and ADR 0011 keeps a format promise within what
    the hosted graphs show
  - a scoped promise can be widened later, and an unscoped one can't be
    withdrawn once files are cited under it
  - it leaves open how a file with revisited nodes files a once-passed
    node that haplotypes walk inside another copy of a repeat, as pggb
    chrY's node at 9,394,014 is
    ([open problem](../open-problems.md#a-once-passed-node-in-a-file-with-revisited-nodes))
- **The dissent.** Two of the three reviews would state it for every
  format 8 file. Their reasons: a reader can't know the writer, so on a
  file with revisited nodes it can say "N of M haplotypes step this node"
  of a once-passed node only on the writer's word; the page's list of
  what a writer chooses grants freedom only where the reference passes a
  node more than once, so the unscoped form takes away nothing the page
  gave; and no design on record files a step on a once-passed node off
  the reference. The third review scoped it, for the pggb chrY node. The
  ruling takes the scoped form for the four reasons above and accepts
  what the dissent names: on a file with revisited nodes a reader's exact
  count of a once-passed node rests on the writer

## The wording

All of it is in [walks-format.md](../walks-format.md), and
[claims7.md](../departures/claims7.md) lists each new claim's checks.

- **What a reader relies on** gains three bullets: `passes` counts the
  file's `ref` rows (C62); in a file that states `revisited:i:0` a step
  on a reference node is on R (C27); any other file makes no such
  promise
- **The C27 bullet counts lines the file holds.** A line that steps a
  reference node has a row, `ref`, `walk` or `abridged`, in that node's
  tile, the reference's own lines having `ref` rows; and what a reader
  can say from a window is how many of the file's haplotypes have a line
  in the file that steps the node. Whether the file holds every line of
  its graph that steps the reference is C4, checked against the GFA
- **The bullet for any other file** says what follows for a departure:
  it can pass over a once-passed node its line steps, so two ends passed
  once do not make its own sequence free of reference nodes
- **The section's opening** says the rules of Files and units, Header and
  Rows are among what a reader relies on, with the orders and names they
  give, and so is what Abridged tiles says a detail record holds and
  decodes against; that what the page calls this writer's choice is not,
  wherever it is stated, the order a tile numbers its detail records in
  being one; and what a decoder needs of the orders, the units' own
  order not among it
- **What the writer guarantees** gains the rule as this writer keeps it,
  on every file (C197), and `passes` over the whole file
- **Two sentences that said a route can hold another tile's reference
  nodes** now say which: nodes the reference passes more than once, and
  none in a file with `revisited:i:0`
- **Header:** a format 8 file's `#walks` line carries `format:i:8` and
  `tile:i:` (C198); a file that states no `revisited` states no count; a
  line carries a tag name at most once (C199); only the page gives a
  kind, a header word or a tag name a meaning in format 8, a file that
  holds one it doesn't give is format 8 still, except a row kind it
  doesn't give in a unit it does (C49), and a later kind takes no word of
  an existing one; a reader takes nothing from the lack of a later unit,
  and an addition that claims completeness says in the header what it is
  complete over, the whole file or the sequences it names; a file added
  beside a walk file is about its bytes
- **blocks:** a run off R can hold a node of another tile's reference in
  a file with revisited nodes, and holds none in a file that states
  `revisited:i:0`
- **Rows:** the shape `seq start end kind` binds the unit kinds the page
  gives (C54)
- **Hosting:** a cited name keeps its bytes
- **Left unsaid:** whether a file may leave out `revisited`, `stay`,
  `abridge` and `abridgebytes`. The checkers disagree on such a file, so
  saying it is more than wording
  ([ADR 0017](0017-format-8-tags-numbers-lines-and-names.md) says it)

## What ADR 0011's rules say

- **Trigger.** A format change needs an issues-log entry whose source is
  a user or a consumer working against a hosted file. None of the six has
  one: the study found none in the log, and the gap behind C27 was found
  by a review on a hand-built file, not by a consumer on a hosted one. So
  no format change is made, and the five additions go to open problems,
  as the rule sends a review's finding. What is taken is the case ADR
  0011 names apart: spec wording that leaves the rows' meaning unchanged,
  matched to what the writer and the reader already do. The log's entry
  names the consumer, graph-walks' counting call and window reads
- **Scope.** A change is measured on a hosted graph. The study measured
  chromosome builds of the hosted graph and pggb chrY, which is not
  hosted; the checks behind C27 ran on the hosted bytes themselves
- **Burden.** A change has to beat shipping unchanged, against criteria
  written first, and mixed evidence leaves the format as it is. For the
  five additions the format stays. For C27 the three reviews wrote their
  criteria before reading the study and made their rulings conditional on
  a whole-file check of both hosted files that had not yet run; it ran
  afterwards and found nothing
- **Briefs.** The study's first agent built its prototype and measured
  it, which the write-up records. The deciders were three reviews that
  held the write-up, the records and their own criteria, and one of them
  ran its own file-wide count
- **Checker evidence.** Each check cited below is cited with its recorded
  failure on a broken file

## Evidence
<!-- record -->

- **The whole-file checks on the hosted bytes**
  ([README](../walks-container/accept-5.0.0/whole-file/README.md), written
  from [results.jsonl](../walks-container/accept-5.0.0/whole-file/results.jsonl)
  by [table.py](../walks-container/accept-5.0.0/whole-file/table.py)).
  `verify7.py` read each file whole on ada:

  | File | Nodes the `ref` rows step once | Route interior steps read | Stepped once and in a route interior | `ref` rows whose `passes` states fewer, more |
  |---|---|---|---|---|
  | HPRC v2.1 Minigraph-Cactus on GRCh38, hosted | 83,303,684 | 679,905,395 | 0 | 0, 0 |
  | HPRC v2.1 Minigraph-Cactus on CHM13, hosted | 90,761,410 | 840,302,328 | 0 | 0, 0 |
  | GRCh38 chr6 with sequences, hosted | 4,799,024 | 25,220,331 | 0 | 0, 0 |
  | pggb chrY on GRCh38, not hosted, 107,467 revisited nodes | 155,947 | 290,043,748 | 0 | 0, 0 |

  On the three hosted files every `ref` step is on a node stepped once,
  so `revisited:i:0` is what their `ref` rows hold
- **The files checked are the hosted ones**
  ([identity.tsv](../walks-container/accept-5.0.0/whole-file/identity.tsv)).
  For each hosted file the local length equals the URL's
  `Content-Length`, the S3 multipart ETag computed from the local bytes
  over 8 MiB parts equals the URL's ETag, and the sha256 of the local
  `.idx` equals that of the hosted `.idx`. No hosted file was downloaded
- **A second count agrees.** The need review counted, with a script of
  its own over the `nodes` rows, the same 83,303,684, 90,761,410 and
  155,947 once-passed nodes and none in a route interior
  ([review-need.txt](../walks-container/format-study/review-need.txt)).
  `spec8.py`, written from the page with no code of `verify7.py`, counts
  the same nodes on the chr6 file and on pggb chrY and disagrees with the
  page nowhere; it holds a file's every piece in memory and does not read
  a genome file
- **Each check fails when broken**
  ([broken-matrix.txt](../walks-container/accept-5.0.0/whole-file/broken-matrix.txt),
  by [matrix.sh](../walks-container/accept-5.0.0/whole-file/matrix.sh);
  [cases.tsv](../departures/scripts/broken/cases.tsv) holds each file to
  the checkers named):

  | Broken file | Fails |
  |---|---|
  | The hand-built file: another tile's once-passed nodes in a route interior | `verify7.py`, `spec8.py`, `claims7.py` |
  | The same across two sequences | `verify7.py`, `spec8.py`, `claims7.py` on the whole file; `claims7.py` a sequence at a time passes it |
  | The same across two sequences in a file with a revisited node | `verify7.py`, `claims7.py` on the whole file; `spec8.py` passes it and counts the node, as the page promises nothing there |
  | A once-passed node in a route interior of its own tile, and of a detail unit | `verify7.py`, `spec8.py`, `claims7.py` |
  | `passes` 1 on every `ref` row that steps a node passed twice | `verify7.py`, `spec8.py`, `audit7.py` |
  | The same where two sequences each pass the node once | `verify7.py`, `spec8.py`, `audit7.py` on the whole file; `audit7.py --seq` passes it |
  | `passes` overstated, understated, and differing between two rows | `verify7.py`, `spec8.py`, `audit7.py` |
  | `revisited` stating 0, or 7, where the `ref` rows step another count of nodes more than once | `verify7.py`, `spec8.py`, `audit7.py`, and `claims7.py` where it states 0 |
  | No `tile:i:` | `verify7.py`, `spec8.py` |
  | A tag name twice on a line | `spec8.py` |

  Every checker passes the unbroken files these were made from, and
  [check-walks.sh](../../scripts/check-walks.sh) passes on every fixture
  and fuzz file
- **No byte of the writer changed.** No file under `src/` differs from
  the commit that built the hosted files, 9e46a46

## Alternatives rejected
<!-- record -->

- **C27 for every format 8 file,** the dissent above. It would settle,
  for a graph nobody hosts, how a once-passed node walked inside another
  copy of a repeat is filed, and a promise that wide can't be taken back
- **C27 as a tag on the `#walks` line,** stated by the files that keep
  it. It needs the same check, a rebuild and re-upload of the hosted
  files before they are cited, and leaves two classes of format 8 file
- **C27 left as this writer's property.** The file names no writer, so a
  reader could not know when its count is exact or its window complete
- **Stored counts in place of C27.** They cost 3.12% of chr22's file and
  6.18% of chr6's, have no checker, and leave a correct count beside a
  window that still lacks the line
- **Any of the five additions now.** None met ADR 0011's trigger, and
  none is closed by waiting

## Consequences
<!-- record -->

- **A file that states `revisited:i:0` and holds a once-passed node in a
  route interior is not format 8,** as the hand-built file is not. Every
  file gfa-to-tabix 5.0 wrote keeps its bytes and stays format 8
- **A file with revisited nodes keeps its placement freedom,** and a
  reader of one holds a once-passed node's count and a window's
  completeness to the writer, not to the format
- **graph-walks follows:** its counting call's exact case rests on the
  format only where the header states `revisited:i:0`, and its README's
  sentence that the rule is "a guarantee of gfa-to-tabix, not of walk
  format 8" is now wrong for those files
- **`verify7.py` and `spec8.py` hold the two properties to the whole
  file,** `verify7.py` in a byte for each node id, and `claims7.py` and
  `audit7.py` print, under `--seq`, that a 0 there is not a 0 for the
  file
- **The hosted files are not rebuilt,** and a later addition to them is a
  side file or a new name: a cited name keeps its bytes
