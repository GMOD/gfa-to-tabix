# Developing

## Checks

CI runs these on every push:

- `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings` and
  `cargo test --release`
- `scripts/figures.py target/release/gfa-to-tabix --check`: the figures in
  [figures/](figures/) are drawn from the tool's output on the GFAs beside
  them, and the check fails when a figure differs. Run it without `--check`
  to redraw them. It also fails when
  [Walk files in brief](walks-format-in-brief.md) quotes a line that the
  tool does not write for [walks-example.gfa](figures/walks-example.gfa)
- `scripts/check-links.py`: every relative link and anchor in the Markdown
- `scripts/check-claims.py`: every normative sentence of
  [walks-format.md](walks-format.md) has a claim ID with a check in
  [claims7.md](departures/claims7.md)
- `docs/comparison/scripts/tables.py --check`: the measured tables of
  [comparison-details.md](comparison-details.md) match the results in
  [comparison/results](comparison/results). Run it without `--check` to
  rewrite them
- `scripts/check-walks.sh`: builds every walk fixture and runs the release
  checks on each file, after showing that those checks fail on broken files
- `scripts/graph-walks-rebuild.mjs`: @jbrowse/graph-walks cuts each
  reference sequence of every fixture's walk files whole and must give back
  every path, placement and departure the GFA states
- `scripts/parity-fixtures.sh`: the `contig` layout against the JBrowse
  scripts it replaced, byte for byte
- `scripts/parity-fold.sh`: `fold` against the fold bandage-core runs in the
  graph track, byte for byte

`scripts/check-windows.sh <gfa-to-tabix binary> <graph-walks checkout>`
holds graph-walks' cut over windows to `scripts/window-oracle.py`, which
works out what a window must return from the rules of
[Reading a window](walks-format.md#reading-a-window), over tiles decoded
by the spec-only reader `spec8.py`: the fragments, the departures and
their own steps, and the node table a viewer draws from, including which
pass a node the reference passes more than once is placed at. It cuts
every window of each short
sequence, and the tile edges, holes, record ends and random windows of
longer ones, on the fixtures and on random graphs, then shows that each
planted reader mistake makes some file fail. Run
`window-oracle.py --digest` on a hosted file to check its windows the same
way. It isn't in CI, because a run takes over an hour. graph-walks 7.0.0
and 8.0.0 failed it on windows inside a `#hole`, which 8.0.1, the version CI
pins, reads as the rules say (see C135 in
[claims7.md](departures/claims7.md)).

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
