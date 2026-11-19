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
    which can be one haplotype of the `#reference` sample
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
  `ref` rows are cut from, each of the `#reference` sample. It can be one
  haplotype of that sample, and the sample's other paths then have walk
  rows, departure records and a `#haplotype` line like any other.
  `#reference` names a sample, never a haplotype: a file whose line
  names `HG002#1` is not format 8. This widens nothing a reader does and
  narrows nothing: it is wording matched to the reader
- **Names (C200).** A sequence name, a `path` and a name a `#reference`,
  `#haplotype` or `#hole` line or a directory line states is one or more
  bytes from 0x21 to 0x7E and does not start with `#`. Two names are the
  same exactly when their bytes are, and their byte order is their order
  in any encoding. A file holding any other name is not format 8

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
  but the names ruling is the case ADR 0011 names apart: spec wording
  matched to what the writer and the reader already do, and checker
  fixes. The names ruling narrows the format, and its
  [issues-log](../issues-log.md) entry names the consumer, graph-walks'
  decoding and ordering of names, as ADR 0016's did for C27
- **Scope.** Every sentence was checked on the fixtures and fuzz files
  and the names rule on the hosted files' bytes
- **Burden.** Leaving the page as it was leaves three reviews' findings
  standing against a format about to be cited, and a reader that merges
  names the format tells apart
- **Checker evidence.** Each check below is cited with its recorded
  failure on a planted file

## Evidence
<!-- record -->

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
  | `revisited:Z:0`, `tile:i:0`, `tile:i:` above 2^40 | `verify7.py` | `spec8.py` on the first; a traceback from `verify7.py` on the second; the third by other checks |
  | An empty header line, directory line or field | `verify7.py`, and `spec8.py` on the lines | `spec8.py` on the header line; `verify7.py`, `audit7.py` and `spec8.py` on the directory's; nothing on the field |
  | A later unit's line beginning `#unit`; an empty departure bin | `verify7.py` | nothing |
  | `#reference` twice; `bytes:i:` on the data file's `#walks` line | `verify7.py`, `spec8.py`, and `claims7.py` on the first | `spec8.py` on both; `verify7.py` on the second |
  | A length of 0; two `ref` rows over one base | `claims7.py` by R5 and R4, `verify7.py` on the length, with others | others, by other checks |
  | A line ending at 2^53 + 1 with no number above 2^53; a `hapOffset` above it | `claims7.py`; `verify7.py` and `claims7.py` | nothing but the rebuild against the GFA |
  | A name with a space, a carriage return, 0xE9 or 0x7F | `verify7.py`, `spec8.py` | nothing but the rebuild against the GFA, and `claims7.py` on the carriage return, which it reads as a line's end |
  | A file whose reference is one haplotype of its `#reference` sample | nothing | `spec8.py`, `walks-truth.py rebuild` |
  | `#reference` naming a haplotype | `claims7.py`, `spec8.py`, `walks-truth.py rebuild` | the same |

- **The hosted bytes.** `verify7.py` with the checks this ADR adds reads
  the three hosted files and pggb chrY whole and passes each
  ([hosted.tsv](../walks-container/spec-sentences/hosted.tsv)): every
  number, line, field, name, tag and coordinate in them is written as the
  page now says. Each file's sha256 is the one
  [identity.tsv](../walks-container/accept-5.0.0/whole-file/identity.tsv)
  records for the copy whose ETag is the hosted file's
- **A reference of one haplotype.** Every checker passes
  `one-haplotype-reference` in the matrix, a file with
  `#reference HG002`, `ref` rows of `HG002#1` alone and `HG002#2` in walk
  rows, which `check-walks.sh` now makes from
  [hapref.gfa](../departures/scripts/broken/hapref.gfa) under two option
  sets; before, `spec8.py` and `walks-truth.py rebuild` failed it.
  `graph-walks-rebuild.mjs --file` cuts each of its sequences whole and
  gets every path, placement and departure back as the GFA states them
  ([run.txt](../walks-container/spec-sentences/run.txt)). Another session
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
  `check-claims.py`, and `graph-walks-rebuild.mjs` against graph-walks
  730e752 pass on ada at the commit
  [run.txt](../walks-container/spec-sentences/run.txt) names, which lacks
  only the files of this record

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

## Consequences
<!-- record -->

- **Every hosted file keeps its bytes and stays format 8**
- **A GFA with a space, a carriage return or a byte above 0x7E in a W or
  P line's name is refused,** where it built until now
- **`verify7.py` is stricter:** a file it passed with a number in another
  text, an empty field or an empty departure bin now fails
- **`spec8.py` checks names and holds no row to a budget.** It does not
  yet check how numbers are written, an empty field, a later unit's
  lines, an empty departure bin or 2^53
  ([open problem](../open-problems.md#checkers-that-hold-a-file-to-more-or-less-than-the-format))
- **graph-walks needs no change.** Its README can say names are ASCII
- **gfa-to-tabix writes no file whose reference is one haplotype of a
  sample:** `--refs` takes samples, and `--refs 'HG002#1'` is refused.
  That is writer support for later, not a question of the format
  ([open problem](../open-problems.md#a-reference-of-one-haplotype-of-a-sample-cant-be-written))
