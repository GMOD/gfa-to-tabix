# Proposal: a step is placed only where its reference passes the node once

- **Status:** rejected, 2026-11-06. It was written as ADR 0011, withdrawn
  the same night, and then rejected after four reviews
  ([reviews](reviews/)):
  - It leaves MC rows byte-identical.
  - On pggb it doesn't make collapsed repeats true: the spanning records
    are still hops between copies.
  - It doubles the attach fetches.
  - It would need at least six amendments to freeze.

  Format 7 is frozen instead ([ADR 0011](../../adr/0011-format-7-is-frozen.md)).
  This page and its data are kept as the measurement
- **Decides:**
  - where a haplotype's steps are placed on a reference that passes some
    nodes more than once
  - where a sequence's detail entries are listed
  - that 0 bp segments are dropped on reading
  - that the format is now frozen
- **Measured by:** one spike that built the candidates on ada with the
  arbA window harness, reproducing arbA's 2,400 windows exactly. Two
  independent reviewers each decided from the spike's numbers, and both
  chose this decision. Data, scripts and the patch are in
  this folder, with
  `out/results.txt` as the summary
- **Supersedes:**
  - [ADR 0001](../../adr/0001-step-placement.md)'s nearest-pass placement on
    revisited nodes
  - `--stay` and the `stay:i:` header tag
  - the `@k` and `:k` copy names
  - `leavePasses` and `rejoinPasses` on departure records
  - the "Exact and chosen" section of
    [walks-format.md](../../walks-format.md)

## Context

A walk file gives every placed step a position on the reference. On a
Minigraph-Cactus graph the reference passes each node once
(`revisited:i:0`), so the position is a fact of the graph.

A pggb graph collapses repeats. GRCh38 passes some chrY nodes up to 50
times, and format 7 placed a haplotype's step on such a node by a rule:
the nearest pass, kept for `--stay` bp. Only 35.9% of pggb chrY pieces
land within 10 kb of where the MC graph puts the same contig
([open problems](../../open-problems.md)). Over a collapsed repeat, the rule
chose the coordinate.

The rule also wrote most of pggb's departure records. 97% of chrY's
425,040 records end on a revisited node, and 86.5% carry 0 own bp: they
are hops between copies the rule picked, not anything a haplotype does.
Two design reviews traced about half of the issues log to this
projection ([henli-fundamental.md](henli-fundamental.md)).

## Decision

- **A step is placed only on a node its reference sequence passes once.**
  A step on a node the sequence passes more than once is route interior,
  like a step on the haplotype's own node. A haplotype crossing a
  collapsed repeat shows as a departure record spanning it, whose
  `ownBp` counts the sequence the file does not place.
- **`ref` rows keep `passes`, and the header keeps `revisited`.** They
  tell a viewer where the reference collapses and why nothing is placed
  there.
- **Detail entries move to a table of their own.** A sequence's table
  lists its detail entries' table as one `#entry`, and that table is read
  the first time an abridged path is expanded. The directory does not
  grow.
- **Segments of 0 bp are dropped on reading.** Their steps leave every
  line, and a line left with no steps is dropped. Neither HPRC graph has
  one: MC chr22 has 3,122,495 segments and pggb chrY 4,122,486, none of
  them 0 bp.
- **The format is frozen.**
  - There is no format 9 until the JBrowse plugin and bandage-core have
    shipped on format 8 and a hosted file has been viewed.
  - A finding made after the port goes into
    [open problems](../../open-problems.md), not into a format change.
  - A review that re-decides the design is no exception.

## Evidence

pggb is HPRC release 2 chrY and MC is HPRC v2.1 chr22, both on GRCh38.
Window bytes are KB (1,000 B), median / p90, over the tile and
departure units within ±1 kb of 300 arbA-seeded windows per size.

| file | data file | 1 kb | 64 kb | 1 Mb |
|---|---|---|---|---|
| MC, format 7 | 58.49 MB | 28.8 / 52.5 | 57.8 / 112.9 | 500.5 / 683.9 |
| MC, this decision | 58.49 MB, same sha256 | same | same | same |
| pggb, format 7 | 187.16 MB | 69.8 / 246.1 | 120.6 / 456.1 | 736.7 / 3,551 |
| pggb, this decision | 236.83 MB | 67.9 / 226.7 | 119.3 / 365.3 | 769.3 / 2,132 |

| pggb chrY | format 7 | this decision |
|---|---|---|
| departure records | 425,040 | 246,739 |
| records with 0 own bp | 367,486 | 5,858 |
| records ending on a revisited node | 405,985 | 0 |
| copies named (`@k`, `:k`) | 284,114 | 0 |
| haplotype bp placed | 2.815 Gbp | 1.950 Gbp |
| steps placed | 175.5 M | 19.7 M |
| detail units | 160.3 MB | 215.9 MB |

At chrY:23,600,000–23,601,000, GRCh38 passes every node four times: at
21.99, 22.59, 23.60 and 26.07 Mb. Under format 7 the window was 110 KB.
It held 91 haplotypes in walk rows and 6,333 records, 98% of them with
0 own bp. Under this decision it is 74 KB, and all 124 haplotypes appear
as 2,760 records spanning it, with a median of 4,095 own bp. Where a node
is passed twice and far apart (chrY:24.03 Mb), there are 195 walk rows
against 200. A control window with no revisited node holds 117 against 117.
Both builds pass `verify7.py` and `claims7.py`, and `--stay 0` gives the
same rows as `--stay 311`.

Detail table, one per sequence, from `out/r3.txt`:

| | open median / max, now | split |
|---|---|---|
| GRCh38, 24 chromosomes | 86.7 / 192.2 KiB (chr9) | 69.7 / 121.3 KiB |
| CHM13 | 84.8 / 173.7 KiB | 63.8 / 114.8 KiB |

GRCh38 chr1's first view goes from 211 KiB to about 144 KiB.

## Consequences

- **Every position and every departure in a walk file is a fact of the
  graph.** MC files are byte-identical in their rows; only the format
  number and the detail table move.
- **On pggb chrY, 31% of placed haplotype bp lose their position.** Most
  of that is in Yq11 and the palindromes, where the old position agreed
  with MC about a third of the time. The file grows 26.5%, all of it in
  detail units no window reads, and p90 window bytes fall at every
  window size.
- **Viewers draw a collapsed stretch from `passes`, as the reference
  passing it k times.** A span's `ownBp` there is sequence the file does
  not place, never sequence the reference lacks, so it is never labelled
  an insertion or a deletion.
- **gfa-to-tabix:**
  - deletes nearest pass, `--stay`, the copy encoding and the pass fields,
    about 270 lines
  - drops 0 bp segments on reading
  - writes the detail table
  - [walks-format.md](../../walks-format.md) loses claims C2, C21–C24, C53,
    C62, C70 and C120, and the Passes part of C79
- **graph-walks 6** drops the copy decoder and reads the detail table on
  first expansion.
- **Lost:** placements continuity made near certain, such as a 603 bp node
  at chrY:18.55 Mb whose other pass is 220 kb away. On pggb chr22 outside
  2.8–26.7 Mb, nearest pass agrees with MC 88.7% of the time. This
  decision can't tell those from the Yq11 coin flips. Getting them back
  needs an alignment of each haplotype to the reference as writer input,
  and that would be a later format with its own ADR. Nothing on ada
  provides one for pggb chrY today.

## Alternatives rejected

- **Keep format 7's placement.** Its rows over collapsed repeats were a
  rule's choice, right about a third of the time, with no mark saying
  which ones. Its records were mostly hops the rule made.
- **Refuse graphs whose reference revisits a node.** That refuses a whole
  file for a per-node problem, and gives up 1.95 Gbp of exact placement on
  pggb chrY. This decision covers the same case: a file with
  `revisited:i:0` is exactly the graph that alternative would accept.
- **Departures as neighbour fields on walk rows.** These are SAM-style
  previous and next pieces. The files were 1.0% smaller on MC and 1.5% on
  pggb, and windows 0–4% smaller at the median. But 4% of MC's records and
  37–46% of pggb's still need the pyramid, so one departure would be
  encoded two ways, and the change removes no mechanism.
  [ADR 0009](../../adr/0009-departure-records.md) had already decided that walk
  rows carry no neighbour tags.
- **A root table pointing at per-sequence tables.** Format 7 already has
  one: the `.idx` is a 7.9 KB directory of per-sequence tables. The 183 KB
  the proposal blamed on a whole-genome table is chr1's own table, and the
  split of detail entries above is the part of it that pays.
