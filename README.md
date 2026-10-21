# gfa-to-tabix

gfa-to-tabix indexes a pangenome graph by genome coordinate, so a browser can fetch the subgraph for any region.

- **In:** a GFA file (`.gfa` or `.gfa.gz`): an rGFA from minigraph or Minigraph-Cactus (`*.sv.gfa.gz`), or a plain GFA with P or W lines from pggb, odgi or `vg convert -f`
- **Out:** `<prefix>.segs.bed.gz` and `<prefix>.links.bed.gz`, one line per node and per link, each with a `.tbi` ([why two files](docs/adr/0002-two-index-files.md))
- **Out, with `--walks --refs GRCh38`:** `<prefix>.GRCh38.walks.bed.gz` and its `.tbi`, every haplotype's path through a base-level graph, which [@jbrowse/graph-walks](https://github.com/GMOD/graph-walks) reads
- A browser fetches the rows for a region with HTTP range requests and never downloads the whole graph
- The [JBrowse 2](https://jbrowse.org) graph track reads the node and link files. The tool is one static binary and needs no bgzip or tabix; `build` runs gfatools, when installed, for an rGFA's bubbles

![The two Tabix queries a browser runs to view chr1:13-18, the node and link lines each returns, and the graph it draws from them, with each node and edge coloured by the file it came from](docs/figures/overview.svg)

## Quick start

```bash
curl -fL https://github.com/GMOD/gfa-to-tabix/releases/latest/download/gfa-to-tabix-x86_64-unknown-linux-musl.tar.gz | tar xz

# rGFA from minigraph or Minigraph-Cactus (*.sv.gfa.gz): coordinates come from its SN/SO/SR tags
./gfa-to-tabix build hprc-v2.1-mc-grch38.sv.gfa.gz -o hprc --assembly hg38

# plain GFA from pggb, odgi or vg: coordinates come from the reference's path
./gfa-to-tabix build ecoli.gfa.gz --reference K12 -o ecoli
```

- `build` writes the index and everything else a JBrowse graph track reads, including a track config for the assembly `--assembly` names
- [Load the files in JBrowse](docs/jbrowse.md)
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

## Docs

- [The node and link index](docs/index-format.md): inputs (rGFA, plain GFA, choosing a reference), options, coordinates, layouts, columns, scale
- [Subcommands](docs/subcommands.md): `build`, `alleles`, `bubbles`, `fold`, `paths`
- [Walk files](docs/walks-format.md): options, placement rules, the row format 5 and its readers
- [JBrowse configuration](docs/jbrowse.md)
- Decisions:
  - [ADR 0001](docs/adr/0001-step-placement.md): which chunk a walk file files each step under
  - [ADR 0002](docs/adr/0002-two-index-files.md): why nodes and links are two files
  - [ADR 0003](docs/adr/0003-long-node-lookback.md): how far a walk reader reads back
  - [ADR 0004](docs/adr/0004-abridged-detours.md): moving a chunk's costliest paths to detail rows
- [Comparison with gbz-base and gbz-haplotype-index](docs/gbz-comparison.md)
- `scripts/figures.py target/release/gfa-to-tabix` redraws the figures from the tool's output, and CI fails when a figure differs from that output

## See also

- [jbrowse-plugin-graphgenomeviewer](https://github.com/GMOD/jbrowse-plugin-graphgenomeviewer): the JBrowse 2 plugin that browses these graphs by locus
- [JBrowse pangenome tutorials](https://jbrowse.org/jb2/docs/tutorials/pangenome_prepare_graph/)
- [BandageJS](https://github.com/GMOD/BandageJS) and [sequenceTubeMap](https://github.com/cmdcolin/sequenceTubeMap): graph viewers in the browser
- [gfa-to-pairwise-paf](https://github.com/cmdcolin/gfa-to-pairwise-paf-rs): graph to PAF, for synteny views

## License

Apache-2.0
