# Departure records: measurements behind ADR 0009

Three rounds of measurement, on HPRC v2.1 Minigraph-Cactus chr22 and HPRC
release 2 pggb chrY and chr22, all on GRCh38, built on ada:

- **The minimal record, 2026-11-04,** in
  [results/minimal/](results/minimal/README.md): the writer at 76c9223,
  with the record cut to eight fields and one copy mechanism on walk
  rows, built on MC chr22 and pggb chrY, audited and sized against the
  port and format 5
- **The port, 2026-11-04,** in [results/port/](results/port/README.md): the
  writer in `src/`, compared row for row with the rebuild's prototype and
  sized and timed against format 5 built from the same commit's parent
- **The rebuild, 2026-11-03,** in [results/rebuild/](results/rebuild/README.md):
  a prototype of the format ADR 0009 specifies, read back by `audit6.py`.
  Its numbers supersede the spike's wherever both measure the same thing
- **The spike, 2026-10-30,** in `results/`: an earlier writer with a
  narrower record, before positions, copies and bin-sized blocks (`--fold`,
  `--chain`, `--alignments` in a scratch copy of `src/walks.rs`)

## Scripts

- `audit7.py walks.gz [--truth dep.tsv] [--shard I/N] [--seq NAME]`:
  `audit6.py`'s checks on a walk format 7 file, read by unit. It adds a
  check of each walk and abridged row's `start end` against its decoded
  steps, of each record's `ownTiles` against the tiles its decoded own
  steps lie in, and of unique tile and detail names. It also checks that a departure inside a piece lies within its
  tile's extent, and costs windows as format 7 reads them, from the unit
  tables. Needs the file's `.idx` beside it
- `verify7.py walks.gz [tile]`: the release checks of a walk format 7 file
  and its directory, those of arbiter A's
  [`verify7.mjs`](../walks-container/arbA/scripts/verify7.mjs) and more
  (each table exactly its sequence's units, unique tile and detail names,
  each departure record in every block of its cover). It reads the file a
  gzip member at a time, so it checks files past the 2 GiB that
  `verify7.mjs`, which reads whole files, can't
- `fuzz7.sh` with `fuzz6-gen.py`: random graphs built in walk format 7 in
  six option modes; each file gets `verify7.py` and `audit7.py`
- `audit6.py walks.bed.gz [--truth dep.tsv] [--shard I/N] [--seq NAME]`:
  reads a format 6 file, from gfa-to-tabix 3.x, as a reader would and
  checks it, as the rebuild's README describes. `--shard` splits the paths so a large graph fits in
  memory, and `--seq` audits one reference sequence of a genome-wide file,
  counting a path's bp on the other sequences as unseen
- `fuzz6.sh` with `fuzz6-gen.py`: random graphs built and audited in six
  option modes. A graph's reference may have holes between its lines, and a
  haplotype's lines may abut
- `summary6.py out/`: one table row per build log and audit

- `audit.py walks.bed.gz [--truth dep.tsv] [--baseline f5.bed.gz]`:
  departures by kind, rows per departure, every (contig, chunk) a contig
  spans without a piece and whether a departure block covers it, rows a
  64 kb window returns against the rows truly over it, and a cross-check
  against `dep.rs`
- `dep.rs`: an independent enumeration of every place a path does not
  follow the reference, straight from the GFA (informed-2's review)
- `tbiq.py file.bed.gz seq length window`: requests and bytes a window
  costs on a sequence and its `~departure` sibling, from the Tabix index
- `primary.py lift.tsv`: chains each contig's lifted alignment blocks
  (`scripts/walks-truth.py lift`) into one non-overlapping co-linear
  projection
- `artefact.py walks.bed.gz lift.tsv seq`: each departure record's ends
  against the alignment's position of the contig bases beside them
- `agree.py mc.walks.bed.gz pggb.walks.bed.gz seq`: a pggb file's
  placement against the Minigraph-Cactus walk file of the same assemblies,
  an independent projection, per piece and per departure end

## Results

- `mc22.audit.txt`, `pggbY.audit.txt`, `pggb22.audit.txt`: `audit.py` on
  the spike's files under nearest-pass placement
- `blocks-and-index.txt`: per-window index cost, 64 kb against 16 kb
  blocks, the leave piece's chunk against the breakpoint's, and how often
  the alignment blocks overlap
- `chrY.placement-vs-mc.txt`: nearest-pass and alignment-guided placement
  of pggb chrY against MC chrY
- `chrY.placement-vs-alignment.txt`: the same files against the primary
  projection of the alignments, with ADR 0001's scores
- `chain.txt`: the chaining placement's builds
