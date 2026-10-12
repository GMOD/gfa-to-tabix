# The node and link index

How `gfa-to-tabix` gives every node a coordinate, files it, and what the rows hold.

## Where the coordinates come from

A GFA lists nodes (S lines) and links (L lines) in no positional order. The tool
gives every node a coordinate one of two ways.

**rGFA.** Every S line has three tags: `SN`, the sequence the node lies on;
`SO`, its offset on that sequence; and `SR`, its rank, 0 for the reference and
higher for a node another assembly contributed. The tool copies them out. It
takes this route when every S line has an `SN` tag and no `--reference` is given.

**Plain GFA.** The P and W lines list the nodes each assembly passes through.
The tool walks every path of the reference assembly first, then every other
path in file order, adding node lengths as it goes. A node takes the path name
and position of the first path to reach it, at rank 0 on the reference and
rank 1 elsewhere. The graph must be blunt (overlaps `*` or `0M`), because
summing node lengths is only the path coordinate when nodes abut.

A node that path reads reversed is turned to read forward there before anything
is written: every link end on it takes the other strand. The index then reads
the reference forward, as an rGFA's does, and only a haplotype that reads
against the reference shows as an inversion.

## Layouts

A reference query has to return the alternate alleles at a locus, and their
nodes do not lie on the reference. The tool files each row under an interval
chosen so that they come back.

**`anchored`** (default). A reference node, rank 0, is filed under its
coordinate. Every other node is filed under the reference interval its bubble
hangs from: the nodes joined to it without passing through the reference form
one component, and the component's interval runs from the first to the last
reference node it links to. One query on each file then returns the whole graph
under a region, however deeply alleles nest. A window inside a large bubble
returns all of that bubble.

A link is filed under the interval that covers what both of its nodes reach: a
component's interval for a node in one, and for a reference node its
coordinate, the components hanging from it and the reference nodes it links
to. A region query on the link file therefore returns every link with a node
under the region and every link between the nodes those lead to. It also
returns links of neither kind, so a reader keeps a link when one of its nodes
came back from the node file, or when both are far ends of links it kept.

A link between two reference nodes on opposite sides of the region, such as a
deletion that spans it, touches no node under the region. The query returns
it all the same, and a reader that wants it drawn keeps it too.

A component that links to two reference sequences gets a row under each. A
component that links to none keeps its coordinates.

A zero-length node is filed under one base, since a region query skips a row
whose interval is empty; its coordinate in the later columns stays exact.

**`contig`**. Every node is filed under its coordinate, as version 0.1.0
did. A reader has to follow links from the reference onto other contigs, one
round of queries per step, and the index covers every contig in the graph. Use
it to browse the graph from a non-reference assembly's coordinates.

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

Rows are sorted by sequence name in byte order, then by start.

## Scale

The tool holds the whole graph in memory. On HPRC release 2's
`hprc-v2.1-mc-grch38.sv.gfa.gz` (759,223 nodes, 1,107,199 links, 841 MB
gzipped) it runs in about 12 s and peaks at 0.9 GB on a laptop; `--layout contig`
takes about 20 s and 2.1 GB. The two anchored indexes total 0.5 MB; the
`contig` layout's total 9 MB and inflate to 635 MB each, because a Tabix index
spends 8 bytes per 16 kb of every contig.

A base-level graph of a human chromosome has millions of nodes and one path
step per node per haplotype; memory grows with the total path length. For
graphs that size, use [`--walks`](walks.md).

A Tabix index holds coordinates up to 512 Mb, so a longer reference sequence
cannot be indexed.

## Wide intervals

A Tabix query reads every row filed in the bins above the window, overlapping
or not. A component with a wide interval costs every query inside its bin, and
the cost grows with the component's node count.

- **Measured:** `chr22.sv.gfa.gz` has 3 filed intervals over 1 Mb, each holding
  one row, and 51 over 128 kb, holding 763 rows. A 100 kb window fetches a
  median 6.9× the bytes of its overlapping node rows and 10.3× for links, mostly
  from the 16 kb bin floor
- **Not measured:** genome-wide HPRC, and BGZF block bytes (the figures above
  count uncompressed rows)
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
