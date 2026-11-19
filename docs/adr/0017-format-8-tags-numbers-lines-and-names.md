# ADR 0017: Format 8's page says how its tags, numbers, lines and names are written, and a name is printable ASCII

- **Status:** accepted, 2026-11-18, before the paper cites walk format 8
- **Decides:**
  - which tags a `#walks` line needs, what a tag left out states, and
    that the abridge budgets bind no row
  - how a number, a line and a field are written, each tag's type letter
    and `tile:i:`'s range
  - which lines begin `#unit`, that a step is 1 bp or more and that R
    ascends, as invariants a reader relies on
  - one `#reference` line, no empty unit, BGZF, and `bytes` as the
    directory's tag
  - that a file's reference is the paths its `ref` rows are cut from,
    one or more whole haplotypes of the `#reference` sample, which
    narrows format 8
  - the order two routes compare in, that a walk row names no default
    and takes a route that is its own flip with flip 0, the order of a
    sequence's detail units, and that the pyramid's four bin sizes are
    format
  - that a reader need not detect a file that is not format 8
  - that a name is bytes 0x21 to 0x7E, which narrows format 8
- **Rejects:** names as any bytes compared as bytes, with today's writer
  rule stated as reader-relied; GFA's ban on a leading `*` or `=` in a
  name; the budgets as a bound on a file's rows
- **Applies** [ADR 0011](0011-format-7-is-frozen.md)'s rules and
  [ADR 0016](0016-format-8-is-frozen.md)'s reasoning on C27: a narrowing
  is stated before the format is cited or not at all

## Context

- **Three independent reviews read the page before the freeze** and each
  found the same kind of gap: a property every file has, and a reader or
  a checker leans on, that the page implied or stated only as what this
  writer does. ADR 0016 had left one of them open by name, the tags a
  file may leave out, since the checkers disagreed on such a file
- **The checkers held a file to more than the page.** `audit7.py` failed
  a file with no `revisited`, and `claims7.py`'s B3 an abridged file with
  no `abridgebytes` or with both budgets stated as 0
  ([before.txt](../walks-container/spec-sentences/before.txt))
- **And to less.** A number written `0100`, `+6` or `-0`, an empty line
  in the header, an empty field, an empty departure bin, a later unit's
  line beginning `#unit` and a line ending past 2^53 passed every file
  check, though the page calls its invariants ones the file checks read
  off a file
- **graph-walks already leaned on ASCII names.** It decodes a unit
  through a non-fatal UTF-8 decoder and orders names with `<`, so it
  reads `H\xe9` and `H\xea` both as `H�`, takes two reference sequences
  that differ only in such a byte for one, and sorts in UTF-16 code
  units where the page sorts in bytes
  ([issues log](../issues-log.md), 2026-11-18)
- **The reader takes the reference from the `ref` rows.** graph-walks
  builds R, places nodes and counts from the rows of kind `ref` alone
  (`refRows`, src/walkChunk.ts; src/walkCounts.ts), and uses the
  `#reference` line only to turn a bare contig into a sequence name
  (`cutRegion`, src/walkReader.ts). The page defined a reference sequence
  as a path of the reference sample and `#haplotype` as "each other path
  with rows", which reads as if every path of the sample were reference.
  Three checks read it so, classed a line by its sample, and failed a
  file the reader reads correctly: `spec8.py`, `walks-truth.py rebuild`
  and `graph-walks-rebuild.mjs`
- **And it tells the reference's lines from the others by
  `sample#haplotype`.** `formsCut` skips every path listed under what
  the reference sequence is (src/walkDepartures.ts), and `counts` folds
  the reference sequences' `sample#haplotype` into one column
  (src/walkReader.ts). The page as first reworded here let any path of
  the `#reference` sample with no `ref` rows be a line like any other.
  A review of that wording built a file with reference sequences
  `HG002#1#chr1` and `HG002#1#chr2` and `HG002#1#alt1` in walk rows:
  every checker passed it, and graph-walks b0d8378 gave the line nothing
  covered and no departures, and counted it with the reference
- **Three more reviews read the page after those rulings** and found
  sentences that left bytes or meaning open: an order with no order
  named, a block's `d` that read as a base where the example used a
  boundary, three things called a number, and rules of the file stated
  as what the tool does

## The rulings

Each is in [walks-format.md](../walks-format.md) under the claim named,
and [claims7.md](../departures/claims7.md) lists its checks.

- **Tags (C201).** A `#walks` line needs `format:i:8` and `tile:i:` and
  no other tag. A file whose line lacks `revisited`, `stay`, `abridge`,
  `abridgebytes`, `graph` or `leftout` is format 8, and a reader doesn't
  refuse it. A tag left out states nothing, which is not stating 0
- **Budgets (C202).** `abridge` and `abridgebytes` record this writer's
  policy and bind no row. A file that states both as 0 and holds
  `abridged` rows is format 8, and so is one with a tile that costs more
  than a budget it states
- **Numbers (C203).** Decimal digits with no sign, no leading zero and no
  space, `0` for zero. A delta token, a choice token and a block's `d`
  alone can begin with `-`, and none is `-0`. So a number has one text
- **Tag types and `tile` (C204, C205).** `format`, `tile`, `revisited`,
  `stay`, `abridge`, `abridgebytes`, `leftout` and `bytes` are `i`,
  `graph` is `Z`, and `tile:i:` is from 1 to 2^40
- **Lines (C206).** Every line of the data file and of the directory is
  fields separated by one tab and ends in one newline. No line and no
  field is empty
- **`#unit` (C207).** No line of the file begins `#unit` except the first
  line of a unit, in a unit of a later kind too. The page had said no
  line after a unit's first starts with `#`, which a table's `#entry`
  lines break
- **What a reader relies on (C208, C209, C172).** A step is 1 bp or more,
  no two `ref` rows of a sequence cover a base twice, so R ascends, and
  no coordinate is above 2^53. The first two were stated only as what
  the tool does, and the third had no file check
- **Small cases (C157, C210, C29, C211).** A file has one `#reference`
  line. No unit of a kind the page gives is empty, so a departure bin
  with no record is not in the file. A unit is BGZF members. The data
  file's `#walks` line carries no `bytes` tag
- **The reference (C9, C51, C157).** A file's reference is the paths its
  `ref` rows are cut from: one or more whole haplotypes of the
  `#reference` sample. No path with `walk` or `abridged` rows is listed
  under what a reference sequence is listed under, its
  `sample#haplotype` or, for a `path` of fewer than three fields, its
  sample, and no `#haplotype` line lists it. The reference can be one
  haplotype of the sample, `HG002#1`, and the paths of `HG002#2` then
  have walk rows, departure records and a `#haplotype` line like any
  other. `#reference` names a sample, never a haplotype: a file whose
  line names `HG002#1` is not format 8
- **Routes and walk rows (C68, C70, C129).** Two routes, or the two ways
  round of one, compare by `entry`, then `interior`, then `exit`: `.`
  before any handle, handles as integers, interiors handle by handle
  with the shorter first where one begins the other. A route is stored
  the way round that comes first, and a piece takes a route that is its
  own flip with flip 0. A `@k` or `:k` that names its default is not
  format 8, so a file has one encoding. The page had said "whose handles
  sort first" and "the tool writes them only where they differ"
- **Unit order and bin sizes (C32, C43).** A sequence's detail units are
  in order of their tile's start and then their number. The pyramid's
  four bin sizes are format: [ADR 0010](0010-walks-unit-table.md) had
  called the pyramid the writer's choice, and a reader selects bins by
  overlap whatever their size, but a second writer with other sizes
  would write other bytes for the same rows, and all three reviews kept
  the sizes
- **Wording that changes no file.** A block's `d` counts between
  boundaries, where a block begins and where the one before ended, a
  `-` block beginning at its high boundary; a P line's digits are a
  name number, the one number is that of Rows, and the ABNF's is that
  number above 0; a departure lies between steps placed on S; `ownTiles`
  lists a tile once; a first route with no entry exits on `startHandle`,
  emitted once; the drawn stretch has one definition; an S line that is
  `*` with no `LN:i:` hashes 2^64 − 1
- **What a reader must detect.** Nothing past the refusals the page
  gives it. graph-walks b0d8378 opens a file with `tile:i:0`, a number
  written `0100`, an empty field, two `#reference` lines or a space in a
  name, and reads plain gzip units: of the 22 planted files of the
  first rulings a review opened with it, it refused `walks-bytes-tag`
  alone (ada, `~/work/walks8-gates/agents/green-reader/r2/planted.out`,
  not in this repository). The file checks hold a file to the page
- **Names (C200).** A sequence name, a `path` and a name a `#reference`,
  `#haplotype` or `#hole` line or a directory line states is one or more
  bytes from 0x21 to 0x7E and does not start with `#`. Two names are the
  same exactly when their bytes are, and their byte order is their order
  in any encoding. A file holding any other name is not format 8

## The ruling on the reference

- **It narrows format 8,** against the wording this ADR first gave it,
  which no release and no hosted file was written under. A file with a
  path on a reference haplotype in walk rows passed every checker, and
  no longer does
- **Why this rule.** It is the rule the reader already keeps
  ([issues log](../issues-log.md), 2026-11-19), stated in the terms the
  reader uses, what a path is listed under. The writer keeps it with no
  change: `--refs` takes a whole sample and makes every path of it with
  steps a reference sequence. No hosted file changes: `claims7.py`'s H4
  and `verify7.py` read each one whole
  ([claims-hosted.tsv](../walks-container/spec-sentences/claims-hosted.tsv),
  [hosted.tsv](../walks-container/spec-sentences/hosted.tsv))
- **What stays legal.** A reference of one whole haplotype, `HG002#1`,
  with `HG002#2` in walk rows: every checker passes
  `one-haplotype-reference` in the matrix, as before
- **Not taken:** teaching the reader to class a line by its `ref` rows
  alone. `counts` gives the reference one column per file and `formsCut`
  one reference to depart from, and a path on a reference haplotype that
  is no reference sequence has no place in either

## The ruling on names

- **It narrows format 8.** Until now the writer wrote any byte of a W or
  P line's name but a leading `#` and a NUL, so a file with a space, a
  carriage return or a byte above 0x7E in a name was format 8. It no
  longer is, and the writer refuses the GFA line
- **Why it is taken now.** As with C27, a narrowing is stated before the
  format is cited or not at all: a narrow promise can be widened later,
  and a wide one can't be withdrawn once files are cited under it
- **Why this rule.** They are the bytes GFA 1 allows in a segment name, a
  path name, a sample and a sequence id, so no GFA that keeps to its
  specification is turned away. The reader needs no change, since it
  already reads names as if the rule held. And no hosted file changes:
  none of the three hosted files, nor pggb chrY, has a line with a byte
  other than a tab and 0x21 to 0x7E
  ([census.tsv](../walks-container/spec-sentences/census.tsv))
- **Who decided.** Two deciders ruled apart, and one of the three
  reviews chose the same rule
- **The dissent.** A referee preferred stating today's writer rule, no
  leading `#` and no NUL, as what a reader relies on, and comparing names
  as bytes. That keeps every file written so far format 8 and leaves the
  reader wrong on a name it can't decode. The ruling takes the narrow
  rule and accepts what the dissent names: a GFA with such a name, which
  built until now, is refused

## What ADR 0011's rules say

- **Trigger.** No hosted file's bytes change, and no row's meaning. All
  but the names ruling and the reference ruling is the case ADR 0011
  names apart: spec wording matched to what the writer and the reader
  already do, and checker fixes. Those two narrow the format, and each
  has an [issues-log](../issues-log.md) entry that names the consumer:
  graph-walks' decoding and ordering of names, and its telling the
  reference's lines by `sample#haplotype`, as ADR 0016's did for C27.
  The route order, the one encoding, the detail units' order and the
  bin sizes were rules of the page already, worded so that a second
  writer could not tell what bytes they fix; `claims7.py` and `spec8.py`
  held files to each before this ADR, but for flip 0 on a route that is
  its own flip and the order among detail units, which they hold a file
  to now
- **Scope.** Every sentence was checked on the fixtures and fuzz files
  and the names rule on the hosted files' bytes
- **Burden.** Leaving the page as it was leaves three reviews' findings
  standing against a format about to be cited, and a reader that merges
  names the format tells apart
- **Checker evidence.** Each check below is cited with its recorded
  failure on a planted file

## Evidence
<!-- record -->

- **Where the runs were made.** All of them on ada.
  [run.txt](../walks-container/spec-sentences/run.txt) names the commit
  of this branch the checks ran at, which lacks only run.txt, matrix.txt
  and before.txt, and the reader they ran against: graph-walks b0d8378,
  cloned there from a bundle of the checkout the reader is developed in.
  [hosted.tsv](../walks-container/spec-sentences/hosted.tsv) and
  [claims-hosted.tsv](../walks-container/spec-sentences/claims-hosted.tsv)
  name the git blob of the `verify7.py` and the `claims7.py` that read
  the hosted files, and each is that commit's
- **The matrix**
  ([matrix.txt](../walks-container/spec-sentences/matrix.txt), by
  [matrix.sh](../walks-container/spec-sentences/matrix.sh);
  [before.txt](../walks-container/spec-sentences/before.txt) is the same
  files read by the checkers of 942ee66, before this ADR). Every checker
  passes the legal files, which `check-walks.sh` now runs, and each
  planted file fails the checkers
  [cases.tsv](../departures/scripts/broken/cases.tsv) names:

  | File | Fails now | Before |
  |---|---|---|
  | A writer's file with no `revisited`, `stay`, `abridge` and `abridgebytes`, or with one of them left out | nothing | `audit7.py` with no `revisited`, `claims7.py` with no `abridgebytes` |
  | The same stating both budgets as 0 over `abridged` rows | nothing | `claims7.py` |
  | `revisited` stating another count than the `ref` rows hold | `verify7.py`, `audit7.py`, `spec8.py` | the same |
  | A stated budget its rows break, or need not have been abridged for | `claims7.py`, as this writer's policy | `claims7.py`, and `spec8.py` on `abridge` |
  | A number written `0100`, `+6` or `-0` | `verify7.py` | nothing |
  | `revisited:Z:0`, `graph:i:5`, `tile:i:0`, no `tile:i:`, `tile:i:` above 2^40 | `verify7.py`; `spec8.py` on all but `graph`; `claims7.py` on the three of `tile`, by name | `spec8.py` on the first; a traceback from `verify7.py` on `tile:i:0` and from `claims7.py` with no `tile:i:`; 2^40 by other checks |
  | An empty header line, directory line or field | `verify7.py`, and `spec8.py` on the lines | `spec8.py` on the header line; `verify7.py`, `audit7.py` and `spec8.py` on the directory's; nothing on the field |
  | A later unit's line beginning `#unit`; an empty departure bin | `verify7.py` | nothing |
  | `#reference` twice; `bytes:i:` on the data file's `#walks` line | `verify7.py`, `spec8.py`, and `claims7.py` on the first | `spec8.py` on both; `verify7.py` on the second |
  | A length of 0; two `ref` rows over one base | `claims7.py` by R5 and R4, `verify7.py` on the length, with others | others, by other checks |
  | A line ending at 2^53 + 1 with no number above 2^53; a `hapOffset` above it | `claims7.py`; `verify7.py` and `claims7.py` | nothing but the rebuild against the GFA |
  | A name with a space, a carriage return, 0xE9 or 0x7F | `verify7.py`, `spec8.py` | nothing but the rebuild against the GFA, and `claims7.py` on the carriage return, which it reads as a line's end |
  | A file whose reference is one haplotype of its `#reference` sample | nothing | `spec8.py`, `walks-truth.py rebuild` |
  | `#reference` naming a haplotype | `claims7.py`, `spec8.py`, `walks-truth.py rebuild` | the same |
  | A path on a reference haplotype in walk rows, beside that haplotype's reference sequences | `verify7.py`, `claims7.py`, `spec8.py` | `spec8.py` and `walks-truth.py rebuild`, by classing a line by its sample, which failed the legal file above too; nothing once they classed by `ref` rows |
  | No `#reference` line | `verify7.py`, `claims7.py`, `spec8.py`, `walks-truth.py rebuild` | all but `verify7.py` |
  | A `@k` or `:k` that names its default, on the start, the entry or the exit; flip 1 on a route that is its own flip | `claims7.py`, `spec8.py` | the same on the defaults; nothing on the flip |
  | Two detail units of a tile in the other order | `claims7.py`, `spec8.py` | `spec8.py` |
  | A `path` that starts with `#` or holds 0x7F in rows alone; `#haplotype #H#1` | `verify7.py`, `spec8.py`, and `claims7.py` by the `#haplotype` list | not `verify7.py` |
  | An empty tile, detail unit or table | `verify7.py`, `claims7.py`, `spec8.py` | the same, but for `verify7.py` on the table |
  | A leading zero, a sign or a space in a tag's value, a `start`, an `nsteps`, a length, a `#unit` line and an `#entry` | `verify7.py`; `spec8.py` on the tags and the `#unit` line | nothing on the `tile` tag, the `start`, the `nsteps` and the length |
  | Two tabs side by side in a row and in a directory line | `verify7.py`, `spec8.py`, and `claims7.py` on the row | `claims7.py` and `spec8.py` on the row; `verify7.py` and `spec8.py` on the directory line |
  | `hapStart + ownBp` above 2^53 where neither is; a breakpoint above it | `verify7.py`, and others by other checks | not `verify7.py` |
  | A header line that begins `#unit`; two `ref` rows of two tiles over one base | `verify7.py`; `claims7.py` by R4 | `verify7.py`; nothing by R4 |

- **The hosted bytes.** `verify7.py` with the checks this ADR adds reads
  the three hosted files and pggb chrY whole and passes each
  ([hosted.tsv](../walks-container/spec-sentences/hosted.tsv)): every
  number, line, field, name, tag and coordinate in them is written as the
  page now says, and no walk row is of a path on a reference haplotype.
  Each file's sha256 is the one
  [identity.tsv](../walks-container/accept-5.0.0/whole-file/identity.tsv)
  records for the copy whose ETag is the hosted file's. None of the four
  has a line with a byte other than a tab and 0x21 to 0x7E
  ([census.tsv](../walks-container/spec-sentences/census.tsv), counted
  again at this commit)
- **The claims that take a sequence's rows, on the hosted files whole.**
  `verify7.py` holds no file to R ascending (R4, C209), to where a walk
  row's piece ends (K13, C172), to the `#haplotype` list (H1), to the
  reference sample of each `ref` row (H3) or to one encoding of a walk
  row (W2, C70), and a review found no whole-file run of `claims7.py`,
  which does, on a hosted file. `claims7.py` has now read the GRCh38 and
  the CHM13 file whole, a batch of sequences at a time with `--seq`
  ([claims-hosted.sh](../walks-container/spec-sentences/claims-hosted.sh)),
  without `--own`, so the claims about a record's own steps are not in
  the run. Every batch exits 0 and every claim counts 0 over each file,
  R4, R5, K13, H1, H3, H4, U1 and W2 among them
  ([claims-hosted.tsv](../walks-container/spec-sentences/claims-hosted.tsv),
  with each batch's seconds and peak memory). N2 and N3 are held within
  a batch's sequences there, and `verify7.py` holds N2 over the file.
  GRCh38's chr1 ran first and alone, to measure the largest peak, 13.2
  GB; each other batch ran under a memory cap the kernel held it to, so
  the run could not take memory from the drawing gate running beside it
- **A reference of one haplotype.** Every checker passes
  `one-haplotype-reference` in the matrix, a file with
  `#reference HG002`, `ref` rows of `HG002#1` alone and `HG002#2` in walk
  rows, which `check-walks.sh` now makes from
  [hapref.gfa](../departures/scripts/broken/hapref.gfa) under two option
  sets; before, `spec8.py` and `walks-truth.py rebuild` failed it.
  `graph-walks-rebuild.mjs --file` cuts each of its sequences whole and
  gets every path, placement and departure back as the GFA states them
  ([run.txt](../walks-container/spec-sentences/run.txt), against
  graph-walks b0d8378). Another session
  ran graph-walks 730e752's `cut`, `cutRegion`, `counts` and `formsCut`
  on such a file of a hand graph and of 9 fuzz graphs, and each returned
  what it returns on the same graph with `HG002#2` under another sample's
  name, 0 lines differing; its scripts are on ada under
  `~/work/visits/hapref/` and are not in this repository
- **A cut returns every visit to the reference nodes it covers.** The
  same session cut every haplotype with graph-walks 730e752, context 0
  and no budgets, and compared each haplotype's count on each node with
  the raw GFA's (`~/work/visits/` on ada: `truth.py`, `cut.mjs`,
  `compare.py`, `run.log`; not in this repository):
  - MC chr22, which has no revisited node: 776 tile windows, 464
    haplotypes, 554,488,368 visits, 0 differing
  - pggb chrY: 874 windows; on nodes the reference passes once, passes
    counted over every line of the reference sample as the file's
    `passes` are, 19,901,967 visits and 0 differing. Nodes passed more
    than once are reported only, a visit's place there being the
    writer's choice
  - a visit credited to another haplotype at an equal count, and a visit
    dropped, each planted on a once-passed node, were both caught, the
    dropped visit at exit 1
  - a cut trimmed inside a tile is exact too: 40 stretches of 1 kb in
    each graph, each compared on once-passed nodes with the cut of its
    whole tile, 376,489 pairs of haplotype and node on MC chr22 and
    12,367 on pggb chrY, 0 differing; with each stretch cut 200 bp short,
    74,059 pairs differ and the comparison exits 1 (`mc22/sub*.log`,
    `pggbY/sub.log`)
- **`spec8.py --gfa` skips a line with no steps,** as the page and the
  writer do (C118). It had looked such a line up by its name and start
  and compared the next line's pieces with no steps. The dialect fixture
  [w-empty-line-first.gfa](../walks-container/dialect/w-empty-line-first.gfa)
  holds the case, and `spec8.py --gfa` still fails broken/interior-flipped
  ([run.txt](../walks-container/spec-sentences/run.txt))
- **The writer.** `named` refuses a W or P line whose name holds a byte
  outside 0x21 to 0x7E, with the line's number, and the three dialect
  fixtures with such names are refused where they built
  ([expected.tsv](../walks-container/dialect/expected.tsv)). No other
  byte of `src/` changed, and the planted files made before this ADR
  rebuild to the same bytes
- **The full run.** `cargo fmt`, `clippy` and `test`, `check-walks.sh`
  on every fixture and fuzz file with `broken.sh` and `check-dialect.sh`,
  `check-claims.py` with `GRAPH_WALKS` set to the reader's clone,
  `check-links.py`, `figures.py --check`, `make-broken.sh`, which writes
  every planted file again to the bytes committed, and
  `graph-walks-rebuild.mjs` against graph-walks b0d8378, on its broken
  files, every fixture and the one-haplotype file, pass on ada at the
  commit [run.txt](../walks-container/spec-sentences/run.txt) names.
  The runs this ADR first recorded were at 2995d1d against graph-walks
  730e752; b0d8378 adds one commit to it, which throws on a contig that
  two haplotypes of the reference sample hold

## Alternatives rejected
<!-- record -->

- **Names as any bytes, compared as bytes,** the dissent above. The
  reader would have to decode names as bytes to keep it, and a carriage
  return in a name still splits a line in every tool that reads text
- **GFA's ban on a leading `*` or `=`.** Nothing in a walk file reads
  either as anything but a name
- **Budgets that bind.** A reader ignores them, and another writer's
  policy would then be another format
- **Rewording "no coordinate is above 2^53" as this writer's guarantee,**
  in place of checking it. The check was cheap to add
- **Any path of the `#reference` sample without `ref` rows as a line
  like any other,** this ADR's first wording. The reader misreads a path
  on a reference haplotype, and every checker passed the file
- **The pyramid's bin sizes as the writer's choice,** ADR 0010's words.
  Two writers would then write other bytes for the same records, and
  the checks that hold a record to its cover would hold to nothing
- **The order among detail units, and the flip of a route that is its
  own flip, left open.** No reader needs either, and the same rows would
  have more than one file

## Consequences
<!-- record -->

- **Every hosted file keeps its bytes and stays format 8**
- **A GFA with a space, a carriage return or a byte above 0x7E in a W or
  P line's name is refused,** where it built until now
- **`verify7.py` is stricter:** a file it passed with a number in another
  text, an empty field or an empty departure bin now fails
- **`spec8.py` checks names, the reference's whole haplotypes,
  `tile:i:`'s range and the `#walks` line's numbers, and holds no row to
  a budget.** It does not yet check how any other number is written, an
  empty field in a row, a later unit's lines, an empty departure bin or
  2^53
  ([open problem](../open-problems.md#checkers-that-hold-a-file-to-more-or-less-than-the-format))
- **A file with a path on a reference haplotype in walk rows is not
  format 8,** where the first wording of this ADR admitted it. No
  release wrote one and no hosted file holds one
- **`claims7.py` and `spec8.py` are stricter:** a walk row that takes a
  route that is its own flip with flip 1, and for `claims7.py` detail
  units out of order, now fail; each refuses `tile:i:0` by name
- **graph-walks needs no change.** Its README can say names are ASCII,
  and that it detects no file that is not format 8 past the refusals the
  page gives a reader
- **gfa-to-tabix writes no file whose reference is one haplotype of a
  sample:** `--refs` takes samples, and `--refs 'HG002#1'` is refused.
  That is writer support for later, not a question of the format
  ([open problem](../open-problems.md#a-reference-of-one-haplotype-of-a-sample-cant-be-written))
