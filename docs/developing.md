# Developing

## Checks

CI runs these on every push:

- `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings` and
  `cargo test --release`
- `scripts/figures.py target/release/gfa-to-tabix --check`: the figures in
  [figures/](figures/) are drawn from the tool's output on the GFAs beside
  them, and the check fails when a figure differs. Run it without `--check`
  to redraw them
- `scripts/check-links.py`: every relative link and anchor in the Markdown
- `scripts/check-claims.py`: every normative sentence of
  [walks-format.md](walks-format.md) has a claim ID with a check in
  [claims7.md](departures/claims7.md)
- `docs/comparison/scripts/tables.py --check`: the measured tables of
  [comparison.md](comparison.md) match the results in
  [comparison/results](comparison/results). Run it without `--check` to
  rewrite them
- `scripts/check-walks.sh`: builds every walk fixture and runs the release
  checks on each file, after showing that those checks fail on broken files
- `scripts/parity-fixtures.sh`: the `contig` layout against the JBrowse
  scripts it replaced, byte for byte
- `scripts/parity-fold.sh`: `fold` against the fold bandage-core runs in the
  graph track, byte for byte

## Design decisions

- [ADR 0001](adr/0001-step-placement.md): where a walk file files a
  haplotype step
- [ADR 0002](adr/0002-two-index-files.md): nodes and links in two files
  (format 1)
- [ADR 0003](adr/0003-long-node-lookback.md): how far a walk reader reads
  back
- [ADR 0004](adr/0004-abridged-detours.md): moving a tile's costliest pieces
  into detail units
- [ADR 0005](adr/0005-giant-components.md): a giant component keeps its own
  coordinates (`--max-component`)
- [ADR 0006](adr/0006-walks-skip-rows.md): marking a haplotype that jumps
  over a window
- [ADR 0007](adr/0007-node-link-format-2.md): node and link format 2, one file
  with each node's assemblies as bits
- [ADR 0008](adr/0008-index-keeps-its-placement.md): the index keeps its
  placement, and walk files take placement work
- [ADR 0009](adr/0009-departure-records.md): one record per departure, and
  walk rows that name the copy (walk format 6)
- [ADR 0010](adr/0010-walks-unit-table.md): gzip units with a unit table, not
  a Tabix file (walk format 7)
- [ADR 0011](adr/0011-format-7-is-frozen.md): walk format 7 is frozen
- [ADR 0012](adr/0012-abridged-blocks.md): walk format 8, an abridged piece's
  shape in a `blocks` row
- [ADR 0013](adr/0013-abridged-hapbp.md): the `abridged` row states the
  piece's bp on its contig
- [ADR 0014](adr/0014-p-line-names.md): a P line's name is read from its
  right end
- [ADR 0015](adr/0015-walk-files-name-their-graph.md): a walk file names its
  graph and the lines it leaves out
- [ADR 0016](adr/0016-format-8-is-frozen.md): walk format 8 is frozen

## Records

- [Open problems](open-problems.md): measured but not decided, such as
  pggb's collapsed repeats
- [Issues log](issues-log.md): every bug and review finding on the walks
  stack, and what now guards it
