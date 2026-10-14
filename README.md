# gfa-to-tabix

- **In:** a pangenome graph as GFA, from minigraph, Minigraph-Cactus, pggb, odgi or vg
- **Out:** bgzip-compressed, Tabix-indexed BED files a genome browser reads by region with HTTP range requests
- One static binary does the whole conversion. It needs no gfatools, awk, bgzip or tabix
- The [JBrowse 2](https://jbrowse.org) graph track reads the files

![A five-node graph, its node and link rows, a region query on both files, and the bubble a browser draws from the rows it keeps](docs/figures/overview.svg)

`scripts/figures.py target/release/gfa-to-tabix` redraws both figures from the tool's output on `docs/figures/*.gfa`, and CI fails when they go stale.

## Input

| Input                | Written by                                                          | Command                                  |
| -------------------- | ------------------------------------------------------------------- | ---------------------------------------- |
| rGFA                 | minigraph; the minigraph stage of Minigraph-Cactus (`*.sv.gfa.gz`) | `gfa-to-tabix graph.gfa.gz`              |
| Plain GFA with paths | pggb, odgi, vg, base-level Minigraph-Cactus                         | `gfa-to-tabix graph.gfa.gz --reference X` |
| Base-level graph with W or P lines, for haplotype paths | `vg convert -f` on a GBZ         | `gfa-to-tabix graph.gfa --walks --refs X` |

- **rGFA:** every S line has `SN`, `SO` and `SR` tags that name the node's sequence, offset and rank. The tool copies them
- **Plain GFA:** no coordinate tags. The tool takes coordinates from the P or W lines of the reference, so the nodes must abut (overlap `*` or `0M`)
- **Reference:** a PanSN sample (`sample#haplotype#contig`), an assembly or a path name
- [How to produce and pass each input](docs/inputs.md)

## Install

A static binary for Linux x86_64 or macOS on Apple silicon, from the
[releases](https://github.com/GMOD/gfa-to-tabix/releases):

```bash
curl -fL https://github.com/GMOD/gfa-to-tabix/releases/latest/download/gfa-to-tabix-x86_64-unknown-linux-musl.tar.gz | tar xz
```

or from crates.io with Rust 1.91 or later:

```bash
cargo install gfa-to-tabix
```

## Usage

For a JBrowse graph track, run [`build`](#everything-a-graph-track-needs) instead:
it takes the same inputs and writes the index and everything else the track reads.

```bash
# an rGFA: minigraph, or the minigraph stage of Minigraph-Cactus
gfa-to-tabix hprc-v2.1-mc-grch38.sv.gfa.gz -o hprc

# a plain GFA with paths: pggb, odgi, vg, base-level Minigraph-Cactus
gfa-to-tabix ecoli.gfa.gz --reference K12 -o ecoli
```

Each command writes the nodes and links, indexed:

```
hprc.segs.bed.gz    hprc.segs.bed.gz.tbi
hprc.links.bed.gz   hprc.links.bed.gz.tbi
```

| Option                 | Effect                                                                                  |
| ---------------------- | --------------------------------------------------------------------------------------- |
| `--reference <name>`   | For a plain GFA: the PanSN sample, assembly or path to use as reference. Default the first path. |
| `-o`, `--out <prefix>` | Output prefix. Default the input name without `.gfa[.gz]`.                              |
| `--layout <layout>`    | `anchored` (default) or `contig`; see [layouts](docs/index-format.md#layouts).          |

The input may be gzipped, and `-` reads stdin.

## Everything a graph track needs

```bash
gfa-to-tabix build hprc-v2.1-mc-grch38.sv.gfa.gz -o hprc --assembly hg38
gfa-to-tabix build ecoli.gfa.gz --reference K12 -o ecoli
```

`build` takes an rGFA or a plain GFA, and reads the graph once and writes the index, a zoomed-out tier, the
alleles, the bubbles, a manifest and a JBrowse track config.

## Haplotype paths

```bash
gfa-to-tabix chr22.gfa --walks --refs GRCh38,CHM13 -o chr22
```

`--walks` indexes the path of every haplotype in a base-level graph by position
on one or more reference genomes:

- **Out:** one Tabix-indexed BED file per sample in `--refs`, here
  `chr22.GRCh38.walks.bed.gz` and `chr22.CHM13.walks.bed.gz`
- Both files list the same paths, including those of GRCh38 and CHM13. Rows in
  the GRCh38 file have GRCh38 coordinates, and rows in the CHM13 file have
  CHM13 coordinates
- A browser showing GRCh38 queries the GRCh38 file, and a region query returns
  the rows a reader needs to rebuild each haplotype's path through that region

![Four haplotype paths through a bubble, the walk rows for their chunk, and the paths a reader rebuilds from them](docs/figures/walks.svg)

## Docs

- [Inputs](docs/inputs.md): rGFA, plain GFA, base-level graphs for walks
- [Subcommands](docs/subcommands.md): `build`, `alleles`, `bubbles`, `fold`, `paths`
- [Walks](docs/walks.md) and [the walks row format](docs/walks-format.md)
- [The node and link index](docs/index-format.md): coordinates, layouts, columns, scale
- [JBrowse configuration](docs/jbrowse.md)

## See also

- [jbrowse-plugin-graphgenomeviewer](https://github.com/GMOD/jbrowse-plugin-graphgenomeviewer): the JBrowse 2 plugin that browses these graphs by locus
- [BandageJS](https://github.com/GMOD/BandageJS): Bandage-style GFA viewer in the browser
- [sequenceTubeMap](https://github.com/cmdcolin/sequenceTubeMap): sequence tube map view of a GFA

Alternative data formats

- [@gmod/gbz-base](https://github.com/GMOD/gbz-base-js): range-request reader for `.gbz.db` databases
- [gbz-haplotype-index](https://github.com/GMOD/gbz-haplotype-index): lists every walk in a gbz-base cut
- [gfa-to-pairwise-paf](https://github.com/cmdcolin/gfa-to-pairwise-paf-rs): graph to PAF, for synteny views

Tutorials

- [JBrowse pangenome tutorials](https://jbrowse.org/jb2/docs/tutorials/pangenome_prepare_graph/)

## License

Apache-2.0
