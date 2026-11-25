---
name: fixtures-that-tell-two-readings-apart
description: Three readings of the walk row decoding rules give the same output on every fixture under tests/data, so no test fails a reader that takes the wrong one; each needs a fixture.
metadata:
  repo: gfa-to-tabix
---

# Fixtures that tell two readings of the decoding rules apart

On 2026-11-25 a reader written from part one of `docs/walks-format.md`
alone printed every W and P line back from 413 walk files, every fixture
with paths under seven option sets. It then swapped a rule for a wrong
reading and got the same output on all of them:

- **The default exit occurrence** taken among the positions of R that
  read the exit handle, where the format says the positions that hold
  its node in either orientation
- **The default start occurrence** taken as R's last, where the format
  says its first
- **A block's run of steps** judged on coordinates alone, or on
  neighbouring positions of R as well

A fixture for each: a reference that passes a node in both orientations
with a route exit nearer the other orientation, a piece that starts on a
revisited node at a pass other than the first without `@k` being
needed, and two passes of R that abut in coordinates but are not
neighbours. Few files reach these columns at all: 12 use `:k`, 6 `@k`
on a choice and 4 `startHandle@k`.
