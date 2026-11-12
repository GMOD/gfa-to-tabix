# Format 8 ruling 1, 2026-11-11

A blinded Fable decider, given format 7 with the `blocks` unit as the
baseline and the [criteria](format8-criteria.md), with existing readers
and files counting for nothing. Its report, in substance:

**Ruling: make it format 8. Keep the `blocks` row and `detail` unit
exactly as on the branch, and cut the `abridged` row down to a walk
row's leading columns plus `detail`.**

```
seq start end abridged path fragStart hapOffset piece nsteps detail
seq start end blocks   path fragStart piece list

R#0#c  0  36  abridged  H#1#c  0  0  0  11  0
R#0#c  0  36  blocks    H#1#c  0  0  7,0+12,0-12,10,24+12,-24+6,50
```

- **`start end`:** the span of all the piece's steps on R, as on a walk
  row and on its `blocks` row (was the two end steps)
- **`hapOffset`:** where the piece starts on its contig, as on a walk
  row (was the first step on R). The piece ends at `hapOffset` plus
  every item of `list`
- **`nsteps`:** the cost of expanding, known before any detail read; not
  derivable from `list`
- **Dropped:** `bp`, `start[@k]`, `end[@k]`: the list's
  first-to-last-block sum and the first and last blocks' ends
- **At open:** refuse any `format` but 8. No table scan for a detail
  unit without `blocks`; a tile with `abridged` rows has its `blocks`
  unit by definition, and a missing one is a broken file
- **Declaration:** `blocks` is a format 8 unit, not a later addition, so
  any other row shape is another number

## Candidates

| Candidate | Design today | One check | Read cost | Checkable | Change cost |
|---|---|---|---|---|---|
| A: branch, format 7 | fails: three derivable fields, two that mislead | fails: table scan; three shapes shared 7 | baseline | best | none |
| B: branch rows, `format:i:8` | as A | passes | as A | loses only the header unit | trivial |
| C: ruled | passes | passes | 0.4% under A | loses byte equality on abridged tiles | small |
| D: one row, in the tile | passes | passes | named cut +28% | as C | medium |
| E: one row, in the `blocks` unit | passes | passes | named cut +28%, and it must read `blocks` to find `detail` | as C | medium |

## Measured on chr22 (18 abridged tiles, 2,572 pieces)

- All 2,572 current `abridged` rows are rebuilt exactly from the ruled
  rows plus `ref` rows; all 2,572 ruled rows equal their detail walk
  row's first nine columns, kind aside
- `hapOffset` is not the piece's start in 113 pieces, and `hapOffset` to
  `hapOffset + bp` is not the whole piece in 1,089 (42%)
- Bytes read over the 18 tiles: named cut 2,163,762 (A, B), 2,154,953
  (C), 2,768,253 (D); every haplotype 2,804,443 (A, B), 2,795,634 (C)

## Still checkable against the hosted files

Byte for byte: every departure block, every detail unit and every tile
without `abridged` rows, 96.4% of chr22's unit bytes outside `blocks` and
tables. As text: the abridged tiles, with each hosted `abridged` row
recomputed from the new rows.

## What would reverse it

A reader that must place an abridged piece from the tile alone, with
neither `blocks` nor detail (none found); or the checker work not fitting
the week, in which case B, never A.
