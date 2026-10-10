# gfa-to-tabix

`gfa-to-tabix` indexes a pangenome graph's GFA by genome coordinate. It writes
the graph's nodes and links as two bgzip-compressed, Tabix-indexed BED files,
and with [`--walks`](#walks) a third holding every haplotype's path, one set
per reference, so a genome browser can fetch the part of the graph under a
region with HTTP range requests. The [JBrowse 2](https://jbrowse.org) graph track reads these files.

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

It writes three files and their indexes for each sample in `--refs`,
`<prefix>.<sample>.<kind>.bed.gz`:

```
chr22.GRCh38.walks.bed.gz  chr22.GRCh38.walks.bed.gz.tbi
chr22.GRCh38.nodes.bed.gz  chr22.GRCh38.nodes.bed.gz.tbi
chr22.GRCh38.links.bed.gz  chr22.GRCh38.links.bed.gz.tbi
chr22.CHM13.walks.bed.gz   chr22.CHM13.walks.bed.gz.tbi
chr22.CHM13.nodes.bed.gz   chr22.CHM13.nodes.bed.gz.tbi
chr22.CHM13.links.bed.gz   chr22.CHM13.links.bed.gz.tbi
```

The tool cuts each path into pieces, one for each stretch the path spends in a
64 kb chunk of a reference, and files each piece under its chunk. A region
query on the walk file returns every path's steps through the region, and the
same query on the node and link files returns the nodes and links those steps
visit. A sample's three files hold only the rows filed under its own chunks,
so a reader on GRCh38 downloads an index that covers GRCh38 alone.

A step on a reference node takes that node's chunk; a step on any other node
takes the chunk of the last reference step before it. A query over a window
therefore returns every path that visits a reference node in it. On the
reference's own paths, a step takes the chunk of its own offset along the
path, so where the reference passes a node more than once, as in a satellite
array, each pass is filed where it lies. A node has one coordinate, from its
first visit, so another haplotype that passes such a collapsed node again is
filed under the reference's first copy. A piece of more than `--cap` steps
continues in further rows. A path that visits no node of a reference has no
rows under it, and the tool counts these on stderr.

| Option            | Effect                                                                |
| ----------------- | --------------------------------------------------------------------- |
| `--refs <names>`  | Comma-separated PanSN samples, each with its own files. Required.     |
| `--chunk <bp>`    | Chunk size. Default 65536.                                            |
| `--cap <steps>`   | Most steps in one row. Default 8192.                                  |
| `--settle <bp>`   | Shortest run that moves a path to another chunk. Default 0, off.      |
| `--sequences`     | Add each node's sequence to its rows.                                 |

`--settle` keeps a run of reference steps in another chunk that spans fewer
than the given bp, such as a pass over a collapsed repeat copy, in the piece it
interrupts. A window over that run's own nodes then lacks those steps, and
after a long stretch off the reference the run can be filed two or more chunks
from its nodes, beyond the one chunk back a reader queries. On the chr22 graph
under [Scale](#scale), 45 windows cut with every haplotype, as the JBrowse
graph track cuts them, hold 18,267 cases of a path visiting a reference node in
the window. With `--settle 32768` the cut left the path out in 60 of them and
drew it without some of those nodes in 89, mostly at 18.74 Mb in the 22q11
repeats; without it, the cut left none out. Against gbz-base with 8
haplotypes, 41 of the windows matched without it and 39 with it. Without it, a
path that passes over nodes placed on another repeat copy, as at 20.3 Mb, is
drawn in more fragments. The files are 408 MB without it and 443 MB with
it, and a window of 10 to 260 kb reads the same bytes within 3%.

Every row is filed under the first base of its chunk, `anchorSeq chunkStart
chunkStart+1`. A row spanning the whole chunk would share a Tabix bin with the
next chunk, and a query would read both. A reader fetching a window therefore
queries from the start of the chunk before the window.

```
walks:  anchorSeq cs cs+1  path fragStart hapOffset piece nsteps steps  [pv:i:cs] [nx:i:cs]
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

`pv` and `nx` give the start of the chunk the path's previous and next piece is
filed under, as `pv:Z:seq:start` when that chunk is on another reference
sequence, and a row at either end of its path has no tag there. A reader that
cuts a path off at the edge of what it read, such as a haplotype that leaves the
reference inside a window and rejoins it in a chunk the read did not reach,
reads on to that chunk, and knows a contig that ends from one that goes on. The
tags add 0.8% to the chr22 walk file under [Scale](#scale).

Each file opens with header lines, which start with `#`: `tabix -H` prints them
and region queries skip them. The first is `#walks` (`#nodes` and `#links` in
the other two files, which have only this line) and three tab-separated
fields: `chunk:i:` the chunk size, `maxnode:i:` the longest node in bp, and
`cap:i:` the most steps in one row, as `--cap` set it. The walk file then
names its reference sample and each other haplotype with rows in the file, the
other `--refs` samples included, as its PanSN `sample#haplotype` (a path name
up to its second `#`), once each in byte order:

```
#walks	chunk:i:65536	maxnode:i:1024	cap:i:8192
#reference	GRCh38
#haplotype	CHM13#0
#haplotype	HG00097#1
#haplotype	HG00097#2
...
```

A node that overlaps a window starts at most `maxnode` bp before it, so the
chunk holding its row is at most that far back: a reader queries from
`max(chunk, maxnode)` bp before the window, rounded down to a chunk start. vg
chops nodes at 1,024 bp, so for its graphs that is the one chunk back described
above; a graph with longer nodes needs more.

A reader can list the haplotypes from the header without reading any rows. On
the chr22 graph under [Scale](#scale) the header is 465 lines and 9,778 bytes,
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

For files written with `--walks`, `walksUri` takes the prefix up to the
reference sample, so a track on hg38 reads the GRCh38 set and a track on hs1
would name the CHM13 one. `defaultHaplotypes` names the haplotypes the track
draws until the user picks others:

```json
"adapter": {
  "type": "RgfaTabixAdapter",
  "walksUri": "https://example.org/hprc-v2.1-mc-grch38.GRCh38",
  "assemblyNameToPanSN": { "hg38": "GRCh38" },
  "defaultHaplotypes": ["HG002", "HG00733"]
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
a 5.0 GB GFA) with `--refs GRCh38,CHM13`, it runs in about 2 min from the
gzipped GFA and peaks at 1.4 GB on a 16-core laptop. The files, three for each
reference, total 408 MB. GRCh38's three indexes total 31 KB, where one set
covering both references took 56 KB.

## Alleles

`gfa-to-tabix alleles <prefix>` reads `<prefix>.segs.bed.gz` and
`<prefix>.links.bed.gz`, indexed with `--layout contig`, and writes
`<prefix>.alleles.bed.gz` with its index: one row per allele the graph holds,
anchored on the reference, with a CIGAR that states its size. The graph itself
is not needed, so a hosted pair works.

```bash
gfa-to-tabix hprc.sv.gfa.gz --layout contig -o hprc
gfa-to-tabix alleles hprc
```

- A link between two backbone nodes that leaves a gap is a deletion
- A link from a backbone node to an off-backbone one enters an allele; the walk
  follows links until it arrives back on the backbone
- A walk that never rejoins the backbone is dropped, and the count goes to
  stderr
- Columns: `#chrom start end name score strand thickStart thickEnd itemRgb class
  delta altLen refLen CIGAR discoveryRank firstSeenIn nested segments`

## Bubbles

`gfa-to-tabix bubbles --snarls <vcf> -o <prefix>` writes
`<prefix>.bubbles.bed.gz` with its index from a `vg deconstruct` snarl VCF
(`pggb -V` writes one too). It gives a plain GFA the bubble file that
`gfatools bubble` gives an rGFA, which finds none on a plain GFA.

```bash
vg deconstruct -P K12 -a graph.gbz > graph.snarls.vcf
gfa-to-tabix bubbles --snarls graph.snarls.vcf -o graph
```

- `-a` makes `vg deconstruct` write the `LV` tag, and the command keeps the
  `LV=0` snarls, none of which overlap
- The reference's contig names in the VCF must match the segment files', so
  rename a PanSN path with `bcftools annotate --rename-chrs` first
- `--min-alleles N` skips a snarl with fewer than N traversals (default 2)
- Columns are `gfatools bubble`'s: chrom, start, end, segments, walks,
  inversion, shortest, longest, three `.`, and the segment ids, the first
  qualified by its reference start (`544433@3943363`)

## Matching the JBrowse scripts

The `contig` layout reproduces `build_rgfa_tabix.sh` and `build_pggb_tabix.sh`
from the
[JBrowse repository](https://github.com/GMOD/jbrowse-components/tree/main/scripts),
which ran `gfatools gfa2bed`, awk, a Python script, `sort`, `bgzip` and
`tabix`. Its rows match those scripts' output byte for byte, and
`scripts/parity.sh` runs both and compares the rows and the answers htslib's
`tabix` gives from each index. `alleles` likewise matches `build_rgfa_alleles.sh`,
and `parity.sh` compares those rows too.

A Tabix index holds coordinates up to 512 Mb, so a longer reference sequence
cannot be indexed.

## See also

- [jbrowse-plugin-graphgenomeviewer](https://github.com/GMOD/jbrowse-plugin-graphgenomeviewer) -
  JBrowse 2 plugin that browses these graphs by locus
- [@gmod/gbz-base](https://github.com/GMOD/gbz-base-js) - range-request reader
  for `.gbz.db` databases
- [gbz-haplotype-index](https://github.com/GMOD/gbz-haplotype-index) - names
  every walk in a gbz-base cut
- [gfa-to-pairwise-paf](https://github.com/cmdcolin/gfa-to-pairwise-paf-rs) -
  graph to PAF, for synteny views

Tutorials on [jbrowse.org](https://jbrowse.org/jb2/docs/tutorials/)

- [Hosting your own graph](https://jbrowse.org/jb2/docs/tutorials/pangenome_prepare_graph/)
- [Minigraph-Cactus](https://jbrowse.org/jb2/docs/tutorials/pangenome_cactus/)
- [pggb](https://jbrowse.org/jb2/docs/tutorials/pangenome_ecoli/)
- [HPRC part 2: haplotypes against each other](https://jbrowse.org/jb2/docs/tutorials/pangenome_hprc_haplotypes/)

## License

Apache-2.0
