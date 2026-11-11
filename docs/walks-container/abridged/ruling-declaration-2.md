# Declaration ruling 2, 2026-11-11

A blinded Opus decider, briefed in different words from
[ruling 1](ruling-declaration-1.md) with the same question and
[criteria](declaration-criteria.md). Its report, as returned:

**Ruling:** keep `format:i:7`. The `blocks` unit goes in as a unit kind
the spec treats as a "later addition", with no new header tag. The next
graph-walks requires it: it refuses any sequence whose table lists a
tile's `detail` unit with no `blocks` unit named for that tile. It has no
fallback drawing path. The new writer adds nothing to files that have no
abridging, so those stay byte-identical to what 4.0.0 writes.

## Cells, the ruling (format 7, `blocks` units)

| | 4.0.0 file | next file |
|---|---|---|
| 6.2.0 | reads, as today | reads it and skips `blocks`, so it draws unloaded pieces exactly as it does today |
| next | reads sequences with no abridging; refuses an abridged sequence with "rebuild", decided from the table pairing `cs:d` → `blocks cs` | reads, drawing unloaded pieces from blocks |

## Cells, ADR baseline (`format:i:8`)

| | 4.0.0 file | next file |
|---|---|---|
| 6.2.0 | reads | refuses at open with "update the viewer" |
| next | refuses at open, including files with no abridging that are byte-identical apart from the 8 | reads |

## Criteria, in their stated order

- **Truth:** a tie. 6.2.0 on a new file says nothing it doesn't say
  today. The next reader never guesses: an abridged tile always has a
  detail unit (walks-format.md:565-568, 787-789), so a missing `blocks`
  unit shows in the table before any window is read.
- **One way to read:** a tie. Neither keeps a fallback drawing path.
- **After the freeze:** the ruling wins. Under the baseline, the swap
  leaves every pinned 6.2.0 install refusing the cited URL for good.
  Under the ruling, no released reader and hosted file ever refuse each
  other.
- **The spec's own rules:** the ruling wins. walks-format.md:352-353 and
  375-376 say a new unit kind or tag is a "later addition" that readers
  skip, not "another format". ADR 0011 says both known fixes "add to
  format 7". The baseline's "8" goes against this, while ADR 0012 itself
  says everything else stays format 7's byte for byte.
- **Cost:** the ruling wins. The hosted file can be swapped before the
  plugin release, since the current plugin reads it. The baseline needs
  file and plugin to flip together.
- **Burden:** the ruling beats the baseline outright, and the rule's
  fallback for mixed evidence ("stays 7") points the same way.

## Facts that carried it (graph-walks at the v6.2.0 tag)

- walkFile.ts:141 refuses any format other than 7. walkFile.ts:126-127
  turns a higher number into "update the viewer".
- walkFile.ts:55-61 (`ROW_KINDS`) has a comment saying an unknown unit
  kind is a later addition whose rows are never read. walkFile.ts:101-105
  checks rows only in unit kinds it knows. Table parsing (about line 307)
  accepts any kind.
- Every read filters by kind: walkReader.ts:177, 324, 376-378, 435. The
  ADR puts `blocks` after the detail units, so it never sits between
  tiles, and merged range reads never pull it in.
- walkRows.ts:117-119 reads only the `format`, `tile` and `revisited`
  tags.

## Where the docs disagree with each other or the code

- ADR 0012 calls this "format 8", against spec lines 352-353 and 375-376
  and against ADR 0011's "add to format 7".
- Spec C49 ("a row kind this page doesn't give is another format") and
  C123 (a new unit kind is a later addition) overlap for a new row kind
  inside a new unit kind. C49 should be scoped to the existing units.
- Spec C156 ("a reader can't tell" when an entry is left out) needs an
  exception for the `detail`/`blocks` pairing.
- walkFile.ts:128 says "rebuild with gfa-to-tabix 4.0 or later". Under
  either option, 4.0 is the wrong version to name.
- The criteria file's Burden rule asks candidates to beat a format 8
  baseline, yet makes 7 the default when evidence is mixed. Those two
  halves point opposite ways.

## What would overturn this

- The owner deciding that a pinned old reader should refuse the cited
  file rather than keep drawing today's falsehoods on it. That means
  rewording Truth to cover files written from now on.
- A released consumer that parses tables itself and refuses unknown unit
  kinds. Only graph-walks was checked, not bandage-core, BandageJS,
  ggbandage or the tube map.
- A tile with `abridged` rows but no `detail` unit.
