# Format 8 concept inventory (Fable 5.2, read-only, 2026-11-18)

- Inventoried: `spec-sentences` 2995d1d (~/src/gfa-to-tabix-spec8), diffed against main
- Reader strings: bandage-core main 96edf31, graph-walks main b0d8378
- Nothing was run or edited. (V) = verified in docs or code, (I) = inferred
- I (gfa-to-tabix-18) re-verified two claims myself:
  - C43 states the bin sizes, while ADR 0010:95 says the pyramid is the writer's choice
  - index-format.md:264 says both link-row tags are named `SB:H:` and are read by position

## Verdict

- **Walk file bytes:** no byte-level change beats shipping unchanged. Every mechanism that could be costed is measured, or is free on hosted MC files. The surplus is in vocabulary, in policy written beside the format, in reader strings, and in how the two outputs are presented.
- **Distance from minimal:** the minimal design has 7 concepts; format 8 has about 55 named things.
  - about 20 are packaging
  - about 10 work only when the reference passes a node more than once
  - about 10 are spec vocabulary
  - the rest are the minimal set under more names
- On a `revisited:i:0` file, the active set is close to minimal plus a compression dictionary (V: C24, C70, C142).

### Drop or merge before the freeze

- **Pyramid bin sizes (C43):** they are stated as format, but a reader selects `departures` units by extent, and ADR 0010 calls the pyramid the writer's choice. Demote the sizes to writer policy. Keep only the invariant that every record over D is in a `departures` unit over D. No bytes change; one claim and its checkers do.
- **Vocabulary:** one word for pass / copy / occurrence / revisited, and one for stretch / span / extent / drawn stretch. All eight are on the page; merging them takes about six terms out of the paper.
- **Policy out of the format page:** `stay`, the two abridge budgets, nearest-pass placement and costliest-first sit beside row definitions, though a reader ignores them all.
- **The two abridge budgets as one writer option:** C202 says budgets bind no row, and ADR 0004 has no measurement separating the byte budget from the step budget (V that none is there).
- **Index format 2:** `SB:H:` is not SAM's `H`, and a link row repeats the tag name, read by position (index-format.md:264). The walk format's C199 forbids exactly that. This is the one true format change suggested.
- **`--format 1`:** it is back-compat; drop it from the story.

### Keep, but stop showing users the format's words

These are bandage-core strings (V):
- "placement choice", and its legend line "the writer chose which pass of a node the reference passes more than once a step takes"
- "departure(s)", as in "N departures outside the row"
- "nodes not shown" and "off the reference not loaded" (abridging)
- "own sequence not drawn", "left out of graph", "no step on the reference"

### One event, four encodings

A haplotype leaving the reference is encoded four ways:
- a route inside a tile
- a departure computed inside a piece
- a departure record between pieces
- `d` and runs in a blocks list

That is the measured price of tiling: ADR 0010 found that holding a bubble in one tile saves at most 1.5%. A user should see one mark.

## Step 1: the minimal design, derived before reading the spec

| Concept | What it is | Cost (docs' numbers) |
|---|---|---|
| Reference coordinate | Regions are named on one path chosen at build | One file per reference |
| Tile | A fixed stretch of the reference, the unit a browser fetches, with a byte table | Not tabix; self-contained SAM-style lines cost 3.1–4.5× the bytes (ADR 0010) |
| Piece | A haplotype's steps within one tile: name, offset on its contig, oriented node list with lengths | Plain GFA fragments per tile cost 32× the bytes (ADR 0012), so some dictionary is unavoidable |
| Pass count | How many times the reference passes a node; 1 means the position is a fact | 0 bytes on MC |
| Jump record | A path that leaves before the window and rejoins after it, findable from the window | 1.5% of MC chr22, 7.8% of pggb chrY |
| Summary with detail on request | For a path too long for any window | Without it, tiles of 14.9 / 12.1 MB on hosted files (ADR 0012) |
| Header | Format number, tile size, reference, haplotypes, graph identity | Negligible |

## Step 2: inventory, walk file

Class: G restated GFA, D derived, P writer policy, K packaging. "Users" means the concept is surfaced in reader text.

| Concept | Class | Why it exists | Simplest alternative and its cost | Users | Verdict |
|---|---|---|---|---|---|
| Tile, extent | K | ADR 0010: MC 1 kb window 95 → 29 KB; pggb 1,545 → 70 KB | Tabix: equal bytes only with fake coordinates; real extents 3.3× | No | Keep |
| Extent overhang | D | Replaces `#long`, `maxnode`, chunk-before | A widening rule | No | Keep |
| `piece` | D | Join key, C16 | `(path, fragStart, hapOffset)` is already a key (I) | No | Keep, redundant but not worth a change |
| `path`, `fragStart` | G | ADR 0014 | None | Names | Keep |
| `hapOffset`, `nsteps` | D | Position on the contig, end of decoding | End handle, rejected in ADR 0009 | No | Keep |
| Path-name reading | P, input | ADR 0014 | Refuse suffixed P names | No | Keep; move out of the format page |
| `ref` row / R | G+D | Reference path with lengths | None | No | Keep |
| `nodes` row | G | Off-reference node lengths | Inline lengths, more bytes (I) | No | Keep |
| `route` row, ids, chained deltas | K | Each way off the reference stored once | Self-contained rows, 3.1–4.5× | Hover "…'s route" | Keep |
| Canonical route orientation | K | ADR 0010: −0.10% MC, +0.53% pggb, kept for determinism | First-walk orientation | No | Keep |
| `walk` row, `startHandle`, `choices` | K | The compressed piece | As above | No | Keep |
| Handle `2×id+r`, delta tokens | K | Compression, no separate measurement | `>id`/`<id` as GFA writes them | No | Keep; the least GFA-like spelling in the file |
| `:k` / `@k` | D given placement | ADR 0009: 0 bytes on MC, 0.8–3.4% pggb; without them 3.8–63% of repeat-tile steps decode to the wrong copy | Every revisited node: 5–17% of pggb | No | Keep (pggb) |
| `passes`, `revisited` | D | Fact vs choice; 0.007% of MC chr22 | Tag only where above 1, rejected | "placement choice" | Keep; reword for users |
| Nearest-pass placement | P | ADR 0001: first-visit gave 311 pieces/pair, 1.65 GB pggb chr22 | Place nothing in repeats, rejected in ADR 0011 | "placement choice" | Keep as policy, off the format page |
| `stay` | P | ADR 0001: 45 → 4.3 pieces/pair; bounded rule of ADR 0009 not re-scored | `stay 0`, free on MC | No | Keep as policy; weakest current evidence |
| Departure record | D | ADR 0009: 16 → 8 fields by measurement | Rows in every tile: +32% chrY | "departure", "rejoins" | Keep; hide the word |
| `ownBp`, `hapStart`, `missingBp` | D | What lies between the ends | None | "left out of graph", "own sequence not drawn" | Keep |
| `ownTiles`, attach fetch | D given placement | ADR 0010: MC 29 → 30 KB, pggb 70 → 389 KB | Never attach | "not drawn (last seen near …)" | Keep |
| `departures` units, pyramid | K, P | Coarse-bin problem under tabix | Per-tile filing | No | Keep units; demote sizes |
| `abridged`, `detail` | P+K | ADR 0004: 166 → 1.6 MB, 87 → 3.5 s | None: 14.9 / 12.1 MB tiles | "nodes not shown", "not loaded" | Keep; one user-facing name |
| `blocks` unit, chain grammar | D | ADR 0012: 1.21% / 1.42%; without it 336/463 haps read as absent at chr2:91.4 Mb | List on the `abridged` row +28–30%; PAF `cg` 0.99× but no strand | No | Keep |
| `hapBp`, attach rule | D | ADR 0013: 4.54 MB vs 4 MB limit on 5/1,689 windows | Read the blocks unit | No | Keep |
| Abridge budgets (steps, bytes), cost, costliest-first | P | ADR 0004 | One budget | No | Merge if they never fire apart |
| `#hole` | D | Clipped reference | None | No | Keep |
| `#reference`, `#haplotype` | G | List paths without a tile | None | Pickers | Keep |
| `graph:Z:`, `leftout:i:` | D | ADR 0015 | Stderr | No reader compares | Keep |
| `stay` / `abridge` / `abridgebytes` tags | P | For a person; readers ignore them | Omit (ADR 0017 makes them optional) | No | Keep; off the concept list |
| `#unit`, `#entry`, directory, `bytes:i:` | K | ADR 0010: open 48.6 KB vs tabix 87 | One flat index, 2.15 MB at open | No | Keep; one sentence, like `.fai`/`.crai` |
| Additions rule | K | ADR 0015/0016 | SAM's rule | No | Keep |
| `SQ:Z:` | G | Optional, about 2× file | Omit | No | Keep |
| ADR 0017 grammar (numbers, tabs, ASCII names, ascending R, step at least 1 bp) | K | Checkers passed `0100`, `-0` and empty fields before it | Unstated | No | Keep; the SAM-like part |
| Terms S, R, stretch, span, extent, drawn stretch, own steps, file order | Vocabulary | Shorthand | Fewer words | No | Merge |

## Step 2: inventory, node and link index

| Concept | Class | Why | Alternative and cost | Users | Verdict |
|---|---|---|---|---|---|
| N/L rows in one tabix BED | G+K | ADR 0007: 2 → 1 range reads, about 45% fewer bytes | Two files | No | Keep |
| Anchored layout | P | No ADR; rationale in index-format.md | `contig`: a query round per step off the reference | No | Keep; say "filed under", never "coordinate" |
| `contig` layout | P | Old JBrowse scripts | Drop; but the hosted E. coli track uses it | No | Keep as option, out of the README |
| Rank | G/D | Copied | Reference flag | No | Keep |
| Off-reference coordinate from the first path to reach it | P | Depends on name order | None | Hover | Keep; a choice no row marks |
| First-pass placement of repeats, wide intervals | P | ADR 0008; pggb 10 kb window reads 2.8 MB of links vs 0.21 | Walk-file placement, rejected in ADR 0008 | Drawn as window-spanning false deletions | Open problem: the two outputs answer one question two ways |
| Node turned to read forward | P | index-format.md | Keep the GFA's strand | Nothing shows it | Mark or drop; open problem |
| Giant components, `--max-component`, stubs | P | ADR 0005: 3.7 M rows → 10 k | Gigabytes | Stub hover | Keep |
| `#samples`, `SB:H:` | D+K | ADR 0007: 2.05 GB → 333 MB | `SM:Z:` name lists | Carrier colouring | Keep bits; fix the type letter and the doubled name |
| `--format 1` | K legacy | Old readers | Drop | No | Drop |

## The branch against main

- **Reference:** redefined as the paths the `ref` rows are cut from, so one haplotype of `#reference` may be the reference (C157). No writer produces such a file yet.
- **Tags:** only `format` and `tile` are required (C201); budgets bind no row (C202).
- **Number grammar:** C203–C205.
- **Lines:** one tab, no empty line or field, `#unit` only on a unit's first line (C206–C207).
- **Invariants:** a step is at least 1 bp (C208), R ascends (C209), no empty unit (C210).
- **`bytes`:** the directory's tag alone (C211); units are BGZF specifically.
- **Names:** bytes 0x21–0x7E (a narrowing).
- None of it adds a row, unit or column.

## Step 3: the gap

- **Beyond minimal with a measured reason:** the route dictionary, the unit table, the pyramid, abridging's three row kinds, `hapBp`, `:k`/`@k`, `ownTiles`.
- **Beyond minimal without a current measurement:**
  - the bounded `stay` on ADR 0001's criteria
  - a byte budget separate from the step budget
  - the delta-token handle spelling
  - the anchored layout itself
  - the pyramid sizes stated as format
  - `piece` (redundant, I)
  - a one-haplotype reference no writer produces
- **Overlap between the outputs:** for a graph with paths, the walk file already holds the reference's nodes, the off-reference nodes and every link a kept line walks. The index adds:
  - links walked only by left-out lines: 32,347 of chr22's 4.7 M, and none in 150 random windows
  - carrier bits
  - the coarse tier
  - every rGFA
- **Where the outputs disagree:** a repeated node's position, and a node's strand.
- **Columns 1–3:** a filing key in the index, data in the walk file.
- **Headers:** two dialects; one forbids the repeated tag name the other requires. `graph:Z:` is their only link, and nothing compares it.
- **Merging:** not justified now (ADR 0008 and open-problems list what the walk view lacks). The cheap merge is in the telling: an rGFA gets the index, a graph with paths gets walk files.
- **Heng Li:** he'd recognise the index as a BED with a kind column, PAF-plain except `SB:H:`. The walk file is CRAM-like, not SAM/PAF-like: slices, a dictionary and a side table. A `walk` row means nothing without its tile's `ref` and `route` rows, and decoding is a four-step procedure. That trade is measured (3.1–4.5×, 32× against GFA fragments). The bulletproof part is real: a reader from the spec alone, a step-for-step rebuild, planted broken files. He'd push on the word count, the policy in the header, and four encodings of one event.

## Step 4: what a newcomer must be told

Five concepts:
- **reference:** regions are asked for in one genome's coordinates, such as GRCh38
- **node and link index:** the graph's nodes and links, findable by region
- **walk file:** every haplotype's path, for the same reference
- **tile:** the 64 kb piece a browser fetches
- **static host:** no server; the browser asks for byte ranges

Three sentences:

> gfa-to-tabix turns a pangenome graph in GFA into files you put on any web server. A browser asks for a region such as chr22:20,000,000-20,010,000 on GRCh38 and downloads only the few kilobytes that hold the graph's nodes there and every haplotype's path through them. No server program runs and the whole graph is never downloaded.

The figure, three panels:
- **Left, "chr1 of a small graph":** five grey nodes labelled GRCh38 and one extra node below. Lines HG002 and CHM13 run through them; CHM13 dips to the extra node. A ruler reads 0/30/60/90, with a bracket "chr1:30-60".
- **Middle, "hprc.GRCh38.walks.gz on a web server":** a bar in three segments under 0–30 / 30–60 / 60–90, only the middle shaded, "bytes 278-417". An arrow "one request" runs from the bracket.
- **Right, "what the browser draws":** the nodes under 30–60, the extra node, and the two lines.
- **Leave out:** "header", "table", "tile" as a label, "#0", row text.

`docs/figures/walks-tile.svg` is close to this; it needs only the right panel and fewer labels. `docs/figures/overview.svg` (every row, "indexed under" / "its own position") belongs in index-format.md only.
