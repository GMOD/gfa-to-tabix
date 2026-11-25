---
name: checkers-hold-a-file-to-the-format-alone
description: No file checker holds a walk file to the format page and nothing else. claims7.py and spec8.py fail policy breaks, verify7.py holds a revisited file to the once-passed rule the format does not promise there, spec8.py skips several ADR 0017 sentences, and audit7.py and walks-truth.py end in tracebacks that broken.sh counts as a pass. The list of where, with the planted file for each.
metadata:
  repo: gfa-to-tabix
---

# Checkers that hold a file to more, or less, than the format

As of 2026-11-19, from `docs/departures/scripts/broken/cases.tsv` and the
scripts; no bullet rechecked against the scripts since, and the checkers
have had only small edits (269073a, fbd2241).

## More than the format

- `claims7.py` and `spec8.py` fail files that break this writer's policy
  and no invariant: `costliest-not-first`, and for `claims7.py`
  `revisited-as-interior` and, where the `#walks` line states a budget
  above 0, `budget-bytes-over`, `budget-steps-over` and `budget-put-back`,
  though the budgets bind no row (C202)
- `verify7.py` holds a file with revisited nodes to the once-passed rule
  this writer keeps and the format does not promise there, where
  `spec8.py` passes it (`other-sequence-as-interior-revisited`)
- Under `--seq`, `claims7.py` reads the fourth column of every row of the
  sequences it was not given, whatever kind of unit holds the row
  (`row_elsewhere`), so a later unit kind's row there whose fourth column
  were `ref` or `nodes` would count toward its `SQ:Z:` claim. The page
  says a later kind takes no row kind word of its own, which keeps the two
  apart; the script still does not skip such a unit as the page says a
  reader does. Read from the code, not run

## Less than the format

- On a file with no `tile:i:`, `audit7.py` and `walks-truth.py rebuild`
  end in a traceback, which `broken.sh` counts as passing the file;
  `verify7.py`, `claims7.py` and `spec8.py` fail it by name
  (`tile-missing`), as they do `tile:i:0` (`tile-zero`). On a name
  holding a carriage return `audit7.py` and `walks-truth.py rebuild` end
  in one, reading the line as two, where `verify7.py` and `spec8.py` fail
  it (`name-cr`)
- Of the sentences
  [ADR 0017](../../docs/adr/0017-format-8-tags-numbers-lines-and-names.md)
  added, `spec8.py` checks the names, the one `#reference` line, the
  `bytes` tag, the whole haplotypes of the reference, `tile:i:`'s range
  and the numbers of the `#walks` line's `i` tags. It does not check how
  any other number is written, an empty field in a row, the lines of a
  unit of a later kind, an empty departure bin or a coordinate above
  2^53, and passes the planted files for each
  ([matrix.txt](../../docs/walks-container/spec-sentences/matrix.txt));
  `verify7.py` holds a file to them, and `claims7.py` to a piece's end
- `verify7.py` does not hold a file to R ascending (C209) or to one
  encoding of a walk row (C70), which take a sequence's rows or decoding:
  `claims7.py` and `spec8.py` do, and `claims7.py` has read each hosted
  file whole for them, a batch of sequences at a time
  ([claims-hosted.tsv](../../docs/walks-container/spec-sentences/claims-hosted.tsv))
- `walks-truth.py rebuild` passes a file whose route interior holds a
  once-passed node, since the steps it rebuilds are the line's whatever
  their filing

## The work

- Each finding above, closed with its planted file
- The split of the claims into format and this writer's policy is
  `../ideas/waiting-on-a-call/name-the-placement-policy.md`
