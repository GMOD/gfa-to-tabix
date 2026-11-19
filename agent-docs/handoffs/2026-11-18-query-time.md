# Handoff, 2026-11-18: query time against gfaidx, and what gfa-to-tabix has going for it

State: docs/comparison.md and docs/comparison/ are on local main at 3ea911a, not pushed. The gbz-haplotype-index README link to the renamed doc is on that repo's local main (6966e4b), also not pushed. Push gfa-to-tabix first, or that link breaks.

The user's concern is query time ([[query-time-first]] in memory). Read docs/comparison.md "Reading a 64 kb window" for the tables; the raw results are in docs/comparison/results.

## Measured

40 evenly spaced 64 kb windows per graph on ada, GRCh38 reference, every haplotype, median (slowest):

| | MC chr22 | pggb chrY |
|---|---|---|
| graph-walks 7 (730e752), reader open, local disk | 158 ms (1.6 s) | 47 ms (8.6 s) |
| graph-walks, new reader, local disk | 165 ms (1.5 s) | 56 ms (7.7 s) |
| graph-walks, new reader, HTTP from jbrowse.org | 176 ms (1.4 s) | not run |
| gfaidx 2.3.2 `get_region --mode all --with_coords` | 68 ms (0.8 s) | 94 ms (3.5 s) |

- gfaidx wins MC chr22 by about 2x; our reader wins pggb chrY in 38 of 40 windows
- Node sets: our cut's stepped nodes equal gfaidx's GFA segments in 38 of 40 chr22 windows and 20 of 40 chrY windows; gfaidx has more in the rest
- Not measured: a real browser, a slow connection, a `keep` list of a few haplotypes, steps and links agreement

## The lever: graph-walks' decode loop

Over HTTP is about as fast as local disk, so reads are not the cost; decoding is. Time follows steps decoded: the median chr22 window decodes about 796,000 steps (464 haplotypes), and `graph.tables` adds about 67 ms on top.

CPU profile of 30 cuts of one typical chr22 window (scratch script, not committed; `node --cpu-prof` on ada, self time):

- `walkCut` walkRows.ts:401, 25%
- `cutRows` walkReader.ts:1086, 6.7%
- `departureTable` walkRows.ts:1355, 5.2%
- `visit` walkRows.ts:1254, 5.0%
- `push` walkChunk.ts:432, 4.7%
- `placeOffReference` walkRows.ts:1244, 4.7%
- `stepsIn` walkGaps.ts:231, 4.6%
- garbage collection 3.3%

Hypotheses, not tested:

- `walkCut` is a candidate for the biggest single saving; read what it does per step before anything else
- Decoding only the haplotypes a viewer draws (`keep`) already exists and should cut time in proportion to steps; measure it first, it may be the answer for browsers
- Allocation (push, GC) may drop with typed arrays per fragment
- Departures cost about 5% plus their share of tables

Any reader change must keep format 8 byte-identical semantics: run graph-walks' suite and `scripts/graph-walks-rebuild.mjs` (on ada, per [[ada-big-runs]]). No format change is implied by any of this.

## What gfaidx cannot match (the pros, measured)

- **Static hosting:** plain files on any web host; a browser reads them by range request. gfaidx needs a process on the machine holding the files and has no HTTP reader
- **Size:** walk file 59 MB vs gfaidx's 1.23 GB on MC chr22, and 194 MB vs 2.42 GB on pggb chrY; with bases 105 MB and 387 MB
- **Requests:** 1 to 4 byte ranges per window, all known from the table read at open, against about 900 dependent reads from five files (open read 22 to 48 KB vs 329 KB to 1.7 MB)
- **Bounded worst case:** largest chrY window under 2 MB read (every window listed in docs/comparison/results/pggbY.cost.txt) against 136 MB read and 530 MB of GFA from gfaidx; abridged tiles are why
- **Time in repeats:** pggb chrY median 56 ms vs 94 ms, and 38 of 40 windows faster
- **Whole genome:** the hosted HPRC v2.1 files are 1.58 GB (GRCh38) and 1.78 GB (CHM13), built in 47 and 63 minutes at 7.3 and 8.6 GiB
- **Beyond walks:** the node and link index (rGFA included), coarse tier and bubbles for zoomed-out views, JBrowse config, readers in BandageJS, the plugin and ggbandage

Where gfaidx is better, say so: faster on typical chr22 windows, builds in under 1 GiB of memory, any path as reference, node-seeded and whole-path queries, graphs without paths.

## Reproduce

```bash
GRAPH_WALKS=~/src/graph-walks docs/comparison/scripts/setup.sh   # sets up ada:~/work/gfaidx-compare
ssh ada 'cd ~/work/gfaidx-compare && ./build.sh'                  # indexes both graphs with both tools
ssh ada 'cd ~/work/gfaidx-compare && ./windows.sh'                # window reads, reader timing, cost
python3 docs/comparison/scripts/tables.py                         # regenerate the doc's tables
```

ada:~/work/gfaidx-compare keeps the indexes (4.6 GB) so reruns skip the builds. Time harness trap: `subprocess.run(timeout=...)` polls at up to 50 ms and rounded gfaidx's short runs up; the timed runs have no timeout.
