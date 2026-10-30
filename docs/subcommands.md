# Subcommands

What each subcommand writes:

| Subcommand              | Writes                                                           |
| ----------------------- | ---------------------------------------------------------------- |
| [build](#build)         | the index, contig layout, coarse tier, alleles, bubbles, manifest and JBrowse config, from one read of the graph |
| [alleles](#alleles)     | one row per allele, anchored on the reference                    |
| [bubbles](#bubbles)     | a plain GFA's bubbles, from a snarl VCF                          |
| [fold](#fold)           | the coarse tier: the graph with small variants folded            |
| [paths](#paths)         | one row per bubble and sample, from `minigraph --call`           |

## build

`gfa-to-tabix build` writes everything a JBrowse graph track reads:

```bash
gfa-to-tabix build hprc-v2.1-mc-grch38.sv.gfa.gz -o hprc --assembly hg38
gfa-to-tabix build ecoli.gfa.gz --reference K12 --snarls ecoli.snarls.vcf -o ecoli
```

| File                               | Holds                                              |
| ---------------------------------- | -------------------------------------------------- |
| `hprc.graph.bed.gz`                | the fine index, anchored layout                    |
| `hprc.contig.graph.bed.gz`         | the contig layout, which `alleles` reads           |
| `hprc.fold10000.graph.bed.gz`      | the coarse tier ([fold](#fold))                    |
| `hprc.alleles.bed.gz`              | the allele inventory ([alleles](#alleles))         |
| `hprc.bubbles.bed.gz`              | the bubbles ([bubbles](#bubbles))                  |
| `hprc.graph.json`                  | the [manifest](#the-manifest)                      |
| `hprc.config.json`                 | the tracks ([JBrowse config](#the-jbrowse-config)) |

`--format 1` writes each of the three indexes as a `.segs.bed.gz` and
`.links.bed.gz` pair instead. Each `.bed.gz` gets a `.tbi`, or a `.csi` when a
row lies past the 512 Mb a Tabix index holds. The config then sets
`"csi": true` on each track whose files have one.

- `--tier N` folds under N bp: default 10000 for an rGFA, 50 for a plain GFA
- `--max-component N` applies to the fine index and the coarse tier, as for
  the index; default 10000
- `--assembly` sets the JBrowse assembly the tracks sit on. Default the
  graph's reference sample, else `reference`; the config maps it onto the
  sample with `assemblyNameToPanSN`
- `build` tells an rGFA from a plain GFA as
  [the index does](index-format.md#how-the-tool-tells-them-apart), and
  `--snarls` makes it a plain GFA
- An rGFA's bubbles need `gfatools` on PATH; `build` runs it on the text
  alongside its own parse. Without it, `build` writes no bubble file and says so
- A plain GFA's bubbles come from `--snarls`, a `vg deconstruct -a` snarl VCF;
  without one there is no bubble file
- `zstd -dc graph.gfa.zst | gfa-to-tabix build - -o graph` reads other
  compression
- `build` replaced JBrowse's retired `build_pangenome_graph.sh`, which read the
  graph four times. `build` parses it once and writes the files concurrently,
  about three times faster on a chr22 SV rGFA

### The manifest

The manifest, `<prefix>.graph.json`, lists each file relative to itself, or
`null` for one not written, so it works wherever the set is hosted:

```json
{
  "schema": 1,
  "reference": "GRCh38",
  "format": 2,
  "index": "hprc",
  "contig": "hprc.contig",
  "tier": { "prefix": "hprc.fold10000", "foldBelowBp": 10000, "format": 2 },
  "bubbles": "hprc.bubbles.bed.gz",
  "alleles": "hprc.alleles.bed.gz"
}
```

- `reference`: the PanSN sample of the first reference segment (`GRCh38` from
  `GRCh38#0#chr1`), `null` when the backbone names have no sample
- `index`, `contig`, `tier.prefix`: prefixes of `.graph.bed.gz` files, or of
  `.segs.bed.gz` and `.links.bed.gz` pairs where the format is 1
- `format` gives the format of `index` and `contig`, `tier.format` that of
  the tier

### The JBrowse config

`<prefix>.config.json` is ready to merge into a JBrowse config. It loads the
[graph genome viewer plugin](https://github.com/GMOD/jbrowse-plugin-graphgenomeviewer)
and holds a graph track, an alleles track and, with a bubble file, two bubble
tracks. A graph track written by hand names the file and its index:

```json
{
  "type": "GraphTrack",
  "trackId": "hprc_graph",
  "name": "HPRC graph",
  "assemblyNames": ["hg38"],
  "adapter": {
    "type": "RgfaTabixAdapter",
    "graphLocation": { "uri": "https://example.org/hprc.graph.bed.gz" },
    "graphIndex": {
      "location": { "uri": "https://example.org/hprc.graph.bed.gz.tbi" }
    },
    "assemblyNameToPanSN": { "hg38": "GRCh38" }
  }
}
```

- `assemblyNameToPanSN` maps the JBrowse assembly name to the sample name the
  graph uses, when the two differ
- When the four files sit side by side under the names the tool gave them, the
  prefix alone is enough, as in the config `build` writes:

  ```json
  "adapter": {
    "type": "RgfaTabixAdapter",
    "uri": "https://example.org/hprc",
    "assemblyNameToPanSN": { "hg38": "GRCh38" },
    "coarse": {
      "uri": "https://example.org/hprc.fold10000",
      "foldBelowBp": 10000
    }
  }
  ```

- `coarse` names the coarse tier ([fold](#fold))
- Walk files take `walksUri`; see [readers](walks-format.md#readers)

## alleles

- **In:** `<prefix>.graph.bed.gz`, or a format 1 pair, indexed with
  `--layout contig`. The command needs no graph, so a hosted index works
- **Out:** `<prefix>.alleles.bed.gz` and its index, one row per allele the graph
  holds, anchored on the reference, with a CIGAR that states its size

```bash
gfa-to-tabix hprc.sv.gfa.gz --layout contig -o hprc
gfa-to-tabix alleles hprc
```

- A link from a backbone node forward to a later one is a deletion. A link back
  to an earlier one is a duplication, which the inventory leaves out
- A link between a backbone node and an off-backbone one enters an allele,
  whichever node the L line names first; the walk follows links until it
  arrives back on the backbone sequence it left
- The walk in from an allele's other end retraces it, so the allele gets one
  row
- A walk that never rejoins the backbone is dropped, and the count goes to
  stderr
- Columns: `#chrom start end name score strand thickStart thickEnd itemRgb class
  delta altLen refLen CIGAR discoveryRank firstSeenIn nested segments`

## bubbles

`gfa-to-tabix bubbles --snarls <vcf> -o <prefix>` writes
`<prefix>.bubbles.bed.gz` and its index from a `vg deconstruct` snarl VCF
(`pggb -V` writes one too). `gfatools bubble` finds no bubbles in a plain GFA,
so this command gives a plain GFA the file `gfatools` gives an rGFA.

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
- `build` knows which segments it turned forward
  ([plain GFA](index-format.md#plain-gfa-with-paths)), so a segment
  the reference reads reversed is no inversion. `bubbles` alone has no graph to
  say which turned, and takes every `<` as reverse

## fold

`gfa-to-tabix fold <graph> --below <bp> -o <prefix>` writes the index of the
graph with every variant under `bp` folded into the reference: the coarse tier a
graph track draws once zoomed out past the fine index, so a whole chromosome
fits.

```bash
gfa-to-tabix fold hprc.sv.gfa.gz --below 10000 -o hprc.fold10000
```

- It keeps the backbone, every allele whose own length or the reference it
  replaces reaches `bp`, and the shortest way from each one's ends back to the
  backbone. The reference between kept alleles becomes one segment
- `--layout` and `--max-component` should match the fine index's, so a tier
  window returns what a fine window does. `--reference` takes a plain GFA's
  backbone path, as for the index
- The graph track folds each cut it draws the same way, at ten of the linear
  view's pixels. A tier folded at N and handed over at N / 10 bp per pixel
  draws close to what the fine cut drew just below the handover:
  `coarse: { uri: "hprc.fold10000", aboveBpPerPx: 1000 }` in the track's config
- The two differ where the way back from a big allele to the backbone runs
  through part of a small allele in one fold and not the other
- The fold is [bandage-core](https://github.com/GMOD/bandage-core)'s
  `foldVariants`, ported. `scripts/parity-fold.sh` compares the rows with
  `bandage-fold | gfa-to-tabix -` byte for byte, at five sizes and both
  layouts, and CI runs it
- The fold takes seconds on HPRC release 2.1's whole-genome SV rGFA, which
  `bandage-fold` cannot read: Node refuses that much text as one string

## paths

`gfa-to-tabix paths -o <prefix> <ref.call.bed> [<sample.call.bed> ...]`

- **In:** the files `minigraph --call` writes, one per sample, the reference's first
- **Out:** `<prefix>.bed.gz` and its index, one row per bubble and sample. A
  multi-row feature display partitioned on `strain` draws a lane per haplotype,
  each block that haplotype's allele at that bubble

```bash
for fa in ref.fa s1.fa s2.fa; do
  minigraph -cxasm --call -t8 graph.rgfa.gz $fa > $(basename $fa .fa).call.bed
done
gfa-to-tabix paths -o graph.paths ref.call.bed s1.call.bed s2.call.bed
```

- A file's name without `.call.bed` is its sample. The reference's sample name
  gives the PanSN prefix (`ref#1#`) that the rows drop from their contigs
- minigraph writes one line per bubble, in the same order for every sample; the
  command refuses files of different lengths
- A bare `.` in a call line is no alignment over the bubble (`nocall`), not a
  deletion of its span

Columns, after the BED's first nine (`itemRgb` is the class colour, so the
track draws with no colour config):

| column | holds |
| ------ | ----- |
| `name` | the length change for the block label (`+113,174`, `-3,217`, `ref`, `no call`) |
| `strand` | the orientation the contig aligned in; `-` over a run of bubbles is an inversion |
| `strain` | the sample, the row |
| `class` | `ref`, `ins`, `del`, `sub` or `nocall` |
| `delta` | `pathLen - refLen` |
| `pathLen` | bp of the sample's path through the bubble (-1 for no call) |
| `refLen` | the reference span the bubble covers, 0 at a pure-insertion site |
| `alleles` | distinct paths observed at the bubble across the samples; `gfatools bubble`'s own count saturates |
| `nonRef` | samples that leave the reference path at the bubble |
| `path` | the segment ids traversed (`>s2650>s1949`), `<` for reverse, the same ids the graph view draws |

- `alleles` and `nonRef` repeat down a bubble's rows, so one filter on either
  cuts the track to the sites worth looking at
- At a pure-insertion bubble, `*` is the reference allele, and `delta`
  classifies it
- The command holds every row in memory, so hundreds of samples over a whole
  genome's bubbles need the memory for all of them
