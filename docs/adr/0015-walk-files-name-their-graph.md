# ADR 0015: A walk file names its graph and the lines it leaves out

- **Status:** accepted, 2026-11-15. gfa-to-tabix 5.0.0 writes it, before
  the paper freezes the walk format on about 2026-11-18
- **Decides:** the `#walks` line gains two tags after `abridgebytes:i:`,
  `graph:Z:`, the hash of the GFA's segments the node and link index
  already states, and `leftout:i:`, how many of the GFA's lines have no
  rows in the file because they visit no node of its reference:
  [Header](../walks-format.md#header)
- **Keeps:** the format number, 8, and every unit, row and column. The
  spec already rules that an addition is a tag, that the `#walks` line's
  tags are found by name in any order, and that a reader ignores those it
  doesn't know, so every format 8 file stays valid and no reader may
  refuse one for lacking the two
- **Rejects:** stating the writer's name and version, a new header line
  kind, a sidecar file, and shipping unchanged
- **Closes** the part of
  [open problems](../open-problems.md#walk-files-name-no-writer) about the
  graph and the count, which suggested this place for them

## Context

- **The index names its graph and the walk file did not.** The node and
  link index's first line states `graph:Z:`, a hash of the segments
  ([index format](../index-format.md#what-the-file-holds),
  [ADR 0007](0007-node-link-format-2.md)). Nothing in a walk file said
  which GFA it came from, so nothing could pair it with an index of the
  same graph or tell that two files of one reference came from different
  builds
- **The count of lines left out went to stderr alone,** as `N paths visit
  no R node and are left out`. A file holding every line of a graph and
  one missing some looked the same
- **The header already records the writer's policy,** `stay`, `abridge`
  and `abridgebytes`, which the format doesn't fix. The graph and the
  count are facts of the build in the same sense
- **Where an addition goes,** from the review that repacked files with
  each kind of addition and ran the readers and checkers on them, as open
  problems records it: tags after the `#walks` line's others were handled
  best; a `#` line of the directory and a tag before `format:i:` were
  handled worst

## Decision

[walks-format.md](../walks-format.md) is the specification; this is what
changed and why.

- **The line,** as the writer writes it, `graph:Z:` and `leftout:i:` last:

  ```
  #walks	format:i:8	tile:i:65536	revisited:i:0	stay:i:311	abridge:i:1000000	abridgebytes:i:3000000	graph:Z:6f8a0816aa66e2d6	leftout:i:0
  ```

  The directory's line 1 is that line plus `bytes:i:`, as before
- **`graph:Z:` is the index's hash, by construction.** Both writers sum
  one function, `GraphHash::add` in `src/gfa.rs`, over the S lines and
  print it with one `Display`: the index over the graph it reads, the
  walk writer as it reads each S line in its first pass, with the id as
  written and the length it uses. The walk writer drops a segment of 0 bp
  from its paths but not from the hash. The hash names the segment set:
  two GFAs with the same segments and other links or paths share it
- **`leftout:i:` is the writer's own count,** `Reference::unplaced`: the
  lines with a step, after steps on 0 bp segments are dropped, that visit
  no node of the reference. Each reference's file states its own
- **The header names no writer and no version.** A walk file's bytes
  depend only on the GFA and the options it was written with

## What a reader does with them

- Nothing, to read rows: no row means anything different with or
  without them, and a reader ignores tags it doesn't know
- A host or viewer that opens a walk file beside an index compares their
  `graph:Z:` values and can say when the two came from different graphs.
  No host does yet ([open problems](../open-problems.md#walk-files-name-no-writer))
- A reader can say that `leftout` lines of the graph have no rows in this
  file, and a file stating 0 has rows for every line with a step
- A file without the tags is format 8 and is read as before: graph-walks
  returns them from `reader.header()` where a file states them, and
  leaves them out where it doesn't

## Evidence
<!-- record -->

- **One hash for one GFA.** On every fixture of `tests/data` that both
  writers build, 19 GFAs giving 13 distinct graphs, and on a GFA whose S
  lines come after its paths, one of them of 0 bp and one stated by
  `LN:i:`, the walk file's `graph:Z:` equals the index's
  (`a_walk_file_names_its_graph_as_the_index_of_the_same_gfa_does`).
  The seven fixtures left out have node ids that aren't integers, which
  `--walks` refuses
- **No other byte moves**
  ([fixtures and slices](../walks-container/header-tags/same-bytes.txt),
  by [walks-header-diff.sh](../../scripts/walks-header-diff.sh) and
  [walks-header-diff.py](../../scripts/walks-header-diff.py)), main's
  writer at 8a965ac against this one: the ten walk fixtures under four
  option sets, `--sequences`, and three real graphs, HPRC's LPA kiv2 and
  amylase slices on GRCh38 and a maize NAM chr8 slice on B73, 56 files.
  In each, the decompressed data differs only in the `#walks` line, which
  gains exactly the two tags, and in the `#entry` offsets of the tables;
  every other byte of the data, units and EOF block, is the same; the
  directory differs in its line 1 and in each table's offset. The header
  unit grows 24 to 29 bytes compressed and a table −2 to +3, from its
  shifted offsets
- **Whole-genome files:** HPRC v2.1 Minigraph-Cactus GRCh38 and CHM13,
  rebuilt with this writer from the same GFA text as the hosted files and
  compared pair by pair with `scripts/walks-header-diff.py`: each new data
  file is the old with the two tags on its `#walks` line (`graph:Z:c9aa0d5f6907f27c
  leftout:i:1698` for GRCh38, `graph:Z:496a04d0071827a0 leftout:i:3312` for
  CHM13), every `#entry` offset moved by the header's and tables' changed
  size, and every other byte the same (1,578,826,994 and 1,782,593,446
  bytes compared, 0 differences); the writer's printed counts of pieces,
  records, rows and left-out lines are identical old and new. The rebuilt
  files replaced the hosted `-f8` copies, sha256 read back from each URL.
  `leftout` was counted again on the whole graphs by a second session's
  program that reads the GFA text once with no writer code
  (walks8-evidence fab8f323/leftout/leftout.c, streamed from `vg convert`
  of each GBZ): 1698 of 53,150 path lines for GRCh38 and 3312 of 60,807
  for CHM13, equal to the headers; neither graph has a 0 bp segment.
  The walk writer also takes the last of two `LN:i:` tags on one segment,
  as the index does, so `graph:Z:` hashes the lengths the index hashed;
  no hosted graph has such a segment
- **The bytes don't depend on the thread count,** one core against all
  (`a_walk_file_is_the_same_bytes_on_one_core_as_on_all`)
- **Each check fails when broken**
  ([cases.tsv](../departures/scripts/broken/cases.tsv), by
  [broken.sh](../departures/scripts/broken.sh)):

  | Broken file | Fails |
  | --- | --- |
  | `graph:Z:` one hex digit off | `walks-truth.py rebuild` |
  | `graph:Z:` in uppercase hex | `verify7.py`, `walks-truth.py rebuild` |
  | `leftout:i:` 0 where U#1#u's line is left out | `walks-truth.py rebuild` |
  | `leftout:i:` stated twice | `verify7.py`, `walks-truth.py rebuild` |

  `walks-truth.py rebuild` recomputes the hash from the GFA's S lines and
  counts the lines with no step on the reference across every shard.
  [check-walks.sh](../../scripts/check-walks.sh) also checks a file with
  both tags removed: every check passes it but `rebuild`, which must
  fail it, since this writer states them. The broken files were rewritten
  by [make-broken.sh](../departures/scripts/broken/make-broken.sh) with
  this writer; with main's writer it reproduced the committed files byte
  for byte

## Alternatives rejected
<!-- record -->

- **Also stating the writer's name and version,** as `program:Z:` and
  `version:Z:`. A version stamp changes a file's bytes at every writer
  release, even one that changes no row, so every hosted file would be
  uploaded again on a sync after any release. The rule kept is that a
  walk file's bytes depend only on the GFA and the options. The
  later-additions rule lets a writer add such tags later without a format
  change
- **A new header line kind,** such as `#graph`: a reader ignores a header
  line it doesn't know, but a tag on the `#walks` line is where the
  options already are, and where the review found readers and checkers
  handled an addition best
- **A sidecar file** beside the data and the directory: a third file to
  host, copy and keep in step, for two values
- **Shipping unchanged:** the walk file stays the one file of a build that
  can't be paired with its index, and a file missing lines looks like one
  holding them all

## Consequences
<!-- record -->

- Every walk file is rebuilt once for 5.0.0, as the format 8 rollout
  already rebuilds them
- graph-walks' `WalkHeader` gains `graph` and `leftout`, optional, parsed
  by name
- The `graph:Z:` of a tier folded by `fold` or `build --tier` hashes the
  folded graph, so only the full-resolution index shares a walk file's
  value
