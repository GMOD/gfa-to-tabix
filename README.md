# gfa-to-tabix

`gfa-to-tabix` indexes a pangenome graph's GFA by genome coordinate. It writes
the graph's nodes and links as two bgzip-compressed, Tabix-indexed BED files,
and with [`--walks`](#walks) a third holding every haplotype's path, so a
genome browser can fetch the part of the graph under a region with HTTP range
requests. The [JBrowse 2](https://jbrowse.org) graph track reads these files.

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

`--walks` writes the paths themselves instead; see [Walks](#walks).

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

A link between two reference nodes on opposite sides of the region, such as a
deletion that spans it, touches no node under the region. The query returns
it all the same, and a reader that wants it drawn keeps it too.

A component that links to two reference sequences gets a row under each. A
component that links to none keeps its own coordinates.

A zero-length node is filed under one base, since a region query skips a row
whose interval is empty; its own coordinate in the later columns stays exact.

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

## Walks

`--walks` indexes every haplotype's path through a base-level graph with integer
node ids and W or P lines, such as `vg convert -f` writes from a
Minigraph-Cactus GBZ:

```bash
vg convert -f chr22.gbz > chr22.gfa
gfa-to-tabix chr22.gfa --walks --refs GRCh38,CHM13 -o chr22
```

It writes six files:

```
chr22.walks.bed.gz  chr22.walks.bed.gz.tbi
chr22.nodes.bed.gz  chr22.nodes.bed.gz.tbi
chr22.links.bed.gz  chr22.links.bed.gz.tbi
```

The tool cuts each path into pieces, one for each stretch the path spends in a
64 kb chunk of a reference, and files each piece under its chunk. A region
query on the walk file returns every path's steps through the region, and the
same query on the node and link files returns the nodes and links those steps
visit. Each sample named in `--refs` gets its own rows, in the same three
files, so one set answers queries on GRCh38 and on CHM13.

A step on a reference node takes that node's chunk; a step on any other node
takes the chunk of the last reference step before it. A run of reference steps
in another chunk that spans fewer than `--settle` bp, such as a collapsed
repeat copy or a short inversion, stays in the piece it interrupts. A piece of
more than `--cap` steps continues in further rows. A path that visits no node
of a reference has no rows under it, and the tool counts these on stderr.

| Option            | Effect                                                                |
| ----------------- | --------------------------------------------------------------------- |
| `--refs <names>`  | Comma-separated PanSN samples to file rows under. Required.           |
| `--chunk <bp>`    | Chunk size. Default 65536.                                            |
| `--cap <steps>`   | Most steps in one row. Default 8192.                                  |
| `--settle <bp>`   | Shortest run that moves a path to another chunk. Default chunk / 2.   |
| `--sequences`     | Add each node's sequence to its rows.                                 |

Every row is filed under the first base of its chunk, `anchorSeq chunkStart
chunkStart+1`. A row spanning the whole chunk would share a Tabix bin with the
next chunk, and a query would read both. A reader fetching a window therefore
queries from the start of the chunk before the window.

```
walks:  anchorSeq cs cs+1  path fragStart hapOffset piece nsteps steps
nodes:  anchorSeq cs cs+1  nodeId rank sequence start end  LN:i:length  [SQ:Z:bases]
links:  anchorSeq cs cs+1  srcId± tgtId±  srcSeq srcStart srcEnd srcRank  tgtSeq tgtStart tgtEnd tgtRank
```

`path` is `sample#haplotype#contig`. `fragStart` is where the W line starts on
that contig, or the start in a P line's name (`[start]`, `#start` or
`:start-end`), and `hapOffset` is where the piece starts. `piece` numbers the
pieces along the path for one reference, so a reader joins consecutive pieces
back into one walk. `steps` lists the piece's steps as integers: the first is
`2 × id + r`, with `r` 1 for a step on the reverse strand, and each one after
is `2 × (id − previous id) + r`. Every row starts from an absolute id, so a row
decodes on its own.

Each file opens with header lines, which start with `#`: `tabix -H` prints them
and region queries skip them. The first gives the chunk size: `#walks`, a tab
and `chunk:i:65536` (`#nodes` and `#links` in the other two files, which have
only this line). The walk file then names each sample in `--refs`, in that
order, and each other haplotype with rows, as its PanSN `sample#haplotype` (a
path name up to its second `#`), once each in byte order:

```
#walks	chunk:i:65536
#reference	GRCh38
#reference	CHM13
#haplotype	HG00097#1
#haplotype	HG00097#2
...
```

A reader can list the haplotypes from the header without reading any rows. On
the chr22 graph under [Scale](#scale) the header is 465 lines and 9,750 bytes,
which the file's first BGZF block holds.

A reference node is placed on its reference at rank 0. Any other node takes
its position from the path whose name sorts first in byte order among the
paths that visit it, at that path's earliest visit, and has rank 1. The rows
therefore do not depend on the order of the W lines, which `vg convert`
changes from run to run. The node file holds every node a piece under the
chunk visits; the link file holds every link between consecutive steps of
those pieces, and the link from the previous piece, which is filed under both
chunks.

The tool reads the GFA twice, so it takes a file, not stdin; gzip is fine. It
keeps 12 bytes per node and 4 per link, 16 bytes per node and 4 per link for
each reference, and with `--sequences` the graph's bases. Rows wait for an
external sort in up to 2 GB of memory and then in compressed runs in a
temporary directory beside the output.

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
gzipped) it runs in about 12 s and peaks at 0.9 GB on a laptop; `--layout contig` takes
about 20 s and 2.1 GB. The two anchored
indexes total 0.5 MB; the `contig` layout's total 9 MB and inflate to 635 MB
each, because a Tabix index spends 8 bytes per 16 kb of every contig.

A base-level graph of a human chromosome has millions of nodes and one path
step per node per haplotype; expect memory to grow with the total path length.

`--walks` holds only per-node and per-link arrays, and streams the paths. On a
Minigraph-Cactus chr22 (3.1 M nodes, 4.7 M links, 1,131 paths, 630 M steps,
a 5.0 GB GFA) with `--refs GRCh38,CHM13`, it runs in about 2 min and peaks at
1.4 GB on a 16-core laptop, and in about 3 min from the gzipped GFA. The six
files total 443 MB.

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
