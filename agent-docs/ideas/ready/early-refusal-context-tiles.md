---
name: early-refusal-context-tiles
description: graph-walks 9.1.0's early refusal counts only tiles strictly inside the window and its context, so a one-tile window whose context reaches a dense neighbouring tile is refused only after a full cut (1–3 s on the comparison's pggb chrY windows under the browser preset).
metadata:
  repo: graph-walks
---

# Early refusal for windows a tile wide

The regenerated comparison (`docs/comparison-details.md`, 7132d2c) times
the browser preset, 1 kb context, on 64 kb windows. Its three refusals,
one on MC chr22 and two on pggb chrY, each took about as long as a full
cut: the window's own tile counted 3.25 M, 3.99 M and 3.91 M steps, under
the 4 M budget, and the tiles the context reaches are not strictly inside,
so they count nothing. A chrY window that cuts in 38 ms without context
takes 625 ms with it, decoding all of a 4.09 M-step neighbour.

- A context tile's rows count only from their first step inside the
  window plus context; a surely-kept bound for them needs each row's
  first on-reference position, which a row states only after decoding its
  routes. Worth finding whether the `blocks` or `ref` rows give it cheaply
- Or decode a context tile's rows lazily, from the window's side, and stop
  at the context's edge
- Neither is needed for correctness; it is the refusal's cost on small
  windows next to dense tiles
