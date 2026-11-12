# How the walk format reads P line names: a proposal

- **Status:** decided by [ADR 0014](../../../adr/0014-p-line-names.md),
  which took none of the four sets below whole. Kept as the record of the
  question and the survey: a proposal for three independent reviewers,
  2026-11-12, written before anything was implemented. Of the evidence it
  names, the tool transcripts are beside this file and the rest stayed in
  the session's scratch directory
- **Decide by:** the paper's format freeze, about 2026-11-18
- **Answers:** `docs/open-problems.md`, "P line names" and the P line items
  of "Inputs the writer accepts and shouldn't"
- **Repo state measured:** gfa-to-tabix 36a190d, its `target/release` binary
  (built after the last change under `src/`); vg v1.69.0; odgi v0.9.4
- **FORMAT CHANGE ALARM.** Two candidates below change what `path`,
  `fragStart` and `#haplotype` hold for some P line inputs (claims C51 and
  C158), so [ADR 0011](../../../adr/0011-format-7-is-frozen.md)'s
  rules apply: burden, scope, briefs, checker evidence. No candidate changes
  the row grammar, a W line's reading, or a byte of a hosted walk file
- **For whoever briefs the reviewers:** everything above the line
  "Recommendation" is question, criteria and data. The recommendation is the
  proposer's framing and can be cut from a decider's brief

## The question

- A P line carries one name. The walk file needs from it a `path`, a
  `fragStart` on that path's sequence, and the `#haplotype` the path is
  listed under. Which parts of a name may the writer read as a coordinate or
  a haplotype, and what does it do with the rest?
- Six rulings are separable, and each has "keep today's reading" as a
  candidate:
  - **R1** a fourth field, `sample#hap#contig#N`
  - **R2** a two-field name, `sample#contig`
  - **R3** a `:start-end` suffix
  - **R4** a `[start]` or `[start-end]` suffix, and its stated end
  - **R5** suffixes in combination, and a name that is only a suffix
  - **R6** a P line with GFA 1.2 `;` jumps

## Criteria, written before the candidates were compared

- **K1 True.** Every `fragStart`, `hapOffset`, `#hole` and extent a file
  states is a 0-based offset on the sequence `path` names, read from a field
  whose primary source defines it as that. None comes from a field its own
  tool documents as something else
- **K2 Determined.** `path`, `fragStart` and `#haplotype` are a function of
  the P line alone: its name and its steps' lengths. No option, no
  dependence on other lines, except the refusal of two lines that collide
- **K3 pggb works.** A pggb graph is accepted, and so is what vg and odgi
  make of it (`vg convert`, `vg chunk`, `odgi extract`)
- **K4 One graph, one reading.** The same paths written as W lines and as
  P lines give the same `path` and `fragStart`, or the P form is refused.
  Never two readings that both succeed
- **K5 Disjoint.** Lines that share a `path` cover disjoint stretches, or
  the GFA is refused. This is what the `hapBp` work on another branch joins
  on, and no candidate may weaken it
- **K6 Checkable.** A checker holding only the GFA can recompute each rule,
  and each rule has a fixture that a broken writer fails
- **K7 Burden** (ADR 0011). A change has to beat shipping unchanged: hosted
  bytes unchanged, fewest rules, and where the evidence is mixed the reading
  stays

## What each tool writes and means

Sources are the default branches on 2026-11-12, at the commits in
`sources/fetched-commits.txt`; copies are in `sources/`.

| Tool | P line names it writes | W lines | What it says the parts mean |
|---|---|---|---|
| PanSN spec | `sample#hap#contig` only | n/a | "`haplotype_id := number`"; no fourth field, no range |
| pggb | the FASTA record names, unchanged | none | README recommends PanSN; nothing more |
| odgi (`extract`) | `name:start-end` appended to the name it was given | writes none, and drops them on read | "(0-based coordinates)"; end exclusive |
| vg | `sample#hap#contig#N`, `…[start]`, `…[start-end]`, both together | default for any path with a sample | fourth field is a **phase block**; brackets are a **subrange**, 0-based, end exclusive and optional |
| gbwtgraph (inside vg) | `sample#hap#contig[count]` | start column = `count` | `count` is the W line's start on the way in, a phase block number from a VCF |
| Minigraph-Cactus | none | all paths | reads `:start-end` in its *inputs* as **1-based, inclusive** |
| GFA 1.1 spec | `PathName`, an opaque string | `SeqStart`, `SeqEnd` | "BED-like half-close-half-open"; "For a haploid sample, `HapIndex` takes 0" |

- **PanSN** ([README](https://github.com/pangenome/PanSN-spec/blob/master/README.md)):
  - "`[sample_name][delim][haplotype_id][delim][contig_or_scaffold_name]`"
  - "our output will be a GFA file whose paths (`P`-lines) encode individual
    records in the FASTA"
  - Two-field names and any suffix are outside it
- **vg, the fourth field**
  ([wiki, Path Metadata Model](https://github.com/vgteam/vg/wiki/Path-Metadata-Model);
  [libhandlegraph `path_metadata.hpp`](https://github.com/vgteam/libhandlegraph/blob/master/src/include/handlegraph/path_metadata.hpp),
  [`path_metadata.cpp`](https://github.com/vgteam/libhandlegraph/blob/master/src/path_metadata.cpp)):
  - "A **phase block**. For haplotype paths, this is used when a contig is
    not phased through end to end. In that case, there will be multiple
    haplotype paths on the contig with different phase block values, with
    the paths cut apart where phasing is unknown."
  - "Phase block identifier: … Must be unique within a sample, locus, and
    haplotype. **May be a number or a start coordinate.**" (`path_metadata.hpp:46-49`)
  - The name grammar is one regex, `path_metadata.cpp:35`:
    `([^[#]*)(?:#(\d+))?(?:#([^[#]*))?(?:#(\d+))?(?:\[(\d+)(?:-(\d+))?\])?`
  - Its own examples include two-field names: "`GRCh38#chrM` (a
    reference)", "`CHM13#chr12[300-400]` (part of a reference)",
    "`NA29239#1#chr1#0` (a haplotype)" (`path_metadata.cpp:18-24`)
- **vg, the subrange** (same wiki page): "A **subrange**, which has a start
  and an optional end coordinate. Positions are 0-based, start-inclusive,
  and end-exclusive. … This field is only used for reference and generic
  paths; it is always unset for haplotype paths. For haplotype paths, the
  *phase block* field does much the same thing and should be used instead."
- **vg reading a GFA** ([`src/algorithms/gfa_to_handle.cpp`](https://github.com/vgteam/vg/blob/master/src/algorithms/gfa_to_handle.cpp)):
  - A three-field P line becomes a haplotype with phase block 0: "Assign a
    phase block if none is specified, since haplotypes need one." (`:163`)
  - A W line: "GFA doesn't really encode phase blocks. Always use the 0th
    one." (`:242`), and its start becomes a subrange, dropped when 0 (`:250-254`)
- **vg writing a GFA** ([`src/gfa.cpp`](https://github.com/vgteam/vg/blob/master/src/gfa.cpp)):
  - "We can't represent nonzero phase blocks in W lines in a way that
    round-trips, so make them P lines." (`:183`)
  - "Write out a W line for a path. Uses a map to keep track of **fake
    offset ranges** used to distinguish multiple phase blocks" (`:14-16`)
  - "If phase blocks are big numbers that came from coordinates, and we can,
    we want to just pass them through in the GFA offset position.
    `start_offset = phase_block;`" (`:242-244`)
  - A wrong stated end is overridden, not refused: "warning: incorrect end
    offset … extracted from from path name …, using … instead", the value
    used being start plus the path's length (`:227-229`)
- **gbwtgraph** ([`src/gfa.cpp`](https://github.com/jltsiren/gbwtgraph/blob/master/src/gfa.cpp)):
  - A W line is written with `path_name.count` as its start and
    `path_name.count + length` as its end (`write_walk`, `:1828-1829`)
  - "If we're actually a haplotype path, vg would expect a
    **not-quite-panSN '#' separator**." (`:1672-1674`)
- **odgi** ([`src/algorithms/subgraph/extract.cpp:47-53`](https://github.com/pangenome/odgi/blob/master/src/algorithms/subgraph/extract.cpp)):
  `out_name = path_name + ":" + std::to_string(offset)`, then
  `"-" + std::to_string(end_offset)` when the end is past the offset, where
  the offset is the bp walked before the first kept step and the end is
  the bp walked through the last. `odgi extract --help`: "(0-based
  coordinates)". odgi's own tutorial lists `grch38#chr6:29722774-33089734`
  and `chm13#chr6:29595119-32911317`, cut from a graph whose URL holds
  `2021_05_06_pggb`
  ([tutorial](https://odgi.readthedocs.io/en/latest/rst/tutorials/extract_selected_loci.html))
- **Minigraph-Cactus** ([`doc/pangenome.md`](https://github.com/ComparativeGenomicsToolkit/cactus/blob/master/doc/pangenome.md)):
  - "`vg` can sometimes output paths with names like `HG002#0#chr1#0`. This
    will be interpreted as `0` and almost surely lead to trouble." (`:133`)
  - "Path subranges denoted by suffixes of the form `:start-end` (1-based,
    inclusive) are now supported (v2.8.1)." (`:134`)
  - "Q: My tools can't read GFA 1.1 and W-lines. A: … you can use
    `vg convert -gfW` to convert from GFA 1.1 to GFA 1.0." (`:1335-1337`)
- **GFA 1** ([`GFA1.md`](https://github.com/GFA-spec/GFA-spec/blob/master/GFA1.md)):
  `SeqStart` and `SeqEnd` are `\*|[0-9]+`, "Optional"; "For two W-lines with
  the same (`SampleId`,`HapIndex`,`SeqId`), their [`SeqSart`,`SeqEnd`) should
  have no overlaps"; a `;` in a P line's `SegmentNames` marks "the usage of
  a jump connection (defined by `J`-line), rather than a link connection"

### What the tools do, run here on tiny graphs

Outputs are in `evidence/tools/`.

- **The same W line gets two different P names from vg**
  (`vg-mc-roundtrip.txt`). `W H 1 c 100 106` becomes:
  - `H#1#c#100` through a GBZ (`vg gbwt -G`, then `vg convert -f -W`): the
    fourth field **is** the start
  - `H#1#c#0[100-106]` through `vg convert -gfW`, the route Cactus's FAQ
    gives: the fourth field is 0 and the start is in the brackets
- **A VCF-phased haplotype's fourth field is a counter**
  (`vg-vcf-phase-blocks.txt`). One unphased genotype among four cuts each
  haplotype into three paths, `S1#0#chr1#0`, `#1`, `#2`, which start at 0, 20 and 50 on
  chr1. vg writes them as `W S1 0 chr1 0 49`, `W S1 0 chr1 1 60` and
  `W S1 0 chr1 2 72`: the counter in the start column, and stretches that
  overlap
- **vg adds `#0` to every three-field P line it reads**
  (`vg-metadata.txt`, `vg-chunk-subranges.txt`): pggb's `H#1#c` leaves
  `vg convert -f -W` as `H#1#c#0`, and leaves `vg chunk` as `H#1#c#0[10-16]`
- **vg reads `sample#contig` as a sample and a contig with no haplotype**,
  writes it back unchanged as a P line, and as `W sample 0 contig` with
  `RS:Z:sample` in the header (`vg-metadata.txt`)
- **vg does not know `:start-end`:** `K#1#c:5-21` comes back as
  `K#1#c:5-21#0`, contig `c:5-21`
- **odgi names** (`odgi-names.txt`): `odgi extract` gives `H#1#c:6-10` for
  the stretch 6-10, 0-based with the end exclusive; a second extract gives
  `H#1#c:6-10:0-4`, an offset inside the first; a W-line GFA built with
  `odgi build` holds 0 paths

## What real graphs contain

| Graph | Where | Path lines | Name shapes |
|---|---|---|---|
| HPRC release 2 pggb chrY | `~/work/pggb/chrY.gfa`, the same 7,695,644,148 bytes as ada's `pggbY.gfa` | 1,053 P | all `sample#integer#contig`; 124 samples; no `:`, `[`, fourth field or repeat |
| E. coli pggb rebuild | ada `~/data/ecoli-pggb-rebuild-2026-10-11` | 5 P | all `sample#1#chr` |
| Minigraph-Cactus W-line graphs | ada `~/work/genome7/diag/W-HG00097-2-CM094088.1.gfa`, `~/work/paf-vs-minimap2/nodes/grch38_walks.gfa.gz` | 17 W, 195 W | starts above 0 in the first, all 0 in the second |
| maize NAM chr8 | `~/work/maize_nam/chr8_450/out/maize_nam_chr8.full.gfa.gz` | 26 W | all start at 0 |
| C. elegans graphs | ada `~/data/celegans-pg`, `chrI.gfa` and `celegans-pg.sv.gfa.gz` | none | no P or W line |
| odgi's test `chr6.C4.gfa` | [odgi `test/`](https://github.com/pangenome/odgi/tree/master/test) | 90 P | 88 `sample#hap#contig:start-end`, 2 `sample#contig:start-end` (`grch38#chr6`, `chm13#chr6`) |
| odgi's test `DRB1-3123.gfa` | same | 12 P | all `name:start-end`, no `#` |
| odgi's test `LPA.gfa` | same | 13 P | all one field, no suffix |

- No graph on either machine has a P line with a fourth field or a bracket.
  Those shapes are evidenced by running vg, not by a graph in use
- **The `:start-end` suffix means two things in the public graphs**
  (`evidence/colon-range-lengths.txt`):
  - `chr6.C4.gfa`: `end − start` equals the path's bp on 90 of 90 lines, so
    0-based with the end exclusive, as odgi writes
  - `DRB1-3123.gfa`: `end − start + 1` equals the path's bp on 12 of 12, so
    1-based and inclusive, as a FASTA record cut by region is named
- The counts are in `evidence/shapes-local.txt` and `evidence/shapes-ada.txt`

## What the writer does today

- **The reading** is `split_path_name`, `src/gfa.rs:111-136`, called for a
  walk file at `src/walks.rs:129`. It tries three suffixes in turn and stops
  at the first that parses:
  - `[start]` or `[start-end]` at the end: `fragStart` is `start`; the end
    is never read (`:113-121`)
  - exactly three `#` and digits after the last: `fragStart` is that
    number (`:122-127`)
  - `:start-end` after the last `:`: `fragStart` is `start`; the end must
    be digits and is otherwise unread (`:128-134`)
  - else the whole name from 0
- **`sample`,** which `--refs` matches, is the name up to its first `#`
  (`src/walks.rs:131`). **`#haplotype`** is the name up to its second `#`,
  or whole (`haplotype`, `src/walks.rs:932-937`)
- **A P line has no end to check** (`end: None`, `src/walks.rs:134`), so
  `record` (`src/walks.rs:495-510`) refuses only a W line whose end column
  disagrees with its steps
- **Two lines of one path:** `link_records` (`src/walks.rs:1474-1496`)
  sorts every line with steps by `path` and start, P and W together, and
  refuses "two lines starting at N" and "the line covering a-b overlaps the
  one covering c-d". So K5 holds today whatever the name rule, and holds
  under every candidate: a candidate changes which lines share a `path`,
  never whether they may overlap
- **The same function serves the node and link index** (`src/gfa.rs:262`,
  and `--reference` at `src/place.rs:201`), so a writer change either
  touches both outputs or forks the reading
- **A model of today's reading agrees with the binary** on 50 of 50 runs,
  rows and refusals (`rulings.py`, `check_model.py`,
  `evidence/model-of-today-vs-writer.txt`). The candidate columns below
  come from that model; no candidate was built

What today's binary makes of each shape, from
`evidence/writer-today.txt`, `writer-today-vg-output.txt` and
`writer-today-public-graphs.txt`:

- **A fourth field is an offset.** `H#1#c#1` is `H#1#c` from 1
- **A VCF-phased graph from vg is refused, for a reason that isn't the
  cause:** "path S1#0#chr1: the line covering 0-49 overlaps the one covering
  1-60", on the P form and the W form alike. Where the blocks present don't
  collide it is accepted: `S1#0#chr1#0` of 6 bp and `S1#0#chr1#7` are
  written as one contig's stretches at 0 and 7
  (`gfa/05-phase-blocks-short.gfa`)
- **One graph, two walk files.** The clipped W-line graph and its GBZ P
  form give the same rows (same md5,
  `evidence/same-graph-three-routes.md5.txt`). Its `vg convert -gfW` form
  gives `H#1#c` from 0 and `H#1#c#0` from 100, two paths for one contig, and
  loses the departure record between them. A pggb-like graph cut by
  `vg chunk` gives the reference sequence `R#0#chr1#0` as P lines and
  `R#0#chr1` as W lines
- **A stated end is ignored:** `H#1#c[5-900]`, `H#1#c:5-900` and
  `H#1#c[21-5]` are placed at 5, 5 and 21
- **`DRB1-3123.gfa` is placed by a range its steps don't span:** the
  reference is `gi|568815592` from 32,578,768 with `#hole … 0 32578768`,
  and all 12 lines likewise
- **A two-field name is its own haplotype:** `chr6.C4.gfa` with
  `--refs grch38` lists `#haplotype chm13#chr6` beside 88 `sample#hap`
  lines. A whole-genome graph would list one per contig
- **A suffix alone leaves an empty `path` and an empty `#haplotype`:**
  `[5]`, `:5-21`
- **`H#1#c:5-21#0`,** vg's form of an odgi extract, is `H#1#c:5-21` from 0,
  where the odgi form is `H#1#c` from 5
- **A `;` jump is refused** as "`--walks` needs integer node ids below
  2^31 …; 1+;3 is not one"
- **Beside the question:** a W line with `*` for its start, which the GFA
  spec allows, is refused as "W line start: * is not a non-negative
  integer" (`evidence/writer-today-w-star-and-jump.txt`)

## The rulings and their candidates

- **R1, a fourth field**
  - **1a keep:** digits after a third `#` are `fragStart`
  - **1b:** `#0` is dropped, since vg adds it to every haplotype; any other
    integer there is refused, since the name doesn't say whether it is a
    counter or a start
  - **1c:** `#0` is dropped; any other stays in the name, a path of its own
    from 0, as vg models a phase block
  - **1e:** never read; the name is whole
  - Set aside: an option naming which meaning holds. It moves the question
    to the user and breaks K2
- **R2, two fields**
  - **2a keep:** the whole name is its `#haplotype`
  - **2b:** `#haplotype` is the sample, the name up to its only `#`. This is
    vg's reading, and graph-walks' (`panSNContig`, `panSNHaplotype`,
    `panSNMatchesPrefix`, `~/src/graph-walks/src/util.ts:135-165`)
  - **2c:** the path becomes `sample#0#contig`, as vg writes its W line
  - **2d:** refused
- **R3, `:start-end`**
  - **3a keep:** 0-based start, end unread
  - **3b:** read as 0-based exactly when `end − start` is the line's bp;
    otherwise it is part of the name, from 0
  - **3c:** 3b, and also 1-based when `end − start + 1` is the line's bp,
    giving `start − 1`
  - **3d:** refused when the steps don't span it
  - **3e:** never read
- **R4, `[start]` and `[start-end]`**
  - **4a keep:** end unread, which is also what vg does, with a warning
  - **4b:** refused when a stated end isn't `start` plus the line's bp, as
    a W line is (C18)
  - **4c:** part of the name when the end disagrees
  - **4e:** never read
- **R5, combinations**
  - **5a keep:** first suffix that parses, nothing under it
  - **5b:** in order: brackets, then the fourth field of what remains, then
    `:start-end` of what remains unless the brackets gave the start. A
    suffix is read only when a name is left before it
- **R6, `;` jumps**
  - **6a keep, and say so:** refused in every candidate. A jump joins two
    segments with no link, at a distance the J line may not give, so no
    offset after it is determined. No pangenome builder surveyed writes
    one. Only the message and a spec sentence change

Four coherent sets are compared below. A reviewer can also rule on R1 to
R4 one at a time.

| Set | R1 | R2 | R3 | R4 | R5 |
|---|---|---|---|---|---|
| **A, today** | 1a | 2a | 3a | 4a | 5a |
| **M, mended:** today's meanings, checked | 1a | 2a | 3b | 4b | 5b |
| **T, tool conventions:** a part is read only as the tool that writes it defines it | 1b | 2b | 3b | 4b | 5b |
| **O, opaque:** a P line's name is its path, from 0 | 1e | 2a | 3e | 4e | none |

### What each name shape maps to

`path` @`fragStart`; "listed under" is given where `#haplotype` differs
from the name up to its second `#`. bp is the line's length. From
`shape_table.py`; the long form is `evidence/shape-table.md`.

| P line name | bp | where it comes from | A today | M mended | T tools | O opaque |
|---|---|---|---|---|---|---|
| `H#1#c` | 16 | pggb; PanSN | `H#1#c` @0 | `H#1#c` @0 | `H#1#c` @0 | `H#1#c` @0 |
| `H#1#c#0` | 16 | vg on any three-field P line | `H#1#c` @0 | `H#1#c` @0 | `H#1#c` @0 | `H#1#c#0` @0 |
| `H#1#c#100` | 6 | vg -W on a GBZ built from a W line starting at 100 | `H#1#c` @100 | `H#1#c` @100 | refused | `H#1#c#100` @0 |
| `S1#0#chr1#2` | 70 | vg, third phase block of a VCF-phased haplotype | `S1#0#chr1` @2 | `S1#0#chr1` @2 | refused | `S1#0#chr1#2` @0 |
| `H#1#c#007` | 16 | made up | `H#1#c` @7 | `H#1#c` @7 | refused | `H#1#c#007` @0 |
| `H#1#c#12345678901234567890` | 16 | made up, 20 digits | `H#1#c#12345678901234567890` @0 | `H#1#c#12345678901234567890` @0 | refused | `H#1#c#12345678901234567890` @0 |
| `H#1#c[100-116]` | 16 | vg subrange | `H#1#c` @100 | `H#1#c` @100 | `H#1#c` @100 | `H#1#c[100-116]` @0 |
| `H#1#c[100]` | 16 | vg subrange, no end | `H#1#c` @100 | `H#1#c` @100 | `H#1#c` @100 | `H#1#c[100]` @0 |
| `H#1#c[100-900]` | 16 | stated end wrong | `H#1#c` @100 | refused | refused | `H#1#c[100-900]` @0 |
| `H#1#c[116-100]` | 16 | stated end below start | `H#1#c` @116 | refused | refused | `H#1#c[116-100]` @0 |
| `H#1#c#0[100-116]` | 16 | vg chunk; vg convert -gfW on a clipped W line | `H#1#c#0` @100 | `H#1#c` @100 | `H#1#c` @100 | `H#1#c#0[100-116]` @0 |
| `M#1#c#2[40-56]` | 16 | vg, phase block and subrange | `M#1#c#2` @40 | refused | refused | `M#1#c#2[40-56]` @0 |
| `H#1#c:5-21` | 16 | odgi extract, 0-based, end = start + bp | `H#1#c` @5 | `H#1#c` @5 | `H#1#c` @5 | `H#1#c:5-21` @0 |
| `H#1#c:6-21` | 16 | region name, 1-based closed, end = start + bp - 1 | `H#1#c` @6 | `H#1#c:6-21` @0 | `H#1#c:6-21` @0 | `H#1#c:6-21` @0 |
| `H#1#c:5-900` | 16 | range the steps do not span | `H#1#c` @5 | `H#1#c:5-900` @0 | `H#1#c:5-900` @0 | `H#1#c:5-900` @0 |
| `H#1#c:5-21:3-13` | 10 | odgi extract of an odgi extract | `H#1#c:5-21` @3 | `H#1#c:5-21` @3 | `H#1#c:5-21` @3 | `H#1#c:5-21:3-13` @0 |
| `H#1#c:5` | 16 | odgi, no end | `H#1#c:5` @0 | `H#1#c:5` @0 | `H#1#c:5` @0 | `H#1#c:5` @0 |
| `H#1#c:5-21#0` | 16 | vg on an odgi extract | `H#1#c:5-21` @0 | `H#1#c` @5 | `H#1#c` @5 | `H#1#c:5-21#0` @0 |
| `H#1#HLA:DRB1` | 16 | colon in a contig name | `H#1#HLA:DRB1` @0 | `H#1#HLA:DRB1` @0 | `H#1#HLA:DRB1` @0 | `H#1#HLA:DRB1` @0 |
| `H#c` | 16 | sample#contig, as in odgi's chr6 graphs and vg's reference examples | `H#c` @0 | `H#c` @0 | `H#c` @0, listed under `H` | `H#c` @0 |
| `H#c:5-21` | 16 | sample#contig, odgi extract | `H#c` @5 | `H#c` @5 | `H#c` @5, listed under `H` | `H#c:5-21` @0 |
| `H#5` | 16 | two fields, second an integer | `H#5` @0 | `H#5` @0 | `H#5` @0, listed under `H` | `H#5` @0 |
| `plain` | 16 | no # | `plain` @0 | `plain` @0 | `plain` @0 | `plain` @0 |
| `gi\|568815592:32578768-32589835` | 11068 | DRB1-3123.gfa | `gi\|568815592` @32578768 | `gi\|568815592:32578768-32589835` @0 | `gi\|568815592:32578768-32589835` @0 | `gi\|568815592:32578768-32589835` @0 |
| `A#b#c#d` | 16 | four fields, last not an integer | `A#b#c#d` @0 | `A#b#c#d` @0 | `A#b#c#d` @0 | `A#b#c#d` @0 |
| `C#1#c#3#4` | 16 | five fields | `C#1#c#3#4` @0 | `C#1#c#3#4` @0 | `C#1#c#3#4` @0 | `C#1#c#3#4` @0 |
| `H#mat#c` | 16 | haplotype not an integer | `H#mat#c` @0 | `H#mat#c` @0 | `H#mat#c` @0 | `H#mat#c` @0 |
| `H#1#` | 16 | empty contig | `H#1#` @0 | `H#1#` @0 | `H#1#` @0 | `H#1#` @0 |
| `[5]` | 16 | suffix alone | `(empty)` @5 | `[5]` @0 | `[5]` @0 | `[5]` @0 |
| `:5-21` | 16 | suffix alone | `(empty)` @5 | `:5-21` @0 | `:5-21` @0 | `:5-21` @0 |
| `#1#c` | 16 | starts with # | refused (starts with `#`) | refused (starts with `#`) | refused (starts with `#`) | refused (starts with `#`) |

### Which lines change on the graphs at hand

How many P lines each set reads differently from today, from
`census.py` (`evidence/census.tsv`). A W line is read the same in every
set, so every Minigraph-Cactus graph, and with it every hosted walk file, is
untouched.

| Names | P lines | M | T | O |
|---|---|---|---|---|
| pggb chrY, HPRC release 2 | 1,053 | 0 | 0 | 0 |
| pggb E. coli | 5 | 0 | 0 | 0 |
| odgi test `LPA.gfa` | 13 | 0 | 0 | 0 |
| odgi test `chr6.C4.gfa` | 90 | 0 | 0 rows; 2 names listed under `chm13` and `grch38` | 90: `path` keeps its `:start-end`, from 0 |
| odgi test `DRB1-3123.gfa` | 12 | 12: `path` keeps its `:start-end`, from 0 | 12, the same | 12, the same |
| vg, clipped W lines through a GBZ, `-W` | 4 | 0 | refused: `H#1#c#100`, `R2#0#chrZ#50` | 3 |
| vg, clipped W lines through `vg convert -gfW` | 4 | 2: now one contig, as the W form | 2, the same | 3 |
| vg, pggb-like graph cut by `vg chunk`, `-W` | 2 | 2: `#0` gone, as the W form | 2, the same | 2 |
| vg, VCF-phased, `-W` | 6 | refused, overlap, as today | refused, 4 lines with a fourth field of 1 or 2 | accepted: 6 paths from 0 |

- pggb chrY's 1,053 names and E. coli's 5 read the same in every set, so the
  writer's input is the same and so are its bytes. That is a deduction from
  the names; the rebuild and `cmp` are listed under checks
- `DRB1-3123.gfa` under M, T and O: `--refs` has to give the whole name,
  `gi|568815592:32578768-32589835`, and the file is in that record's own
  coordinates. Under 3c it would stay `gi|568815592`, from 32,578,767

### The same paths as W lines and as P lines

vg wrote each pair from one graph. From `pw_equivalence.py`
(`evidence/p-vs-w-forms.tsv`).

| Pair | A | M | T | O |
|---|---|---|---|---|
| clipped W lines, through a GBZ | same rows | same rows | P refused | different rows |
| clipped W lines, `vg convert -gf` | **different rows** | same rows | same rows | different rows |
| pggb-like graph, `vg chunk` | **different rows** | same rows | same rows | different rows |
| VCF-phased haplotypes | both refused | both refused | both refused | W refused, P read |

### Against the criteria

| | A, today | M, mended | T, tool conventions | O, opaque |
|---|---|---|---|---|
| K1 true | no: three measured cases | in part: the fourth field is a start where it came from a W line, a counter where it came from a VCF | yes for P lines | yes |
| K2 determined | yes | yes | yes | yes |
| K3 pggb works | accepted; `vg chunk` output gets another sequence name | yes | yes | accepted; an odgi cut has no reference coordinates |
| K4 one reading | no: 2 of 4 pairs give different rows | yes: 3 same, 1 refused both ways | yes: 2 same, 1 refused both ways, 1 refused as P only | no, though the names show it |
| K5 disjoint | yes | yes | yes | yes, each line its own path |
| K6 checkable | no stated end is checked | yes | yes | nothing to check |
| K7 burden | the baseline | hosted bytes same; same rules, one order | hosted bytes same; refuses one vg form that reads right today | hosted bytes same; three rules fewer; 90 of 90 `chr6.C4.gfa` lines change |

### A, keep today's reading

- **Strongest case:** nothing changes, no hosted byte, no fixture. The
  fourth field as a start is what vg itself writes into a W line's start
  column, so a P form reads as vg's W form of the same paths would. No real
  graph at hand has a fourth field, a bracket or a wrong end, and ADR 0011
  says a finding from review alone goes to open problems
- **Refused:** a name that starts with `#` or holds a NUL; two lines of a
  path that overlap or start together; a `;` jump, by a message about node
  ids
- **What a referee could attack:**
  - vg documents the fourth field as a phase block. A lone block, or blocks
    that don't collide, is written at a coordinate no input states
    (`gfa/03-fourth-1.gfa`, `gfa/05-phase-blocks-short.gfa`)
  - `DRB1-3123.gfa`, from odgi's test data, gets a
    `fragStart` and a `#hole` from a range whose end its steps contradict
    on 12 of 12 lines
  - `H#1#c[5-900]` is accepted where `W H 1 c 5 900` is refused
  - one graph through `vg convert -gfW`, the route Cactus documents, gives
    two paths for one contig
  - an empty `path`; a `#haplotype` per contig for `sample#contig`; the
    spec's "`path` is `sample#haplotype#contig`" is false for such a line

### M, mended: today's meanings, checked

- **Strongest case:** it keeps what the spec says a fourth field, two
  fields and each suffix mean, and changes only names that contradict their
  own steps or carry two suffixes. Of the graphs here only `DRB1-3123.gfa`
  changes, so it is close to ADR 0011's "writer fixes that leave real
  graphs' bytes unchanged". It makes every tool-written P form read as its
  W form does (3 pairs the same rows, 1 refused both ways), which no other
  set does, and keeps the clipped-GBZ form that reads right today. Each fix
  answers one measured wrong output
- **Refused, beyond today:** a stated `[start-end]` end that isn't start
  plus the line's bp; a fourth field above 0 beside a `[start]`, which is
  two starts
- **What a referee could attack:**
  - the fourth field is still read as a start. The answer is vg's own
    writer; the hole is the lone VCF block
  - two-field names, as in A
  - a name whose `:a-b` isn't a range, but whose difference happens to be
    the line's bp, is read as one. Nothing in a P line can rule that out
  - under any set: vg writes a phase block counter into a W line's start
    column, and a W line is read as written. The overlap refusal catches
    it only when two colliding blocks of a contig are present

### T, tool conventions

- **Strongest case:** each part of a name is read only as the tool that
  writes it defines it, and only when the line bears it out: brackets as
  vg's subrange with its end checked, `:start-end` as odgi's when the steps
  span it, `#0` as the phase block vg adds, two fields as vg and
  graph-walks already read them. A fourth field above 0 is the one part
  whose meaning the name can't settle, counter or start, so it is refused
  with a message naming vg's W-line output. No P line then states a
  coordinate that a primary source calls something else
- **Refused, beyond M:** a fourth field of digits other than `0`
  - This refuses no pggb graph: vg gives a P line it reads phase block 0,
    and no step of pggb, `odgi extract`, `vg convert` or `vg chunk` made
    another here
  - It refuses `vg convert -f -W` on a GBZ built from clipped W lines,
    which today reads right. The same GBZ without `-W`, and the source GFA
    through `vg convert -gfW`, are both accepted
- **What a referee could attack:**
  - "You refuse `H#1#c#100` but accept the W line vg writes for the same
    path with 100 in its start column." The answer is that GFA defines that
    column as a start and nothing defines the fourth field as one
  - the lone-VCF-block hole stays open through W lines, as in M
  - the coincidence on `:a-b`, as in M
  - a 1-based region name loses a start it did state (`DRB1-3123.gfa`)
  - `S#c` and `S#1#c` in one graph are listed as `S` and `S#1`, and a
    reader asking for `S` by prefix gets both

### O, opaque

- **Strongest case:** GFA defines a `PathName` and nothing inside it. Every
  suffix is one tool's convention, and they conflict: `:start-end` is
  0-based in odgi and 1-based in Cactus and in `DRB1-3123.gfa`; the fourth
  field is a counter or a start. Reading none of them is the only rule that
  needs no check and can state no false coordinate. It is the simplest
  candidate and removes three rules. A graph that needs offsets has W lines
  for them
- **Refused:** as today
- **What a referee could attack:**
  - nothing on truth
  - a pggb region cut with `odgi extract` can't be shown in reference
    coordinates, and has no route to them: odgi writes no W lines and vg
    doesn't read `:start-end`
  - pggb through `vg convert -W` gets `GRCh38#0#chrY#0` as its sequence
    name
  - pieces of one contig become separate paths, so no departure record
    joins them. Today's two-path reading of the `-gfW` form shows the
    effect: 0 departure records where the W form has 1
  - `chr6.C4.gfa`: 90 of 90 lines change

---

## Recommendation

Everything from here is the proposer's view.

- **Adopt T.** It is the only set that meets K1 for P lines, K3 and K4
  together, and by the name census it changes no byte of a hosted walk
  file or of either pggb graph
- **How close each ruling is:**
  - **R3, R4, R5 are not close.** 3b, 4b and 5b each remove a measured
    wrong or self-contradicting output: a start taken from a range that
    `DRB1-3123.gfa`'s steps don't span, an end the steps contradict, two paths for one contig, an empty `path`. M and
    T agree on all three
  - **R2 is a small change with a clear direction.** 2b alters only
    `#haplotype` lines of two-field names, and makes the header say what
    vg and graph-walks' own helpers already read. 2c would also make the
    P and W forms of such a name agree, but writes a haplotype number the
    input doesn't state
  - **R1 is the close one.** 1b is the stricter reading, and the one a
    referee who knows vg has least to say against; 1a keeps a vg form that reads right
    today and matches vg's own W lines. No real graph at hand decides it.
    Under ADR 0011's burden rule a reviewer can fairly hold 1a, which is M
    plus 2b
- **If the reviewers split, M is the floor:** its fixes are the part M and
  T share. It keeps what the spec says each part of a name means and
  changes only names that contradict their own steps or carry two suffixes
- **Not recommended:** 3c, reading 1-based names by arithmetic. It would
  give `DRB1-3123.gfa` its GRCh38 coordinates, but it is a second
  convention inferred from a coincidence of lengths, for one toy graph. If
  it is wanted it has to be ruled on now: adding it after the freeze would
  change the rows of every such graph
- **Format number:** no row, column or header key changes and graph-walks
  reads every row as before, so 8 can stay. That is a call for the owner,
  who has said this stack may break freely

## What would change, for T

- **Spec text** (`docs/walks-format.md`)
  - C158: a P line's `path` and `fragStart` by the order of 5b, each part
    with its condition and its source: brackets (vg subrange, 0-based, end
    checked), `#0` (dropped), `:start-end` (read when `end − start` is the
    line's bp), otherwise the name whole from 0
  - "`path` is `sample#haplotype#contig`": true of a W line; for a P line,
    its name less what was read
  - C51: `#haplotype` is the name up to its second `#`, the name up to its
    only `#`, or the name whole
  - New claims beside C18, one per refusal: a fourth field of digits other
    than `0`; a stated end that isn't start plus the line's bp; a `;` jump
  - C17 says "two W lines of a contig"; the writer applies it to any two
    lines of a `path`, P or W. Say so, and that a line maps to exactly one
    `path` and `fragStart`
  - A line with no steps: its bracket end is still checked, as a W line's
    end column is (C118)
- **Other docs**
  - one measured ADR recording the ruling, as the open problem asks
  - `docs/open-problems.md`: close "P line names" and the four P line items
    of "Inputs the writer accepts and shouldn't"; add vg's phase block
    counters in W lines, a W line's `*` start, and 3c
  - `docs/departures/claims7.md`: rows C51 and C158, and the new claims
- **Writer**
  - `split_path_name` (`src/gfa.rs:111`) reads in 5b's order and returns
    what it read and any stated end; the walk reader (`src/walks.rs:129`)
    decides with the line's bp
  - The bp is known when `record` runs (`src/walks.rs:495`), but a line
    whose segments come later in the file is deferred (`src/walks.rs:538`,
    `:619`), and the later passes parse each name again and look it up
    (`src/walks.rs:653`, `:970`, `:1857`), so every pass must reach the
    same verdict
  - `haplotype` (`src/walks.rs:932`) for two fields
  - Refusal messages for a fourth field, a stated end and a `;` jump
  - The node and link index reads names through the same function
    (`src/gfa.rs:262`, `src/place.rs:201`). Give it the same reading, after
    checking the names in each hosted index's source GFA, or the two
    outputs of one GFA disagree on a path's coordinates
  - Nothing in the W-line reader changes
- **Fixtures**
  - `docs/walks-container/dialect/`, expected results that change:
    `p-arity4-phase.gfa` refused; `p-arity2.gfa` lists `H` once;
    `p-bracket-end-wrong.gfa` refused; `p-name-only-bracket.gfa` and
    `p-name-only-colon.gfa` give the paths `[5]` and `:5-21` from 0;
    `p-jump-semicolon.gfa` refused with its own message.
    `p-colon-range.gfa` is unchanged: its steps span 5-21
  - New, one per row of the shape table: the 39 in `gfa/` here
  - Tool-written, made by a script that runs vg and odgi: the four P and W
    pairs in `evidence/tools/`
  - Public: `chr6.C4.gfa` and `DRB1-3123.gfa`, fetched by a script
- **Checks,** each recorded failing on today's binary before it counts
  - A unit table: every row of the shape table
  - An independent recompute in the truth checker: each P line's `path`
    and `fragStart` and the `#haplotype` set, from the GFA alone.
    `rulings.py` is a starting point. Today's binary is the broken writer
    for 18 of the 39 in `gfa/`, 8 of them under M too
    (`evidence/fixtures-where-candidates-differ.txt`)
  - The four pairs: decompressed rows identical, or the P form refused
  - Real graphs: rebuild pggb chrY for both references and MC chr22, and
    `cmp` with the current files
  - Consumers: graph-walks on `chr6.C4.gfa`, where the header lists `chm13`
    and a cut asking for `chm13` keeps the walk of `chm13#chr6`
  - The invariant K5 rests on, stated and attacked: among accepted lines,
    `path` and `fragStart` name one GFA line. The argument is
    `link_records`; the attack is a fuzz over the name grammar

## Limits of this study

- No candidate was built. The M, T and O columns are a model's, checked
  against the binary only for today's reading
- No real graph with a fourth field or a bracket in a P line was found. R1
  and R4 rest on vg 1.69.0 run on graphs of 4 to 13 nodes, and the VCF case
  on one construction (`vg construct -a`, `vg gbwt -v`)
- The hosted node and link indexes' source GFAs were not inspected
- The `hapBp` branch was not read; K5 is argued from `link_records` on main
- ada was read twice, for a file list and for the heads of five small GFAs

## Evidence

All under
`plines/`.

- `rulings.py`: the model of each set's reading; `check_model.py`,
  `census.py`, `pw_equivalence.py`, `shape_table.py`, `shapes.py`,
  `range_check.py`: the scripts behind each table
- `evidence/model-of-today-vs-writer.txt`: the model against the binary
- `evidence/writer-today.txt`, `writer-today-vg-output.txt`,
  `writer-today-public-graphs.txt`, `writer-today-w-star-and-jump.txt`,
  `same-graph-three-routes.md5.txt`: what the binary does
- `evidence/shape-table.md`, `shape-table-compact.md`, `census.tsv`,
  `p-vs-w-forms.tsv`, `fixtures-where-candidates-differ.txt`: the
  candidates' tables
- `evidence/shapes-local.txt`, `shapes-ada.txt`, `pggbY.names.txt`,
  `ecoli-pggb.names.txt`, `chr6.C4.names.txt`, `DRB1-3123.names.txt`,
  `colon-range-lengths.txt`, `ada-gfa-list.txt`, `ada-heads.raw.txt`: what
  real graphs contain
- `evidence/tools/`: what vg and odgi wrote, and the GFAs they wrote
- `gfa/`: 39 fixtures, made by `mkfix.sh` and run by `runfix.sh`
- `sources/`: the quoted files and `fetched-commits.txt`; `downloads/`:
  odgi's three test graphs
