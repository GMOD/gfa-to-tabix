# Draft for review: per-group units in walk files (a format change, proposal only)

Context: MC chr22 (HPRC v2.1) walk files written by gfa-to-tabix 5.0.1, GRCh38 reference,
at 464 real haplotypes and at 2,000 and 5,000 haplotypes made by recombining the real
W lines (mosaics switching at shared reference nodes every few Mb; the 464 real
haplotypes included). Data, all under ~/work/handoff-1121/gfa-to-tabix-scale/docs/placement/:

- scale-files.tsv: per file (464, 2000, 5000; default budgets) size, .idx size, the
  header unit's and the sequence table's compressed bytes, and units by kind with
  compressed-byte quantiles
- scale-windows.tsv: per file, 40 window positions (one per 1.245 Mb of chr22) x
  10 kb / 100 kb / 1 Mb windows centred in a tile, widened by the browser's 1 kb
  context: compressed bytes of tiles, blocks units and departure bins over them,
  tiles gunzipped, and graph-walks' bytesFor (all haplotypes)
- scale-alt-files.tsv, scale-alt-windows.tsv: the same for files written with
  abridging off (--abridge-steps 0 --abridge-bytes 0) at 464/2000/5000, and with
  4x the default budgets at 5000 (5000-s4m)
- scale-distinct.tsv: walk rows and distinct walk rows per tile (synthetic copies
  repeat real rows, real haplotypes almost never do)
- the spec: ~/work/handoff-1121/gfa-to-tabix-scale/docs/walks-format.md (frozen,
  format 8), ADR 0004 (abridging), ADR 0010 (unit table), ADR 0012 (blocks)
- ~/work/handoff-1121/runs/scale/warm.query.tsv (if present): bytes graph-walks
  9.0.0 actually read per cut for 4 haplotypes (haps4), 4 expanded (haps4x), all

What the numbers say (read them yourself; this is my reading):

- With default budgets the file grows 59 MB -> 464 MB -> 1,885 MB (464/2000/5000).
  Nearly all of it is detail units: from 2,000 haplotypes on, ordinary tiles pass the
  1M-step abridge budget by haplotype count alone, so about half of every tile's
  walks move to per-W-line detail units (220k units at 2000, 1.73M at 5000), which
  compress poorly alone. The sequence table, which a reader fetches whole before its
  first cut, grows 46 kB -> 1.9 MB -> 14.0 MB
- With abridging off the files are 32 MB / 72 MB / 142 MB and the table about 22 kB
- Per window, the tiles over a 100 kb window (median of 30 positions) are about
  80 kB / 211 kB / 271 kB compressed (default) or 80 / 243 / 560 kB (off); a cut of
  every haplotype also reads the blocks units, 0 / 37 / 301 kB. A 4-haplotype view
  reads the same tiles, plus blocks units where a kept walk is abridged and not
  expanded. A 1 Mb window's tiles are about 0.46 / 1.15 / 1.5 MB (default) and
  0.46 / 1.4 / 3.2 MB (off)

The proposal (for the owner, not a decision): split each tile's walk rows into units
by haplotype group, so that a reader keeping a few haplotypes fetches the tile's
shared rows (ref, nodes, route) and only its groups' walk/abridged rows.

- Sketch: a tile becomes a `tile` unit with ref, nodes and route rows, followed by
  one `walks` unit per haplotype group (groups fixed file-wide, e.g. by sample in
  header order, G groups); the table lists each; a reader keeping k haplotypes
  reads the tile unit and at most k group units per tile
- Gain (estimate): at 5,000 haplotypes with G = 50, a 4-haplotype view of a 100 kb
  window would read the shared rows plus 4/50 of the walk rows instead of all of
  them
- Costs: G times the tile units (776 x 50 = 39k entries at the default tile), so a
  bigger table fetched whole; worse compression of small units; up to k+1 reads
  per tile instead of one; every reader changes; a new format number (format 8 is
  frozen, ADR 0016); the writer's abridging interacts (detail units are already
  per W line)
- Alternatives: no change; writer policy only (abridge budgets that scale with
  the number of haplotypes or abridge only outlier walks, which the format
  already leaves to the writer); a paged or two-level table so a reader does not
  fetch every detail unit's entry; detail units grouped per tile and haplotype
  group instead of per W line; a smaller tile
