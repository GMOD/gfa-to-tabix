# Brief: what is the ideal design for the walks file?

You are one of four independent reviewers. The others work separately; you
will not see their work. Your job: find the IDEAL design for storing every
haplotype's path through a pangenome graph so a browser can fetch any region
over HTTP, and back it with measurements. Don't defend the current design
because it exists, and don't change it for its own sake.

## Why this review exists

gfa-to-tabix 3.0.0 shipped walk format 6 today (2026-11-05). On reading the
encoding, the user (the project owner) was surprised that every row of a
64 kb chunk is filed at the chunk's first base, `seq cs cs+1`, so a plain
`tabix file chr1:15-35` returns nothing, and only a reader that rounds to
chunk starts (graph-walks) gets rows. Their words: "that sounds crazy to me",
"would this not incur large data download", "it seems somewhat like a misuse
of tabix even", "im really trying to get the right format not some hacky
system", "i am surprised we are still sort of fumbling with this design.
lets try to get the ideal thing hammered out", "think about ideal designs",
"we can do measurements".

No ADR records the chunk-first-base choice or measured its alternative. The
spec's whole rationale is one sentence: "A row spanning the whole chunk
would share a Tabix bin with the next chunk, and a query would read both."

The project allows format breaks: there is no backward compatibility to
keep for the walks stack (gfa-to-tabix, graph-walks, bandage-core, the
JBrowse plugin), and hosted data can be rebuilt.

The user also said: "we dont strictly have to file each chunk at its real
span if there is issue....clearly something drove us to the current way the
format is. we can look at history and run tests as needed". So treat the
current design's history as evidence: find what drove it (git history of
docs/walks-format.md, README.md, src/, docs/handoff/, docs/adr/,
docs/issues-log.md; e.g. `git log -S'cs cs+1'`, commit 842a19b, 08ffa5a,
and graph-walks' history of its chunk reads) and test whether those reasons
hold with measurements.

## What the file must do (requirements, as the project states them)

- Static hosting: a browser reads it with HTTP range requests from any
  static host (S3, GitHub Pages); no server-side code
- A region query gives what a reader needs to rebuild every haplotype's exact
  path (every step, strand, which pass of a repeated reference node) through
  the region, plus every place a path departs from the reference
- Scale: HPRC release 2, ~460 haplotypes, genome-wide, Minigraph-Cactus
  (vg, nodes ≤1 kb) and pggb (long nodes, collapsed repeats, many passes)
- Readers: @jbrowse/graph-walks (TypeScript) rebuilds paths for the JBrowse
  graph plugin and BandageJS
- Views range from ~1 kb to ~1 Mb windows

## Read first

In /home/cdiesh/src/gfa-to-tabix (read only; do not edit or commit):
- docs/walks-format.md: the format 6 spec (rows, chunks, encoding, reading
  a window, scale)
- docs/adr/0001 to 0009: decisions so far, with measurements
- docs/open-problems.md, docs/issues-log.md (history of what broke and why)
- docs/index-format.md: the sibling node/link index (`.graph.bed.gz`), a
  different file the graph track reads
- docs/format-2/: earlier measurements; chr22-chunks.jsonl.gz has per-chunk
  gzipped sizes from MC chr22 (format 2 era, 463 haplotypes)
- src/: the writer (Rust)

Reader: /home/cdiesh/src/graph-walks (TypeScript; read only). @gmod/tabix, the
Tabix client JBrowse uses, is at
/home/cdiesh/src/graph-walks/node_modules/@gmod/tabix.

## Data and machines

- Local machine (~30 GB RAM, shared by several agents): keep runs small.
  Don't run the repo's full test suites or cargo builds of the main checkout;
  if you need to build a prototype, use your own `git worktree` under your
  OUTDIR and build only that. node is available locally
- `ssh ada`: 125 GB RAM, 24 cores, SHARED with other users. Work only under
  `~/work/review-<your name>/`. Cap memory on anything heavy:
  `systemd-run --user --scope -p MemoryMax=60G -p MemorySwapMax=0 <cmd>`.
  A genome-wide build is running there (gfa-to-tabix from
  ~/src/gfa-to-tabix-3.0.0, `grch38.gfa`); never touch it or its files.
  Don't `pkill -f` over ssh (it matches its own command line). ada has
  cargo, bgzip, tabix, zstd and node (via fnm). Ship local code with a
  `git bundle`; don't modify ada's existing ~/src checkouts
- On ada: `~/work/rel3/mc22.GRCh38.walks.bed.gz` (+ .tbi) is the 3.0.0
  format 6 file for HPRC v2.1 MC chr22 (59 MB); its GFA is
  `~/work/mc/chr22.gfa` (built with `--walks --refs GRCh38`). `~/work/pggb/`
  holds HPRC pggb chrY and chr22 GFAs (`*.gfa.zst`) and measurement scripts
  (`windows.sh`). `~/work/pggbY.GRCh38.walks.bed.gz` is a format 6 pggb chrY
  file
- Copy what you need locally with scp if it's small (the 59 MB file is fine)

## Questions every reviewer answers

- Is filing a chunk's rows at a 1 bp interval a misuse of Tabix? What does it
  cost (bytes per window, requests, correctness for generic tools), and what
  does it actually buy? Verify the bin-sharing claim against @gmod/tabix's
  real fetch behaviour and htslib's, with numbers
- What is the right unit of storage and retrieval: fixed chunks, sites
  (bubbles), nodes, per-haplotype pieces, or something else?
- Should the walks file be Tabix at all, or a different container (e.g. a
  custom block format with its own index, bigBed-style R-tree, Parquet row
  groups, a GBWT-like structure)? Consider prior art
- Should walks and the node/link index (`.graph.bed.gz`) stay separate files?
- What does your ideal design cost, measured against format 6 on MC chr22 (and
  pggb chrY where it matters): bytes fetched per window at 1 kb, 10 kb,
  100 kb and 1 Mb (fixed random windows, report median/p90/p99), requests
  per window, file size, writer and reader complexity, failure modes
  (repeats, long nodes, inversions, huge chunks)

## Deliverable

Write `OUTDIR/proposal.md` (bullet lists, not numbered lists):
- Diagnosis: what is wrong or right with format 6, with evidence
- Your ideal design: record layout, index/container, the exact query
  procedure a reader runs for a window, how it rebuilds paths
- Measurements: method (scripts kept in OUTDIR), numbers, against format 6
- Tradeoffs and failure modes, honestly
- Verdict: what the project should do, and the smallest first step

Measure where you can; where a number would take a full prototype, estimate
from real data and say it's an estimate. Your final reply: the proposal's
Verdict section plus a 5-line summary of your measurements.
