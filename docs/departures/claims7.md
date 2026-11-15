# Walk format 7's claims and their checks

The table below is kept with [walks-format.md](../walks-format.md): every
normative sentence there carries a claim ID, `<!-- C76 -->`, and has a row
here naming the check that tests it. ADR 0010 reuses the spec's IDs on its
matching sentences, and the README and ADR 0009 carry C114 and C91.
[check-claims.py](../../scripts/check-claims.py) fails CI when an ID has no
row, a row names no check or a check that doesn't exist, or a universal
sentence of the spec or ADR 0010 has no ID. After the table, the audit of
2026-11-06 that produced it: what it found false, how the sentences got
in, and the root cause.

- **Claim:** the sentence, abridged; the spec's text is the claim
- **Check:** what fails when the claim breaks, each written from the
  sentence and not from the writer's code, with no case exempted:
  `build:f`, function `f` of `src/` fails the build; `unit:f`, the unit
  test `f` of `src/`; `test:f`, function `f` of `tests/walks.rs`, where
  `verify` runs on every file a test builds; `claims7:ID`, a claim of
  [claims7.py](scripts/claims7.py), and `verify7:text` and `audit7:text`,
  a check of [verify7.py](scripts/verify7.py) or
  [audit7.py](scripts/audit7.py), which
  [check-walks.sh](../../scripts/check-walks.sh) runs in CI on every
  fixture under four option sets, audit7 given the fixture, and, through
  [fuzz7.sh](scripts/fuzz7.sh), on random graphs, each failing by its exit
  status; `graph-walks:title`, a test of graph-walks' format 8 reader, as
  [graph-walks-tests.txt](../walks-container/reader/graph-walks-tests.txt)
  lists them; `script:path`, the file that runs the check, or the fixture
  of `tests/data` whose run in check-walks.sh makes it fail when the claim
  breaks
- **Enforced by:** the code path that makes the claim hold
- **Result:** `holds`, with the commit that made it hold where the audit
  found the claim false or ambiguous, or that reworded it to what the
  writer does. C1 to C115 are the audit's inventory numbers (the ADR 0010
  and README numbers 107 to 115 restate spec claims and reuse their IDs,
  except C114); C116 and up are claims the spec pass found unnumbered

| ID | Claim | Check | Enforced by | Result |
|---|---|---|---|---|
| C1 | A reader rebuilds every piece of every path over a window from the tiles whose extents overlap it, an abridged piece by expanding its `detail` unit; each step sits on the pass the placement gave it, and the records give every departure the rows can't show | `test:every_path_rebuilds_from_its_rows` `test:every_path_rebuilds_from_its_detail_rows_when_abridged` `audit7:MISSING RECORD` `graph-walks:walkReader.test.ts: a cut reads the tiles and departure blocks its window overlaps, in one read where they touch, and a tile for the own steps of a record that leaves or rejoins on it alone: $window` `graph-walks:walkReader.test.ts: an expanded walk is read from its detail records as the unabridged file cuts it` `script:scripts/graph-walks-rebuild.mjs` `script:scripts/walks-truth.py` | `assign_chunks`, `encode_all`, `record_departures`; the reader | holds as reworded in ae7dada: the audit's #1 said every step, exactly from the tiles, which attach fetches and detail units belie |
| C2 | Every reference node and every record end states how many times the reference passes it | `claims7:R1` `claims7:D5` `audit7:state two pass counts` `audit7:stating fewer passes` `test:a_record_states_how_many_times_the_reference_passes_each_end` | `emit_rows`, `Departure::body` | holds |
| C3 | A tile holds R once, each distinct route once, and every other piece as its list of routes | `claims7:T2` `claims7:W1` `test:a_tile_holds_its_reference_its_routes_and_a_walk_row_per_piece` | `Routes::intern` | holds |
| C4 | A file lists every W or P line with a step on a node of its reference, the `--refs` samples' lines included; a line with none has no rows there, and its contig's other lines keep theirs | `test:assert_rebuilds` `test:a_line_on_one_references_nodes_is_in_that_references_file_alone` `test:a_contig_departs_once_from_each_w_line_to_the_next_with_a_step_on_r` `script:scripts/walks-truth.py` | `assign_chunks`, `cut_path` per line | holds since ae7dada: the audit's #4 said every file lists the same paths |
| C5 | A reader lists the haplotypes with rows in the file from the header, reading no tile | `claims7:H1` `graph-walks:walkReader.test.ts: the header names the format, the reference, the haplotypes, the tile size, the graph and the lines left out, read from byte 0 and no tile` | the `haplotypes` set in `run`; the reader | holds |
| C6 | The options table: `--refs`, `--tile`, `--sequences` and `--stay`, with the defaults 65536, 311, 1000000 and 3000000 | `test:the_defaults_are_65536_311_1000000_and_3000000` `test:each_reference_has_one_file_holding_only_its_rows` `test:sequences_adds_the_bases_of_ref_and_nodes_rows` `test:a_short_stretch_over_a_revisited_node_stays_in_its_piece_on_a_pass_there` | `main.rs` | holds |
| C7 | `--abridge-steps` moves a tile's costliest paths to its detail records until the rest cost at most n interior steps; 0 turns it off | `claims7:B2` `claims7:B3` `test:every_path_rebuilds_from_its_detail_rows_when_abridged` | `abridged_groups` | holds |
| C8 | `--abridge-bytes`: and until the rest compress to at most this many bytes, measured as Abridged tiles says | `claims7:B1` `test:a_tile_that_keeps_walk_rows_fits_its_budgets` | `abridged_groups`, `compressed_len` | holds since 3cb7aaa: the writer estimated the bytes and kept rows over the budget on 1 of 1,600 fuzz files |
| C9 | A file holds every sequence of its reference with a W or P line that has steps; the sequence's length is where its last line ends, which its table's `#unit` line states | `claims7:U8` `verify7:not 0 and` `test:a_w_line_with_no_steps_is_skipped` | `run` (`ends`), `UnitFile::table` | holds since d4af535 (the table states the length) and 16d8e0b (an empty line names no sequence) |
| C10 | Span: a walk row's, from the first base its steps placed on R cover to the last, over all of them; an abridged row's, from its first and last steps on R | `claims7:W4` `claims7:A1` | `encode_all`, `summary_row` | holds as reworded in ae7dada: the audit's #10 gave one span for both kinds, which 4,562 fuzz rows contradicted |
| C11 | Own steps: strictly between the leave step and the rejoin step | `claims7:O1` `test:a_record_names_the_tiles_holding_its_own_steps` | `record_departures` | holds; reworded when the tool began dropping 0 bp segments on read (C152) |
| C12 | Tiles of `tile` bp at multiples of `tile` | `claims7:U2` | `Chunks::new` | holds |
| C13 | A step on a reference node takes a pass, its position, and the tile holding the pass's start | `claims7:W1` `claims7:U2` `test:a_walk_back_into_a_tile_starts_a_new_piece_there` | `Chunks::of` | holds |
| C14 | Any other step takes the tile of the last step before it in its W line with a position, on any sequence, or of the first after it; a W line with no step on the reference has no tile | `claims7:O2` `test:a_path_off_every_reference_is_counted_and_left_out` `test:a_contig_that_leaves_a_sequence_for_good_has_no_record` | `assign_chunks` | holds |
| C15 | On the reference's own lines a step takes the tile holding its offset | `claims7:U2` `test:a_reference_files_its_own_revisits_at_its_own_offset` | `assign_chunks` | holds |
| C16 | `piece` numbers a W line's pieces from 0; a reader keys a piece by `path`, `fragStart` and `piece` and joins consecutive pieces | `claims7:W5` `graph-walks:walkRows.test.ts: continuation rows join by piece index, and a missing piece splits the walk` `script:scripts/walks-truth.py` | `write_pieces` | holds |
| C17 | The tool refuses two lines of a `path` with steps, W or P, that overlap or start at the same base | `test:records_of_a_contig_that_overlap_or_share_a_start_are_refused` `test:an_overlap_refusal_says_vg_numbers_phase_blocks_where_this_tool_reads_starts` `test:a_w_line_with_no_steps_is_skipped` | `link_records`, `collision` | holds since 16d8e0b: the audit's #17 held for lines with steps only, which the sentence now says |
| C18 | The tool refuses a W line whose end column is not its start plus its nodes' lengths | `test:a_w_line_whose_end_disagrees_with_its_steps_is_refused` | `record` | holds |
| C19 | The lines are the same for any order of the W lines | `test:the_order_of_the_paths_changes_no_row` | `Stable`, the sorts | holds |
| C20 | A W or P line with steps but none on a node of a reference has no rows there, and is counted on stderr | `test:a_path_off_every_reference_is_counted_and_left_out` | `assign_chunks` | holds |
| C21 | The nearest pass on the same sequence to the predicted offset, the lower offset on a tie, or the node's first pass: the pass of the line whose name sorts first in bytes, at its lowest offset | `test:a_step_takes_the_lower_pass_on_a_tie_and_the_first_pass_where_its_sequence_has_none` `test:a_route_exit_names_the_copy_where_it_is_not_the_nearest_and_a_block_lies_on_it` | `visit_near`, `first_visit` | holds as reworded in ae7dada: the audit's #21 said "the first pass", undefined |
| C22 | Placing starts at the line's first step on a node the reference passes once, or on any reference node, and runs outward both ways | `test:a_walk_row_names_the_copy_it_starts_on_where_it_is_not_the_first` | `visits_along` | holds |
| C23 | The stay: a run stays home when the path returns, it holds at most `stay` bp of reference nodes, none passed once, and each step on a node of the home R has a pass within `stay` bp of its prediction; such a step moves to the nearest, lower on a tie; a node R lacks is interior; any other run starts a piece; the reference's own lines are exempt | `test:a_short_stretch_over_a_revisited_node_stays_in_its_piece_on_a_pass_there` `test:a_stay_refuses_a_stretch_over_a_node_the_reference_passes_once` `test:a_reference_files_its_own_revisits_at_its_own_offset` | `stay_home`, `rehome` | holds |
| C24 | A reference passing each node once gets the same rows at any `stay` | `test:a_stay_leaves_a_reference_that_passes_each_node_once_alone` | follows from C23 | holds |
| C25 | The walk row states each step's position, so a reader never chooses a pass, and the build fails if a row decodes to another node or position; a row's `start end` is the span of the decoded positions | `build:encode_all` `build:summary_row` `claims7:W4` `graph-walks:walkReader.test.ts: a walk row takes the passes its :k, @k and start@k name, and the defaults where it names none` | `encode_all` (`decodes_to`) | holds |
| C26 | A step the placement leaves off the reference is route interior, only where its tile has no pass of its node: no route interior holds a node of its own tile's R | `build:encode_all` `claims7:W1` `claims7:N5` | `encode` | holds |
| C27 | Under nearest-pass placement no step on a node the reference passes once is route interior (ADR 0009) | `claims7:N2` | `visits_along`, `rehome` | holds |
| C28 | The data file is a series of units, then a BGZF EOF block | `verify7:no EOF block at the end` `test:verify` | `UnitFile` | holds |
| C29 | Each unit is a whole run of gzip members: it starts and ends a member | `build:starting` `verify7:belongs to no unit` `test:verify` | `UnitFile::end` cuts | holds |
| C30 | The header unit is first, from byte 0, with no `#unit` line; `#walks` is its first line, which a reader matches against the directory's line 1 | `verify7:a header line that is not a header line` `test:verify` `verify7:ends inside the member` `verify7:line 1 differs from the header` `script:docs/departures/scripts/broken/cases.tsv` `graph-walks:walkReader.test.ts: a directory and data that disagree are refused by %s` | `UnitFile::start`; verify7 and spec8 fail broken/line-before-walks, a header line before `#walks` | holds |
| C31 | Sequences in byte order of their names | `claims7:U1` `test:verify` `script:tests/data/walks-sequences.gfa` | `Chunks::new` | holds |
| C32 | Per sequence: its tile and departures units in order of a tile's name and a block's start, then its detail units, a tile's followed by its blocks unit, then its table | `claims7:U1` `test:a_blocks_unit_follows_its_tiles_detail_units` | `Outputs` | holds |
| C33 | At one start a tile before the departure bins that start there, and smaller bins before larger | `claims7:U1` | `Outputs::tile`, the departure sort key | holds |
| C34 | Every unit but the header starts with `#unit seq start end kind name` | `verify7:belongs to no unit` `test:verify` `graph-walks:walkReader.test.ts: a tile with %s is refused` | `UnitFile::begin` | holds |
| C35 | A tile unit: its extent; named by its start in decimal with no leading zero; its ref, nodes, route, walk and abridged rows | `claims7:U2` `claims7:U3` `claims7:U9` | `Outputs::tile` | holds |
| C36 | A departures unit: the bin; named `.`; one bin's records | `verify7:is not aligned` `claims7:U9` `test:a_departure_block_is_named_dot_and_every_other_name_is_unique` | `Outputs::departures` | holds |
| C37 | A detail unit: from the first base its walk rows' spans cover to the last; named `cs:d`; one W line's moved pieces | `verify7:has extent` `claims7:A2` `claims7:A4` `test:an_abridged_row_stands_for_one_piece_and_names_its_detail_record` | `unit_of`, `Details::flush` | holds |
| C38 | A table: 0 to the sequence's length; named `.`; one `#entry` per unit | `claims7:U8` `verify7:does not list its units` | `UnitFile::table` | holds since d4af535: the audit's #38 said 0 to the units' largest end |
| C39 | A unit's name is the key other lines point at it by, `.` where none does; every other name is unique within its kind and sequence | `build:table` `verify7:units of {seq} named` `test:a_departure_block_is_named_dot_and_every_other_name_is_unique` | `UnitFile::table` | holds |
| C40 | A tile's extent runs from the first base of its ref rows' steps to the last, over any gap between two lines of the reference | `claims7:U3` `verify7:has extent` `test:verify` | `unit_of` | holds as reworded in ae7dada: the audit's #40 said "union", which 166 fuzz tiles with a gap contradicted; reworded when the tool began dropping 0 bp segments on read (C152) |
| C41 | Every piece's span lies inside the tile's extent, since every placed step is on R | `build:unit_of` `verify7:outside its unit` `verify7:where its` `claims7:U3` `claims7:W4` | `unit_of` | holds |
| C43 | Pyramid bins of `tile × 8^L` for L 0 to 3, aligned; a record's cover from `floor(start / tile) × tile` to `ceil(end / tile) × tile`, in the largest aligned bins | `build:cover` `verify7:where a larger one fits` `verify7:no aligned pyramid block` `verify7:uncovered or overlap` `script:tests/data/walks-long-jump.gfa` | `departures::cover` | holds; reworded when the tool began dropping 0 bp segments on read (C152) |
| C44 | Within a bin lines are in order of `start`, `end`, then text | `claims7:U6` | the departure sort key | holds |
| C45 | A table lists each unit of its sequence before it, in file order, as its `#unit` columns, byte offset and length, decimal integers below 2^53, each length above 0 | `build:table` `verify7:does not list its units` `verify7:lists a unit of 0 bytes` `test:verify` | `UnitFile::table` | holds |
| C46 | Every sequence in the file has at least one tile, so no table is empty | `claims7:U10` `test:a_w_line_with_no_steps_is_skipped` | `first_pass` skips a line with no steps; `unit_of` fails a tile with no ref row | holds since 16d8e0b: the audit's #46 said a sequence with no units has an empty table |
| C47 | Directory line 1 is the `#walks` line plus `bytes:i:` | `verify7:bytes:i: is` `verify7:ends inside the member` `verify7:runs past the units` `test:verify` | `UnitFile::finish` | holds |
| C48 | One `seq offset length` line per reference sequence, every one listed, in file order | `verify7:is not the directory` `test:verify` | `UnitFile::table` | holds |
| C49 | `format:i:8` marks this format; a reader refuses any other; a file that breaks an invariant of What a reader relies on, or holds a row kind the page doesn't give in a unit it does, is not format 8 | `test:a_walk_file_names_its_format_reference_and_each_haplotype_with_rows` `claims7:U9` `graph-walks:walkReader.test.ts: a walk file whose directory states $walks is refused as format $format, with what to rebuild it with` `graph-walks:walkReader.test.ts: a format %i walk file is refused, asking for a newer reader` | the header in `run`; the reader | holds; reworded with ADR 0013, when placement became this writer's policy and the invariants the format |
| C50 | `revisited` counts the nodes the reference's paths pass more than once, all sequences counted | `audit7:header revisited differs` `test:a_pass_count_counts_every_sequence_of_the_reference` | `visits_of.len()` | holds |
| C51 | `#haplotype` lists what each other path with rows is listed under, once each in byte order: `sample#haplotype` of three fields or more, the sample of fewer | `claims7:H1` `test:a_haplotype_with_two_contigs_is_listed_once` `test:a_p_line_reads_the_same_before_its_segments_as_after_them` `unit:a_p_line_name_reads_as_the_shared_table_says` | the `haplotypes` set, `haplotype` | holds; a `path` of two fields is listed under its sample since ADR 0014 |
| C52 | `#hole`: each stretch of a reference sequence no line covers, `start` below `end`, in order of name in bytes then start, none overlapping | `claims7:G5` `script:tests/data/walks-sequences.gfa` `test:steps_either_side_of_a_hole_in_the_reference_are_adjacent` | `Holes::between`, the sort in `run` | holds; the order was unstated before ae7dada |
| C53 | `revisited:i:0` states every position and every departure as a fact of the graph | `claims7:H2` | follows from the placement | holds |
| C54 | Every line not starting with `#` begins `seq start end kind` | `claims7:U9` `verify7:a line of another sequence` `test:verify` | `unit_of`, `Outputs::departures` | holds |
| C55 | A walk row's `start end` is the span of all its placed steps; interiors holding another tile's reference nodes lie outside it | `claims7:W4` `build:encode_all` `audit7:start end differ from the span` | `encode_all` | holds |
| C56 | An abridged row's `start end` is the span of its first and last steps on R, as `start` and `end` decode | `claims7:A1` `build:summary_row` `claims7:A1` `claims7:A8` | `summary_row` | holds; ADR 0010's #109 said the moved piece's stretch, which the coordinator aligns |
| C57 | `ref`, `nodes` and `route` rows state the unit's extent | `verify7:not stating its unit` `test:verify` | `unit_of` | holds |
| C58 | A departure line's `start end` runs from the first base of its leave or rejoin node to the last base of the other, or the breakpoint stretch where wider | `claims7:D6` `claims7:D3` `audit7:breakpoints lie outside` `test:a_path_that_jumps_over_the_reference_has_a_departure_record_over_the_stretch` | `Departure::extent` | holds |
| C59 | A tile lists its ref rows, at most one nodes row, its route rows, its walk rows, then its abridged rows | `claims7:U5` | `write_chunk`, `emit_rows` | holds |
| C60 | A handle is `2 × id + r`; a list of handles is delta tokens, the first from 0 unless a row says otherwise; an empty list is `.` | `claims7:W1` `claims7:R1` `test:deltas` | `delta_steps`, `push_list` | holds |
| C61 | One ref row per piece of the reference's own lines in the tile, at least one per tile, all pieces of S | `claims7:R3` `test:p_lines_give_the_rows_w_lines_do` `test:a_reference_files_its_own_revisits_at_its_own_offset` `script:scripts/walks-truth.py` | `write_pieces`, `unit_of` | holds |
| C62 | `passes` has one count per step, all sequences counted, or is `.` exactly when every one is 1 | `claims7:R1` `audit7:state two pass counts` `audit7:stating fewer passes` `test:a_pass_count_counts_every_sequence_of_the_reference` | `emit_rows` | holds |
| C63 | R is every ref row's steps joined in `hapOffset` order; positions count from 0, each with its offset | `claims7:R2` `claims7:W1` `graph-walks:walkReader.test.ts: a tile's R joins its ref rows in hapOffset order` `script:scripts/walks-truth.py` | `write_chunk` sorts by offset | holds |
| C64 | The nodes row lists the route interiors' nodes, ascending, and no other; a tile or detail unit has one exactly when a route has an interior step | `claims7:N1` `claims7:A6` | `emit_rows` | holds |
| C65 | `SQ:Z:` holds the bases, in id order on a nodes row and in step order, forward, on a ref row; `--sequences` refuses a `*` segment | `audit7:SQ:Z: differs from its nodes` `test:sequences_adds_the_bases_of_ref_and_nodes_rows` `test:sequences_refuses_a_segment_with_no_bases` | `emit_rows`, `first_pass` | holds |
| C66 | `entry` or `exit` is `.` for a route starting or ending the piece off R, which has an interior step; `interior` is `.` for a direct route | `claims7:T3` `test:a_tile_holds_its_reference_its_routes_and_a_walk_row_per_piece` `test:a_walk_row_names_the_copy_it_leaves_r_from_where_stepping_would_stop_early` | `encode` | holds |
| C67 | Route tokens chain across columns and rows; the tile's first route row starts from 0 | `claims7:W1` `test:decode_file` | `emit_rows` | holds |
| C68 | A route is stored the way round whose handles sort first; its flip is the reverse | `claims7:T1` `claims7:T2` | `Routes::intern` | holds |
| C69 | A walk row's `startHandle` is the piece's first handle on R, absolute; every piece has one | `claims7:W1` `build:encode_all` | `encode` | holds |
| C70 | `@k` and `:k`: their defaults, written only where they differ, so a file has one encoding, and none on a reference that passes every node once | `claims7:W2` `test:a_walk_row_names_the_copy_it_starts_on_where_it_is_not_the_first` `test:a_route_exit_names_the_copy_where_it_is_not_the_nearest_and_a_block_lies_on_it` `test:a_walk_row_names_the_copy_it_leaves_r_from_where_stepping_would_stop_early` | `encode` | holds |
| C71 | The walk continues along R only where R's next position is the step's, and otherwise takes a route; after its last route it follows R to `nsteps` | `claims7:W3` `claims7:W1` | `encode` | holds |
| C72 | One abridged row per moved piece, the leading columns of its detail walk row, its bp on its contig and the record's number; a reader keys it as a walk row, so every piece of a line has one row in its tile, walk or abridged | `claims7:W5` `test:an_abridged_row_stands_for_one_piece_and_names_its_detail_record` | `write_chunk` | holds |
| C73 | An abridged row's `start end`, `hapOffset` and `nsteps` are the piece's, as its walk row states them: the span of its steps on R, where it starts on its contig, and its steps | `claims7:A1` `claims7:A8` `audit7:abridged rows unlike the hapOffset` `test:decode_file` `test:an_abridged_row_spans_its_piece_from_its_first_step_on_r_to_its_last` | `summary_row` | holds |
| C74 | A record's leave step is the last step on R of its piece and its rejoin step the first on R of its piece | `claims7:L1` `graph-walks:walkRows.test.ts: a record's own steps come from its leave and rejoin pieces, and a record lacking either is asked for` | `record_departures` | holds |
| C75 | From `nsteps`, all the piece's steps, a reader learns the cost of expanding the piece before it reads the detail unit | `claims7:A8` `audit7:abridged rows unlike the hapOffset` `test:decode_file` `test:an_abridged_row_spans_its_piece_from_its_first_step_on_r_to_its_last` | `summary_row` | holds |
| C76 | `detail` names the tile's record holding the piece's walk row; a W line's moved pieces in one tile share one record, one record per W line | `claims7:A3` `claims7:A4` `test:an_abridged_row_stands_for_one_piece_and_names_its_detail_record` | `abridged_groups` by `(path, fragStart)` | holds since ae7dada: the audit's #76 said one record per contig, which 170 tiles of MC chr22 contradicted |
| C77 | A record for each departure between two pieces, and none for one inside a piece | `audit7:MISSING RECORD` `audit7:recorded though the reader computes it` `test:a_departure_between_pieces_has_a_record_and_one_inside_a_piece_has_none` | `record_departures` | holds |
| C78 | Departures are per sequence, steps on other sequences counted as own; a contig's W lines are one path in start order | `audit7:MISSING RECORD` `test:a_contig_departs_once_from_each_w_line_to_the_next_with_a_step_on_r` | `contig_after` | holds |
| C79 | `Pos`, `Strand` and `Passes` of each end | `audit7:field mismatch` `claims7:O1` `test:a_record_states_how_many_times_the_reference_passes_each_end` | `step_end` | holds |
| C80 | `hapStart`, `ownBp` and `missingBp` | `audit7:field mismatch` `claims7:O4` `test:a_contig_departs_once_from_each_w_line_to_the_next_with_a_step_on_r` | `record_departures`, `contig_after` | holds |
| C81 | Adjacent steps depart nowhere | `test:a_step_on_a_node_of_0_bp_between_two_lines_is_no_departure` `test:steps_either_side_of_a_hole_in_the_reference_are_adjacent` `audit7:records with no recomputed departure` | `Holes::adjacent` | holds; reworded when the tool began dropping 0 bp segments on read (C152) |
| C82 | A contig's sequence before its first step on S or after its last has no record | `test:a_contig_that_leaves_a_sequence_for_good_has_no_record` `audit7:records with no recomputed departure` | `record_contig_departures` | holds |
| C83 | A record's extent runs from the first base of its end nodes, each at its pass, to the last base of the other | `claims7:D6` `claims7:D3` | `Departure::extent`, `step_end` | holds; reworded when the tool began dropping 0 bp segments on read (C152) |
| C84 | `ownTiles` lists the tiles of S holding the record's own steps, by start, in the path's order, `.` for none | `claims7:O1` `claims7:D1` `test:a_record_names_the_tiles_holding_its_own_steps` `test:own_tiles` | `tiles_of` | holds |
| C85 | An own step on no reference node takes the tile of the last step before it with a position: the leave's, unless a step on another sequence comes between | `claims7:O2` | `assign_chunks` | holds since ae7dada: the audit's #85 said the leave's tile always, which E2 contradicted |
| C86 | Own steps leading the next W line take the tile of the first step after them with a position, the rejoin's unless a step on another sequence comes first; a record can have both tiles, the leave's first | `claims7:O2` `claims7:D2` `test:a_record_names_the_tiles_holding_its_own_steps` | `record_contig_departures` | holds |
| C87 | Own steps on other sequences lie in those sequences' tiles; own steps in a W line with no reference step and own sequence in no W line are in no tile; `ownTiles` lists none, and an attach fetch doesn't read them | `claims7:O1` `claims7:O4` `test:a_step_takes_the_lower_pass_on_a_tie_and_the_first_pass_where_its_sequence_has_none` `graph-walks:walkReader.test.ts: a leave piece the read lacks is fetched for the own steps, once per tile, within the byte budget` | `tiles_of` filters by S | holds as reworded in ae7dada: the audit's #87 didn't say where such steps lie |
| C88 | The record's line is in every bin of its cover, the same text in each; a reader drops exact duplicates | `build:close_before` `verify7:not its cover` `test:verify` `graph-walks:walkReader.test.ts: a cut returns every record whose line overlaps its window, in a hole too: $start-$end` | `Departure::file` | holds |
| C89 | Every departure line overlaps each bin it is in; every record is in every bin of its cover and no other | `claims7:U7` `build:departures` `build:close_before` `verify7:not overlapping its block` `verify7:not its cover` `test:verify` | `Outputs::departures` | holds; reworded when the tool began dropping 0 bp segments on read (C152) |
| C91 | The ref rows of S hold one node ending at a `+` leave's or `-` rejoin's breakpoint and one starting at the other kind's | `claims7:D4` | construction | holds since ae7dada: the audit's #91 said one node, which 11,029 fuzz ends contradicted; ADR 0009's sentence says the same since c6bd91f; reworded when the tool began dropping 0 bp segments on read (C152) |
| C92 | Every row of one record repeats the same columns (ADR 0009) | `build:close_before` `verify7:not its cover` `test:verify` `graph-walks:walkReader.test.ts: a cut returns every record whose line overlaps its window, in a hole too: $start-$end` | `Departure::file` | holds |
| C93 | The header, the units, the tables and the EOF block partition the file; every unit starts and ends a gzip member and starts with its `#unit` line | `build:starting` `verify7:belongs to no unit` `verify7:units after the last table` `verify7:no BGZF member` `test:verify` | `UnitFile` | holds since d4af535 and ae7dada: the audit's #93 said the tool checks each guarantee, which it didn't |
| C94 | Each table lists every unit of its sequence in file order before it, with lengths above 0, and states the sequence's length; the directory lists every sequence | `build:table` `claims7:U8` `verify7:does not list its units` `test:verify` `verify7:ends inside the member` | `UnitFile::table` | holds |
| C95 | Path names hold no tab, newline or NUL byte and don't start with `#`; the build refuses one that starts with `#` or holds a NUL byte | `build:named` `test:a_path_name_starting_with_a_hash_is_refused` `test:a_hash_in_a_w_lines_sample_or_haplotype_is_refused` | `named`, `path_line` | holds |
| C96 | The data file is written under a temporary name and renamed, then the directory likewise | `build:finish` `test:a_failed_write_leaves_no_temporary_file` | `Temp` | holds |
| C97 | Each record's `ownTiles` are the tiles of S holding its own steps, in the path's order | `test:own_tiles` `claims7:O1` | `tiles_of` | holds since 904d2fb: the test took own steps by bp range |
| C98 | Offsets and lengths are the BGZF writer's u64 block starts in decimal; a unit test writes blocks past 2^31, 2^32 and 2^40 | `unit:offsets_past_2_to_the_31_and_32_round_trip` | `parallel_bgzf` | holds |
| C99 | A piece costs its routes' interior steps once per use plus a quarter of all its steps | `claims7:B2` | `piece_cost` | holds |
| C100 | Over `abridge`, or over `abridgebytes` bytes of kept rows from `kind` on, uncompressed, whole W lines' pieces move, costliest first, the fewest that bring the rest within both, or all | `claims7:B1` `claims7:B2` `claims7:A4` `claims7:A7` `test:a_tile_that_keeps_walk_rows_fits_its_budgets` `test:every_path_rebuilds_from_its_detail_rows_when_abridged` `claims7:B3` `script:tests/data/walks-abridge-bytes.gfa` | `abridged_groups`, `compressed_len` | holds since 3cb7aaa |
| C101 | The tile keeps its ref rows, its other pieces' nodes, route and walk rows encoded without the moved pieces, and an abridged row per moved piece with where it starts on its contig, its steps, its bp and its detail record | `claims7:T5` `claims7:N1` `claims7:A1` `claims7:W5` `claims7:A9` | `write_chunk` | holds |
| C102 | A record holds at most one nodes row, one exactly when its routes have an interior step, then route rows and walk rows | `claims7:A6` `claims7:U5` | `emit_rows` | holds since ae7dada: the audit's #102 said a nodes row always, which 5,309 fuzz records contradicted |
| C103 | A record's routes number from 0 and chain from 0; its walk rows decode against the R of tile `cs` | `claims7:W1` `test:every_path_rebuilds_from_its_detail_rows_when_abridged` `audit7:abridged rows whose piece is not in the detail record` | `write_chunk` | holds |
| C104 | The Example's lines are the tool's for walks-two-refs.gfa at `--tile 10 --stay 0`, and read as described | `test:the_specs_example_quotes_the_tools_lines` | | holds |
| C105 | The tool reads the GFA more than once, so it takes a file path and refuses stdin; gzip input works | `test:walks_reads_a_file_not_stdin` `test:gzipped_input_gives_the_same_rows` `test:the_order_of_the_paths_changes_no_row` | `first_pass`, `run` | holds as reworded in ae7dada: a6fce8e said twice or three times, a count no test can see |
| C106 | Sorts wait in up to 512 MB and 128 MB of memory, then in compressed runs in a temporary directory beside the output | `unit:the_sorts_wait_in_512_and_128_mb` `test:a_failed_write_leaves_no_temporary_file` | `SORT_BUDGET`, `DEPARTURE_SORT_BUDGET`, `TempDir` | holds |
| C112 | The build decodes every walk row and compares, and gives an abridged row the span of its piece's blocks; no other row's `start end` is checked at build | `build:encode_all` `build:summary_row` `verify7:not stating its unit` `claims7:D6` `test:verify` | `encode_all`, `summary_row` | holds since d4af535 and ae7dada: ADR 0010's #112 said every row |
| C114 | A file is a series of gzip units: the header, then per sequence its tiles, departure bins, detail units and table (README, as the coordinator rewords it) | `claims7:U1` `claims7:U9` `verify7:does not list its units` | `Outputs` | holds as reworded: the audit's #114 said a unit per tile and per block only |
| C116 | Together the files hold every W or P line with a step on a node of that reference, cut into pieces filed under its tiles | `test:assert_rebuilds` `claims7:W5` `script:scripts/walks-truth.py` | `assign_chunks`, `cut_pieces` | holds |
| C117 | An attach fetch reads the tiles `ownTiles` names, for a record whose leave or rejoin piece the read lacks, and takes its own steps and nothing else | `graph-walks:walkReader.test.ts: a tile fetched to attach gives its record the own steps and nothing else: $opts` `graph-walks:walkReader.test.ts: a leave piece the read lacks is fetched for the own steps, once per tile, within the byte budget` | the reader | holds |
| C118 | A W or P line with no steps is skipped once its end is checked: no rows, record or `#hole`, it names no sequence, is not counted on stderr, and the overlap refusal doesn't apply | `test:a_w_line_with_no_steps_is_skipped` | `first_pass` | holds since 16d8e0b |
| C119 | A reader places a node at a reference position from a ref row it read whenever one exists: a pass over `D` first, then the path sorting first at its earliest start; other nodes take haplotype offsets | `graph-walks:walkRows.test.ts: a node's reference position wins, whichever chunk is read first` `graph-walks:walkRows.test.ts: a node's pass over the window wins over the reference's other passes, whichever is read first` `graph-walks:walkRows.test.ts: off the window, a node takes the reference row whose path sorts first, then its earliest start, whichever is read first: reversed %s` `graph-walks:walkReader.test.ts: keeps its reference position, in whichever order the chunks come` | the reader | holds |
| C120 | `passes`, `leavePasses` and `rejoinPasses` say which steps and ends lie on revisited nodes; a reader states a departure with such an end as a placement choice | `claims7:R1` `claims7:D5` `graph-walks:walkDeparture.test.ts: a departure is a placement choice where either end lies on a node the reference passes more than once` `graph-walks:walkReader.test.ts: a departure computed from steps takes its ends' pass counts from the ref rows` `claims7:H2` `audit7:field mismatch` | `emit_rows`, `Departure::body`; the reader | holds |
| C122 | A reader refuses a directory whose line 1 differs from the header's or whose `bytes` differs from the data's length; one that can't learn the length skips that check | `graph-walks:walkReader.test.ts: a directory and data that disagree are refused by %s` `graph-walks:walkReader.test.ts: a reader that cannot learn the data's length skips the directory's bytes check` | the reader | holds |
| C123 | A unit kind this page doesn't give is a later addition, which a reader skips | `graph-walks:walkReader.test.ts: a unit of a kind the reader does not know is skipped` | the reader | holds |
| C124 | Later additions are tags, header lines, unit kinds or files, and a reader of format 8 reads a file that has them as it reads one that doesn't | `graph-walks:walkReader.test.ts: tags a reader does not know are ignored on any row and header line` `claims7:G6` `script:docs/departures/scripts/spec8.py` `script:docs/departures/scripts/repack.py` `verify7:a directory line of a sequence` | the reader | holds; the checkers brought in line with it after a review repacked a file with each kind of addition |
| C125 | A tile's walk rows are in order of `path` in bytes, then `fragStart`, `hapOffset` and `piece` | `claims7:G1` | the sort key in `PieceRef::write` | holds |
| C126 | Every id is below 2^31; the tool refuses a GFA with a larger one | `claims7:G4` `build:node_id` `test:a_node_id_of_2_to_the_31_is_refused` | `node_id` | holds |
| C127 | Ref rows in `hapOffset` order, each piece's steps starting in `[name, name + tile)` | `claims7:R2` `claims7:U2` | `write_chunk`, `Chunks::of` | holds |
| C128 | `entry` and `exit`, where given, are on R | `claims7:T4` | `encode` | holds |
| C129 | A route's id is its row index; rows are in order of the first position in R of their entry's or exit's node, a route with neither last, then by `entry`, `interior` and `exit` | `claims7:T6` `claims7:W1` | `emit_rows` | holds |
| C131 | A tile's records are numbered from 0, the costliest line first | `claims7:A5` `claims7:A7` | `write_chunk` | holds |
| C132 | An attach fetch takes the record's own steps from the tiles `ownTiles` names: the steps after the leave and before the rejoin, from `hapStart` over `ownBp`; nothing else joins a fragment or yields a departure | `graph-walks:walkReader.test.ts: a tile fetched to attach gives its record the own steps and nothing else: $opts` `graph-walks:walkReader.test.ts: a record over a 0 bp segment alone holds no step, cut $start-$end` `graph-walks:walkReader.test.ts: a jump back whose own steps lie in the rejoin piece gets them attached where it leaves or rejoins on the window, cut $start-$end` | the reader | holds; reworded when the tool began dropping 0 bp segments on read (C152) |
| C133 | For a piece an attach fetch finds abridged it builds the record's own run from the `abridged` row and the record by the attach rule, with no `blocks` read; where the cut expands that path it reads the piece's detail unit | `claims7:A13` `claims7:O5` `test:twin_graphs_differ_in_hap_bp_alone_in_their_tiles_and_records` `graph-walks:walkReader.test.ts: an attach fetch reads an abridged piece's own steps where the cut expands the walk, and else holds a placeholder for them: $steps` | the reader | holds of the file since ADR 0013, which made the run a fact of the row and the record; graph-walks reads a `blocks` unit there until its own change lands |
| C134 | The read selects tile and departures units with `start < D.end` and `end > D.start`, skips length 0, merges touching ranges, and GETs each as one single-range request | `graph-walks:walkReader.test.ts: a cut reads the tiles and departure blocks its window overlaps, in one read where they touch, and a tile for the own steps of a record that leaves or rejoins on it alone: $window` `graph-walks:walkReader.test.ts: a table entry of length 0 is never read: $at` `graph-walks:walkReader.test.ts: a cut reads the tiles its window overlaps, and nothing else` | the reader | holds |
| C135 | A cut returns every piece over `D`, every record whose line overlaps `D`, each once, and every departure it computes inside one piece over the drawn stretch; one between pieces is a record, so none comes twice | `graph-walks:walkReader.test.ts: a cut returns every record whose line overlaps its window, in a hole too: $start-$end` `graph-walks:walkReader.test.ts: a cut computes no departure outside its drawn stretch, even inside a fragment` `graph-walks:walkRows.test.ts: a departure between the pieces of one run comes from the records, not the steps` | the reader | holds |
| C136 | No two units of a kind and sequence share a name other than `.` | `build:table` `verify7:units of {seq} named` `test:a_departure_block_is_named_dot_and_every_other_name_is_unique` | `UnitFile::table` | holds |
| C137 | A tile's extent runs from the first base of its ref rows' steps to the last; every tile, detail and blocks line lies within its unit | `claims7:U3` `claims7:U4` `build:unit_of` `verify7:outside its unit` `test:verify` `verify7:where its` | `unit_of` | holds since 15178df; reworded when the tool began dropping 0 bp segments on read (C152) |
| C138 | A record's leave step is the last on R of its piece and its rejoin the first | `claims7:L1` | `record_departures` | holds |
| C139 | The rows' order, names and encoding: walk rows in path order; decimal tile names; a ref row of S per tile with steps in `[name, name + tile)`; one W line per detail unit; a route with no entry or exit has an interior and its ends are on R; ids below 2^31; `#hole` lines sorted and disjoint | `claims7:G1` `claims7:U2` `claims7:R3` `claims7:A4` `claims7:T3` `claims7:T4` `claims7:G4` `claims7:G5` `build:node_id` | the sorts, `Chunks::of`, `abridged_groups`, `encode`, `node_id`, `Holes::between` | holds |
| C140 | A line left out of a reference's file is one W or P line; its contig's other lines keep their rows | `test:a_contig_departs_once_from_each_w_line_to_the_next_with_a_step_on_r` `test:assert_rebuilds` | `cut_path` per line | holds |
| C141 | The decoding rules: along R forward or backward, each route the way round its flip says, the entry reached by stepping or `:k`, the exit nearest or `@k`, then R to `nsteps`; every handle on R emitted with its position | `claims7:W1` `test:decode_walk` `build:encode_all` `graph-walks:walkReader.test.ts: a walk row takes the passes its :k, @k and start@k name, and the defaults where it names none` | `decode` | holds |
| C142 | On HPRC v2.1's Minigraph-Cactus chr22, GRCh38 passes no node twice and no walk row needs `@k` or `:k` | `claims7:H2` | the graph | holds on MC chr22's file, `revisited:i:0`, in 8279ebd's audit |
| C143 | The command writes a data file and its directory per `--refs` sample, and no other file | `test:each_reference_has_one_file_holding_only_its_rows` `test:build` | `run` | holds |
| C144 | The drawn stretch is the reference's nodes over `D`, whole, widened by every pass of a walk's step over them | `graph-walks:walkReader.test.ts: a cut's drawn stretch takes every pass over the window, not one per node` `graph-walks:walkReader.test.ts: a cut reads the chunks under its context, not only under its window` | the reader | holds |
| C145 | Readers address tiles by extent, never by `floor(base / tile)` | `graph-walks:walkReader.test.ts: a node longer than a tile is read from the tile whose extent holds it` | the reader | holds |
| C146 | `lengths` lists each step's node length in bp | `claims7:R1` `test:sequences_adds_the_bases_of_ref_and_nodes_rows` `test:the_specs_example_quotes_the_tools_lines` `script:scripts/walks-truth.py` | `emit_rows` | holds |
| C147 | One walk row per piece of every other line, the other references' included | `claims7:W5` `test:a_walk_file_names_its_format_reference_and_each_haplotype_with_rows` `test:a_tile_holds_its_reference_its_routes_and_a_walk_row_per_piece` `script:scripts/walks-truth.py` | `write_chunk` | holds |
| C148 | `choices` lists the routes in order, `.` for none, each token `2 × (route id − previous) + flip`, the first from 0 | `claims7:W1` `test:decode_walk` | `encode` | holds |
| C149 | Gunzip each unit; decode a tile's rows from `kind` on; keep the departure lines overlapping `D` and drop exact duplicates | `graph-walks:walkReader.test.ts: a cut keeps the departure lines overlapping its window, of the blocks it reads: 0-$end` `graph-walks:walkReader.test.ts: a cut returns every record whose line overlaps its window, in a hole too: $start-$end` | the reader | holds |
| C150 | The moved pieces' rows go to the detail unit `cs:d`; a window read names tile and departures units only, an attach fetch tiles only; a viewer reads a detail record when it expands that path | `claims7:A2` `graph-walks:walkReader.test.ts: a cut reads the tiles and departure blocks its window overlaps, in one read where they touch, and a tile for the own steps of a record that leaves or rejoins on it alone: $window` `graph-walks:walkReader.test.ts: an expanded walk is read from its detail records as the unabridged file cuts it` `graph-walks:walkReader.test.ts: an attach fetch reads an abridged piece's own steps where the cut expands the walk, and else holds a placeholder for them: $steps` | `Details::flush` | holds |
| C151 | A guarantee names its check: build; tests, on every file the tests build; or files, which `check-walks.sh` runs in CI on every fixture under four option sets and on random graphs | `script:scripts/check-walks.sh` `script:scripts/check-claims.py` `script:.github/workflows/push.yml` | | holds |
| C152 | The tool drops every segment of 0 bp as it reads the GFA: its steps leave every W and P line, a line left with no steps is skipped, and a sequence left with no bases has no units and no directory line | `test:steps_of_0_bp_with_the_same_departure_text_twice_build` `test:a_node_of_0_bp_passed_twice_at_one_offset_leaves_the_lines` `test:a_reference_line_of_0_bp_after_the_last_is_no_line` `test:a_reference_line_of_0_bp_inside_a_hole_is_no_line` `test:a_reference_step_of_0_bp_widens_no_tile` `test:reference_steps_of_0_bp_alone_make_no_tile` `test:a_line_of_0_bp_inside_another_is_no_overlap` `test:a_sequence_of_0_bp_has_no_units_and_steps_of_0_bp_make_no_tile` `test:a_step_on_a_node_of_0_bp_between_two_lines_is_no_departure` `script:scripts/walks-truth.py` | `first_pass`, `Builder::path` | holds
| C153 | Each `--walks` option takes at most 2^40, refused above | `test:each_walks_option_takes_at_most_2_to_the_40` | `cli.rs`, `WALK_OPTION_MAX` | holds |
| C154 | A reader refuses a unit whose `#unit` line doesn't state its table entry's `seq start end kind name`, or whose text doesn't end in a newline | `graph-walks:walkReader.test.ts: a tile with %s is refused` `graph-walks:walkReader.test.ts: a tile cut partway through a gzip member is refused` | the reader | holds |
| C155 | A reader refuses a row of another sequence, or of a kind its unit doesn't hold: tile ref, nodes, route, walk, abridged; departure bin departure; detail nodes, route, walk | `graph-walks:walkReader.test.ts: a tile with %s is refused` `graph-walks:walkReader.test.ts: a %s unit holding a row of a kind it does not hold is refused` `claims7:U9` `verify7:a row of a kind` | the reader | holds |
| C156 | A reader refuses a table that doesn't start with its own table `#unit` line, from 0 to the sequence's length, or holds a line that isn't an `#entry`; a table missing a unit's entry breaks the byte tiling of C194, by which a reader can tell the gap and may refuse the table | `graph-walks:walkReader.test.ts: a table with %s is refused` `verify7:does not list its units as they are` | the reader; verify7 for the tiling, shown on broken/entry-dropped | holds; graph-walks' refusal of a gapped table is a [follow-up](../open-problems.md#a-reader-does-not-yet-refuse-a-gapped-table) |
| C157 | `#reference` names the reference sample | `claims7:H3` `test:a_walk_file_names_its_format_reference_and_each_haplotype_with_rows` | the reader | holds |
| C158 | `path` and `fragStart` name the line a piece is cut from: a W line's name and start column, or what a P line's name reads as by the three steps of Path names and no other rule | `unit:a_p_line_name_reads_as_the_shared_table_says` `unit:the_specs_table_of_p_line_names_reads_as_it_says` `test:a_p_line_reads_the_same_before_its_segments_as_after_them` `test:p_lines_give_the_rows_w_lines_do` | `read_path_name`, `settle` | holds since ADR 0014, which replaced `split_path_name`'s first suffix that parses |
| C159 | A `blocks` unit runs from the first base its rows' blocks cover to the last, is named by its tile's start and holds a `blocks` row per `abridged` row of that tile | `test:verify` `test:decode_file` `claims7:K1` `claims7:K4` | `unit_of`, `Details::flush` | holds |
| C160 | A `blocks` row's `start end` runs from the first base its blocks cover to the last | `build:blocks_row` `test:decode_file` `claims7:K4` | `blocks_row` | holds |
| C161 | One `blocks` row per `abridged` row of a tile, keyed and ordered as the tile's; a tile with no `abridged` row has no `blocks` unit | `test:decode_file` `test:a_blocks_unit_follows_its_tiles_detail_units` `claims7:K1` `claims7:K2` | `write_chunk` | holds |
| C162 | A block is a run of consecutive steps on R, a step beginning on the base the one before ended on, all one way, as long as its steps allow; a run off R holds all the steps off R between two blocks; no two blocks join, no two runs are side by side, a list has a block and no run of 0 bp | `test:decode_file` `test:a_blocks_row_lists_an_abridged_pieces_runs_on_r_in_path_order` `claims7:K6` | `blocks_of` | holds |
| C163 | The items add up to the piece's bp, its `abridged` row's `hapBp`: it runs on its contig from that row's `hapOffset` for their sum, and ends where the line's next piece begins | `build:blocks_row` `test:decode_file` `claims7:K3` `claims7:K9` `claims7:K10` `claims7:A10` | `blocks_row` | holds |
| C164 | The list is what the piece's walk row in its detail record decodes to, with each run off R as its bp | `test:decode_file` `script:scripts/walks-truth.py` `script:docs/departures/scripts/expand7.py` | `blocks_of`, from the steps `encode_all` checked | holds |
| C165 | The tool reads back every `blocks` list it writes and fails the build where it differs from the piece, its blocks don't begin at its first step on R and end at its last, or they don't hold its `bp` | `build:blocks_row` `test:decode_file` `claims7:K7` | `blocks_row` | holds |
| C166 | A run before the first block or after the last is the piece's steps off R at its ends; only a line's first piece has a leading run | `test:decode_file` `test:a_blocks_row_lists_an_abridged_pieces_runs_on_r_in_path_order` `claims7:K8` `claims7:K9` `claims7:K10` `claims7:K11` `claims7:K12` | `blocks_row` | holds |
| C167 | `hapBp` is the sum of the lengths of all the piece's steps, on R or off it, and at least 1: the bp of the detail walk row's steps and the sum of the blocks row's items; the piece covers `[hapOffset, hapOffset + hapBp)` of its contig | `build:blocks_row` `test:decode_file` `test:an_abridged_rows_hap_bp_is_how_far_its_piece_runs_on_its_contig` `claims7:A10` `claims7:A11` `audit7:abridged rows whose hapBp is not the bp of the steps` `script:docs/departures/scripts/expand7.py` `script:docs/departures/scripts/spec8.py` `script:scripts/walks-truth.py` | `piece_bp`, `summary_row` | holds since ADR 0013 added the column |
| C168 | A line's piece 0 starts at `fragStart`, and `hapOffset + hapBp` is the `hapOffset` of the line's next piece, on whichever sequence it is filed | `test:decode_file` `claims7:A12` `claims7:K10` `audit7:whose hapOffset plus hapBp is` `script:docs/departures/scripts/spec8.py` `script:scripts/walks-truth.py` | `write_pieces`, `piece_bp` | holds |
| C169 | The attach rule: a record's own steps in a piece of its path on its sequence are the piece's steps within `[hapStart, hapStart + ownBp) ∩ [hapOffset, hapOffset + hapBp)`; where not empty, the piece's whole run off R after its last step on R, the record's leave, or before its first, its rejoin, never the whole piece | `test:decode_file` `test:twin_graphs_differ_in_hap_bp_alone_in_their_tiles_and_records` `claims7:A13` `claims7:O5` `audit7:holds other bp of an abridged piece` `script:docs/departures/scripts/spec8.py` | `record_departures`, `cut_pieces`: follows from C69, C74 and C77 | holds |
| C170 | A list is items joined by commas, each a block `d sign len` or a run; `d` is 0 or a decimal with no leading zero that may be negative, never `-0`; `len` and a run are decimals of at least 1 with no leading zero | `claims7:K7` `claims7:K8` `build:read_collapsed` `script:docs/departures/scripts/expand7.py` | `push_collapsed` | holds; the grammar was in claims7.py alone until ADR 0013 |
| C171 | The tool fails the build where a blocks list's items don't add up to its abridged row's `hapBp`, and the checks hold `hapBp` to the detail walk row's steps, the list and the next piece's `hapOffset` | `build:blocks_row` `test:decode_file` `claims7:A10` `claims7:A11` `claims7:A12` `script:docs/walks-container/hapbp/broken-writers.py` | `blocks_row` | holds |
| C172 | The tool refuses a W or P line that starts or ends past 2^53 on its contig and a reference sequence whose last tile ends past it, so no coordinate a file states is above 2^53 | `build:past_max` `build:record` `test:a_line_past_2_to_the_53_is_refused_and_one_ending_there_builds` `test:a_reference_whose_last_tile_ends_past_2_to_the_53_is_refused` | `named`, `record`, `Chunks::new` | holds since 5.0.0: a line at 2^53 + 1 built, and one near 2^63 panicked |
| C180 | A row's `path` and `fragStart` name one line of the GFA, `fragStart` a 0-based offset on `path`; a `path` is final and a reader reads no suffix out of it | `test:every_path_rebuilds_from_its_rows` `test:a_p_line_reads_the_same_before_its_segments_as_after_them` `script:scripts/check-dialect.sh` | `settle`, `link_records` | holds |
| C181 | A W line's `path` is its `sample#haplotype#contig` and its `fragStart` its start column; a start of `*` is refused | `test:a_jump_in_a_p_line_and_a_star_for_a_w_lines_start_are_refused_as_what_they_are` `unit:a_w_line_start_of_star_is_refused_as_stating_no_offset` | `w_coordinate` | holds |
| C182 | A P line's name is read from its right once its steps' bp are summed, in three steps in order, each at most once; a number is one to nineteen digits | `unit:a_p_line_name_reads_as_the_shared_table_says` `unit:a_p_line_is_named_whether_its_segments_come_before_or_after_it` | `read_path_name`, `suffix` | holds |
| C183 | `:a-b` leaves the name and adds `a` where `b − a` is the line's bp and above 0; any other `:a-b` stays in the name, a 1-based range among them | `unit:a_p_line_name_reads_as_the_shared_table_says` `script:docs/walks-container/dialect/p-colon-1-based.gfa` | `read_path_name` | holds |
| C184 | `[s]` or `[s-e]` leaves the name and adds `s`; an `e` with no `:a-b` read before it must be `s` plus the line's bp or the line is refused, and beneath a `:a-b` no `e` is read | `unit:a_p_line_name_reads_as_the_shared_table_says` `test:a_p_line_whose_bracket_end_disagrees_with_its_steps_is_refused` | `read_path_name` | holds |
| C185 | A number after the last of exactly three `#` leaves the name with its `#` and is added; `#0` adds 0 | `unit:a_p_line_name_reads_as_the_shared_table_says` `script:docs/walks-container/dialect/vg-clipped-gbz-p.gfa` | `read_path_name` | holds |
| C186 | The text left is `path` and the sum `fragStart`; a line that leaves no text, or a sum past 2^53, is refused; no suffix is read beneath a fourth field and no second of a kind | `unit:a_p_line_name_reads_as_the_shared_table_says` `test:a_p_line_named_by_a_start_alone_is_refused` `test:a_line_past_2_to_the_53_is_refused_and_one_ending_there_builds` `unit:starts_that_add_up_past_2_to_the_64_are_refused` | `read_path_name` | holds |
| C187 | The dialect fixtures' forms of one graph, W lines and P lines as vg wrote them and as odgi cut them, give one walk file byte for byte | `script:tests/dialect.rs` `script:scripts/check-dialect.sh` `script:docs/walks-container/dialect/expected.tsv` `test:p_lines_give_the_rows_w_lines_do` | `read_path_name` | holds |
| C188 | A path is listed under its `path` up to the second `#`, up to its only `#`, or whole; its sample is its `path` up to the first `#` | `unit:a_p_line_name_reads_as_the_shared_table_says` `test:refs_names_the_sample_a_p_lines_name_reads_as` `claims7:H1` `script:docs/walks-container/dialect/p-arity2.gfa` | `haplotype`, `sample` | holds |
| C189 | A P line whose steps hold a `;`, GFA 1.2's jump, is refused | `test:a_jump_in_a_p_line_and_a_star_for_a_w_lines_start_are_refused_as_what_they_are` | `path_line` | holds |
| C190 | The `#walks` line's `graph:Z:` is the `graph:Z:` the full-resolution node and link index of the same GFA states, over each S line's sequence length or else its last `LN:i:`, 16 lowercase hex digits, whatever the order of the S lines, over every S line, 0 bp or not | `test:a_walk_file_names_its_graph_as_the_index_of_the_same_gfa_does` `test:steps_of_0_bp_with_the_same_departure_text_twice_build` `verify7:not one {name} of {form}` `script:scripts/walks-truth.py` `script:docs/departures/scripts/broken/cases.tsv` | `GraphHash`, `first_pass` | holds |
| C191 | `leftout:i:` counts the GFA's W and P lines with a step that visit no node of the reference; a line of 0 bp steps alone is not counted | `test:a_walk_file_counts_the_lines_it_leaves_out` `script:scripts/walks-truth.py` `script:docs/departures/scripts/broken/cases.tsv` | `cut_path` | holds |
| C192 | A file without `graph:Z:` and `leftout:i:` is format 8, and a reader doesn't refuse it | `script:scripts/check-walks.sh` `graph-walks:walkReader.test.ts: a file that states its graph and the lines it leaves out cuts as one that does not` `graph-walks:walkRows.test.ts: a walk file's header states its graph and the lines it leaves out, by name in any order, and a file without them is read alike` | the later-additions rule, C124 | holds |
| C193 | The header names no writer and no version, so a file's rows depend only on the GFA and the options and its bytes also on the compressor; a writer release that changes no row and not the compression leaves every file as it was | `test:a_walk_files_header_names_no_writer_or_version` `test:a_walk_file_is_the_same_bytes_on_one_core_as_on_all` `test:a_walk_files_compressed_bytes_are_as_pinned` | `run`; `LEVEL` and the locked flate2 and zlib-rs in `units.rs`, whose output the pinned hashes hold | holds; a bump that moves the pinned bytes is a release decision |
| C194 | A table's entries tile the bytes from the end of the table before it, or of the header unit, to the table's own offset, with no gap and no overlap, so a reader may refuse a table whose entries leave a gap or overlap | `build:starting` `build:table` `test:verify` `verify7:does not list its units as they are` `script:docs/departures/scripts/broken/cases.tsv` | `UnitFile::starting` holds each unit to start where the last ended and `UnitFile::table` each entry to follow the one before it (src/units.rs:122-125, 202-206); `verify` in tests/walks.rs walks every file's gzip members and holds each table to them (tests/walks.rs:176-212); verify7 does the same on every fixture's files, shown on broken/entry-dropped (its entry left out, its unit kept) | holds |
| C195 | Tags follow a row's fixed columns, or the stated fields of a `#reference`, `#haplotype` or `#hole` line, in any order; a reader ignores the ones it doesn't know, on any row, on those three lines and on the `#walks` line | `graph-walks:walkReader.test.ts: tags a reader does not know are ignored on any row and header line` `script:docs/departures/scripts/repack.py` `script:scripts/check-walks.sh` | the reader; every checker | holds: the reader test tags the `#reference` and `#haplotype` lines of its fixture, which has no `#hole` line; `walkHeader` (graph-walks src/walkRows.ts:139-144) reads a `#hole` line's sequence, start and end by place and nothing after them; check-walks.sh runs every checker on repack.py's legal `tag-reference`, `tag-haplotype` and `tag-hole`, the last on walks-sequences.gfa's ten `#hole` lines |
| C196 | A later unit of a sequence lies before that sequence's table and is listed there | `verify7:lists a unit of another sequence` `script:docs/departures/scripts/spec8.py` `script:docs/departures/scripts/repack.py` `script:docs/departures/scripts/broken/cases.tsv` | `UnitFile::table` lists the units of one sequence; verify7 and spec8 fail broken/unit-new-kind-other-seq, a unit about no sequence listed in the first sequence's table, and every checker passes repack.py's legal `unit-new-kind-*` variants | holds |

## The audit

An audit of every normative statement about the walk files in
walks-format.md, ADR 0010, the parts of ADR 0009 still in force and the
README's walk sections, as they stood on `format7-tidy` at 688689c,
against the writer in `src/` at the same commit (gfa-to-tabix 4.0.0). Its
inventory is the table above; its checks are `claims7.py`'s, run then on
the test fixtures (20 files), 1,600 fuzz files (seeds 1 to 200 under 8
option sets) and the real files MC chr22 and pggb chrY on GRCh38, built on
ada by that commit's writer, the `--own` checks on 1/64 of each real file's
paths, which is what fits in 30 GB.

Of the 115 claims, 34 had no check before the audit. 15 were false, 13 of
them distinct (111 restated 42, 115 restated 105), and 7 ambiguous. 9 of
the false claims had no check; the other 6 had a check that tested
something else (17, 42, 97, 109, 111, 112). Each is fixed in the writer or
reworded in the spec, as the Result column says, and the hand-made graphs
below are now fixture tests or in the fuzz generator's space.

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

What would have caught them: the claims table above, kept with the spec,
each row naming its check, and checks written from the spec's sentence,
not the writer's code. That means no exemptions, and fuzz graphs with several
sequences, two references, empty and abutting W lines, and 0 bp sequences,
which `fuzz7-gen.py` now writes.
