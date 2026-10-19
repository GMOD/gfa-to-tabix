# gfa-to-tabix

gfa-to-tabix indexes a pangenome graph by genome coordinate, so a browser can fetch the subgraph for any region.

- **In:** a GFA from minigraph, Minigraph-Cactus, pggb, odgi or vg
- **Out:** Tabix-indexed BED files, each row filed under a reference interval:
  - the graph's nodes and links, one row each
  - or, with `--walks` on a base-level graph, every haplotype's path through it
- **Why:** a browser fetches only the rows for a region, with HTTP range requests, and never downloads the whole graph
- The [JBrowse 2](https://jbrowse.org) graph track reads the files. One static binary does the conversion, with no bgzip or tabix; `build` uses gfatools, when installed, for an rGFA's bubbles

![A five-node graph, its node rows queried at chr1:25-30, and the nodes and links a browser draws from the rows returned](docs/figures/overview.svg)

The tool files each bubble's alleles and their links under the reference span the bubble hangs from, so a query anywhere inside that span returns every allele of the bubble.

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

- **In:** a base-level graph with W or P lines, such as `vg convert -f` writes from a GBZ
- **Out:** one file per reference, here `chr22.GRCh38.walks.bed.gz` and `chr22.CHM13.walks.bed.gz`
- A region query returns the rows a reader needs to rebuild every haplotype's path through that region

![Four haplotype paths through a bubble, the rows the GRCh38 file has for one 64 kb stretch of chr1, and the paths a reader rebuilds from those rows](docs/figures/walks.svg)

## Docs

- [Inputs](docs/inputs.md): rGFA, plain GFA, base-level graphs, and choosing a reference
- [The node and link index](docs/index-format.md): options, coordinates, layouts, columns, scale
- [Subcommands](docs/subcommands.md): `build`, `alleles`, `bubbles`, `fold`, `paths`
- [Walks](docs/walks.md) and [the walks row format](docs/walks-format.md)
- [JBrowse configuration](docs/jbrowse.md)
- [Comparison with gbz-base and gbz-haplotype-index](docs/gbz-comparison.md)
- `scripts/figures.py target/release/gfa-to-tabix` redraws the figures from the tool's output, and CI fails when they go stale

## See also

- [jbrowse-plugin-graphgenomeviewer](https://github.com/GMOD/jbrowse-plugin-graphgenomeviewer): the JBrowse 2 plugin that browses these graphs by locus
- [JBrowse pangenome tutorials](https://jbrowse.org/jb2/docs/tutorials/pangenome_prepare_graph/)
- [BandageJS](https://github.com/GMOD/BandageJS) and [sequenceTubeMap](https://github.com/cmdcolin/sequenceTubeMap): graph viewers in the browser
- [gfa-to-pairwise-paf](https://github.com/cmdcolin/gfa-to-pairwise-paf-rs): graph to PAF, for synteny views

## License

Apache-2.0
