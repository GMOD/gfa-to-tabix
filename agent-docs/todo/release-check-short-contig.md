---
name: release-check-short-contig
description: graph-walks release-check/realData.test.ts throws on a contig shorter than its chr22 windows (tiles[0]!.start on an empty list); a harness bug, the reader is never reached.
metadata:
  repo: graph-walks
---

# release-check crashes on a short contig

`release-check/realData.test.ts:82` builds each window from `tiles[0]!.start`
and `tiles.at(-1)!.end`. Its windows are chr22 coordinates, so on a shorter
contig a window past its end leaves `tiles` empty and the test throws
"Cannot read properties of undefined (reading 'start')".

Fix: skip a window no tile overlaps and say so, or take windows from the file.
