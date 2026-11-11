# Criteria for the abridged-piece decision, written 2026-11-11 before any decider ran

The user has authorised a walk format change if it is a win. Every
candidate, including changing nothing, is judged on these, in this order:

- **Truth.** On both hosted files, in every view that reads walk files
  (every haplotype, the default four, contained cuts, forms), the view
  states nothing false about an unloaded abridged piece: not absent where
  it steps, not present where it has no step, no size, strand or departure
  that the loaded piece contradicts. The loaded (expanded) cut over the
  same window is the truth. A candidate that leaves any false statement
  fails unless it says which, how many, and why that is acceptable.
- **What the user sees before loading.** Among candidates that pass Truth,
  the one that shows more true information without loading (where in the
  window an unloaded piece steps, its size there) is better, by how much
  it shows, with numbers on the hosted files where measurable.
- **Cost of reading.** Bytes and requests a window reads, median and
  worst, on the hosted files, against today.
- **Cost of the change.** Bytes added to the hosted files; whether they
  are rebuilt; releases of gfa-to-tabix, graph-walks, bandage-core, the
  plugin and the other consumers (BandageJS, ggbandage, the tube map,
  jb2hubs); the mechanisms added to the spec. Every mechanism earns its
  place with a number.
- **ADR 0011's burden.** A format change must beat the best candidate
  that leaves the format unchanged on the criteria above. When the
  evidence is mixed, the smaller move wins.
