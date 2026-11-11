# Declaration ruling 1, 2026-11-11

A blinded Fable decider, given the question of how a file with `blocks`
units declares itself, the [criteria](declaration-criteria.md) and the
code, with ADR 0012's `format:i:8` as the baseline. Its report, as
returned:

**Ruling: keep `format:i:7` and declare `blocks` only by its unit kind in
each sequence's table, with no new number and no new tag. The next
graph-walks refuses any sequence whose table lists a `detail cs:d` unit
without a `blocks cs` unit.**

Nothing was run; this is from reading the code, tests and docs.

## Matrix, ruled candidate

| | 4.0.0 file | next file (7 + `blocks`) |
|---|---|---|
| graph-walks 6.2.0 | reads, as today | reads, with output identical to today: the number passes and `blocks` units are never selected |
| next graph-walks | reads sequences with no abridged tile; refuses the rest with a "rebuild" error from the table | draws from blocks |

## Matrix, baseline (ADR 0012, `format:i:8`)

| | 4.0.0 file | next file (format 8) |
|---|---|---|
| graph-walks 6.2.0 | reads, as today | refused: "update the viewer" |
| next graph-walks | refused whole, even a file with no abridged tile | draws from blocks |

## Deciding facts

- **The spec already names this mechanism.** "A unit kind this page
  doesn't give is a later addition, which a reader skips" is at
  `docs/walks-format.md:352-353` (C123), and "Later additions are tags,
  unit kinds or files" at `:375-376` (C124). The baseline bumps the
  number for exactly that and names no sentence it changes.
- **6.2.0 refuses any number but 7 and skips unknown unit kinds.** The
  refusal is `format !== WALK_FORMAT` at graph-walks
  `src/walkFile.ts:141`. Unit selection is by kind at
  `src/walkReader.ts:376-378` and `:435`, tested at
  `src/walkReader.test.ts:2000`. So the baseline's swap at the cited URL
  makes every pinned 6.x install a refusing pair, and the ruled
  candidate makes none.

## On the criteria

- **Truth:** tie. 6.2.0 states nothing new, and the missing-blocks
  refusal is needed under either candidate.
- **One way to read:** tie.
- **After the freeze:** the ruled candidate wins. The paper cites
  format 7 permanently, and later additions never strand a released
  reader.
- **Spec's rules:** the ruled candidate wins, with fewer mechanisms.
- **Cost:** the ruled candidate wins. Hosted files can be rebuilt first
  while old readers keep working, then the readers released, so no
  atomic swap is needed.
- **Burden:** met, and mixed evidence would also keep 7.

## Different from the docs

- **C49 is broader than the reader.** It says a file with an unknown row
  kind is another format, but 6.2.0 checks row kinds only inside `tile`,
  `departures` and `detail` units (`walkFile.ts:101-106`, test
  `walkReader.test.ts:1943`). C49 needs the clause "in a unit this page
  gives", a wording change ADR 0011 permits.
- **"Format 8" is a leftover.** It comes from ruling Q's column on
  `abridged` rows, which was another format under C49. The
  cross-examination moved the data to a unit and kept the number
  (`ruling-cross.md:9-10`).
- **ADR 0012's "never a mismatched pair" covers only the latest
  plugin.** bandage-core, the plugin, BandageJS, ggbandage and the tube
  map depend on `^6.x`.
- **ADR 0011 says both things.** Its collapsed-repeat fixes "add to
  format 7" (`:28-30`, `:130`), yet its example says such a fix "can be
  an ADR for format 8" (`:199-200`). `docs/open-problems.md:390-393`
  takes the former reading.

## What would reverse it

- The owner wanting pinned 6.2.0 installs to stop reading the hosted
  file, rather than keep today's false every-haplotype statements. The
  Truth criterion as written permits those.
- The build changing any existing unit's bytes or meaning, for example
  `abridged` rows' `start end`.
- Abridged tiles existing without a `detail` entry in the table. I
  inferred from C150 that none do and did not check it on a file. The
  refusal would then move to cut time, and a `blocks:i:1` header tag,
  which refuses at open, becomes the better declaration.
