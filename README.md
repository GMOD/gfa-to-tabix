# gfa-to-tabix

`gfa-to-tabix` indexes a pangenome graph's GFA by genome coordinate. It writes
the graph's nodes and links as two bgzip-compressed, Tabix-indexed BED files,
so a genome browser can fetch the part of the graph under a region with HTTP
range requests. The [JBrowse 2](https://jbrowse.org) graph track reads this
pair.

One binary does the whole conversion. It needs no gfatools, awk, bgzip or tabix.

## Install

A static binary for Linux x86_64 or macOS on Apple silicon, from the
[releases](https://github.com/GMOD/gfa-to-tabix/releases):

```bash
curl -fL https://github.com/GMOD/gfa-to-tabix/releases/latest/download/gfa-to-tabix-x86_64-unknown-linux-musl.tar.gz | tar xz
```

or build it from crates.io with Rust 1.91 or later:

```bash
cargo install gfa-to-tabix
```

## Usage

```bash
# an rGFA: minigraph, or the minigraph stage of Minigraph-Cactus
gfa-to-tabix hprc-v2.1-mc-grch38.sv.gfa.gz -o hprc

# a plain GFA with paths: pggb, odgi, vg, base-level Minigraph-Cactus
gfa-to-tabix ecoli.gfa.gz --reference K12 -o ecoli
```

Either command writes four files:

```
hprc.segs.bed.gz    hprc.segs.bed.gz.tbi
hprc.links.bed.gz   hprc.links.bed.gz.tbi
```

| Option                  | Effect                                                                                                                  |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `--reference <name>`    | For a plain GFA: the PanSN sample (`GRCh38`), assembly (`HG002#1`) or path to use as reference. Default the first path. |
| `-o`, `--out <prefix>`  | Output prefix. Default the input name without `.gfa[.gz]`.                                                              |
| `--layout <layout>`    | `anchored` (default) or `contig`; see [Layouts](#layouts).                                                              |

The input may be gzipped, and `-` reads stdin, so
`zstd -dc graph.gfa.zst | gfa-to-tabix - -o graph` handles other compression.

## Where the coordinates come from

A GFA lists nodes (S lines) and links (L lines) in no positional order. The tool
gives every node a coordinate one of two ways.

**rGFA.** Every S line carries three tags: `SN`, the sequence the node lies on;
`SO`, its offset on that sequence; and `SR`, its rank, 0 for the reference and
higher for a node another assembly contributed. The tool copies them out. It
takes this route when every S line has an `SN` tag and no `--reference` is given.

**Plain GFA.** The P and W lines list the nodes each assembly passes through.
The tool walks every path of the reference assembly first, then every other
path in file order, adding node lengths as it goes. A node takes the path name
and position of the first path to reach it, at rank 0 on the reference and
rank 1 elsewhere. The graph must be blunt (overlaps `*` or `0M`), because
summing node lengths is only the path coordinate when nodes abut.

## Layouts

A reference query has to return the alternate alleles at a locus, and their
nodes do not lie on the reference. The tool files each row under an interval
chosen so that they come back.

**`anchored`** (default). A reference node, rank 0, is filed under its own
coordinate. Every other node is filed under the reference interval its bubble
hangs from: the nodes joined to it without passing through the reference form
one component, and the component's interval runs from the first to the last
reference node it links to. One query on each file then returns the whole graph
under a region, however deeply alleles nest. A window inside a large bubble
returns all of that bubble.

A link is filed under the interval that covers what both of its nodes reach: a
component's interval for a node in one, and for a reference node its own
coordinate, the components hanging from it and the reference nodes it links
to. A region query on the link file therefore returns every link with a node
under the region and every link between the nodes those lead to. It also
returns links of neither kind, so a reader keeps a link when one of its nodes
came back from the node file, or when both are far ends of links it kept.

A component that links to two reference sequences gets a row under each. A
component that links to none keeps its own coordinates.

**`contig`**. Every node is filed under its own coordinate, as version 0.1.0
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

## Reading the files in JBrowse

With the
[graph genome viewer plugin](https://github.com/GMOD/jbrowse-plugin-graphgenomeviewer),
a graph track names the node file, the link file and the index of each:

```json
{
  "type": "GraphTrack",
  "trackId": "hprc_graph",
  "name": "HPRC graph",
  "assemblyNames": ["hg38"],
  "adapter": {
    "type": "RgfaTabixAdapter",
    "segmentsLocation": { "uri": "https://example.org/hprc.segs.bed.gz" },
    "segmentsIndex": {
      "location": { "uri": "https://example.org/hprc.segs.bed.gz.tbi" }
    },
    "linksLocation": { "uri": "https://example.org/hprc.links.bed.gz" },
    "linksIndex": {
      "location": { "uri": "https://example.org/hprc.links.bed.gz.tbi" }
    },
    "assemblyNameToPanSN": { "hg38": "GRCh38" }
  }
}
```

`assemblyNameToPanSN` maps the JBrowse assembly name to the sample name the
graph uses, when the two differ.

When the four files sit side by side under the names the tool gave them, the
prefix alone is enough:

```json
"adapter": {
  "type": "RgfaTabixAdapter",
  "uri": "https://example.org/hprc",
  "assemblyNameToPanSN": { "hg38": "GRCh38" }
}
```

## Scale

The tool holds the whole graph in memory. On HPRC release 2's
`hprc-v2.1-mc-grch38.sv.gfa.gz` (759,223 nodes, 1,107,199 links, 841 MB
gzipped) it runs in about 12 s and peaks at 0.9 GB on a laptop. The two anchored
indexes total 0.5 MB; the `contig` layout's total 9 MB and inflate to 635 MB
each, because a Tabix index spends 8 bytes per 16 kb of every contig.

A base-level graph of a human chromosome has millions of nodes and one path
step per node per haplotype; expect memory to grow with the total path length.

## Matching the JBrowse scripts

The `contig` layout reproduces `build_rgfa_tabix.sh` and `build_pggb_tabix.sh`
from the
[JBrowse repository](https://github.com/GMOD/jbrowse-components/tree/main/scripts),
which ran `gfatools gfa2bed`, awk, a Python script, `sort`, `bgzip` and
`tabix`. Its rows match those scripts' output byte for byte, and
`scripts/parity.sh` runs both and compares the rows and the answers htslib's
`tabix` gives from each index.

A Tabix index holds coordinates up to 512 Mb, so a longer reference sequence
cannot be indexed.

## License

Apache-2.0
