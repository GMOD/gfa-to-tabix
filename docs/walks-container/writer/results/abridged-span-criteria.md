# Criteria, written 2026-11-11 before any decider ran

A response to the abridged-span finding is accepted only if all hold:

- **Misses:** on both hosted walk files, a window that a piece's step
  positions overlap shows that piece, abridged or not. Today 1,279 of
  74,053 (GRCh38) and 469 of 65,396 (CHM13) abridged pieces miss such
  windows.
- **False showings:** a window shows no abridged piece that none of its
  steps overlap, or the decider says how many it adds and why that is
  acceptable.
- **ADR 0011:** a change to walk format 7's rows, or to what their
  columns mean, needs ADR 0011's trigger (a user, or a consumer working
  against a hosted file) and must beat shipping unchanged against these
  criteria. A review finding alone goes to open problems.
- **Cost:** count every release and hosted-file rebuild it needs
  (gfa-to-tabix, graph-walks, the consumers that pin graph-walks, the two
  hosted walk files), against what it fixes.
- **Mixed evidence:** the smaller move wins.
