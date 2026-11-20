# Agent documentation

Laid out as jbrowse-components' `agent-docs/` is. Every file below
`handoffs/`, `todo/` and `ideas/` carries `name:` and `description:`
frontmatter, and `ls` is the index: nothing generates a table, so none is
kept by hand.

- `handoffs/`: the live state of an unfinished thread, as pointers rather than
  content. When the thread lands, file its remainder below and delete the
  handoff in the same pass. An empty folder is the normal state.
- `todo/`: work someone intends to do, one item per file. `metadata.repo`
  names the repo the change lands in, since this is where the walks stack's
  sessions coordinate.
- `ideas/`: one parked proposal per file, in the subfolder naming what it
  waits on: `ready/`, `waiting-on-a-call/`, `waiting-on-a-number/`,
  `waiting-on-someone-else/`, or `collections/` for several small ones in one
  file. A verdict moves it to an ADR, `todo/`, or a deletion.
- `reference/`: settled descriptions and audits, each saying when it was
  taken.
- Format and spec questions go to `docs/open-problems.md`, and decisions to
  `docs/adr/`, not here.
- Git history holds what a session did, so no file here restates it.
