# Handoff, 2026-11-02: a haplotype as a walk file's reference

Goal: let a researcher browse a pangenome from any chosen assembly's
coordinates, HG002#1 for example, instead of only GRCh38. Two reviewers read
the code in gfa-to-tabix, graph-walks and the graphgenomeviewer plugin, and
the line references below were rechecked. Nothing here has been built or run
yet: every behaviour stated is traced from code.

## What this is, and what it is not

- **The mechanism is one walk file per reference.** `--refs A,B` already
  writes `<prefix>.A.walks.bed.gz` and `<prefix>.B.walks.bed.gz`. Each file
  holds every haplotype's walks again, indexed along that reference's
  coordinates. The plugin opens each file as its own track on its own
  assembly
- **The work makes a haplotype usable as A.** `--refs` can name only a
  sample today, which is wrong for a diploid sample
- **It swaps the reference; it does not remove it.** A browser needs a
  one-dimensional key to fetch a window, so navigation stays tied to some
  reference. Reference-free *analysis* inside a window is separate work, see
  [Related work](#related-work)
- **Cost is linear in references.** One HPRC v2.1 file is about 1.2-1.6 GB
  (`hprc-v2.1-mc-grch38-f5s.CHM13.walks.bed.gz` is 1.46 GB) and about 2.5 h
  and 13 GB RSS to build (jbrowse-components `demos/hprc/README.txt`). That
  suits a handful of chosen haplotypes, but all 464 would be about
  570-760 GB. For E. coli or the maize NAM founders it is cheap
- **The alternative is a per-assembly index.** One GRCh38 walk file plus a
  small index per assembly, mapping that assembly's positions to the GRCh38
  chunk its walk is filed under. Its size is unmeasured; measure it before
  choosing it over copies, and only if every haplotype as a frame is wanted

## Why `--refs HG002` is wrong today

- `--refs` is compared with the sample column only (`src/walks.rs:589`,
  `:903`, `:1030`), so both HG002 haplotypes become the reference
- **HG002#2 can never be a lane.** It gets no walk rows and no `#haplotype`
  line (`walks.rs:903-920`)
- **Other walks break.** Nodes the two haplotypes share are marked revisited
  (`walks.rs:755`), and `visit_near` keeps a walk on the last sequence it
  used. So GRCh38#0 hops between `HG002#1#chr22` and `HG002#2#chr22`, and the
  reader only follows a walk along one sequence (graph-walks
  `walkReader.ts:455`)
- **The plugin shows the wrong haplotype.** Open track reads the file name
  `x.HG002.walks.bed.gz` as `HG002`. Both haplotypes then write the same
  `HG002\tchr22` lookup key and the later wins, so an HG002.1 assembly
  silently shows hap 2's coordinates

## The change

### gfa-to-tabix (about half a day with tests)

- One matcher, `r == path.sample || r == haplotype(&path.name)`
  (`haplotype` is at `walks.rs:873`), used at `:589`, `:903` and `:1030`. It
  serves `HG002` and `HG002#1` alike
- The no-match error (`walks.rs:643`, and the one near `:564`) lists
  haplotypes as well as samples
- File name: `#` becomes `.` (`walks.rs:1495`), so `HG002#1` writes
  `<prefix>.HG002.1.walks.bed.gz`, matching ADR 0007's `SM:Z:HG002.1`. The
  `#reference` header (`:1499`) and the `#haplotype` list need no change
- **Refuse overlapping refs** such as `--refs HG002,HG002#1` or
  `GRCh38,GRCh38#0`. Chunk ownership goes to the first ref (`walks.rs:1413`),
  so the first file gets the reference rows twice and the second gets only a
  header. `main.rs` removes exact duplicates only
- **Refuse a bare sample with more than one haplotype.** It ends today's
  silent wrong output, and the error names the haplotypes to pick from
- Needs no change: chunking and `path_ends` (`walks.rs:686-690`) are keyed by
  path name; placement, nearest pass, `stay`, abridging, `#long` and
  `maxnode` work from the matched walks. A ref that is a haplotype in another
  ref's file (`--refs GRCh38,HG002#1`) is fine
- Docs to update: `docs/walks-format.md` (lines 5-7, 143 and 385),
  `src/cli.rs:83-90` help text, and the "Walk files: references and
  abridging" section of `docs/open-problems.md`

### Plugin (jbrowse-plugin-graphgenomeviewer, about a day)

- **File name to sample.** `walkFileSample` (`src/locationName.ts:10`) takes
  the text after the last dot, so `HG002.1` reads as sample `1`. It is used
  by `withWalkReference` (`src/graphTrackDefaults/index.ts`) and the
  add-track form (`src/GraphAddTrackWorkflow/buildTrackConfig.ts`). An
  all-digit last field should mean `<previous field>#<digits>`. The header
  can't serve here: `withWalkReference` is a synchronous config hook. Expect
  the mapping `{ "HG002.1": "HG002#1" }`
  - Map to `HG002#1`, not `HG002`: the lanes adapter drops every lane whose
    sample equals the anchor's prefix (`WalkTabixSyntenyAdapter.ts:83-86`),
    so mapping to `HG002` would hide HG002#2
- **Holes in the reference.** Minigraph-Cactus clips haplotypes, so
  HG002#1's chr22 is several W lines with gaps between them. GRCh38 and
  CHM13 are unclipped, so no shipped walk file has had this
  - A window inside a gap gets no rows. The cut returns empty tables, then
    bandage-core's `loadGraph` throws "No graph segments in …"
    (`pipeline.ts:66`). It needs a "no reference here" state; lanes come back
    empty with no notice
  - Over a piece's end, each piece ends with a `break` stop carrying the gap
    in bp (graph-walks `walkRows.ts:737-754`), and node positions are right
  - **Probable bug:** when two reference pieces share a window, `walkRowsGraph`
    (`src/GraphGenomeView/walkRowsCut.ts:20-50`) keeps only walk 0 as the
    reference and turns the second piece into a stepless stub path of the
    same name. Its effect on screen is unverified
- **Genes need no change.** The backbone takes the region's assembly's gene
  track (`graphViews.ts:735-757`); the GRCh38#0 row takes hg38's through its
  `GRCh38` alias

## Test fixture first

A new `tests/data/walks-diploid-ref.gfa`, 10 bp nodes, `--chunk 10`:

```
W HG002  1 chr  0  20 >1>2
W HG002  1 chr  40 60 >5>6
W HG002  2 chr  0  60 >1>7>3>4>5>6
W GRCh38 0 chr1 0  60 >1>7>3>4>5>6
```

- **gfa-to-tabix** (`tests/walks.rs`, after the `walks-records` tests near
  `:916-947`), run with `--refs HG002#1`:
  - only `out.HG002.1.walks.bed.gz` is written, and tabix lists only
    `HG002#1#chr`
  - the header has `#reference HG002#1`, `#haplotype GRCh38#0` and
    `#haplotype HG002#2`
  - the ref row in chunk 10 has `ng:i:20 nr:i:40`, and chunk 40 has `pg:i:20`
  - which rows chunks 20 and 30 hold is the open question below
  - `--refs HG002,HG002#1` is refused; `--refs HG002` alone is refused and
    names the haplotypes; `--refs HG002#3` errors listing haplotypes
  - `--refs R#0,Q#0` on `walks-two-refs.gfa` gives the same rows as `R,Q`
- **graph-walks** (copy the `records` helper and `cutRegion` tests in
  `walkReader.test.ts:170-300`):
  - `sequenceFor('HG002#1','chr')` is `HG002#1#chr`
  - a cut over 22-38 has no nodes and doesn't throw
  - a cut over 10-45 has two `HG002#1#chr` pieces with a 20 bp `break`
    between, nodes 5 and 6 at 40 and 50, and GRCh38 as one piece
- **plugin** (`WalkTabixSyntenyAdapter.test.ts` `makeAdapter`, with
  `assemblyNames: ['HG002.1']` and `{ "HG002.1": "HG002#1" }`):
  - lane labels are `GRCh38#0` and `HG002#2`, and `getRefNames()` is `['chr']`
  - lane features cover only 0-20 and 40-60; the 22-38 window returns `[]`
  - `withWalkReference` on the real file name gives `{ "HG002.1": "HG002#1" }`
  - a subgraph over 10-45 has no duplicate reference stub path, and a 22-38
    window shows the "no reference here" message
- The plugin's `walks5_*` fixtures are committed builds with no script.
  Gzip and tabix the new one the same way, and commit the command

## Open question: skip rows inside a hole

- One reviewer traced `write_skips` (`walks.rs` near `:1100` and `:1111`) as
  writing a skip row for other paths in every chunk of a reference hole.
  Readers draw a skip as no step on the reference (ADR 0006), but in a hole
  the reference simply has no sequence. The other reviewer found no rows in a
  hole chunk. The fixture settles it
- **Don't design format 5 semantics for it.** ADR 0009 (walk format 6,
  accepted 2026-10-31, not implemented) replaces skip rows with departure
  records. Those were designed for gaps in a haplotype's path, not holes in
  the reference itself. Format 6 has to say what a hole in the reference
  is, distinct from a haplotype leaving it

## Order with format 6

[The departures handoff](2026-10-31-departures.md) ports a spike writer into
the same `src/walks.rs`. This change touches about five lines there and is
independent of it, so land it first, then add one line to that handoff: format
6 must state reference holes.

## After the fixture passes

- **Prove the plugin path with no code first:**
  - E. coli: `gfa-to-tabix <pggb.gfa> --walks --refs K12,Sakai,CFT073,NCTC86,IAI39`.
    The strains are haploid, so sample matching is already right and each
    strain's file opens on its own assembly with its own genes. Where the full
    pggb GFA lives is unverified
  - CHM13: point an hs1 track at the hosted
    `hprc-v2.1-mc-grch38-f5s.CHM13.walks.bed.gz`, which no config names yet
- **Then HG002#1 on real data:**
  - No chr22-only GFA exists. The hosted files came from `vg convert` of the
    whole GBZ (17 min, 90 GB) and a 2.5 h build. Whether
    `hprc-v2.1-mc-grch38.W.gfa.gz` is still on ada (disk 90% full) is
    unverified, and whether `vg chunk` could cut chr22 cheaper is untried
  - The data side is in jb2hubs `website/pangenome-config/hprc-grch38.json`:
    HG002.1 (alias `HG002#1`), chrom sizes with bare `chr1`..`chr22`, and
    `HG002.1_liftoff_genes`. So the file's sequence is `HG002#1#chr22`; this
    is not checked against the GBZ
  - Done means, in the hosted app: an HG002.1 track drawing HG002#1's own
    coordinates and genes, lanes for GRCh38#0 and HG002#2, and a hole window
    stating that no reference sequence is there

## Related work

These are not part of this change; they are the reference-free half of the
same goal.

- **Structural forms that open in the graph, naming carriers.** graph-walks
  computes each form's `members` (`structuralForms.ts:83`), but the plugin's
  `formSources` (`src/WalkFormsAdapter/formRows.ts:88-111`) keeps only a
  count. About 2-3 days in the plugin; GSTM1 is the figure
- **A list of differences between two chosen haplotypes, neither being the
  reference.** Build `walkDepartures`' position lookup (graph-walks
  `walkDepartures.ts` near `:80`) from walk A instead of rank-0 tags. About
  2-4 days
- **Population split.** `RgfaTabixAdapter` has no `samplesTsvLocation`
  (plugin `agent-docs/todo/rgfa-samples-tsv-slot.md`)
- **"Draw x along"** probably does nothing on walk-file cuts, which are
  tag-anchored. Fixing it first needs plugin
  `agent-docs/todo/reference-path-undo.md` and guards on host x placement,
  the reference strip and `clipToWindow`; hide the picker until then
