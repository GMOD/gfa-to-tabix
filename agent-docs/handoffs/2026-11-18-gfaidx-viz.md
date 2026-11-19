# gfaidx-viz, and what its views need from walk files: state on 2026-11-18

Written by session `gfa-to-tabix-18`. It covers the analysis of
[gfaidx-viz](https://github.com/fawaz-dabbaghieh/gfaidx-viz), the checks it
led to, and what is left. Nothing is pushed. main is at 6fb39f8 plus this
commit; the worktree branch `compare-gap` holds the same commits.

## What gfaidx-viz is

- A React app by Fawaz Dabbaghieh, gfaidx's author, forked on 2026-06-02
  from cmdcolin/BandageJS when it was still the C++/OGDF wasm port. That was
  before BandageJS moved onto bandage-core
- A browser sends a region to MMseqs2-App's Go server at search.foldseek.com.
  The server queues a job, runs `gfaidx get_region --mode all --haplotype_gap
  10kb`, and returns GFA text, which the browser lays out with the old
  Bandage FMMM wasm
- The server hosts HPRC r1 and r2 graphs, but not r2.1 MC GRCh38
- Its views: a straightened reference with a ruler that isn't linear in bp,
  MANE genes, path overlays, a per-path copy-number track, paths per link by
  direction, CSV node styling and depth colouring from S-line tags
- Its own to-do files (`ideas_to_implement.md`, `PERFORMANCE_OPTIONS.md`)
  list a pinned-reference layout and a spatial index. bandage-core already
  has both (`layout/anchoredLayout.ts`, `util/SpatialIndex.ts`)

## Decided or settled

- **Format 8 is unaffected.** A Fable 5.2 review found nothing in gfaidx-viz
  that needs new bytes before the freeze. Each view is reader work, a side
  file or a later addition. See the new section of `docs/comparison.md`,
  "gfaidx-viz's views from a walk file"
- **Visit counts are exact,** checked in `docs/comparison/visits/`. A cut
  holds every haplotype's visits to the window's reference nodes, matching
  the raw GFA:
  - MC chr22: every tile
  - pggb chrY: every tile, on nodes the reference sample passes once
  - 1 kb stretches cut inside tiles
  - Three planted breaks are caught
  - Passes count over every line of the reference sample, as the file's
    do. pggb chrY also has `GRCh38#0#chrY_KI270740v1_random`
- **Per-haplotype reference: admitted** by gfa-to-tabix-bb, which owns the
  format gates and the spec-sentences branch. A file whose `ref` rows are
  one haplotype of the `#reference` sample (HG002#1 as reference, HG002#2
  as walks) is legal.
  - It needs C9 and C51 reworded and spec8.py, walks-truth.py and
    graph-walks-rebuild.mjs fixed, all in bb's branch
  - graph-walks needs no change. `#reference HG002#1` is not admitted
  - Writer support (`--refs HG002#1`) comes after the freeze
  - Fixtures are in ada:~/work/visits/hapref/
- **Bare contig names on a file with two reference haplotypes:**
  graph-walks' `refNameLookup` (src/refNames.ts:16-21) silently picks the
  last one. No hosted file hits it, but bb's Fable check found that the
  candidate plugin 6196d00 does, through Add Track's default `#reference`
  mapping, and can draw the wrong haplotype.
  - It's fixed before the graph-walks 7.0.0 tag: `resolveRefName` throws
    an exported `AmbiguousSequenceError` naming the sequences and the
    haplotypes to pick from
  - The tube map's own first-match resolver goes through graph-walks too
  - Then the consumer loop, the drawing gate and the owner's
    re-approval of the manifest
  - bb's lane owns all of it. Leave graph-walks and the candidate branches
    alone until it's done
- **The `spec8.py --gfa` failure on fuzz seed 8 is a checker bug:** it
  doesn't skip a W line with empty steps (spec8.py:1423-1441). The writer is
  right (walks.rs:1034-1036). It's in bb's branch
- **GFA tags are not kept,** unlike gfaidx. That's recorded in
  `docs/open-problems.md` ("GFA tags neither file keeps") as a later
  addition
- **`docs/comparison.md` measures gfaidx with `--haplotype_gap 10kb` too.**
  It halves the largest pggb chrY GFA and brings the nodes it returns near
  the walk cut's, but reads about as many bytes

## Left to do

- **Prove the per-direction link list,** before bandage-core builds the
  view. The plan follows `docs/comparison/visits/`:
  - truth from the GFA: for each haplotype and each link between two
    reference nodes of a tile, the crossings in each direction
  - cut side: the same from consecutive fragment steps with their strands
  - compare, including stretches inside tiles
  - plant a reversed crossing and a dropped one
  - links with an end off the reference are a lower bound: report how
    often a cut's count falls short, don't judge it
  - run on ada under the caps in `run.sh`
- **The message to Fawaz:** a GitHub issue on gfaidx-viz.
  - Its three points: the bandage-core offer; a request to check the gfaidx
    column of `docs/comparison.md`; and permission to borrow the
    copy-number track and per-direction path list, credited
  - The owner posts it after pushing main, so the link shows the
    `--haplotype_gap` version. The draft is in the session transcript
- **Build both views in bandage-core,** credited to gfaidx-viz.
  Copy-number is proven; the link list waits on the proof above
- **Later additions, not before the freeze:**
  - a lookup side file from a haplotype's own coordinates to tiles, built
    from walk rows' `path` and `hapOffset`
  - per-node tags as a unit kind or a side file
