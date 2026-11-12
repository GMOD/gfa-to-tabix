# Final-row ruling 2, 2026-11-11

A blinded Opus decider, briefed in different words from
[ruling 1](ruling-final-row-1.md) with the same row,
[criteria](final-row-criteria.md) and
[measurements](list-grammar.chr22.txt). Its report, as returned:

**Ruling:** one thing about the row changes. The runs off R become bare
items in the list, placed in path order, and the `ownBefore`/`ownAfter`
columns go. Block spelling, `start end`, the key columns, and the unit's
name and order stay exactly as they are.

**One condition first.** The byte measurement for this exact spelling
did not exist: the variant that was measured also swapped `+`/`-` for
`>`/`<`. If its BGZF total came out above the current 632,569, the
Burden clause would apply and the row would stay unchanged. (Measured
afterwards: 610,624, in [list-grammar.chr22.txt](list-grammar.chr22.txt).)

## Grammar

`seq start end blocks path fragStart piece list`

- `list` gives the piece in path order, comma-separated. Each item is
  either a block or a run off R:
  - A block is `<d><+|-><len>`, as before. `d` is measured from where
    the previous block ended; runs off R don't move it
  - A run off R is a bare decimal, its bp. It is off the tile's R and
    may hold another tile's reference nodes. It is never 0, and two
    never stand side by side
- The piece runs from `hapOffset −` (a leading run, if any) to that
  point plus the sum of all the items

`R#0#c 0 36 blocks H#1#c 0 0 7,0+12,0-12,10,24+12,-24+6,50`

**Parser:** split the list on `,`. An item that is all digits is a run
off R. Otherwise it is a block, split at its `+` or `-` that isn't the
first character. No token can be read two ways.

## Scores

| Candidate | Determines the piece | One way, no manual | Names | Bytes (BGZF) | Cost |
|---|---|---|---|---|---|
| As it stood | Proven | Off-R bp said two ways; `:own` sits after the block it comes before; `-24+6` | "own" claims too much | 632,569 | 0 |
| **Items, `+`/`-`** | Same claim, a lossless remap; the extent is one sum, no three-way case split | One mechanism, in path order; `-24+6` stays | No "own" anywhere | below current | One pass, nothing hosted |
| Items, `>`/`<` | Same | `24>12` reads as a GFA walk, node 24 then node 12 (the example even has a node 12). This swaps the sum misreading for a node misreading | Same | 610,914 | Same |
| Absolute begins | Same | No delta arithmetic | Same as its parent | 1,539,200 | Rejected |

## What tipped it

- The row as it stood states off-R bp two ways, and readers tripped on
  three of the four points that follow from that: `:own`'s placement,
  two mechanisms, and the word "own". Bare items in path order remove
  all three, and the first criterion's claim gets shorter
- Changing the strand glyph is a mixed result under the GFA W-line habit
  the criteria name, so Burden keeps `+`/`-`
- Absolute begins lose badly on bytes
- Keep `start end` and the keys: every row opens `seq start end kind`,
  and the key matches the `abridged` row's

**Spec wording still needed:** say that `-24+6` is a jump of −24
followed by a 6 bp block running along R, not a sum.

## New assertions

- Every item is a block or a bare positive decimal, with no `-0`, no
  leading `+` and no leading zeros
- No bare item is 0, and no two bare items are adjacent
- The list holds at least one block. The first block begins at the
  `start` step and the last ends at the `end` step
- The block lengths plus the inner bare items equal the `abridged`
  row's `bp`
- A leading bare item appears only on the first piece of a W line
- The piece's extent ends where the line's next piece begins
- The list matches the detail record's walk row, runs off R included
- Each check proved with a deliberately broken file
