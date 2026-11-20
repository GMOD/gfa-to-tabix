# gfa-to-tabix

gfa-to-tabix indexes a pangenome graph by genome coordinate, so a browser can
fetch any region of it from a static web host without downloading the whole
graph.

- **In:** a GFA file (`.gfa` or `.gfa.gz`): an rGFA from minigraph or
  Minigraph-Cactus (`*.sv.gfa.gz`), or a plain GFA with P or W lines from pggb,
  odgi or `vg convert -f`
- **Out:** a node and link index, `<prefix>.graph.bed.gz`, that a graph track
  reads at any locus
- **Out, with `--walks`:** walk files, `<prefix>.GRCh38.walks.gz`, holding every
  haplotype's path through the graph
- The tool is one static binary and needs no bgzip or tabix

## Quick start

```bash
curl -fL https://github.com/GMOD/gfa-to-tabix/releases/latest/download/gfa-to-tabix-x86_64-unknown-linux-musl.tar.gz \
  | tar xz --strip-components=1 gfa-to-tabix-x86_64-unknown-linux-musl/gfa-to-tabix

# rGFA: coordinates come from its SN/SO/SR tags
./gfa-to-tabix build hprc-v2.1-mc-grch38.sv.gfa.gz -o hprc --assembly hg38

# plain GFA: coordinates come from the reference's path
./gfa-to-tabix build ecoli.gfa.gz --reference K12 -o ecoli
```

- `build` writes the index and everything else a JBrowse graph track reads,
  including a [track config](docs/subcommands.md#the-jbrowse-config)
- [Releases](https://github.com/GMOD/gfa-to-tabix/releases) also has a macOS
  binary for Apple silicon, and `cargo install gfa-to-tabix` builds one with
  Rust 1.91 or later

## Haplotype paths

```bash
vg convert -f chr22.gbz > chr22.gfa
./gfa-to-tabix chr22.gfa --walks --refs GRCh38 -o chr22
```

`--walks` reads a base-level GFA with integer node ids and W or P lines, as
`vg convert -f` writes from a GBZ. The command writes `chr22.GRCh38.walks.gz` in
walk format 8, cut into tiles along GRCh38, and its directory
`chr22.GRCh38.walks.gz.idx`. A viewer fetches the tiles over a region by range
request, and [@jbrowse/graph-walks](https://github.com/GMOD/graph-walks)
rebuilds every haplotype's path through the region from them.

![A 90 bp chr1 graph with GRCh38#0, HG002#1 and CHM13#0 as lines through its nodes, CHM13#0 dipping to a node of its own between 30 and 60; under it hprc.GRCh38.walks.gz as a bar of header, tile 0-30, tile 30-60, tile 60-90 and table, each tile under its stretch of chr1; tile 30-60 is shaded with the graph above it, and an arrow runs from table to the tile's bytes 278-417](docs/figures/walks-tile.svg)

## Gallery

Drawn from gfa-to-tabix's files of the HPRC v2.1 graph by the
[JBrowse graph plugin](https://github.com/GMOD/jbrowse-plugin-graphgenomeviewer)
and [ggbandage](https://github.com/GMOD/ggbandage).

<table>
<tr>
<td width="33%"><a href="https://github.com/GMOD/jbrowse-plugin-graphgenomeviewer/blob/main/docs/haplotypes.md#walk-rows"><img src="https://raw.githubusercontent.com/GMOD/jbrowse-plugin-graphgenomeviewer/main/img/walk_rows_kiv2.png" width="100%" alt="A JBrowse view of LPA's KIV-2 repeat with one bar per haplotype, its length in kb and in repeat units"></a><br>LPA's KIV-2 repeat length, a row per haplotype</td>
<td width="33%"><a href="https://github.com/GMOD/ggbandage/blob/main/docs/gallery.md#amylase-haplotypes-from-146-to-475-kb"><img src="https://raw.githubusercontent.com/GMOD/ggbandage/main/gallery/amylase_rows.png" width="100%" alt="Walk rows over the amylase genes for GRCh38 and seven haplotypes, from 146 kb to 475 kb long"></a><br>Amylase haplotypes from 146 to 475 kb</td>
<td width="33%"><a href="https://github.com/GMOD/jbrowse-plugin-graphgenomeviewer/blob/main/docs/tube-maps.md#routes-and-tube-colour"><img src="https://raw.githubusercontent.com/GMOD/jbrowse-plugin-graphgenomeviewer/main/img/tube_map_c4_routes_by_population.png" width="100%" alt="A tube map of C4 in JBrowse, one tube per route, coloured by superpopulation"></a><br>C4 routes by superpopulation</td>
</tr>
<tr>
<td width="33%"><a href="https://github.com/GMOD/ggbandage/blob/main/docs/gallery.md#cyp2d6-deletion-as-a-dashed-edge-past-the-gene"><img src="https://raw.githubusercontent.com/GMOD/ggbandage/main/gallery/cyp2d6_deletion.png" width="100%" alt="The CYP2D6 graph drawn force-directed, with a dashed link crossing from before CYP2D6 to after it"></a><br>CYP2D6 and the link that skips it</td>
<td width="33%"><a href="https://github.com/GMOD/ggbandage/blob/main/docs/gallery.md#core-shell-and-cloud-at-gstm1"><img src="https://raw.githubusercontent.com/GMOD/ggbandage/main/gallery/gstm1_core.png" width="100%" alt="The GSTM1 graph, each node coloured by the share of HPRC haplotypes through it"></a><br>GSTM1's nodes by share of haplotypes</td>
<td width="33%"><a href="https://github.com/GMOD/jbrowse-plugin-graphgenomeviewer/blob/main/docs/haplotypes.md#facets"><img src="https://raw.githubusercontent.com/GMOD/jbrowse-plugin-graphgenomeviewer/main/img/force_kiv2_facet.png" width="100%" alt="KIV-2 in a JBrowse graph track, one panel per haplotype showing its own loops"></a><br>KIV-2, a panel per haplotype</td>
</tr>
</table>

## Docs

- [The node and link index](docs/index-format.md): inputs, reference choice,
  layouts, giant components, columns and scale
- [Walk files in brief](docs/walks-format-in-brief.md): the walk format in a
  few pages, with one tile decoded
- [Walk files](docs/walks-format.md): the specification of walk format 8, its
  options, rows and readers
- [Subcommands](docs/subcommands.md): `build` and its JBrowse config, `bubbles`,
  `fold` and `paths`
- [Comparison with gbz-base and gfaidx](docs/comparison.md): how the three
  formats differ and which to pick

## See also

- [jbrowse-plugin-graphgenomeviewer](https://github.com/GMOD/jbrowse-plugin-graphgenomeviewer):
  draws these graphs as a JBrowse 2 track
- [BandageJS](https://github.com/GMOD/BandageJS): draws a region of a walk file
  in a web browser
- [ggbandage](https://github.com/GMOD/ggbandage) (R): Bandage-style figures as
  ggplot2 layers
- [JBrowse's guide to hosting your own graph](https://jbrowse.org/jb2/docs/tutorials/pangenome_prepare_graph/)

## License

Apache-2.0
