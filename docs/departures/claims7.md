# Walk format 7's claims against its writer

An audit of every normative statement about the walk files in
[walks-format.md](../walks-format.md), [ADR 0010](../adr/0010-walks-unit-table.md),
the parts of [ADR 0009](../adr/0009-departure-records.md) still in force and
the README's walk sections, as they stand on `format7-tidy` at 688689c,
against the writer in `src/` at the same commit (gfa-to-tabix 4.0.0).

- **Enforced:** the code path that makes the claim hold, or `build` where
  the writer checks it and fails the build
- **Checked before:** what would have failed had the claim broken before
  this audit: `V` is `verify()` in `tests/walks.rs`, run on every file the
  tests build; `P` is `verify7.py`; `A` is `audit7.py`; `E` is the
  build-time encode-decode check (`routes.rs` `encode_all`,
  `summary_row`); a test name is a test in `tests/walks.rs`; `fuzz7.sh`
  runs `P` and `A` on random graphs
- **Checked now:** the check this audit added, `C:<id>` in
  [claims7.py](scripts/claims7.py), run by
  [claims7-fuzz.sh](scripts/claims7-fuzz.sh), or a hand-made GFA (`E1` to
  `E5`, below)
- **Result:** on the test fixtures (20 files), 1,600 fuzz files (seeds 1 to
  200 under 8 option sets) and the real files MC chr22 and pggb chrY on
  GRCh38, built on ada by this commit's writer

Of the 115 claims, 34 had no check before this audit. 15 are false, 13 of them
distinct (111 restates 42, 115 restates 105), and 7 are ambiguous. 9 of
the false claims had no check; the other 6 had a check that tests something
else (17, 42, 97, 109, 111, 112).

## Inventory

`wf` is walks-format.md, `0010` and `0009` the ADRs, `RM` the README; the
numbers are lines.

### Overview, options and terms

| # | Claim | Where | Enforced | Checked before | Checked now | Result |
|---|---|---|---|---|---|---|
| 1 | A reader rebuilds every step of every path through a window exactly from the tiles whose extents overlap it | wf 9 | reader | none | C:O4, E2 | ambiguous: needs attach fetches and detail units, and own steps in a W line with no reference node are in no tile |
| 2 | Every reference node and every record end states its pass count | wf 13 | `emit_rows`, `Departure::body` | A | | holds |
| 3 | A tile holds R once and each distinct route once | wf 37 | `Routes::intern` | none | C:T2 | holds |
| 4 | Every file lists the same paths | wf 40 | none: `assign_chunks` leaves out a path with no node of that reference | none | E4 | **false** |
| 5 | A reader lists the haplotypes from the header | wf 43, 307 | `haplotypes` BTreeSet | `a_walk_file_names_its_format_reference_and_each_haplotype_with_rows` | C:H1 | holds |
| 6 | Option defaults 65536, 311, 1000000, 3000000 | wf 48-52 | `main.rs` 112-117 | none | read | holds |
| 7 | `--abridge-steps`: moves paths until the rest cost at most n | wf 51, 623 | `abridged_groups` | none | C:B2 | holds |
| 8 | `--abridge-bytes`: ...until the rest compress to at most this many bytes | wf 52, 623 | `abridged_groups`, by an estimate of the bytes each path saves | none (a test comment says the estimate can leave a path) | C:B1 | **false** at the margin: 1 of 1,600 fuzz files keeps walk rows at 306 bytes against 300, and 6 fixture tiles at `--abridge-bytes 1` |
| 9 | `\|S\|` is where S's last node or line ends | wf 67 | `run`, `ends` | none | | holds; the file never states `\|S\|` |
| 10 | Span: from the first base of a row's first step on R to the last base of its last | wf 74 | walk rows take the span of all placed steps (`encode_all`) | V, P, A check the span of all placed steps | C:W4b | **ambiguous**: the first and last steps span less than the row states on 4,562 fuzz rows, 9 MC chr22 rows and 170,648 pggb chrY rows |
| 11 | Own steps: strictly between leave and rejoin, a 0 bp step included | wf 83 | `record_departures` `tiles_of(i + 1..j)` | A; the test's check uses the bp range (`tests/walks.rs:721`) | C:O1, O3 | holds; the test checks the definition W1 replaced, which differs on 5,735 fuzz records |

### Tiles, pieces and placement

| # | Claim | Where | Enforced | Checked before | Checked now | Result |
|---|---|---|---|---|---|---|
| 12 | Tiles at multiples of `tile` | wf 95, 216 | `Chunks::new` | none | C:U2 | holds |
| 13 | A step on a reference node takes the tile holding its pass's start | wf 99 | `Chunks::of`; `Piece::read` fails a step not on R | build | C:U2 | holds |
| 14 | Any other step takes the tile of the last reference step before it, or the first after | wf 100 | `assign_chunks` | none | C:O2, E2 | holds |
| 15 | On the reference paths a step takes the tile holding its offset | wf 103 | `assign_chunks` | none | C:U2 | holds |
| 16 | `piece` numbers a W line's pieces from 0 | wf 105 | `write_pieces` | `decode_file` (fixtures) | C:W5 | holds |
| 17 | The tool refuses two W lines of a contig that overlap or start at the same base | wf 110 | `link_records` | `records_of_a_contig_that_overlap_or_share_a_start_are_refused` | E3 | **false** for W lines with no steps, which `first_pass` never records |
| 18 | It refuses a W line whose end is not its start plus its nodes' lengths | wf 111 | `record` | `a_w_line_whose_end_disagrees_with_its_steps_is_refused` | | holds |
| 19 | The lines are the same for any order of the W lines | wf 112 | `Stable`, the sorts | `the_order_of_the_paths_changes_no_row` (fixtures) | E5 | holds: 60 seeds × 3 option sets × 2 orders identical |
| 20 | A path with no node of a reference has no rows there, counted on stderr | wf 114 | `assign_chunks` | `a_path_off_every_reference_is_counted_and_left_out` | | holds; "path" means one W line, unstated |
| 21 | Nearest pass, the earlier on a tie, or "the first pass" when the sequence has none | wf 116-121 | `visit_near`, `first_visit` | repeat fixtures | | **ambiguous**: "first" is the pass of the reference path whose name sorts first in bytes, at its lowest offset (`Stable`), not the first in the file |
| 22 | Placing starts at the first step on a node passed once | wf 122 | `visits_along` | none | | holds (code) |
| 23 | The stay's rules | wf 125-136 | `stay_home`, `rehome` | `a_short_stretch_...`, `a_stay_refuses_...` | | holds; between two passes equally near, the lower offset wins, unstated |
| 24 | A reference passing each node once gets the same rows at any `stay` | wf 136 | follows from 23 | `a_stay_leaves_a_reference_that_passes_each_node_once_alone` | | holds |
| 25 | The build fails if a row decodes to another node or position | wf 138 | build (`encode_all`) | E | | holds |
| 26 | A step placement leaves off the reference is route interior | wf 140 | `encode` | E | | holds |
| 27 | Under nearest pass no step on a node passed once is route interior | 0009 129 | `visits_along`, `rehome` | none | C:N2 | holds |

### Files, units, directory and header

| # | Claim | Where | Enforced | Checked before | Checked now | Result |
|---|---|---|---|---|---|---|
| 28 | The data file is units, then a BGZF EOF block | wf 197, 0010 53 | `UnitFile` | V, P | | holds |
| 29 | Each unit starts and ends a gzip member | wf 198 | `UnitFile::end` cuts | V, P | | holds |
| 30 | The header unit is first, from byte 0, with no `#unit` line | wf 202, 207 | `UnitFile::start` | V, P | | holds; no ADR gives a reason for the header's missing `#unit` line |
| 31 | Sequences in byte order of their names | wf 203 | `Chunks::new` | V, P (directory) | C:U1 | holds |
| 32 | Per sequence: tiles and blocks by start, then detail units, then the table | wf 203-205, 0010 67 | `Outputs` | none (V, P check only that tables match file order) | C:U1 | holds |
| 33 | At one start a tile before the blocks starting there, smaller blocks first | wf 205 | `Outputs::tile`, the departure sort key | none | C:U1 | holds |
| 34 | Every unit but the header starts with `#unit seq start end kind name` | wf 207 | `UnitFile::begin` | V, P | | holds |
| 35 | A tile is named by its start, a multiple of `tile` | wf 216 | `Outputs::tile` | none | C:U2 | holds |
| 36 | A departure block is named `.` | wf 217 | `Outputs::departures` | V, P (tidy) | | holds |
| 37 | A detail unit spans its walk rows' spans, named `cs:d` | wf 218 | `unit_of`, `Details::flush` | V, P, A | | holds |
| 38 | A table spans 0 to its units' largest end, named `.` | wf 219 | `UnitFile::table` | V, P (name only) | C:U8 | holds |
| 39 | Every name other than `.` is unique within its kind and sequence | wf 221, 0010 157 | construction | V, P (tidy) | | holds |
| 40 | A tile's extent is the union of its `ref` rows' stretches | wf 226, 581 | `unit_of` takes min to max of ref stretches and piece spans | V, P (min to max of both) | C:U3, U3g | **ambiguous**: it is the hull; 166 fuzz tiles' ref stretches leave a gap inside it |
| 41 | Every piece's span lies inside the tile's extent | wf 227 | follows from every placed step being on R | V, P | C:U3 | holds |
| 42 | A unit covering no base takes `[p, p + 1)`, or `[p − 1, p)` where `p` is `\|S\|` | wf 231 | `unit_of` | `a_unit_or_record_at_a_point_takes_the_base_beside_it`; V, P | C:U4, E1 | **false** where `\|S\|` is 0: the tile is `[0, 0)`, which no window selects; V and P accept it |
| 43 | The pyramid's blocks and a record's cover | wf 237 | `departures::cover` | V, P | | holds |
| 44 | Within a block, lines in order of start, end, then text | wf 242 | the departure sort key | none | C:U6 | holds |
| 45 | A table lists its sequence's units before it, in file order, decimal below 2^53 | wf 244 | `UnitFile::table` | V, P | | holds |
| 46 | A sequence with no units has a table of its `#unit` line only | wf 248 | `close_before` | `a_reference_sequence_with_no_units_has_an_empty_table` | | holds |
| 47 | Directory line 1 is the `#walks` line plus `bytes:i:` | wf 261 | `UnitFile::finish` | V, P | | holds |
| 48 | One directory line per reference sequence, in file order | wf 266 | `UnitFile::table` | V, P | | holds |
| 49 | `format:i:7`, `tile`, `stay`, `abridge`, `abridgebytes` | wf 290-302 | header in `run` | header tests | | holds |
| 50 | `revisited` counts nodes passed more than once | wf 295 | `visits_of.len()` | A | | holds |
| 51 | `#haplotype`: each other haplotype with rows, once, in byte order | wf 307 | BTreeSet | fixture test | C:H1 | holds |
| 52 | `#hole`: each stretch no reference line covers, before its first and between | wf 309 | `Holes::between` | `steps_either_side_of_a_hole_in_the_reference_are_adjacent` | | holds; hole lines are in (sequence, start) order, unstated |
| 53 | A 0-count file states every position as a fact; MC chr22 on GRCh38 passes no node twice and has no `@k` or `:k` | wf 292, 663; 0009 166, 189 | follows from placement | none | C:H2 | holds |

### Rows

| # | Claim | Where | Enforced | Checked before | Checked now | Result |
|---|---|---|---|---|---|---|
| 54 | Every line not starting `#` begins `seq start end kind` | wf 319 | `unit_of`, `Outputs::departures` | V, P | C:U9 | holds |
| 55 | A walk row's `start end` is the span of all its placed steps | wf Rows | build (`encode_all`) | E, V, A | C:W4 | holds |
| 56 | An abridged row's `start end` is the span of its first and last steps on R | wf Rows, 443 | build (`summary_row`) | E, A | C:A1 | holds |
| 57 | `ref`, `nodes`, `route` rows state the unit's extent | wf Rows | `unit_of` | V, P | | holds |
| 58 | A departure line's `start end` | wf Rows, 503 | `Departure::extent` | A (breakpoints inside) | C:D3 | holds |
| 59 | A tile lists ref rows, at most one nodes row, routes, walks, then abridged rows | wf 331 | `write_chunk`, `emit_rows` | none | C:U5 | holds |
| 60 | Handles and delta tokens, `.` for an empty list, rounding down | wf 334-341 | `delta_steps`, `push_list` | V, A decode | C:W1 | holds |
| 61 | One `ref` row per piece of the reference paths; `fragStart` and `hapOffset` as stated | wf 349-352 | `write_pieces`, `split_path_name` | `p_lines_give_the_rows_w_lines_do` | | holds |
| 62 | `passes` counts every sequence's passes, `.` when all are 1 | wf 355 | `emit_rows` | A, `a_pass_count_counts_every_sequence_of_the_reference` | C:R1 | holds |
| 63 | R is the `ref` rows joined in `hapOffset` order | wf 359 | `write_chunk` sorts by offset | V, A decode | C:R2, R3 | holds; rows are written in that order and a tile of S holds only S's `ref` rows, both unstated |
| 64 | The `nodes` row lists the nodes the tile's routes visit, ascending | wf 371 | `emit_rows` | none | C:N1 | holds, for route interiors only: an entry or exit node is not listed |
| 65 | `SQ:Z:` bases; `--sequences` refuses `*` | wf 374-377 | `emit_rows`, `first_pass` | `sequences_adds_the_bases_of_ref_and_nodes_rows` | | holds |
| 66 | `entry` or `exit` is `.` for a route starting or ending off R; `interior` `.` for a direct route | wf 387 | `encode` | E | C:T3 | holds; a route without an entry or exit always has a non-empty interior, unstated |
| 67 | Route tokens chain across columns and rows from 0; a route's id is its row index | wf 390-393 | `emit_rows` | V, A decode | C:W1 | holds |
| 68 | A route is stored the way round whose handles sort first | wf 394 | `Routes::intern` | none | C:T1 | holds; no ADR records or measures the choice |
| 69 | A walk row's `start` is its first handle on R, absolute | wf 408 | `encode` | E | C:W1 | holds |
| 70 | `@k` and `:k` defaults, written only where they differ, so a file has one encoding | wf 414-424 | `encode` | none: E checks decoding, not minimality | C:W2 | holds |
| 71 | A walk continues along R only where R's next position is the step's | wf 425 | `encode` | none | C:W3 | holds |
| 72 | Every piece of a path has one row in its tile, walk or abridged | wf 435-438 | `write_chunk` | A, `decode_file` | C:W5 | holds |
| 73 | An abridged row's `hapOffset` and `bp` give its stretch on its contig | wf 444 | `summary_row` | `an_abridged_row_spans_...`, A | | holds |
| 74 | A record leaves at a piece's last step on S and rejoins at a piece's first, so no own bp meets an abridged stretch | wf 449 | `record_departures` | A | | holds |
| 75 | An abridged row's `nsteps` counts all the piece's steps | wf 454 | `summary_row` | `decode_file`, A | | holds |
| 76 | A path's moved pieces in one tile share one record, one per contig of the path | wf 459-460 | `abridged_groups` groups by `(path, fragStart)`, one W line | none | C:A3 | **false**: 170 tile and path pairs on MC chr22 (NA18976#2#CM089769.1 has records 1, 11 and 156 in tile 11,796,480), 156 in fuzz, and `walks-records.gfa` with `--abridge-bytes 1` (H#1#h, records 1 and 2 in tile 0) |
| 77 | A record for each departure between different pieces, none inside one | wf 466-471 | `record_departures` | A | | holds |
| 78 | Departures per sequence, other sequences counted as own, W lines in start order | wf 473 | `contig_after` | A, `a_contig_departs_once_...` | | holds |
| 79 | `Pos`, `Strand`, `Passes` of each end | wf 476 | `step_end` | A | | holds |
| 80 | `hapStart`, `ownBp`, `missingBp` | wf 484 | `record_departures`, `contig_after` | A | C:D5 | holds |
| 81 | Adjacent steps depart nowhere; a 0 bp step between changes nothing | wf 489 | `Holes::adjacent` | `a_step_on_a_node_of_0_bp_between_two_lines_is_no_departure`, A | | holds |
| 82 | A contig's sequence before its first step on S or after its last has no record | wf 492 | `record_contig_departures` | `a_contig_that_leaves_a_sequence_for_good_has_no_record` | | holds |
| 83 | A record's extent: end nodes, widened to the breakpoint stretch, clamped into S | wf 503-511 | `Departure::extent`, `step_end` | A, point test | C:D3 | holds |
| 84 | `ownTiles`: the tiles of S holding the own steps, in path order, `.` for none | wf 512 | `tiles_of` | `decode_file` (bp definition), A | C:O1, D1 | holds (fuzz, fixtures, real shards) |
| 85 | Own steps after the leave in its W line take the leave's tile | wf 518 | `assign_chunks` | none | C:O2, E2 | **false**: an off-reference own step after a step on another reference sequence takes that sequence's tile (E2) |
| 86 | Own steps leading the next W line take the rejoin's tile; a record can have both, the leave's first | wf 521-524 | `record_contig_departures` | none | C:O2, D2 | holds |
| 87 | Own steps on other sequences and own sequence in no W line are not listed | wf 525 | `tiles_of` filters by S | none | C:O4 | **ambiguous**: own steps in a W line with no reference node are in no tile at all, and steps after another sequence's step lie in its tiles; neither is said (`walks-records.gfa`, E2) |
| 88 | A record's line is in every block of its cover, the same text in each | wf 527 | `Departure::file` | V, P | | holds |
| 89 | Every departure line overlaps each block it is in | wf 584 (tidy) | follows from the cover | V, P (tidy) | C:U7 | holds |
| 90 | A departure inside a piece lies in its tile's extent | wf 561 | construction | A | | holds |
| 91 | R holds one node ending at a `+` leave's breakpoint and one starting at the other kind's | 0009 95 | none | none | C:D4 | **false** with 0 bp nodes, where several do: 11,029 ends in fuzz; none on MC chr22 or pggb chrY |
| 92 | Every row of one record repeats the same columns | 0009 104 | `Departure::file` | V | | holds |

### What the writer guarantees, abridged tiles, scale

| # | Claim | Where | Enforced | Checked before | Checked now | Result |
|---|---|---|---|---|---|---|
| 93 | "The tool checks each of these as it writes" | wf 574 | build checks only claims 55, 56 and the `#` refusal | none | read | **false**: partition, tables, extents, containment, cover, `ownTiles` and the renames hold by construction and are checked only by V, P and A |
| 94 | Tables list every unit, lengths above 0; the directory every sequence | wf 579 | `UnitFile` | V, P | | holds |
| 95 | Path names hold no tab or newline and don't start with `#` | wf 590, 0010 151 | build (`named`, `path_line`) | `a_path_name_starting_with_a_hash_is_refused` | | holds |
| 96 | Data then directory, each under a temporary name and renamed | wf 593, 0010 158 | `Temp` | `a_failed_write_leaves_no_temporary_file` | | holds |
| 97 | `tests/walks.rs` checks every record's `ownTiles` against its decoded own steps | wf 596 | | `decode_file` | C:O3 | **false** as written: the test takes own steps by bp range (`tests/walks.rs:721`), the definition W1 replaced |
| 98 | Offsets are u64 block starts; files past 2^32 bytes | wf 604 | `parallel_bgzf` | `offsets_past_2_to_the_31_and_32_round_trip` | | holds |
| 99 | A piece's cost: interior steps per use plus a quarter of all steps | wf 619 | `piece_cost` | none | C:B2 | holds |
| 100 | Costliest paths move first; a path's pieces move together | wf 623 | `abridged_groups` | `every_path_rebuilds_from_its_detail_rows_when_abridged` | | holds |
| 101 | The tile keeps its ref rows and the rest re-encoded, an abridged row per moved piece | wf 627 | `write_chunk` | A | | holds |
| 102 | A record holds a `nodes` row, `route` rows and `walk` rows | wf 635 | `emit_rows` writes `nodes` only where an interior exists | none | C:A6 | **false**: 5,309 fuzz detail units and 44 on the fixtures have no `nodes` row |
| 103 | A record's routes number from 0 and its walk rows decode against tile `cs`'s R | wf 636 | `write_chunk` | A | C:W1 | holds |
| 104 | The Example's lines | wf 666 | | tidy test "the spec's example quotes the tool's lines" | | holds |
| 105 | The tool reads the GFA twice | wf 711, RM 179 | `first_pass` | none | read | **false** when a path line comes before an S line it uses: `first_pass` reads the file again for those, a third read |
| 106 | Sorts in up to 512 MB and 128 MB | wf 715 | `SORT_BUDGET`, `DEPARTURE_SORT_BUDGET` | none | read | holds |

### ADR 0010 and the README

| # | Claim | Where | Enforced | Checked before | Checked now | Result |
|---|---|---|---|---|---|---|
| 107 | A tile's `start end` is the union of its rows' | 0010 73 | `unit_of` | V, P | C:U3g | ambiguous, as 40 |
| 108 | Departure blocks, cover and identical lines | 0010 78-84 | `departures.rs` | V, P | | holds |
| 109 | `abridged`: "the moved piece's stretch on the reference path" | 0010 104 | `summary_row` writes its start and end steps' span | E, A (against walks-format's reading) | C:A1b | **false** against the writer under its plain reading: the placed steps span more on 70,765 of pggb chrY's 110,886 abridged rows and on 1,364 fuzz rows |
| 110 | Each table lists every unit of its sequence, in file order, before it | 0010 144 | `UnitFile::table` | V, P | | holds |
| 111 | Tile and detail lines lie within their unit; every step placed in `[a, b)` is in a tile whose extent overlaps it | 0010 145-148 (tidy) | `unit_of` | V, P | C:U3, U4 | **false** where `\|S\|` is 0, as 42 |
| 112 | "Each line's `start end` agrees with its decoded steps, checked at build ... on every row" | 0010 149 | build checks walk and abridged rows | E | read | **false** as written: no departure, `ref`, `nodes` or `route` row is checked at build |
| 113 | Offsets exact integers below 2^53 | 0010 153 | u64 decimal | P | | holds for any file below 8 PiB |
| 114 | Each file is units, "one per 64 kb tile of the reference and per block of departure records" | RM 41 | | none | read | ambiguous: also detail units, a header and a table per sequence; a tile the reference doesn't pass has no unit |
| 115 | `--walks` reads the GFA twice | RM 179 | | | | **false**, as 105 |

Not counted: the descriptive sections and the reader's rules (Paralogs and
collapsed repeats, Exact and chosen, Reading a window, Hosting, Readers),
except where a sentence there states something about the file, which has a
row above.

## Hand-made GFAs

- **E1:** a reference sequence of two 0 bp nodes, so `|S|` is 0. Its tile is
  `#unit R#0#chr0 0 0 tile 0`, and every row in it reads `0 0`
- **E2:** H leaves chrA at node 2, steps on chrB's node 11 and its own node
  20, and rejoins chrA at node 3. Node 20 is in chrB's tile 0, a route with
  no entry. The chrA record says `ownBp 10` and `ownTiles .`
- **E3:** two W lines of `H#1#h` with no steps, both starting at 5, and one
  more starting at 0, where a W line with a step starts. The build succeeds
- **E4:** `walks-two-refs.gfa` plus `W X 1 x 0 6 >6`, with node 6 on Q and not
  on GRCh38. `X#1` is in Q's `#haplotype` lines and not in GRCh38's
- **E5:** each fuzz graph's W lines shuffled and reversed. All 360 builds
  match the original byte for byte, as does a pair of abutting reference
  lines passing a 0 bp node in opposite orientations, in either order

## Unstated guarantees

| Guarantee | Writer | Reader that relies on it |
|---|---|---|
| Within a tile, walk rows are sorted by path name in bytes, then `fragStart`, `hapOffset` and `piece` | the sort key in `PieceRef::write` | graph-walks `walkChunk.ts` 415, 780-838: the first walk to take a route places its off-R nodes |
| A tile's `ref` steps start in `[name, name + tile)` | `Chunks::of` | `walkReader.ts` 519 (`readTo`), `walkRows.ts` 1040, 1055 |
| A tile's name is a decimal with no leading zeros | `to_string` | `walkChunk.ts` 520 (`Number(name)` keys detail units) |
| A tile of S holds `ref` rows of S only, at least one | `assign_chunks`; `unit_of` fails a tile with none | `walkReader.ts` 334-346 keeps only S's |
| A detail unit holds one W line's moved pieces | `abridged_groups` | `walkReader.ts` 480-515 decodes a detail unit for its first row's path only |
| Detail numbers in a tile run from 0, costliest path first | `write_chunk` | none |
| A route with no entry or no exit has a non-empty interior; its entry and exit nodes are on R | `encode` | decoders |
| Route rows are ordered by their ends' first position in R, then by handles | `emit_rows` | the one-encoding claim (70) |
| Node ids are below 2^31; larger ones are refused | `node_id` | `walkChunk.ts` keeps ids in `Int32Array` |
| `\|S\|`, on which extents at the sequence's end depend, is in no line | | `walkReader.ts` 297 takes the largest tile end |
| "A path" with no node of a reference is one W line; the contig's other W lines keep their rows | `cut_path` per line | attach fetches, claim 87 |
| `#hole` lines are in (sequence, start) order, never overlapping | `Holes::between`, the sort in `run` | `walkDeparture.ts` 48-61 assumes no overlap |
| A departure line's text is the same in every block | `Departure::file` | `walkReader.ts` 191 dedups by whole line |
| The output is the same for any W-line order | `Stable`, the sorts | stated (19) and true; tested on fixtures only before |

## Measurements the leads asked for

- **A bubble across a tile edge:** a record with both ends passed once, on
  one strand, rejoining at or after the leave with nothing missing, whose
  end nodes start in different tiles ([bubbles7.py](scripts/bubbles7.py)).
  Inside one tile the same bubble is a route and has no record.

  | | MC chr22 | pggb chrY |
  |---|---|---|
  | records | 24,648 | 425,040 |
  | bubbles across a tile edge | 23,586 (95.7%) | 6,785 (1.6%) |
  | of them, ends 0 bp apart | 2,417 | 191 |
  | 1-50 bp | 18,255 | 1,084 |
  | 51-1,000 bp | 505 | 2 |
  | 1,001-10,000 bp | 383 | 579 |
  | over 10,000 bp | 2,026 | 4,929 |

  So on MC chr22, 21,177 of the 24,648 records (86%) are bubbles of at
  most 1 kb that a tile edge cut, which a tile holding both ends would
  give as a route. On pggb chrY the records are mostly collapsed-repeat
  hops
- **Routes stored the way round whose handles sort first:** came in with
  format 2 (677ed02 and 08ffa5a, 2026-10-12) and was carried through formats
  5, 6 and 7 with no ADR recording or measuring it
- **The header unit's missing `#unit` line:** consistent between spec and
  writer (claim 30), with no recorded reason
- **Arbiter A's 292 and 288 KB:** `walks-container/arbA/decision.md` gives F6p's pggb 1 kb
  median as 292 KB in its table at line 142 and at line 169, and as 288 KB in
  its table at line 414 and at line 439 ("288 → 187 KB")
- **Link orientation:** no claim in the spec says which way round a reader
  should give a route's links; claim 68 fixes only how a route is stored

## How the false claims got in

| # | Added | What the writer did then | Why no check caught it |
|---|---|---|---|
| 4 | 200c0a5, 2026-10-21, merging walks.md into the spec | left out a path with no node of the reference; the same commit's page says so at its line 62 | no check compares two references' files; the sentence survived formats 5, 6 and 7 |
| 8 | 200c0a5 | moved paths by an estimate of the bytes each saves | the test's comment states the estimate can leave a path, and the spec was not changed |
| 17 | c5d388c, 2026-11-04 | `first_pass` recorded only W lines with steps | the refusal test uses lines with steps |
| 42, 111 | 1a0646f and ADR 0010's amendment, 2026-11-05 | `unit_of` gave `[0, 0)` at `\|S\|` 0 | V and P accept a unit whose extent equals its rows' hull before testing the point rule; no fixture or fuzz graph has a sequence of 0 bp |
| 76 | 86d1006, 2026-11-05, the format 7 rewrite | `abridged_groups` grouped by `(path, fragStart)` since a57515d, 2026-11-04 | no check counts records per path and tile; the format 6 text said "a path's moved pieces in one chunk share one record", and the rewrite added "one per contig" |
| 85 | c4caa2f, 2026-11-05, `ownTiles` | `assign_chunks` filed an off-reference step after another sequence's step in that sequence's tile | the fuzz generator writes one reference sequence, so no path crosses sequences; the test's ownTiles check compares against the writer's own placement |
| 91 | f672193, 2026-11-05, ADR 0009 | 0 bp nodes on the reference were legal and tested (`a_step_on_a_node_of_0_bp_...`, a57515d) | an explanatory sentence, never treated as a guarantee to check |
| 93 | 86d1006 | the build checked spans and names only | the sentence introduces a list that grew; each bullet was checked by tests, so the sentence read true |
| 97 | c4caa2f; definition changed by 108bab7, 2026-11-06 (W1) | wrote ownTiles from the steps strictly between | W1 changed the spec's definition and not the test's (`tests/walks.rs:721`); the fixtures have no 0 bp end in another tile, so the test still passes |
| 102 | c00c433, 2026-10-20, format 5's docs | `emit_rows` wrote `nodes` only for a non-empty interior | no check reads detail units' row kinds; carried through three rewrites |
| 105, 115 | 200c0a5 | a path line before its S line triggers a third read (`first_pass`'s deferred pass, since earlier) | performance prose, never checked |
| 109 | 2b0f7a5, 2026-11-05 18:49, ADR 0010 | ADR 0009's final review that day had defined the abridged row's span as its start and end steps' | ADR 0010 was written before format 7's writer and never re-read against it; A and E check walks-format's wording, which is right |
| 112 | 2b0f7a5 | the encode-decode check covered walk rows (abridged rows from f672193) | "every row" stated for the rows a decoder checks; departure extents have no build check |

## Root cause

- **The prose is written from the design, and the checks from the code.**
  Every false claim above states what the author intended or what holds in
  the common case. The checks beside them (V, P, A) were written by the same
  hand from the writer's formulas: `verify()` checks a tile's extent against
  the writer's own min-to-max of ref stretches and piece spans, not against
  the spec's "union of its `ref` rows' stretches"; the ownTiles test takes own
  steps by the writer's bp arithmetic of the time. A check that restates
  the code can't find a sentence the code contradicts
- **Checks exempt the cases they can't state rather than fail on them.**
  `verify()` and `verify7.py` skipped containment for departure blocks and
  name uniqueness for the `departures` kind; the point rule is accepted
  whenever the hull equals the extent, so `[0, 0)` passes. Each exemption
  hid a false sentence (the three the drawings found, and 42 here)
- **Definitions change in the spec and not in the checks.** W1 replaced the
  own-steps definition in 108bab7; the test that checks ownTiles still uses
  the old one (97)
- **The fuzz graphs cover one reference sequence, one reference, no empty W
  line, and no path off every reference.** Claims 4, 17, 42 and 85 fail
  only outside that space, and the fixtures cover only some of it
- **Rewrites carry old sentences forward.** 4, 8, 102 and 105 came from
  format 5's docs (2026-10-20 and 21) and passed through the format 6 and
  format 7 rewrites, the last of them 514 lines in one commit (86d1006);
  76 and 93 were new sentences in that rewrite
- **Universal words cover the common case.** "Every file", "each of
  these", "one per contig", "R holds one node", "every row": each holds
  on MC chr22's ordinary tiles and fails on a 0 bp node, a second W line, a
  second sequence or a second reference

What would have caught them: a claims table like this one kept with the spec,
each row naming its check, and checks written from the spec's sentence,
not the writer's code. That means no exemptions, and fuzz graphs with several
sequences, two references, empty and abutting W lines, and 0 bp sequences.
