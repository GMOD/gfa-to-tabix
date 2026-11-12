# Decide: should format 8's `abridged` row gain a `bp` column?

## The question
Format 8 walk files (gfa-to-tabix, spec `~/src/gfa-to-tabix/docs/walks-format.md`)
have an `abridged` row:

```
seq start end abridged path fragStart hapOffset piece nsteps detail
```

- One row per piece of a haplotype's walk that the writer moved to a
  detail record.
- It gives where the piece starts on its haplotype contig (`hapOffset`),
  not where it ends.
- ADR 0012 (`docs/adr/0012-abridged-blocks.md`) dropped format 7's piece
  bp and end steps from this row. It says they "stay dropped unless this
  number says otherwise" (`:206-212`); see also `:88-90`.

The proposal is to add one column, the piece's bp on its haplotype contig.
The format freezes about 2026-11-18. It would have to be decided by about
2026-11-13 to ride the single planned genome rebuild (about 50 min per
genome on ada).

## The case for (from a reviewer; treat as claims)
- A departure record attached to an abridged tile has its own steps in some
  piece. Without the piece's end, a reader cannot find which piece from the
  tile plus the record. It must read the `blocks` unit (a separate per-tile
  unit listing the pieces' runs) or guess.
- Measured on both genome files, simulating the column from `blocks` rows:
  - own steps = `[hapStart, hapStart+ownBp) ∩ [hapOffset, hapOffset+bp)`
    for all 25,117 (CHM13) and 17,670 (GRCh38) pieces holding own steps,
    0 broken;
  - picking the piece "by `hapOffset`" (the reader-only rule another
    reviewer proposed) picks a piece with no own steps 506 / 1,201 times;
  - the record alone is exact for 12,016 of 12,521 within `ATTACH_BP`
    (CHM13).
- Cost: abridged tiles +0.26% (CHM13) and +0.37% (GRCh38); worst tile
  +4.1 KB.
- It would make `bytesFor` and attach a format guarantee, not a proof about
  one writer.
- Measurement output:
  `/tmp/claude-1001/-home-cdiesh-src-gfa-to-tabix/8d998258-253a-4650-bff8-c3784f138aa2/scratchpad/review-nobc/`
  (`measure.py`, `ada-both.txt`, `ada-chm13.txt`, `ada-grch38.txt`).

## The case against (from another reviewer; treat as claims)
- They are the fields ADR 0012 dropped as redundant with the `blocks` list
  and narrower than they look; consumers misread them.
- The measured excess reads (four named haplotypes on the worst tiles,
  `review/four-*.txt`) are reader policy: `resolve()` in graph-walks
  `src/walkReader.ts` routes every met unloaded piece through `blocks`.
- A reader rule decided from the `abridged` row alone (load overlapping
  pieces, pieces between two drawn pieces of a line, and the piece holding
  an attached record's own steps by `hapOffset`) would bring reads to about
  format 7's.
- Notes in
  `/tmp/claude-1001/-home-cdiesh-src-gfa-to-tabix/8d998258-253a-4650-bff8-c3784f138aa2/scratchpad/decide-opus/`.

## Context
- No back-compat is owed anywhere: writer, graph-walks reader, bandage-core,
  the JBrowse plugin, BandageJS, ggbandage, the tube map, hosted files. No
  format 8 file is released or hosted.
- The owner's bar is that the format is bulletproof and unassailable to a
  careful referee:
  - every field true and fully determined;
  - invariants precise and checkable by an independent reader, not
    dependent on one writer's behaviour;
  - every edge case specified and checked;
  - every byte justified by measurement.
  
  Plain-text readability is a nice-to-have.
- Judge SAM/PAF-style: minimal non-redundant columns, real coordinates
  only, few record kinds.
- ADR 0011 governs format changes:
  - a change must beat shipping unchanged;
  - criteria are written before the evidence is weighed;
  - mixed evidence keeps the format.
- Code:
  - writer: `~/src/gfa-to-tabix` (Rust);
  - reader: `~/src/graph-walks-blocks` (branch `blocks-unit`);
  - spec checkers: `~/src/gfa-to-tabix/docs/departures/scripts/` (`spec8.py`,
    `claims7.py`, `expand7.py`) and `docs/walks-container/`.
- Genome files on ada:
  `~/work/blocks/genome/hprc-v2.1-mc-{chm13.CHM13,grch38.GRCh38}.walks.gz`.
  Fixture: `~/src/graph-walks-blocks/test_data/blocks.R.walks.gz`.
- Other pre-freeze items in flight (not yours to decide, but say if they
  interact):
  - P line name ruling;
  - a 2^53 coordinate refusal;
  - a spec section separating reader invariants from writer policy;
  - per-cut placeholder ids in the reader.
