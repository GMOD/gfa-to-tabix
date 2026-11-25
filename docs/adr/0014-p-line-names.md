# ADR 0014: A P line's name is read from its right end, against its steps

- **Status:** accepted, 2026-11-12, before the paper freezes the walk
  format on about 2026-11-18
- **Decides:** how the tool reads a P line's one name into a `path`, a
  `fragStart` and what the path is listed under, for walk files and for the
  node and link index alike: [Path names](../walks-writer.md#path-names)
- **Changes** what `path`, `fragStart` and `#haplotype` hold for some P
  line inputs (claims C51 and C158), so
  [ADR 0011](0011-format-7-is-frozen.md)'s rules applied: burden, scope,
  briefs, checker evidence. No row, column or header key changes, a W
  line reads as before, and no hosted walk file's bytes move
- **Rejects:** keeping today's reading, refusing a fourth field above 0,
  reading no suffix, a 1-based `:start-end`, guessing the writing tool
  from the header, and an option that says what a name means

## In short

- **A W line has columns for its start and end. A P line has one name,**
  and pggb, odgi and vg each put a start into it their own way. The tool
  read the first suffix that parsed and never looked at the line's steps
- **That wrote coordinates no input stated.** A 1-based region name was
  placed one base off; a stated end the steps contradicted was accepted;
  the P form vg writes of a clipped graph gave two paths for one contig;
  a name that was only a suffix gave a path with no name
- **Now the name is read from the right, as the tools nest their
  suffixes,** and checked against the bp of the line's steps: odgi's
  `:a-b` only where the steps span it, then vg's `[s-e]` with its end
  checked, then a fourth field, and the starts add up
- **The same paths written as W lines and as P lines now give one file,**
  byte for byte, on every pair vg and odgi wrote here

## Context
<!-- record -->

- [The proposal](../walks-container/dialect/evidence/proposal.md) surveyed
  what each tool writes and means, and split the question into six
  rulings, each with "keep today's reading" as a candidate:
  - **R1** a fourth field, `sample#hap#contig#N`
  - **R2** a two-field name, `sample#contig`
  - **R3** a `:start-end` suffix
  - **R4** a `[start]` or `[start-end]` suffix, and its stated end
  - **R5** suffixes in combination, and a name that is only a suffix
  - **R6** a P line with GFA 1.2 `;` jumps
- **What the tools mean,** from their sources and from runs of vg 1.69.0
  and odgi 0.9.4 on tiny graphs:
  - pggb copies FASTA record names unchanged; PanSN defines three fields
    and no suffix
  - `odgi extract` appends `:start-end` to whatever name it was given,
    0-based with the end exclusive
    ([run](../walks-container/dialect/evidence/odgi-names.txt))
  - vg appends `#0` to every three-field P line it reads, and writes a
    subrange as `[start]` or `[start-end]`, 0-based, end exclusive
    ([run](../walks-container/dialect/evidence/vg-chunk-subranges.txt),
    [run](../walks-container/dialect/evidence/vg-metadata.txt))
  - vg calls the fourth field a phase block, and libhandlegraph's header
    says a phase block "may be a number or a start coordinate". One W line,
    `W H 1 c 100 106`, leaves vg as `H#1#c#100` through a GBZ and as
    `H#1#c#0[100-106]` through `vg convert -gfW`
    ([run](../walks-container/dialect/evidence/vg-mc-roundtrip.txt)). A
    haplotype cut by an unphased VCF genotype leaves it as blocks 0, 1,
    2, in the fourth field of P lines and in the start column of W lines
    ([run](../walks-container/dialect/evidence/vg-vcf-phase-blocks.txt))
  - `vg chunk` of a haplotype clipped from 100 writes both at once:
    `H#1#c#100[16-22]` for the stretch 116 to 122
    ([run](../walks-container/dialect/evidence/vg-chunk-of-clipped-gbz.txt))
- **What the tool did,** on main at 36a190d (`split_path_name`): the first
  of bracket, fourth field and colon range that parsed gave the start;
  no end was read; nothing was read beneath it; a path with fewer than
  three fields was listed whole in `#haplotype`

## Decision

The reading is [Path names](../walks-writer.md#path-names) in the spec;
the spec's text is the rule. By ruling:

- **R5, order and the outermost `:a-b`.** The name is read from the
  right, one layer of each kind at most: `:a-b`, then a bracket, then a
  fourth field. That is the order the tools nest them in: odgi cuts last
  and appends to any name, and vg writes its bracket after its fourth
  field. The tool reads no layer twice and none beneath a fourth field
- **R3, `:a-b`.** Read only where `a < b` and `b − a` is the line's bp,
  0-based and half-open, adding `a`. Any other colon text is part of the
  name
- **R4, a bracket.** Adds `s`. Outermost with an end, `e − s` must be the
  line's bp or the line is refused, as a W line's end column is (C18).
  Beneath a `:a-b` the end is not read: an odgi cut leaves the bracket
  describing the piece it was cut from
- **R1, a fourth field.** In `sample#hap#contig#N`, exactly three `#`
  and `N` a number, `#N` leaves the name and `N` is added; `#0` adds 0.
  `H#1#c#100[16-22]` is `H#1#c` from 116, which is where the stretch
  lies on the contig of the W line it was clipped and cut from
- **A colon beneath `#0` is not read.** `H#1#c:5-21#0` is the path
  `H#1#c:5-21` from 0, as the W line of the same path,
  `W H 1 c:5-21 0 16`, is: vg takes `c:5-21` for the contig
  ([run](../walks-container/dialect/evidence/vg-metadata.txt))
- **No empty path.** A name that is only a suffix, or empty, is refused
- **R2, two fields.** `sample#contig` is listed under its sample in
  `#haplotype`, which is what the node and link index's assemblies,
  graph-walks' helpers and vg already do; a name of one field is its own
  sample
- **R6, jumps.** A `;` in a P line's steps stays refused, by a message
  that says what it is and how to remove it. A W line's `*` start stays
  refused, by a message that says GFA allows it and it states no offset
- **One function.** `read_path_name(name, bp)` in `src/gfa.rs` reads every
  P line name, for `--walks` and for the node and link index. The index
  refuses what `--walks` refuses: a stated end the steps contradict, an
  empty path, and two lines of a path that overlap or share a start
- **`--refs` and `--reference`** match what a line reads as, and
  `--reference` also the name as its P line writes it; neither reads a
  suffix out of its own text
- **A start past 2^53 is refused** where a P line's start is settled,
  once its steps are summed, as a W line's is at its column
  ([Tiles and pieces](../walks-writer.md#where-a-step-is-filed))
- **A number** is one to nineteen decimal digits. Text that is no number
  makes no suffix
- **A stated limit, phase blocks.** The tool can't tell vg's counter from
  a start, in a P name's fourth field or in a W line's start column. It
  reads a start, and where the blocks then overlap it refuses with a
  message that says so. The spec states the limit and
  [open problems](../open-problems.md#starts-a-name-or-a-column-states-that-are-not-starts)
  keeps it
- **The format number stays.** No reader reads a row differently

## How it was decided
<!-- record -->

- Three reviews read the proposal independently, each writing its
  criteria before reading the proposal's: a paper referee, a user of the
  pangenome tools who ran vg and odgi pipelines end to end, and an
  implementer who built a prototype
- **What was taken** is the proposal's set M, today's meanings checked
  against the line, with its set T's ruling on two-field names, the order
  of R5 turned round, and a fourth field and a bracket summed
- **The reviews split 2 to 1 on R1, and it keeps.** Refusing a fourth
  field above 0 refuses the P lines vg writes of a clipped
  Minigraph-Cactus GBZ, `H#1#c#100`, which read right before this change,
  and whose W form the tool accepts with the same number in its start
  column. What stands against keeping is the VCF phase block, which is
  the stated limit
- **They split 2 to 1 on R3's base, and it is 0-based only.** Reading
  `b − a + 1 == bp` as a 1-based range would give `DRB1-3123.gfa` its
  chromosome coordinates, but it infers a second convention from
  arithmetic alone
- **The order of R5 changed in review.** The proposal read a bracket
  first and a colon range last. The tool user's pipelines put odgi's cut
  outermost on vg's names, `H#1#c#0[100-114]:6-14`, which that order
  left as a path of its own from 6
  ([19 names against their pipelines](../walks-container/dialect/evidence/pipeline-names.md))
- **The sum came from the prototype.** The proposal refused a fourth
  field above 0 beside a bracket as two starts. `vg chunk` of a clipped
  GBZ writes exactly that, and the line lies at their sum
  ([run](../walks-container/dialect/evidence/vg-chunk-of-clipped-gbz.txt))

## Evidence
<!-- record -->

- **What the reading before this wrote,** main at 36a190d, from the
  proposal's runs
  ([public graphs](../walks-container/dialect/evidence/writer-today-public-graphs.txt)):
  - **Off by one on odgi's test graph `DRB1-3123.gfa`.** Its 12 names
    are 1-based and inclusive, `end − start + 1` being each line's bp
    ([lengths](../walks-container/dialect/evidence/colon-range-lengths.txt)),
    and the reference `gi|568815592:32578768-32589835` was placed from
    32,578,768 with a `#hole` up to there, one base past where it lies
  - **Two paths for one contig.** A clipped haplotype's two W lines leave
    `vg convert -gfW` as `H#1#c#0` and `H#1#c#0[100-106]`, which read as
    `H#1#c` from 0 and `H#1#c#0` from 100, with no departure record
    between them; the W lines and vg's GBZ P form gave one path and the
    record
    ([vg-clipped-w.gfa](../walks-container/dialect/vg-clipped-w.gfa),
    [vg-clipped-gfw-p.gfa](../walks-container/dialect/vg-clipped-gfw-p.gfa))
  - **Phantom haplotypes.** A `sample#contig` path was listed whole, so
    odgi's `chr6.C4.gfa` built on `grch38` listed `#haplotype chm13#chr6`
    beside its `sample#haplotype` lines, and a whole-genome graph named
    that way would list a haplotype per contig
  - **A stated end the steps contradict was accepted,** `H#1#c[5-900]`
    of 16 bp from 5, where `W H 1 c 5 900` is refused; and `[5]` alone
    gave a path and a `#haplotype` line with no name
- **Against the checks this ADR adds,** the writer this change lands on,
  main at 17b5bc5, fails 28 of the 53
  [dialect fixtures](../walks-container/dialect/expected.tsv)
  ([run](../walks-container/dialect/results/mutants.txt)). The
  implementer's review counted 14 of the 44 GFAs it ran; its table stayed
  with the review and was not rerun
- **One file from each form of a graph.** vg's W lines, its P lines
  through a GBZ, through `vg convert -gfW` and mixed, and the same with
  the P lines before the S lines, give one walk file and directory byte
  for byte; so do `vg chunk`'s P form, its mixed form and the W lines
  written by hand for the same stretch, vg's two forms of a chunk of a
  pggb-like graph, and odgi's cuts of vg's two P forms against their W
  lines. vg's VCF-phased blocks are refused in both forms
  ([tests/dialect.rs](../../tests/dialect.rs),
  [check-dialect.sh](../../scripts/check-dialect.sh))
- **Each check fails on a broken writer**
  ([run](../walks-container/dialect/results/mutants.txt), by
  [mutants.sh](../walks-container/dialect/scripts/mutants.sh)). Every
  mutant fails the table's unit test, the dialect test, a test of
  `tests/walks.rs` and `check-dialect.sh`:

  | Broken writer | Fixtures of check-dialect.sh it fails | What catches it there |
  | --- | --- | --- |
  | no end check | 3 | the builds that should be refused |
  | a `:a-b` read beneath a fourth field | 1 | the lines its rows name, `walks-truth.py rebuild`, its W twin |
  | a fourth field dropped, not added | 9 | the same, and two graphs refused for lines that now collide |
  | a fourth field not added to a bracket | 3 | the lines its rows name, `walks-truth.py rebuild`, its W twin |
  | two-field paths listed whole | 5 | the `#haplotype` lines, `claims7.py`, `spec8.py` |
  | main's writer at 17b5bc5 | 28 | each of the above |

- **Each reader of P line names is held to one table.** The Rust unit
  test, `audit7.py`, `spec8.py`, `claims7.py`, `walks-truth.py` and
  `graph-walks-rebuild.mjs` read
  [p-names.tsv](../walks-container/dialect/p-names.tsv); with a row of it
  changed, each reader of the changed column exits non-zero (the same
  run)
- **No byte of a file built before moves**
  ([fixtures](../walks-container/dialect/results/same-bytes-fixtures.txt),
  [pggb chrY](../walks-container/dialect/results/same-bytes-pggbY.txt),
  by [same-bytes.sh](../walks-container/dialect/scripts/same-bytes.sh)):
  - every GFA of `tests/data`, the E. coli pggb subgraph and its
    `:start-end` names among them, as walk files and as an index in both
    formats: the same files from main's writer at 17b5bc5 and from this
    one
  - HPRC release 2's pggb chrY, 1,053 P lines: the walk files for GRCh38
    and for CHM13, their directories, and the node and link index in
    both formats, identical
- **What the graphs at hand hold**
  ([census](../walks-container/dialect/results/census.txt), by
  [census.py](../walks-container/dialect/scripts/census.py)):
  - the two P-line graphs at hand, HPRC release 2's pggb chrY and the
    E. coli pggb graph hosted as `ecoli_pggb`, name every path
    `sample#hap#contig`, none twice. Neither has a suffix, a fourth field
    or a two-field name, so both read as they did
  - the base-level Minigraph-Cactus GRCh38 graph, the source of the
    hosted GRCh38 walk file, has W lines and no P line, and no two lines
    of a path overlap or share a start; an E. coli Minigraph-Cactus graph
    at hand likewise
  - the rGFAs behind the hosted `ecoli_minigraph` and Arabidopsis indexes
    have no path line; an rGFA's index comes from its tags
  - not found on ada: the rGFAs behind the hosted HPRC, bovine and mouse
    indexes, the Minigraph-Cactus CHM13 graph, and the graph behind
    `ecoli_cactus`, which is lost. Of the hosted indexes, `ecoli_pggb` and
    `ecoli_cactus` alone list samples, as an index placed by path lines
    does ([samples per hosted index](../placement/hosted-duplicate-links.txt))

## Alternatives rejected
<!-- record -->

- **Set A, today's reading:** the first suffix that parses, unchecked.
  It wrote the false outputs under Evidence
- **Set T, tool conventions:** a fourth field above 0 refused, as a phase
  block that isn't an offset. It refuses vg's P form of a clipped GBZ
  while accepting the W form of the same paths, and leaves the VCF hole
  open through W lines all the same
- **Set O, opaque names:** no suffix read, every P line its own path
  from 0. It can state no false coordinate, but a region cut by
  `odgi extract` has no route to reference coordinates (odgi writes no W
  lines and vg doesn't read `:start-end`), every piece of a contig
  becomes a path with no departure record between them, and all 90 lines
  of odgi's `chr6.C4.gfa` change
- **A 1-based `:start-end`,** read where `b − a + 1` is the bp: a second
  convention inferred from a coincidence of lengths
- **Sniffing the header** for the tool that wrote the file: the GFAs here
  carry `VN:Z:` and sometimes `RS:Z:`, neither names a tool, and a name
  passes through several tools
- **A command-line option** saying what a fourth field or a range means:
  it moves the question to the user, and one GFA would give two files

## Consequences
<!-- record -->

- A walk file's `path` is final. A reader that parses a start or a
  haplotype out of a `path` its own way now disagrees with the file
- **Consumers, not changed here.** Each reads a haplotype or a start out
  of a path name its own way:
  - graph-walks, `src/walkDepartures.ts`: the reference's haplotype
    falls back to its whole name and a path's to its sample, so another
    contig of a two-field reference isn't taken for the reference's. It
    needs one
    exported helper for what a path is listed under, `sample#haplotype`
    of three fields or more and the sample of fewer, used at both, and
    in `walksKept` of `src/walkRows.ts`
  - the plugin, `src/WalkTabixSyntenyAdapter/WalkTabixSyntenyAdapter.ts`:
    its `haplotypeOf` falls back to the whole name, where the header now
    lists the sample. It needs the same helper
  - bandage-core, `pathOrigin` in `src/pathAnchoring.ts`: it strips any
    `:a-b` and `[s-e]` unchecked. On a name from a walk file it has to
    stop, since `fragStart` already holds the start and a `:a-b` left in
    a `path` is part of the name; on a GFA's own P lines it should read
    by this rule, with the line's bp
- The node and link index refuses GFAs it built before: a P line with a
  stated end its steps contradict or with no name left, and lines of one
  path that overlap or share a start
- `--reference K12#1#chr:0-8` no longer matches a path written
  `K12#1#chr`; it matches a path written with that range
- The reading can accept more after the freeze. It can't re-mean a name
  it reads today without changing the rows of graphs already built
