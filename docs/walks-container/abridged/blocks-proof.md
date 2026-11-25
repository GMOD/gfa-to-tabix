# What a `blocks` row determines, proved 2026-11-11

A Fable agent was asked to prove three claims about a `blocks` row from
the spec and the writer's code, or break them with a graph. It proved
all three and found no counterexample, on the row with `ownBefore` and
`ownAfter` columns under format 7; the row has since moved those two
numbers into the list as its first and last runs, and format 8's
`abridged` row gives the piece's start where format 7's gave its first
step on R, which changes no step of the proof. A later review wrote a
reader from walks-format.md alone and reproduced every piece of chr22
and of 85 small files with it
([reviews](reviews.md#format-8-from-the-spec-alone)).
The statements and proofs below are worded for the row as
[walks-format.md](../../walks-format.md#blocks) gives it. Code is named
by function, in `src/walks.rs` and `src/routes.rs`.

## Statements

A piece p in tile T of sequence S has steps of at least 1 bp, each at a
position j of T's R (along R when its handle equals R[j]) or off R. Its
collapsed walk cw(p) is its steps with each maximal run of steps off R
replaced by the run's bp.

- **(A) The row determines the piece.** cw(p) is the row's `list`
  expanded against T's `ref` rows: a block's stretch `[lo, hi)` of S
  reads as the positions of R lying in it, ascending for `+` and
  descending for `-`, and a bare item is one run off R. p covers its
  contig from its `abridged` row's `hapOffset` for the sum of the list's
  items
- **(B) The row holds nothing else.** `seq start end` and `list` are a
  function of cw(p); only `path fragStart piece` is not
- **(C) A W line's pieces tile it.** Over every sequence of the file,
  piece 0 starts at `fragStart`, each piece ends where the next starts,
  and the last ends at the line's end. This is per W line, not per
  contig: a contig's lines can leave gaps

## Proofs

**(A)**

- Every step has at least 1 bp (C152; `parse_steps`)
- R's positions occupy disjoint, increasing stretches of S (C63, C17,
  C61; `write_chunk`, `link_records`)
- Every placed step is at a position of T's R, or the build fails (C41;
  `Piece::read`)
- A step joins a block only if it follows a step on R, runs the same way
  and begins on the base the block ended on (`collapsed`). So a block's
  stretch is the gapless union of its steps, and the positions of R
  inside it are those steps in order, which also fixes the pass where R
  passes a node more than once
- A run is absent exactly when no step off R lies between, since every
  step has at least 1 bp
- The list reads back at build (`blocks_row`), and its grammar reads one
  way: an item of digits alone is a run, and any other is
  `(-?\d+)([+-])(\d+)`
- The detail row decodes to the same placements `collapsed` reads
  (`encode_all`; C25), so a loaded piece and an unloaded one split on
  and off R alike

**(B)** `collapsed` reads only each step on R's position and direction
and the summed lengths of the steps off R, and `start end` is the hull
of the blocks. Maximal runs of a chain are unique.

**(C)** `cut_pieces` partitions the line's steps, and a piece's offset
is the line's start plus the bp before its first step (`write_pieces`).
The `abridged` row states that offset, and the list holds every step's
bp, the runs off R before the piece's first step on R and after its last
among them. Steps off R
take the tile of the step on R before them, and only those before a
line's first placed step take the tile of the one after
(`assign_chunks`; `stay_home` fills inner runs only), so only piece 0
has a leading run.

## Where the spec and the code had parted

- **Holes.** The code's "begins where the one before ended" is the same
  base of S, so a block ends at a `#hole`. With R as `>1>2` at 0 and
  `>3>4` at 20, a piece `>1>2>3>4` lists `0+12,8+12`. C81 calls those
  steps adjacent, so a reader takes the hole out before it calls a block
  boundary a departure. The blocks section now says so
- **Off R is off the tile's R.** With R `>1>2>3>7>4>7>5` (4 bp nodes, 7
  and 8 of 2 bp), `--tile 12 --stay 100`, pieces `>1>2>7>3` and
  `>1>2>8>3` both list `0+8,2,0+4`: the first one's 2 bp are reference
  node 7 of tile 12. A run can hold up to `stay` bp of nodes the
  reference passes more than once. The blocks section now says so, and
  the row no longer says "own"
- **The window rule.** "Reading a window" doesn't name `blocks` units
  and returns an abridged piece by the span of its two end steps; a
  loaded piece is returned by its steps. In the spec's example the span
  is 0-18 and the blocks reach 36. It changes with the reader
- **(C) across sequences** holds (796 such joins in the fuzz), but a row
  names no neighbour's sequence or tile, so only a whole-file check
  tests it
- **Large coordinates, not of `blocks` alone.** A reference line
  starting past 2^53 is accepted, and a reader holding doubles misreads
  its positions; one near 2^63 panics in the writer
  (`docs/open-problems.md`)

## What the claim covers in a reader

| A reader's output | A function of the collapsed walk? |
|---|---|
| Pieces overlapping a window | Yes, by blocks; not by either row's `start end` |
| Steps on R and their strands | Yes |
| Haplotype offsets | Yes for steps on R and run ends; not inside a run |
| Departures: bp off R, positions, strands | Yes, with the `#hole` lines; missing bp is 0 within a piece |
| Gaps | Yes, from (C) |
| Structural forms and shared forms | Yes while they key on departure geometry; not if a call reads a run's nodes |
| Trimming to a window | Yes |
| A contained cut with a context in bp | Not where the context ends inside a run: a loaded cut ends at a node |
| Step and node budgets | Steps on R yes; a run's steps only as the `abridged` row's `nsteps`; distinct nodes no |
| Links | Yes between steps on R; not into, out of or within a run |

Of two haplotypes with equal collapsed walks, a viewer may say they are
placed alike on R, on the same passes and strands, with the same
departure geometry and lengths. It may not say they have the same
sequence, nodes or allele, or that their runs are absent from the
reference, and it must not merge their placeholders.

## Checks

- **(B) and the forward half of (A):** `tests/walks.rs` `decode_file`
  and `walks-truth.py rebuild` recompute the row from the decoded detail
  row
- **(C):** `claims7.py`, on the whole file
- **(A) as a reader meets it:** `expand7.py` expands each row against
  the `ref` rows alone and compares with the detail row decoded and
  collapsed. The agent's first version of it, on the earlier row, passed
  1,870 random graphs with revisits, holes, 0 bp nodes, two sequences,
  two references, tiles of 2 to 1,000 and stays of 0 to 1,000, 15,654
  abridged pieces in all, and failed each of seven broken rows
