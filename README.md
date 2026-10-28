# gfa-to-tabix

gfa-to-tabix indexes a pangenome graph by genome coordinate, so a browser can fetch the subgraph for any region.

- **In:** a GFA file (`.gfa` or `.gfa.gz`): an rGFA from minigraph or Minigraph-Cactus (`*.sv.gfa.gz`), or a plain GFA with P or W lines from pggb, odgi or `vg convert -f`
- **Out:** `<prefix>.segs.bed.gz` and `<prefix>.links.bed.gz`, one line per node and per link, each with a `.tbi` ([why two files](docs/adr/0002-two-index-files.md))
- **Out, with `--walks --refs GRCh38`:** `<prefix>.GRCh38.walks.bed.gz` and its `.tbi`, every haplotype's path through a base-level graph, which [@jbrowse/graph-walks](https://github.com/GMOD/graph-walks) reads
- A browser fetches the rows for a region with HTTP range requests and never downloads the whole graph
- The [JBrowse 2](https://jbrowse.org) graph track reads the node and link files
- The tool is one static binary and needs no bgzip or tabix; `build` runs gfatools, when installed, for an rGFA's bubbles

![The two Tabix queries a browser runs to view chr1:13-18, the node and link lines each returns, and the graph it draws from them, with each node and edge coloured by the file it came from](docs/figures/overview.svg)

## Quick start

```bash
curl -fL https://github.com/GMOD/gfa-to-tabix/releases/latest/download/gfa-to-tabix-x86_64-unknown-linux-musl.tar.gz \
  | tar xz --strip-components=1 gfa-to-tabix-x86_64-unknown-linux-musl/gfa-to-tabix

# rGFA from minigraph or Minigraph-Cactus (*.sv.gfa.gz): coordinates come from its SN/SO/SR tags
./gfa-to-tabix build hprc-v2.1-mc-grch38.sv.gfa.gz -o hprc --assembly hg38

# plain GFA from pggb, odgi or vg: coordinates come from the reference's path
./gfa-to-tabix build ecoli.gfa.gz --reference K12 -o ecoli
```

- `build` writes the index and everything else a JBrowse graph track reads, including a [track config](docs/subcommands.md#the-jbrowse-config) for the assembly `--assembly` names
- `./gfa-to-tabix hprc-v2.1-mc-grch38.sv.gfa.gz -o hprc`, without `build`, writes only the index: `hprc.segs.bed.gz` and `hprc.links.bed.gz`, each with a `.tbi`
- [Releases](https://github.com/GMOD/gfa-to-tabix/releases) also has a macOS binary for Apple silicon, and `cargo install gfa-to-tabix` builds one with Rust 1.91 or later

## Haplotype paths

```bash
./gfa-to-tabix chr22.gfa --walks --refs GRCh38,CHM13 -o chr22
```

- `chr22.gfa` is a base-level GFA with integer node ids and W or P lines, as `vg convert -f chr22.gbz > chr22.gfa` writes
- The command writes one file per `--refs` sample, here `chr22.GRCh38.walks.bed.gz` and `chr22.CHM13.walks.bed.gz`, each with a `.tbi`
- A region query returns the rows a reader needs to rebuild every haplotype's path through that region. [@jbrowse/graph-walks](https://github.com/GMOD/graph-walks) rebuilds them, and BandageJS and the JBrowse graph plugin draw through it

![Four haplotype paths through a bubble, the rows the GRCh38 file has for one 64 kb stretch of chr1, and the paths a reader rebuilds from those rows](docs/figures/walks.svg)

## FAQ

### What does gfa-to-tabix add to an rGFA?

- An rGFA, as minigraph writes it, gives every node a place on a genome in
  three tags: `SN` names the sequence, `SO` the offset and `SR` the rank, 0 for
  the reference and higher for a node another assembly contributed
- An rGFA has no index, so a program that shows one region parses the whole
  file first. `gfatools view -R chr1:101-200` cuts a region out of a local
  rGFA that way
- gfa-to-tabix writes the nodes and links as Tabix-indexed BED, so a browser
  fetches one region's rows over HTTP from a static host
- A node of rank 1 or more has `SN` and `SO` on the assembly that contributed
  it, such as `HG002#1#chr1`, so a GRCh38 query by tag coordinates misses it.
  The default layout files such a node under the GRCh38 interval its bubble
  hangs from, and `--layout contig` keeps the tag coordinates
  ([layouts](docs/index-format.md#layouts))

### Can I index a GFA without rGFA tags?

- Yes, when it has P or W lines, as pggb, odgi and `vg convert -f` write
- The tool walks the reference's paths and gives each node the values an
  rGFA's tags would hold: the path name, the offset along it, and rank 0 on the
  reference or 1 elsewhere
- `--reference` names the reference, a PanSN sample such as `GRCh38`, an
  assembly such as `HG002#1` or a path; the default is the first path
- The tool sums node lengths along a path, so it refuses an L or P line with
  an overlap other than `*` or `0M`; blunt the graph first
- [Plain GFA with paths](docs/index-format.md#plain-gfa-with-paths) has the
  rules for collapsed repeats and reversed nodes

### What differs between an rGFA and a plain GFA in the output?

|                           | rGFA                                                          | Plain GFA                                      |
| ------------------------- | ------------------------------------------------------------- | ---------------------------------------------- |
| Written by                | minigraph, Minigraph-Cactus `*.sv.gfa.gz`                     | pggb, odgi, `vg convert -f`                    |
| Node coordinates from     | the `SN`, `SO` and `SR` tags                                  | the reference's P or W lines                   |
| Assemblies with each node | not in the index                                              | an `SM:Z:` column on every row                 |
| `build`'s bubbles         | `gfatools bubble`, when on PATH                               | a `vg deconstruct -a` VCF, given as `--snarls` |
| `build --tier` default    | 10000 bp                                                      | 50 bp                                          |
| Walk files (`--walks`)    | minigraph writes no paths and names nodes `s1`, `s2`, so none | from a base-level graph with integer node ids  |

### Which output do I need?

- The node and link index holds the nodes and links a graph track draws at a
  locus, for any input graph. `build` writes it with the coarse tier, alleles,
  bubbles and a JBrowse config
- The walk files hold each haplotype's path through a base-level graph, which a
  viewer needs to draw haplotypes
- [gbz-comparison.md](docs/gbz-comparison.md) compares the walk files with
  gbz-base, which serves a GBZ from SQLite

### How large a graph does it handle?

- For the node and link index, the tool holds the whole graph in memory:
  HPRC's whole-genome SV rGFA indexes in seconds on a laptop, in about a
  gigabyte
- `--walks` streams the paths from disk, reading the GFA twice; HPRC v2.1's
  Minigraph-Cactus graph took 29 minutes and 13 GB on 24 cores
- A Tabix index holds coordinates up to 512 Mb, so a file with a row past that,
  such as one on wheat's 830 Mb chromosome 3B, gets a `.csi` index instead,
  which holds up to 34 Gb. htslib and JBrowse read both, and JBrowse needs
  `"csi": true` in the track's adapter

## Docs

- [The node and link index](docs/index-format.md): inputs (rGFA, plain GFA, choosing a reference), options, coordinates, layouts, columns, scale
- [Subcommands](docs/subcommands.md): `build` and its JBrowse config, `alleles`, `bubbles`, `fold`, `paths`
- [Walk files](docs/walks-format.md): options, placement rules, the row format 5 and its readers
- Decisions:
  - [ADR 0001](docs/adr/0001-step-placement.md): which chunk a walk file files each step under
  - [ADR 0002](docs/adr/0002-two-index-files.md): why nodes and links are two files
  - [ADR 0003](docs/adr/0003-long-node-lookback.md): how far a walk reader reads back
  - [ADR 0004](docs/adr/0004-abridged-detours.md): moving a chunk's costliest paths to detail rows
  - [ADR 0005](docs/adr/0005-node-link-format-2.md), proposed: node and link format 2, for pggb's collapsed repeats, carrier lists and a header
  - [ADR 0006](docs/adr/0006-walks-skip-rows.md), proposed: walk rows for a haplotype whose deletion spans the window
- [Comparison with gbz-base and gbz-haplotype-index](docs/gbz-comparison.md)
- `scripts/figures.py target/release/gfa-to-tabix` redraws the figures from the tool's output, and CI fails when a figure differs from that output

## See also

- [jbrowse-plugin-graphgenomeviewer](https://github.com/GMOD/jbrowse-plugin-graphgenomeviewer): the JBrowse 2 plugin that browses these graphs by locus
- [JBrowse pangenome tutorials](https://jbrowse.org/jb2/docs/tutorials/pangenome_prepare_graph/)
- [BandageJS](https://github.com/GMOD/BandageJS) and [sequenceTubeMap](https://github.com/cmdcolin/sequenceTubeMap): graph viewers in the browser
- [gfa-to-pairwise-paf](https://github.com/cmdcolin/gfa-to-pairwise-paf-rs): graph to PAF, for synteny views

## License

Apache-2.0
