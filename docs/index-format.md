# The node and link index

- **In:** an rGFA, or a plain GFA with paths; see [inputs](inputs.md)
- **Out:** `<prefix>.segs.bed.gz`, one row per node, and `<prefix>.links.bed.gz`, one row per link, each with a `.tbi`
- **Filing:** the tool files each row under a reference interval, so one region query on each file returns the nodes and links a browser draws there
- **Why two files:** every graph drawing reads both, and issues the two reads together. One file would save some bytes and an index load, so the merge waits for the next format change; [ADR 0002](adr/0002-two-index-files.md) has the readers and measurements

```bash
gfa-to-tabix hprc-v2.1-mc-grch38.sv.gfa.gz -o hprc
gfa-to-tabix ecoli.gfa.gz --reference K12 -o ecoli
```

| Option                 | Effect                                                                                  |
| ---------------------- | --------------------------------------------------------------------------------------- |
| `--reference <name>`   | For a plain GFA: the PanSN sample, assembly or path to use as reference. Default the first path. |
| `-o`, `--out <prefix>` | Output prefix. Default the input name without `.gfa[.gz]`.                              |
| `--layout <layout>`    | `anchored` (default) or `contig`; see [layouts](#layouts).                              |

The input may be gzipped, and `-` reads stdin.

## Where the coordinates come from

- **rGFA:** the tool copies each S line's `SN` (sequence), `SO` (offset) and
  `SR` (rank: 0 for the reference, higher for a node another assembly
  contributed). [Inputs](inputs.md#how-the-tool-tells-them-apart) lists when
  the tool takes this route
- **Plain GFA:** the tool walks every path of the reference first, then every
  other path in file order, summing node lengths. A node takes the path name
  and position of the first path to reach it, at rank 0 on the reference and
  rank 1 elsewhere
- **Collapsed repeats:** pggb merges the copies of a repeat into shared nodes
  the reference passes more than once. Such a node has one row, at its first
  pass. A window over a later pass returns no row for the node, only its links,
  which the tool files under an interval covering both passes, so they can span
  megabases ([wide intervals](#wide-intervals)). [Walk files](walks.md#paralogs-and-collapsed-repeats)
  place each haplotype step at the nearest pass instead
- **Blunt graphs only:** summing node lengths gives the path coordinate only
  when nodes abut, so a plain GFA needs overlaps `*` or `0M`
- **Orientation:** when the first path to reach a node reads it reversed, the
  tool turns the node to read forward before writing anything, and every link end on it
  takes the other strand. The index then reads the reference forward, as an
  rGFA's does, and only a haplotype that reads against the reference shows as
  an inversion

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
Use it to browse the graph from a non-reference assembly's coordinates.

## What the files hold

Every graph drawing reads both files ([ADR 0002](adr/0002-two-index-files.md)).

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
- Memory grows with total path length, so for a base-level graph of a human
  chromosome use [`--walks`](walks.md)
- A Tabix index holds coordinates up to 512 Mb, so the tool cannot index a
  longer reference sequence

## Wide intervals

A Tabix query reads every row filed in the bins above the window, overlapping
or not. A component with a wide interval adds its rows to every query inside its
bin, and the added bytes grow with the component's node count.

- **Effect on chr22:** wide intervals are few and hold few rows. A window still
  fetches several times the bytes of the rows it overlaps, mostly because
  Tabix's smallest bin spans 16 kb
- **Unmeasured:** genome-wide HPRC, and compressed bytes
- **Cause:** `widen` in `src/anchor.rs` keeps one minimum and maximum per
  reference sequence, so a component attached at 1 Mb and 40 Mb files as 1-40 Mb.
  A reference node's links share the interval of its deletion link
- **Fix if the genome-wide tail is heavy:** file a component once per cluster of
  attachments, split where the gap exceeds a threshold, and file a deletion
  link under its span only

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
