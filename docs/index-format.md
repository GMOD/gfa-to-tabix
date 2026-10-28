# The node and link index

- **In:** an rGFA, or a plain GFA with paths; see [inputs](#inputs)
- **Out:** `<prefix>.segs.bed.gz`, one row per node, and
  `<prefix>.links.bed.gz`, one row per link, each with a `.tbi`
- **Filing:** the tool files each row under a reference interval, so one region
  query on each file returns the nodes and links a browser draws there
- **Why two files:** every graph drawing reads both, and issues the two reads
  together. One file would save some bytes and an index load, so the merge
  waits for the next format change;
  [ADR 0002](adr/0002-two-index-files.md) has the readers and measurements

```bash
gfa-to-tabix hprc-v2.1-mc-grch38.sv.gfa.gz -o hprc
gfa-to-tabix ecoli.gfa.gz --reference K12 -o ecoli
```

| Option                 | Effect                                                                                  |
| ---------------------- | --------------------------------------------------------------------------------------- |
| `--reference <name>`   | For a plain GFA: the PanSN sample, assembly or path to use as reference. Default the first path. |
| `-o`, `--out <prefix>` | Output prefix. Default the input name without `.gfa[.gz]`.                              |
| `--layout <layout>`    | `anchored` (default) or `contig`; see [layouts](#layouts).                              |
| `--max-component <n>`  | Anchored: a component of more than n nodes keeps its own coordinates, and a graph track draws it as stubs; `none` files every component under the reference. Default 10000; see the [README](../README.md#why-does-the-graph-track-draw-some-bubbles-as-stubs---max-component). |

## Inputs

The tool reads a GFA file, plain or gzipped, and recognizes gzip by the file's
first two bytes, whatever the name. `-` reads stdin, given `-o`. The tool takes
coordinates from rGFA tags or from a reference path, depending on which lines
the file has; see
[how the tool tells them apart](#how-the-tool-tells-them-apart).

### rGFA

- An rGFA has `SN`, `SO` and `SR` tags on every S line. The tool copies each
  S line's `SN` (sequence), `SO` (offset) and `SR` (rank: 0 for the reference,
  higher for a node another assembly contributed)
- Written by: minigraph (`-cxggs`), and the minigraph stage of
  Minigraph-Cactus (`*.sv.gfa.gz`)
- Command: `gfa-to-tabix graph.gfa.gz -o prefix`
- Bubbles need `gfatools` on PATH; see [build](subcommands.md#build)

### Plain GFA with paths

- Written by: pggb (`*.smooth.final.gfa`), `odgi view -i graph.og -g`,
  `vg convert -f graph.gbz`, and base-level Minigraph-Cactus (`*.gfa.gz`, or
  the GBZ through `vg convert -f`)
- Paths are P lines or W lines, named `sample#haplotype#contig` (PanSN) where
  possible
- Command: `gfa-to-tabix graph.gfa.gz --reference K12 -o prefix`
- `--reference` takes a PanSN sample, an assembly or a path name, with or
  without the `:start-end` range pggb appends; without it the first path is
  the reference
- **Coordinates:** the tool walks every path of the reference first, then every
  other path, each group in byte order of name and then start, summing node
  lengths. A node takes the path name and position of the first path to reach
  it, at rank 0 on the reference and rank 1 elsewhere. The rows are the same
  for any order of the P and W lines, which `vg convert` changes from run to
  run
- **Blunt graphs only:** summing node lengths gives the path coordinate only
  when nodes abut, so a plain GFA needs overlaps `*` or `0M`
- **Orientation:** when the first path to reach a node reads it reversed, the
  tool turns the node to read forward before writing anything, and every link
  end on it takes the other strand. The index then reads the reference forward,
  as an rGFA's does, and only a haplotype that reads against the reference
  shows as an inversion
- **Collapsed repeats:** pggb merges the copies of a repeat into shared nodes
  the reference passes more than once. Such a node has one row, at its first
  pass. A window over a later pass returns no row for the node, only its links,
  which the tool files under an interval covering both passes, so they can span
  megabases ([wide intervals](#wide-intervals)).
  [Walk files](walks-format.md#paralogs-and-collapsed-repeats) place each
  haplotype step at the nearest pass instead
- Bubbles come from a `vg deconstruct -a` VCF; see
  [bubbles](subcommands.md#bubbles)

### How the tool tells them apart

- Every S line has an `SN` tag, and no `--reference`: rGFA
- Some S lines have `SN` tags and the graph has no P or W lines: rGFA, which
  leaves out the untagged segments
- Anything else: plain GFA

### Errors

The tool stops before writing anything on these:

- `--reference NOPE matches no path; have: K12#0#chr`: the name matches no
  path. The message lists the paths the graph has
- `link 1->2 has a non-blunt overlap (5M)`: the graph's nodes overlap. The
  message says to blunt the graph first, or use an rGFA
- `no P or W lines, and the S lines carry no rGFA tags`: the file has neither
  coordinate source

## Layouts

A reference query has to return the alternate alleles at a locus, though their
nodes lie off the reference. The tool files each row under an interval chosen
so that they come back, and `--layout` sets how it chooses.

**`anchored`** (default):

- The tool files a reference node (rank 0) under its coordinate
- The tool files every other node under the reference interval its bubble
  hangs from. The nodes joined to it without passing through the reference form one
  component, whose interval runs from the first to the last reference node it
  links to
- The tool files a link under the interval that covers what both of its nodes
  reach: a component's interval for a node in one, and for a reference node its
  coordinate, the components hanging from it and the reference nodes it links to
- One query on each file then returns the whole graph under a region, however
  deeply alleles nest. A window inside a large bubble returns every allele of
  that bubble
- A region query on the link file returns every link with a node under the
  region and every link between the nodes those lead to. It also returns links
  of neither kind, so a reader keeps a link when one of its nodes came back from
  the node file, or when both are far ends of links it kept
- A link between two reference nodes on opposite sides of the region, such as a
  deletion that spans it, touches no node under the region. The query returns
  it all the same, and a reader that wants it drawn keeps it too
- A component that links to two reference sequences gets a row under each. A
  component that links to none keeps its coordinates
- The tool files a zero-length node under one base, since a region query skips
  a row whose interval is empty; its coordinate in the later columns stays exact

![The two Tabix queries a browser runs to view chr1:13-18, the node and link lines each returns, and the graph it draws from them, with each node and edge coloured by the file it came from](figures/overview.svg)

**`contig`**: the tool files every node under its own coordinate, as version
0.1.0 did. A reader has to follow links from the reference onto other contigs,
one round of queries per step, and the index covers every contig in the graph.
Use it to browse the graph from a non-reference assembly's coordinates. A
zero-length node keeps its empty interval, as the JBrowse scripts wrote it, so
a region query never returns it.

## What the files hold

`<prefix>.segs.bed.gz` has one row per node:

```
anchored:  anchorSeq anchorStart anchorEnd  nodeId  rank  sequence start end  [SM:Z:assembly,...]
contig:    sequence start end  nodeId  rank  [SM:Z:assembly,...]
```

`sequence start end` is the node's own coordinate. The last column appears for a
plain GFA only, and lists the assemblies whose paths visit the node, written
`sample.haplotype`.

`<prefix>.links.bed.gz` states both nodes of a link in full after the interval
the row is filed under:

```
seq start end  srcId± tgtId±  srcSeq srcStart srcEnd srcRank  tgtSeq tgtStart tgtEnd tgtRank  [srcSM tgtSM]
```

Anchored, a link has one row per reference sequence. By contig, it has two rows,
one under each node's coordinate.

The tool sorts rows by sequence name in byte order, then by start.

## Scale

- The tool holds the whole graph in memory. HPRC's whole-genome SV rGFA
  indexes in seconds on a laptop, in about a gigabyte with `anchored` and about
  twice that with `contig`
- The `contig` indexes are much larger than the `anchored` ones, because a
  Tabix index spends 8 bytes per 16 kb of every contig
- Memory grows with total path length. HPRC's pggb chrY, 7.7 GB of GFA,
  indexes in a minute and 5.2 GB, and pggb chr22, 27 GB, in 6.5 minutes and
  18.7 GB. For a larger graph use [`--walks`](walks-format.md)
- A Tabix index holds coordinates up to 512 Mb. A file with a row past that
  gets a `.csi` index instead, which holds up to 34 Gb, and every other file
  keeps its `.tbi`

## Wide intervals

A row with a wide interval overlaps every window inside it, so every query
there reads it. Rows sort by start, so wide rows lie scattered through the file
and each costs a reader a compressed block.

- **Cause:** `widen` in `src/anchor.rs` keeps one minimum and maximum per
  reference sequence, so a component attached at 1 Mb and 40 Mb files as 1-40 Mb.
  A reference node's links share the interval of its deletion link
- **Minigraph-Cactus and rGFA graphs:** the reference passes each node once, and
  wide intervals are few
- **Giant components:** on HPRC's pggb chrY, one component of 3.5 M nodes
  fills GRCh38's 30 Mb Yq12 gap, and with `--max-component none` a 10 kb
  window there overlaps 3.7 M node rows and 7.1 M link rows. The default limit
  of 10,000 leaves the three larger components on their own coordinates, which
  caps a window's node rows near 10,000. A window's link rows still reach
  69,000, from chrY's repeats, and the link file grows from 378 to 682 MB. On
  pggb chr22 the limit takes a median window from 3.9 M link rows to 626
  ([ADR 0005](adr/0005-node-link-format-2.md))
- **pggb graphs:** a node the reference passes several times has one
  coordinate, its first pass, so its links and the alleles beside it span
  every pass. A synthetic 20 Mb graph with repeats at pggb's density has 15% of
  link rows over 1 Mb. A 10 kb window reads 2.8 MB of links and 1.5 MB of nodes
  through @gmod/tabix, against 0.21 and 0.12 MB without the repeats, and
  graph-walks' cut keeps a median of 3,808 nodes, 3,285 of them over 100 kb
  outside the window. [ADR 0005](adr/0005-node-link-format-2.md) proposes the
  fix
- **Graphs without wide rows:** a 10 kb window still reads 0.12 MB of nodes
  through @gmod/tabix 3.10 to 3.12, where htslib's `tabix` reads 0.012 MB.
  htslib and noodles both fold every bin under 64 KB compressed into its parent,
  so the index holds a whole 1 Mb bin as one chunk. htslib reads that chunk from
  the window's linear-index entry and stops at the first row past the window;
  @gmod/tabix reads it whole

## Matching the JBrowse scripts

The `contig` layout reproduces `build_rgfa_tabix.sh` and `build_pggb_tabix.sh`,
and `alleles` reproduces `build_rgfa_alleles.sh`, from the
[JBrowse repository](https://github.com/GMOD/jbrowse-components/tree/c87a58557c2a74b6b770f34994350b69e842ace9/scripts),
where they ran `gfatools gfa2bed`, awk, Python, `sort`, `bgzip` and `tabix`.
JBrowse has since dropped them for this tool.

- The rows match those scripts' output byte for byte
- `scripts/parity.sh` runs both from a checkout of that commit and compares the
  rows and the answers htslib's `tabix` gives from each index
- `bubbles` matches `snarls_to_bubble_bed.py` as of the same commit
