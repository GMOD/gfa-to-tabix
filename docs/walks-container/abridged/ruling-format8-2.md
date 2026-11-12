# Format 8 ruling 2, 2026-11-11

A blinded Opus decider, briefed in different words from
[ruling 1](ruling-format8-1.md) with the same baseline and
[criteria](format8-criteria.md). Its report, in substance:

**Ruling: cut format 8.** The `abridged` row becomes a pointer to the
piece's detail unit. The `blocks` row becomes a twin of the `walk` row,
with `list` where the `walk` row has `start choices`.

```
seq start end abridged path fragStart piece detail
seq start end blocks   path fragStart hapOffset piece nsteps list

R#0#c 0 36 abridged H#1#c 0 0 0
R#0#c 0 36 blocks   H#1#c 0 0 0 11 7,0+12,0-12,10,24+12,-24+6,50
```

- **Both rows' `start end`:** the span of the piece's blocks on R
- **`hapOffset`:** where the piece starts on its contig, as on a `walk`
  row
- **`nsteps`:** read for an unloaded piece, so it moves to the `blocks`
  row
- **Dropped:** `bp` and `start[@k] end[@k]`
- **At open:** `format:i:8` or refuse. Format 8 requires a `blocks` unit
  for every tile with `abridged` rows, with the same keys in the same
  order; a missing unit is a corrupt file. The clause that lets a reader
  skip unknown unit kinds stays, for additions after the freeze

## Options

| | Design today | One check | Bytes | Provable, checkable | Cost |
|---|---|---|---|---|---|
| A: 7 + `blocks` | `bp`, end handles, `hapOffset` and `nsteps` repeat or bend facts | fails | | proof holds; all but `blocks` units byte-identical | none |
| B: 8, rows as now | as A | passes | as A | as A, header differs | trivial |
| **C: 8, as ruled** | passes | passes | a wash | holds, simpler; abridged tiles checked by derivation | moderate |
| D: one row in `blocks`, no `abridged` rows, detail units named by path | passes | passes | best | holds | high, and outside the tier |
| E: `list` on the `abridged` row | passes | passes | named cut much worse | holds | moderate |

## Measured on chr22

| | A | C | D |
|---|---|---|---|
| Tiles (named cut) | 2,164 KB | 2,138 KB | 2,094 KB |
| `blocks` units | 641 KB | 659 KB | 667 KB |
| Every haplotype (tile + `blocks`) | 2,804 KB | 2,797 KB | 2,760 KB |

## What would overturn it

A reader that has to draw an abridged piece's place or length from the
tile alone, such as an attach fetch that reads only tiles; then `bp` and
the end handles stay and the ruling falls back to B.

## The split, and how it was settled

The two rulings agree on format 8, on `blocks` as a required unit, on
dropping `bp` and the end steps, and on what `start end` and `hapOffset`
mean. They differ on where `hapOffset` and `nsteps` sit. The session
kept them on the `abridged` row, as ruling 1 has it: a cut of named
haplotypes reads the tile and never the `blocks` unit, and `nsteps` is
there so a reader knows a piece's cost before it loads the detail unit.
That also leaves the `blocks` row as the final-row rulings gave it.
