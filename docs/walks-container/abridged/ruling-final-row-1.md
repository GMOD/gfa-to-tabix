# Final-row ruling 1, 2026-11-11

A blinded Fable decider, given the row as it stood (`ownBefore ownAfter`
columns and `<d><+|-><len>[:<own>]`), the
[criteria](final-row-criteria.md), the proof's results and the
[measurements](list-grammar.chr22.txt). Its report, as returned:

**Ruling: change the row. Write every off-R run as its own item in the
list, in path order, drop the two end columns, and mark direction with
`>` and `<`.** This is a format change to the unreleased `blocks` unit
only.

## Grammar

`seq start end blocks path fragStart piece list`

- `list` is the piece's collapsed walk, comma-separated in path order.
  Each item is one of:
  - `<off>`: a maximal run of steps off R, as its bp, at least 1
  - `<d>><len>` or `<d><<len>`: a block, `>` along R, `<` against it.
    `d` is where it begins on R less where the block before ended, or
    less 0 for the first
- Numbers are decimal with no leading zero, and only `d` may be 0 or
  negative. There is at least one block, and no two `off` items are
  adjacent
- The items from the first block to the last add up to the `abridged`
  row's `bp`. An `off` item before the first block or after the last is
  the piece's end

Example: `R#0#c 0 36 blocks H#1#c 0 0 7,0>12,0<12,10,24>12,-24>6,50`

## Scores

| Candidate | Determines | One way, readable | Names | Bytes | Cost |
|---|---|---|---|---|---|
| As it stood | yes, three cases (before, between, after) | fails: two mechanisms, `:own` out of order, `-24+6` | "own" overclaims | baseline | none |
| **Items, `>`/`<`** | yes, one case: the list is the collapsed walk | passes | "off" | −3.4% | one pass |
| Items, `+`/`-` | same | worse: reads as a list of sums | "off" | −3.6% | one pass |
| Absolute begins | same | closest to GAF's `>start-end` | | 2.43× | |
| One number per item, jump separate | needs an order rule | `>12<12` without commas reads as a W walk | | +12% with commas | |

## Deciding facts

- **Bytes:** 632,569 to 610,914, and the largest unit 183,646 to 176,110.
  A rerun on a local chr22 build gave −3.56%, and `+`/`-` against
  `>`/`<` differ by 0.03 points
- **Absolute begins break ADR 0012's limits:** the largest unit grows
  2.96×, taking GRCh38's 1.71 MB unit past 2 MB
- **Marking off-R runs (`*10`) loses to the baseline,** +1.9%: 95% of the
  871,645 blocks follow an off-R run, so a marker is paid on nearly
  every block
- **`>`/`<` is a judgement, not a measurement.** 22% of `d` are
  negative, so the sign collision is common. An arrow can't be summed,
  and it matches the spec's own `>1>2<2`. No reader has been tested on
  it, and `<` needs code spans in markdown
- **Stay:** `start end`, the unit's name and order, and row order; the
  key columns (dropping them saves a further 7.7 points, but a row could
  then be joined only by counting rows in another unit); `d` as a delta
  attached to its block

## New assertions

- **Read-back:** the list reads back as the whole collapsed walk, end
  runs included
- **Checkers:** a row has exactly eight columns; items match the
  grammar, with no 0 off item and no two off items adjacent; at least
  one block; the sum to `bp` runs from the first block to the last; the
  first and last block items, not the first and last items, meet the
  `start` and `end` steps; the piece's ends come from the leading and
  trailing items; a leading off item appears only on piece 0
- **Broken files:** one for each
