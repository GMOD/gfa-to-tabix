# Departure records: measurements behind ADR 0009

The writer spike that produced these files lives in a scratch copy of the
repository (`write_departures`, `--fold`, `--chain`, `--alignments` in
`src/walks.rs`); its code is ported into the tool under ADR 0009. The
graphs are HPRC v2.1 Minigraph-Cactus chr22 and HPRC release 2 pggb chrY
and chr22, all on GRCh38; the builds ran on ada.

## Scripts

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
