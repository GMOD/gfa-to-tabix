# Forms arbitration, 2026-11-05

- `r28.summary.txt`: contradicted members (`formContradictions`) on the
  28 chr22 windows of `../minimal/mc22.forms-compare-review.txt`, for
  edf4acd (`base`) and 7601e9e (`graph-walks`), folded (`keep 0`) or not
  (`keep 1`), at each floor. Written by `scripts/run28.sh` from cuts
  cached by `scripts/dump.test.ts`
- `gate.summary.txt`: the same on the jb2hubs gate's 59 windows, by
  `scripts/rungate.sh`, with `scoreForms.py --complete-claims` against
  `truth2.tsv`; the claim scores are in `gate/*.score.txt`
- `fable-branch.cyp2d6-place.txt`: the no-fold branch's forms at
  chr22:42.10-42.15 Mb holding the haplotypes with a 13.7 kb insertion
  at 42,134,095, their form's mark at 42,125,923
- The scripts ran from `~/src/arb-forms-opus/`; copy the `.test.ts` files
  into graph-walks' `src/arb/` to rerun them
- `combined.txt`: the same check after the format arbitration landed
  (graph-walks ec8ecd9), on that arbitration's MC chr22 build: no
  contradicted member on any of the 28 windows, at any floor
