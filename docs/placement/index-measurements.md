# The node and link index: measurements

What was measured of the [node and link index](../index-format.md) on
HPRC's graphs: build time and memory, and how many rows a window reads
where rows are filed under wide intervals. The index page gives the
takeaways.

## Build time and memory

- The tool holds the whole graph in memory. HPRC's whole-genome SV rGFA
  indexes in seconds on a laptop, in about a gigabyte with `anchored` and about
  twice that with `contig`
- The `contig` indexes are much larger than the `anchored` ones, because a
  Tabix index spends 8 bytes per 16 kb of every contig
- Memory grows with total path length. HPRC's pggb chrY, 7.7 GB of GFA,
  indexes in 7.3 GB, in about 65-77 s built with cargo and 95 s with the
  release binary, 100 s up to 5.0.0
  ([measured](pggb-chrY-build.txt),
  [5.0.1](musl-alloc-pggb-chrY.txt)),
  and pggb chr22, 27 GB, took 6.5 minutes and 18.7 GB with the version of
  2026-10-28. For a larger graph use [`--walks`](../walks-format.md)
- A Tabix index holds coordinates up to 512 Mb. A file with a row past that
  gets a `.csi` index instead, which holds up to 34 Gb, and every other file
  keeps its `.tbi`. htslib and JBrowse read both; JBrowse needs `"csi": true`
  in the track's adapter

## Wide intervals

A row with a wide interval overlaps every window inside it, so every query
there reads it. Rows sort by start, so wide rows lie scattered through the file
and each costs a reader a compressed block.

- **Cause:** `widen` in `src/anchor.rs` keeps one minimum and maximum per
  reference sequence, so a component attached at 1 Mb and 40 Mb files as 1-40 Mb.
  A reference node's links share the interval of its deletion link
- **Minigraph-Cactus and rGFA graphs:** the reference passes each node once, so
  no interval spans megabases for a repeat's sake. An interval still runs from
  the start of the first reference node its component links to to the end of
  the last, so a small bubble between two long reference nodes is filed under
  both of them whole, and every window on either returns it. On HPRC's SV
  rGFA most off-reference node rows are filed under more than a kilobase
  and a tenth under more than 100 kb
  ([widths](hprc-sv-interval-widths.txt), from
  `scripts/interval-widths.sh`)
- **Giant components:** on HPRC's pggb chrY, one component of 3.5 M nodes
  fills GRCh38's 30 Mb Yq12 gap, and with `--max-component none` a 10 kb
  window there overlaps 3.7 M node rows and 7.1 M link rows. With the default
  limit of 10,000, the tool leaves the three components over 10,000 nodes on
  their own coordinates, which caps a window's node rows near 10,000. A
  window's link rows still reach 69,000, from chrY's repeats, and the link
  file grows from 378 to 682 MB. On pggb chr22 the limit takes a median window
  from 3.9 M link rows to 626 ([ADR 0005](../adr/0005-giant-components.md))
- **pggb graphs:** a node the reference passes several times has one
  coordinate, its first pass, so its links and the alleles beside it span
  every pass. A synthetic 20 Mb graph with repeats at pggb's density has 15% of
  link rows over 1 Mb. A 10 kb window reads 2.8 MB of links and 1.5 MB of nodes
  through @gmod/tabix, against 0.21 and 0.12 MB without the repeats, and
  graph-walks' cut keeps a median of 3,808 nodes, 3,285 of them over 100 kb
  outside the window. [Open problems](../open-problems.md#collapsed-repeats-in-pggb-graphs)
  has a candidate fix
- **Graphs without wide rows:** a 10 kb window still reads 0.12 MB of nodes
  through @gmod/tabix 3.10 to 3.12, where htslib's `tabix` reads 0.012 MB.
  htslib and noodles both fold every bin under 64 KB compressed into its parent,
  so the index holds a whole 1 Mb bin as one chunk. htslib reads that chunk from
  the window's linear-index entry and stops at the first row past the window;
  @gmod/tabix reads it whole
