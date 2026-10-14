# Subcommands

Each subcommand writes one more file a graph track reads. `build` runs all of
them from one read of the graph.

## build

`gfa-to-tabix build` writes everything a JBrowse graph track reads, from one
read of the graph:

```bash
gfa-to-tabix build hprc-v2.1-mc-grch38.sv.gfa.gz -o hprc --assembly hg38
gfa-to-tabix build ecoli.gfa.gz --reference K12 --snarls ecoli.snarls.vcf -o ecoli
```

| File                               | Holds                                              |
| ---------------------------------- | -------------------------------------------------- |
| `hprc.segs/links.bed.gz`           | the fine index, anchored layout                    |
| `hprc.contig.segs/links.bed.gz`    | the contig layout                                  |
| `hprc.fold10000.segs/links.bed.gz` | the coarse tier ([fold](#fold))                    |
| `hprc.alleles.bed.gz`              | the allele inventory ([alleles](#alleles))         |
| `hprc.bubbles.bed.gz`              | the bubbles ([bubbles](#bubbles))                  |
| `hprc.graph.json`                  | the manifest                                       |
| `hprc.config.json`                 | the tracks, ready to merge into a JBrowse config   |

Each `.bed.gz` gets a `.tbi`.

- `--tier N` folds under N bp: default 10000 for an rGFA, 50 for a plain GFA
- `--assembly` sets the JBrowse assembly the tracks sit on. Default the
  graph's reference sample, else `reference`; the config maps it onto the
  sample with `assemblyNameToPanSN`
- An S line with no `SN` tag among the first 100,000, `--reference` or
  `--snarls` makes it a plain GFA
- An rGFA's bubbles need `gfatools` on PATH, which reads the text alongside the
  parse. Without it the build says so and writes no bubble file
- A plain GFA's bubbles come from `--snarls`, a `vg deconstruct -a` snarl VCF;
  without one there is no bubble file
- The config's coarse slot is `{ "uri": "hprc.fold10000", "foldBelowBp": 10000 }`
- `zstd -dc graph.gfa.zst | gfa-to-tabix build - -o graph` reads other
  compression
- It replaced JBrowse's retired `build_pangenome_graph.sh`. It parses the graph
  once, where the script read it four times, and writes the index, tier,
  alleles and bubbles concurrently: 0.77 s against the script's 2.46 s on a
  59 MB chr22 SV rGFA

The manifest, `<prefix>.graph.json`, lists each file relative to itself, or
`null` for one not written, so it works wherever the set is hosted:

```json
{
  "schema": 1,
  "reference": "GRCh38",
  "index": "hprc",
  "contig": "hprc.contig",
  "tier": { "prefix": "hprc.fold10000", "foldBelowBp": 10000 },
  "bubbles": "hprc.bubbles.bed.gz",
  "alleles": "hprc.alleles.bed.gz"
}
```

- `reference`: the PanSN sample of the first reference segment (`GRCh38` from
  `GRCh38#0#chr1`), `null` when the backbone names have no sample
- `index`, `contig`, `tier.prefix`: prefixes of `.segs.bed.gz` and
  `.links.bed.gz` pairs

## alleles

`gfa-to-tabix alleles <prefix>` reads `<prefix>.segs.bed.gz` and
`<prefix>.links.bed.gz`, indexed with `--layout contig`, and writes
`<prefix>.alleles.bed.gz` with its index: one row per allele the graph holds,
anchored on the reference, with a CIGAR that states its size. The graph itself
is not needed, so a hosted pair works.

```bash
gfa-to-tabix hprc.sv.gfa.gz --layout contig -o hprc
gfa-to-tabix alleles hprc
```

- A link from a backbone node forward to a later one is a deletion; a link back to an earlier one is not
- A link from a backbone node to an off-backbone one enters an allele; the walk
  follows links until it arrives back on the backbone
- A walk that never rejoins the backbone is dropped, and the count goes to
  stderr
- Columns: `#chrom start end name score strand thickStart thickEnd itemRgb class
  delta altLen refLen CIGAR discoveryRank firstSeenIn nested segments`

## bubbles

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
- `build` reads a step on a segment it turned forward
  ([plain GFA](index-format.md#where-the-coordinates-come-from)) the other way
  round, so a segment the reference reads reversed is no inversion. `bubbles`
  alone has no graph to say which segments turned, and takes every `<` as
  reverse

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
- `--layout` should match the fine index's, so a tier window returns what a fine
  window does. `--reference` takes a plain GFA's backbone path, as for the index
- The graph track folds each cut it draws the same way, at ten of the linear
  view's pixels, so a tier folded at N and handed over at N / 10 bp per pixel
  draws close to what the fine cut drew just below the handover. The two differ
  where the way back from a big allele to the backbone runs through part of a
  small allele in one fold and not the other. In the track's config,
  `coarse: { uri: "hprc.fold10000", aboveBpPerPx: 1000 }` is that handover
- The fold is [bandage-core](https://github.com/GMOD/bandage-core)'s
  `foldVariants`, ported. `scripts/parity-fold.sh` compares the rows with
  `bandage-fold | gfa-to-tabix -` byte for byte, at five sizes and both
  layouts, and CI runs it
- On HPRC release 2.1's SV rGFA the fold takes 12 s and 640 MB. `bandage-fold`
  cannot read that graph: Node refuses the 3.5 GB of text as one string

## paths

`gfa-to-tabix paths -o <prefix> <ref.call.bed> [<sample.call.bed> ...]` writes
`<prefix>.bed.gz` with its index: one row per bubble and sample, so a
multi-row feature display partitioned on `strain` draws a lane per haplotype,
each block that haplotype's allele at that bubble. The inputs are the files
`minigraph --call` writes, one per sample and the reference's first:

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
