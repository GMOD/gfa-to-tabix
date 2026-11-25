# Reading walk files

How a program reads a window of a [walk file](walks-format.md), as
@jbrowse/graph-walks does, then the programs that read walk files and how
to host one. The terms are the format page's
([Terms](walks-format.md#terms)).

## Reading a window

For a window `[s, e)` with context `c`, the stretch
`D = [max(0, s − c), e + c)`
([ADR 0010](adr/0010-walks-unit-table.md)):

- **At open:** GET the directory and refuse any format but 8. GET the
  header unit and the sequence's table in parallel, and refuse what
  [a reader refuses](walks-format.md#what-a-reader-refuses)
- **The read:** select the `tile` and `departures` units with
  `start < D.end` and `end > D.start`. Merge byte ranges that touch, and
  GET each as one single-range request, never a multi-range one
  <!-- C134 -->
- **Decode:** gunzip each unit. <!-- C149 --> Decode a tile's rows from
  `kind` on by [Rows](walks-format.md#rows) and
  [Decoding a walk row](walks-format.md#decoding-a-walk-row). Keep the
  departure lines overlapping `D` and drop exact duplicates
  <!-- C149 -->
- **The drawn stretch** is `D` widened to whole steps of the reference:
  it runs from the first base to the last of `D` and of every position
  of R, in the tiles the read selects, whose stretch overlaps `D`.
  <!-- C144 --> A position is one pass of the reference over a node, so
  where the reference passes a node more than once each pass over `D`
  counts and no pass elsewhere does <!-- C144 -->
- **Where a node is drawn:** a reader places a node at a reference
  position from a `ref` row of a tile it read whenever one exists: a pass
  over `D` before any other, then the row whose path sorts first in
  bytes, at its earliest start. Other nodes take haplotype offsets
  <!-- C119 -->

### Abridged pieces

- A cut that leaves an abridged piece of a window's tile unexpanded reads
  that tile's `blocks` unit and builds the piece from its row there: a
  block as the steps of R in its stretch, and a run off R as one step of
  that many bp whose nodes it doesn't know
  ([blocks](walks-format.md#blocks))
- Expanding an abridged piece, which a viewer does on request, reads the
  `detail` unit `cs:d`

### Attach fetches

An **attach fetch** is a reader's read of the tiles a departure record's
`ownTiles` names, for a record whose own steps it wants and whose leave
piece or rejoin piece the window's read lacks. It takes the record's own
steps from them and nothing else <!-- C117 -->

- Which records get one is the reader's choice: a record's line gives its
  two ends and its `ownBp` without one. @jbrowse/graph-walks makes one
  for a record that leaves or rejoins on `D` with own steps within its
  `attachBp`, and for no other record
- The own steps are the path's steps after its leave step and before its
  rejoin step, which start at `hapStart` on its contig and span `ownBp`.
  Nothing else an attach fetch reads joins a fragment or yields a
  computed departure <!-- C132 -->
- For a piece there that the tile abridged, the reader builds the
  record's own run from the `abridged` row and the record by
  [the attach rule](walks-format.md#row-rules), as one step of that many
  bp whose nodes it doesn't know, and reads no `blocks` unit for it.
  Where the cut was asked to expand that path it reads the piece's
  `detail` unit, and takes the own steps from the walk row there
  <!-- C133 -->
- Own steps on the reference's other sequences, in a line with no step
  on the reference, or in no line are in no tile `ownTiles` lists, and an
  attach fetch doesn't read them <!-- C87 -->

### What a cut returns

- Every piece with a step whose position overlaps the drawn stretch, an
  unexpanded abridged piece by its blocks; every departure record whose
  line overlaps `D`, unfiltered, one in a `#hole` included, each once;
  and every departure the reader computes between consecutive steps of
  one piece whose extent, from the first base of its end nodes to the
  last as a record's runs, overlaps `D`, one across a `#hole` included.
  <!-- C135 --> A departure between two pieces is a record, even where
  the read holds both, so none comes back twice <!-- C135 -->
- **A piece comes back trimmed** to its steps on the drawn stretch, with
  the bp of it the read holds past either end stated. A record for where
  the line goes after a step outside the drawn stretch need not overlap
  `D`, so a whole piece could show its line ending where it goes on
- **An end at the drawn stretch's edge is not the line's end.** Inside
  the drawn stretch a reader holds either the line's next step on the
  sequence or the record that gives it, so a line with neither has no
  later step on that sequence. At the edge it holds neither for a line
  with no later step there and for one that goes on in a tile it didn't
  read, and it says nothing of which
- **No later step on the sequence is not the line's end either.** No row
  states where a W or P line ends or how many pieces it has. After its
  last step on a sequence a line can go on over nodes off the reference,
  which its piece holds; in a piece filed on another sequence of the
  reference, which this sequence's units don't point to; or, for a
  contig, in a later line. A reader can say a line has no later step
  on the sequence, and how many bp its last piece there holds after that
  step. It cannot say the line ends there, nor where on the reference it
  goes

## Readers
<!-- background -->

- [@jbrowse/graph-walks](https://github.com/GMOD/graph-walks) 7 and later
  read format 8, with `WalkReader.open(url)` or
  `WalkReader.fromFilehandles({ data, directory })`, and refuse any other
  format. Its README gives the options of a cut
- The file has no link rows: a reader takes a link from two consecutive
  steps of a path
- The JBrowse graph genome viewer plugin,
  [BandageJS](https://jbrowse.org/demos/bandagejs/), ggbandage and
  ggtubemap read through @jbrowse/graph-walks
- [scripts/walks-brief.py](../scripts/walks-brief.py) is one short
  Python file that prints every W and P line back from a walk file
- jbrowse.org hosts HPRC v2.1's files in format 8, each with its `.idx`
  beside it:
  `https://jbrowse.org/demos/hprc/hprc-v2.1-mc-grch38-f8.GRCh38.walks.gz`
  from the GRCh38-referenced graph and
  `https://jbrowse.org/demos/hprc/hprc-v2.1-mc-chm13-f8.CHM13.walks.gz`
  from the CHM13-referenced one. The same names without `-f8` serve the
  same files, and the `-f8` names are the ones to cite

In a JBrowse graph track, `walksUri` takes the prefix up to the reference
sample, so a track on hg38 reads the GRCh38 file of the GRCh38-referenced
graph, and a track on hs1 the CHM13 file of the CHM13-referenced one.
`defaultHaplotypes` lists the haplotypes the track draws until the user
picks others:

```json
"adapter": {
  "type": "RgfaTabixAdapter",
  "walksUri": "https://example.org/hprc-v2.1-mc-grch38.GRCh38",
  "assemblyNameToPanSN": { "hg38": "GRCh38" },
  "defaultHaplotypes": ["HG002", "HG00733"]
}
```

## Hosting
<!-- background -->

- Any static web host that answers range requests serves a walk file.
  Serve single-range requests: CloudFront answers a multi-range request
  with the whole object
- Expose `Content-Range` to cross-origin readers, so a reader can check
  the directory's `bytes` against the data file's length
- Version the file names, so a data file and a directory from different
  builds can't meet. Upload the data file before its directory: a reader
  that meets a directory of another build refuses the pair
- A name that is cited keeps its bytes: a rebuild goes up under a new
  name, so the walk file a citation names, and a file built beside it,
  stay the same bytes
