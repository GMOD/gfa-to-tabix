**Verdict:** per-group units are a new format touching every invariant family listed, and my measurements put the gain well below the draft's "4/50 of the walk rows".

Measured on 39 tiles (every 20th of 776) of the files under `runs/scale/{pre,alt}`, splitting walk/abridged rows into 50 groups by sample and compressing with zlib level 6:

| file | whole tile | shared rows (ref, nodes, route) | walk rows together | walk rows as 50 groups |
|---|---|---|---|---|
| 5000-off | 10.03 MB | 4.35 MB | 5.68 MB | 7.23 MB (+27%) |
| 5000 default | 2.47 MB | 0.15 MB | 2.32 MB | 3.60 MB (+55%) |
| 464-off | 5.07 MB | 4.35 MB | 0.71 MB | 1.32 MB |

**Where the draft is wrong or overstated**
- **Gain with abridging off:** a 4-haplotype view at 5000 reads about 4.93 MB against 10.03 MB, so 2x, not 12x. Routes are 28.5 MB of the raw text and stay shared.
- **Gain at 464-off (my split of a 464-haplotype file):** about 12%, because shared rows are 86% of the tile.
- **Gain with default budgets:** tiles shrink about 5.6x, but the per-tile `blocks` unit stays whole. The draft's own 100 kb numbers (271 kB tiles, 301 kB blocks) then give roughly 572 → 350 kB, unless blocks are split per group too, which the sketch omits.
- **"About half of every tile's walks move":** in the sample, 20% of rows are abridged at 2000 (283 of 1,394 per tile) and 66% at 5000 (2,282 of 3,479).
- **File size:** untouched. Detail units remain 1,750 of 1,885 MB at 5000, and the 14.0 MB table stays.

**Spec invariants (`walks-format.md`)**
- **Format number:** a format 8 reader skips unknown unit kinds (C123/C196), so `walks` units under `format:i:8` would draw the reference alone, silently. It must be format 9.
- **Rows per unit:** the units table and C155, C59, C125 and C72 ("every piece of a line has one row in its tile") all need rewriting.
- **C27 and counting:** "the tiles a window's read selects hold a row of every line" becomes tile plus all its group units. Counting calls read all of them and pay the +27–55%.
- **Names (C39):** a `walks` unit needs a `cs:g` name. Path-to-group needs a header rule or tag, including for the other references' lines and paths with fewer than three fields.
- **Empty groups (C210):** a group with no row in a tile must be absent.
- **Order (C32/C33):** group units need a stated place among tiles and departure bins.
- **Blocks (C161):** "one blocks unit named by the tile's start" breaks if blocks are split per group.
- **Budgets (C100):** "the tile's rows other than abridged rows" must be redefined across units.
- **Departures and attach (C84/C97/C132):** `ownTiles` can stay, but "reads those tiles and no other" becomes tile plus the record's group unit.
- **Detail records:** `cs:d` and one record per W line survive unchanged.
- **Table:** 38,800 more entries. At the 8–12 B per entry the current tables show, that is about 0.3–0.5 MB against 22 kB with abridging off. A chr1 table (about 3,800 tiles) would be about 1.5–2.3 MB at open.
- **Requests (C134):** a 100 kb window is 3 tiles and a 1 Mb window 17 (`scale-windows.tsv`), so k=4 means up to 15 and 85 ranges where one merged range serves today.

**Reader (`graph-walks/src`, 9.0.0)**
- `walkFile.ts:226` refuses any format but 8; `ROW_KINDS` at `walkFile.ts:60` fixes the rows per unit kind.
- `walkReader.ts` filters `kind === 'tile'` at lines 268, 284, 535, 585, 607, 1137 and 1672, covering window selection, `attachTiles`, `bytesFor`, the step tallies and counts.
- `bytesFor`'s documented promise, "a cut that keeps fewer walks reads no more", becomes keep-dependent.
- `links: 'between'` survives, since it reads ref and route rows (line 205).
- The fixtures in `graph-walks/test_data` need rebuilding.

**Writer (`gfa-to-tabix-scale/src`, 5.0.1)**
- The code change is small: `Output::tile` (`walks.rs:1820`) writes one unit per tile, and the abridge selection sits in `routes.rs:710–832`.
- The checks are the real cost: `verify7.py`, `claims7.py`, `spec8.py` and `walks-truth.py` (4,348 lines), `tests/walks.rs` (3,662 lines), `claims7.md` and `graph-walks-rebuild.mjs`.

**Hosted files and other readers**
- The `-f8` names keep their bytes (Hosting), so format 9 means new names, a rebuild and re-upload of both HPRC files, and a second cutover.
- The viewer plugin, BandageJS, ggbandage, ggtubemap and the tube map all need a graph-walks release.
- ADR 0011's trigger, upheld by ADR 0016, is a real problem on a hosted file. The evidence here is synthetic 2,000 and 5,000 haplotype files; the hosted files are HPRC v2.1's.

Not checked: 464 with default budgets, real compression under BGZF, and `warm.query.tsv`, which is absent.
