---
name: walk-files-in-place-of-the-index
description: Whether walk files can replace the node and link index as a path graph's graph-track source. ADR 0008 kept the index and this question; of the four things then in the way, a zoomed-out tier and carrier colouring from walk files remain, and the loss counts of 2026-10-30 predate format 6's departure records and were never rerun.
metadata:
  repo: gfa-to-tabix, graph-walks, bandage-core, jbrowse-plugin-graphgenomeviewer
---

# Walk files in place of the index for path graphs

[ADR 0008](../../../docs/adr/0008-index-keeps-its-placement.md)
(2026-10-30) keeps the index's placement and its role as a path graph's
graph-track source, and keeps this question open with its measurement as
the baseline: graph-walks 4.4's own cuts over 80 to 100 windows of 10 kb
per graph ([docs/placement/](../../../docs/placement/)).

## What was measured, on walk format 5 and graph-walks 4

- On GRCh38's chr22, off segmental duplications, a graph track drawn from
  walk files loses nothing a user needs and reads about a third of the
  bytes (ADR 0008's table)
- The harness counts as lost every node of a kept haplotype that the index
  draws and the walk view doesn't, so its losses are an upper bound. With
  graph-walks 4b064ec, of the nodes it counts lost, the share the
  haplotype carries on a stretch before or after the window, which the
  index draws only because it files a whole component under one interval,
  is 49% on Minigraph-Cactus chr22, 5% on pggb chr22 and 12% on pggb chrY
  ([lost-placement-fix.txt](../../../docs/placement/lost-placement-fix.txt)).
  At Minigraph-Cactus chr22 18.45 Mb the 3,061 nodes are a 32 kb insertion
  before the window, and the haplotypes carry a deletion across it
- graph-walks 4.5.0 closed two gaps in the reader alone, a detour spanning
  the window and a deletion across it. With 8 haplotypes, lost allele
  nodes fell from 6,180 to 2,150 on Minigraph-Cactus chr22, 6,217 to 3,941
  on pggb chr22 and 10,699 to 8,160 on pggb chrY; windows that lose
  nothing stayed at 85, 71, 72 and 59; every window drew all its
  reference nodes, against 3, 1 and 7 that didn't on pggb chr22, pggb chrY
  and CHM13 with 4.4
- Those counts are of format 5's skip rows, which format 6's departure
  records replaced ([ADR 0009](../../../docs/adr/0009-departure-records.md)),
  and have not been rerun since

## What stood in the way on 2026-10-30, read again on 2026-11-25

- **The viewer:** bandage-core then drew a skip only for a haplotype with
  no walk in the cut, and every skip as a deletion. Skip rows are gone
  since format 6, and the file cited (`src/layout/walkRowRuns.ts`) is no
  longer in bandage-core; how today's bandage-core draws a capped crossing
  and a jump beside a fragment was not rechecked here
- **Haplotypes jumping between repeat copies:** now the placement question,
  `../waiting-on-a-call/pggb-placement-rule.md`
- **Zoomed out:** the coarse tier, alleles and bubbles exist only for the
  index. Still so: the overview-tier study for walk files is queued in
  `../../handoffs/2026-11-21-ada-next.md`, and
  `../waiting-on-someone-else/lanes-coarse-table.md` waits on it
- **Carriers:** a walk-drawn graph coloured no node by its samples, so the
  hosted `ecoli_pggb_carriage` track had no walk-file source. Not
  rechecked against today's plugin; the E. coli demo has no walk track yet
  (`../ready/ecoli-walk-file-per-strain.md`)

## What it waits on

The overview-tier study, and a rerun of `docs/placement/scripts` on
format 8 counting only nodes a haplotype carries on the window.
