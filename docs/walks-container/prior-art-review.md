# S7: prior-art and failure-mode review (2026-11-05)

An independent review for ADR 0010, written by a Fable agent from the
gfa-to-tabix-dd session. It read arbA/decision.md, arbA/scripts/s7.mjs,
arbB/decision.md, docs/walks-format.md, graph-walks' walkReader.ts, the
harness's S7 reader (measure.mjs) and the real S7 file on ada (its 45-byte
directory, header, tile/route/walk/departure rows and `#unit` table). It did
not re-measure bytes. Line references are to those files as of 18:15-18:18.

## Verdict in one line

Adopt S7, with the changes listed at the end. It is a known structure (a CRAM-style slice table over a segment-tree cover), not a hack; its gaps are in binding, self-delimiting and a few edge rules, none in the idea.

## Prior art

- **CRAM / `.crai` — S7 is this.** A `.crai` is gzipped text `refSeqId start span containerOffset sliceOffset size`, one line per self-contained slice; S7's `#unit seq start end kind name offset length` (`s7.mjs:125,138,142`) is the same table with `kind name` in place of the slice offset. CRAM does two things S7 does not: every container begins with its own header (ref, start, span, size), so the file is self-delimiting and `samtools index` can rebuild the `.crai`; and the file starts with a magic, version and file id. S7's units have no in-stream marker, so the table cannot be rebuilt from the data, and tile rows carry no tile id (format 6's `cs` column did that job, `walks-format.md:206`).
- **PMTiles.** Root directory → leaf directories → tiles is exactly `.idx` → per-sequence unit table → units (`measure.mjs:315-325`). PMTiles' lessons S7 lacks: the directory sits in the file at a fixed place (first 16 KB; one request bootstraps), and readers validate the ETag so a rebuilt file under the same URL cannot mix with cached ranges. Its run-length entries do not apply (no identical units); its clustering S7 already has (units in position order, `s7.mjs:102-104`).
- **bigBed/bigWig.** Stores each item once under an R-tree over blocks; one 4.6 Mb departure (the real record at `GRCh38#0#chr22 10510000 15154322` in the S7 file) in a leaf would make that leaf hot for every window under it — the Ou measurement, 3.5× on pggb (`decision.md:236-239`). Zoom levels are summaries, not records; a viewer needs records, so they are not an alternative to the pyramid (they could later ride on its upper levels as summaries). Worth copying: the index inside the file, and a magic/version at byte 0.
- **BGZF + `.gzi` + `.fai`.** S7 is strictly better for extraction: units start on block boundaries, so `tail -c | head -c | gzip -dc` needs no `.gzi`. The cautionary lesson is faidx's classic failure: a stale sidecar gives garbage without an error. S7 has the same hole (see failure modes).
- **Zarr sharding / COG.** A sequence is a shard: its `(offset, length)` index sits at the end of its run (`s7.mjs:141-144`), as a Zarr shard footer does. COG's IFD tile tables assume a regular grid; S7's tiles have true, irregular extents, which is why a table rather than arithmetic is right — and why any reader that keeps `floor(base / chunk)` (today's `walkReader.ts:579`) is wrong on S7, as arbB's 8-of-65 attach failures showed (arbB `decision.md:664-674`).
- **Tabix/CSI.** Format 6's departure cut (`walks-format.md:379-388`, `departures.rs:57-69`) is already S7's cover rule expressed through bins; S7 removes the bin machinery, the fake keys and the `~` siblings (`walkReader.ts:112-114`), and keeps the rule. arbB's T64b reaches S7's bytes only by faking three coordinates and relying on a non-folding CSI that `tabix` itself won't regenerate (arbB `decision.md:609-621`).

## Is the pyramid principled?

- Yes: it is the segment tree's canonical cover (de Berg ch. 10). A record is stored at the largest aligned blocks inside its tile-rounded extent (`sfinal.mjs:70-78`), not "every block it overlaps" — the brief's phrasing would be unbounded (70 copies of a 4.6 Mb record at level 0) and the ADR must state the cover precisely.
- Its property is the one nobody else gives in one round trip: every line fetched from a level above 0 covers the window's whole block, and every level-0 line overlaps the window's tile. Bytes per window are bounded by records touching the window's 64 kb tile, times the copy count (≤ 7 per level per side with base 8). Tabix (store once at the smallest containing bin) over-reads neighbours; an R-tree over-reads under long items; NCList and interval trees are output-sensitive but cost dependent fetches down the nesting. Duplication is paid on disk (1.5% MC, 8% pggb, `decision.md:486-496`) — the right side to pay.
- Dedup is inherent, not a patch: a point query sees each record once; a range query spanning leaves sees it from several nodes. Exact-line dedup is sound because the line is the record with its true extent (the S7 departure lines are identical in every block), unlike T64b where the block's interval leads and the real extent trails.
- The reader needs no knowledge of levels or base: "fetch every unit overlapping D" (`measure.mjs:329`). The ADR should say so: the pyramid is a writer filing choice, changeable without a reader release, as `walks-format.md:387-388` already promises for the cut.

## Failure modes

- **Sidecar desync.** `.idx` has no version and no binding to the data (`s7.mjs:147`, 45 bytes: `#header 0 1386`, `GRCh38#0#chr22 68667552 47546`). A stale `.idx` beside a rebuilt file, or a crashed rewrite under a stale `.idx`, is detected only by luck: misaligned ranges usually fail gzip's member header/CRC, but not reliably.
- **Versioning.** The reader parses the directory before it sees `format:i:7` (`measure.mjs:315-319`); a format-8 directory would fail with a parse error, not the refusal `walkReader.ts:237-243` gives today.
- **CDN.** Never issue multi-range requests (CloudFront answers with the whole object). Small ranges are fine; CloudFront fetches origin in 1 MB parts, so a window's up-to-four scattered levels are four cold parts, latency only. A rebuild under the same name is a mixed-cache hazard for any range-read format: version the file name.
- **Zero-length units.** `BgzfWriter.flush` writes nothing for an empty run (`bgzf.mjs:30`), so an empty unit or sequence section would yield `length 0` and a `Range: bytes=n-(n-1)` request, which is a 416. A sequence with no units vanishes from the directory entirely.
- **Names.** GFA allows a name starting with `#` (it is a legal first character in the GFA1 name regex), which would read as a header line; tabs/newlines likewise. Inherited from format 6 and Tabix, but S7 should refuse them at build. `~` and `:` are now ordinary characters.
- **Offsets.** Decimal text; no 4 GB limit; exact below 2^53, which the spec should state.
- **Crash / concurrency.** Immutable file: no reader issue. The writer should write data then `.idx` under temp names and rename, so an index never points at a partial file.
- **Table order.** Sections are in file order, which is not start order (details follow tiles, `s7.mjs:127-139`); say so, and that readers scan, not bisect.
- **Row extents cost.** Per-row true spans on `route` rows (`s7.mjs:66-71`) are already on disk: `s7.walks.gz` 68.7 MB against 59.2 MB for `s7t` (route/nodes rows take the tile's extent) and 57.8 MB for S on MC; 191.7 / 187.9 / 184.5 MB on pggb. A route's span is not a query key and gzip cannot absorb thousands of distinct spans per tile.

## Self-description

- With only `zcat` and `awk`, `awk '$1==S && $2<E && $3>B'` finds every row over a window, which no earlier format allowed. What it cannot do is decode: a walk row names routes by index within its tile, and nothing on the row or in the stream says where a tile begins. The `#unit` tables are at the end of each sequence's run, so a stream reader needs two passes.
- The sentence a newcomer needs: "Every data line starts `seq start end` with the true extent of what it describes; lines are grouped into units (a tile's rows, a departure block, a detail record), each a whole run of BGZF blocks listed with its byte range in a `#unit` table; a window reads every tile and departure unit whose range overlaps it, decodes each tile alone, and drops duplicate lines."

## Changes, smallest first

- **Bind and version the directory:** its first line echoes the data file's `#walks` line plus `bytes:i:<file length>`; the reader checks both against the header and the first response's `Content-Range` total, before any unit read. Closes faidx's failure and gives a clean refusal of a newer format.
- **Zero-length and empty-sequence rules:** list every reference sequence in the directory; allow `length 0` entries and never fetch them.
- **Dictionary rows take the tile's extent** (the `s7t` rule): `route` and `nodes` rows say "I belong to the tile covering [a, b)", which is true and cheap; walk, ref, abridged and departure rows keep their own spans.
- **State the index invariant and the cover rule** in the spec: `start end` is the unit's cover range; every line overlapping a window lies in a unit whose range overlaps it; the cover is the largest aligned blocks inside the record's tile-rounded extent.
- **An in-stream unit header** `#unit seq start end kind name` at each unit's start (offsets only in the trailing table). This makes the file self-delimiting like a CRAM container, lets `awk` decode one tile in a single pass, and makes the `.idx` rebuildable by a `gfa-to-tabix index` walk over BGZF block starts — the `.fai` property. One short line per unit.
- **Structural release checks:** header, units, tables and the EOF block partition the file; each unit range begins with a gzip member header; each tile's lines lie within its range; each departure line's cover includes the block it sits in.
- **Build-time name hygiene:** refuse sequence or path names containing tab or newline or starting with `#`.
- **Hosting rule in the ADR:** versioned file names, single-range requests only.

## Why not another design

- T64b closes the byte gap only by keeping three fictions (rows claiming the chunk's span while overhanging by `reach`, detail at `d × chunk`, block intervals leading departure rows), `#long`, `reach`, a patched client and an index `tabix` won't reproduce. Under the user's own criterion — principled, Tabix expendable — S7's one rule and true coordinate on every line win, and `awk` on true extents is a better debugging tool than `tabix` returning opaque rows ever was.
