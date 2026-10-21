# Inputs

`gfa-to-tabix` reads a GFA file, plain or gzipped; it recognizes gzip by the file's first two bytes, whatever the name. The tool takes coordinates from rGFA tags or from a reference path, depending on which lines the file has; see [how the tool tells them apart](#how-the-tool-tells-them-apart).

## rGFA

An rGFA has `SN`, `SO` and `SR` tags on every S line, so each node already names its sequence, offset and rank.

- Written by: minigraph (`-cxggs`), and the minigraph stage of Minigraph-Cactus (`*.sv.gfa.gz`)
- Command: `gfa-to-tabix graph.gfa.gz -o prefix`
- Bubbles need `gfatools` on PATH; see [build](subcommands.md#build)

## Plain GFA with paths

A plain GFA has no coordinate tags. The tool takes coordinates from the paths of one reference.

- Written by: pggb (`*.smooth.final.gfa`), `odgi view -i graph.og -g`, `vg convert -f graph.gbz`, and base-level Minigraph-Cactus (`*.gfa.gz`, or the GBZ through `vg convert -f`)
- Paths are P lines or W lines, named `sample#haplotype#contig` (PanSN) where possible
- Nodes must abut, with overlaps `*` or `0M`; the tool sums node lengths along each path
- Command: `gfa-to-tabix graph.gfa.gz --reference K12 -o prefix`
- `--reference` takes a PanSN sample, an assembly or a path name; without it the first path is the reference
- Bubbles come from a `vg deconstruct -a` VCF; see [bubbles](subcommands.md#bubbles)

## Large base-level graphs

A base-level graph of a human chromosome has millions of nodes, and the node and link index's memory grows with total path length. `--walks` files every haplotype's path by reference chunk; see [walks](walks.md). It needs integer node ids and W or P lines, as `vg convert -f` writes.

## How the tool tells them apart

- Every S line has an `SN` tag, and no `--reference`: rGFA
- Some S lines have `SN` tags and the graph has no P or W lines: rGFA, which leaves out the untagged segments
- Anything else: plain GFA

## Errors

The tool stops before writing anything on these:

- `--reference NOPE matches no path; have: K12#0#chr`: the name matches no path. The message lists the paths the graph has
- `link 1->2 has a non-blunt overlap (5M)`: the graph's nodes overlap. The message says to blunt the graph first, or use an rGFA
- `no P or W lines, and the S lines carry no rGFA tags`: the file has neither coordinate source
