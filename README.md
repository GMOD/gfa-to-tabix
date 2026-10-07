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

## What the files hold

`<prefix>.segs.bed.gz` has one row per node:

```
sequence  start  end  nodeId  rank  [SM:Z:assembly,assembly,...]
```

The sixth column appears for a plain GFA only, and lists the assemblies whose
paths visit the node, written `sample.haplotype`.

`<prefix>.links.bed.gz` has two rows per link, one under the coordinate of each
node it joins, so a region query finds a link from either side. Every row
states both nodes in full, so the reader learns where the far node lies even
when it sits on another sequence:

```
sequence  start  end  srcId±  tgtId±  srcSeq srcStart srcEnd srcRank  tgtSeq tgtStart tgtEnd tgtRank  [srcSM tgtSM]
```

Rows are sorted by sequence name in byte order, then by start.

## Reading the files in JBrowse

With the
[graph genome viewer plugin](https://github.com/GMOD/jbrowse-plugin-graphgenomeviewer),
point a graph track at the prefix:

```json
{
  "type": "GraphTrack",
  "trackId": "hprc_graph",
  "name": "HPRC graph",
  "assemblyNames": ["hg38"],
  "adapter": {
    "type": "RgfaTabixAdapter",
    "uri": "https://example.org/hprc",
    "assemblyNameToPanSN": { "hg38": "GRCh38" }
  }
}
```

## Scale

The tool holds the whole graph in memory. On HPRC release 2's
`hprc-v2.1-mc-grch38.sv.gfa.gz` (759,223 nodes, 1,107,199 links, 841 MB
gzipped) it runs in about 27 s and peaks at 2.0 GB on a laptop.

A base-level graph of a human chromosome has millions of nodes and one path
step per node per haplotype; expect memory to grow with the total path length.

## Matching the JBrowse scripts

The tool replaces `build_rgfa_tabix.sh` and `build_pggb_tabix.sh` from the
[JBrowse repository](https://github.com/GMOD/jbrowse-components/tree/main/scripts),
which ran `gfatools gfa2bed`, awk, a Python script, `sort`, `bgzip` and
`tabix`. The BED rows match those scripts' output byte for byte, and
`scripts/parity.sh` runs both and compares the rows and the answers htslib's
`tabix` gives from each index. On the HPRC graph above, the rows equal the
files hosted at `https://jbrowse.org/demos/hprc/`.

## License

Apache-2.0
