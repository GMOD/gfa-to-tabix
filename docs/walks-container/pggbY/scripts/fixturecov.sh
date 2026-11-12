#!/usr/bin/env bash
# Builds what check-walks.sh builds (the walk fixtures under its four option
# sets, and fuzz7.sh's seeds 1 to 6 under its 13 variants) and runs stats8.py
# on each file, so the repeat-only mechanisms' reach on fixtures can be set
# beside pggb chrY's. Writes fixcov/*.json.
cd ~/work/blocks/pggbY
B=~/work/blocks/src/target/release/gfa-to-tabix
R=src
D=fixcov
rm -rf $D && mkdir -p $D
one() {
  local name=$1 gfa=$2 refs=$3
  shift 3
  if $B "$gfa" --walks --refs "$refs" "$@" -o "$D/o" > /dev/null 2>&1; then
    for r in ${refs//,/ }; do
      python3 -I stats8.py "$D/o.$r.walks.gz" > "$D/$name.$r.json" 2> /dev/null
    done
  fi
  rm -f "$D"/o.*
}
for f in "walks-two-refs.gfa GRCh38,Q" "walks-two-refs-p.gfa GRCh38,Q" "walks-repeat.gfa R" "walks-loop.gfa R" \
         "walks-records.gfa R" "walks-contig-ends.gfa R" "walks-skip.gfa R,Q" "walks-sequences.gfa R" \
         "walks-long-jump.gfa R"; do
  read -r gfa refs <<< "$f"
  k=0
  for opts in "--tile 10" "--tile 7 --stay 0" "--tile 10 --abridge-bytes 1" "--tile 1000 --abridge-steps 1"; do
    read -r -a args <<< "$opts"
    one "${gfa%.gfa}.$k" "$R/tests/data/$gfa" "$refs" "${args[@]}"
    k=$((k + 1))
  done
done
one abridge-bytes "$R/tests/data/walks-abridge-bytes.gfa" R --tile 100 --abridge-bytes 600
for seed in 1 2 3 4 5 6; do
  shapes=()
  [ $((seed % 3)) = 0 ] && shapes+=(--zero)
  [ $((seed % 2)) = 0 ] && shapes+=(--two-haplotypes)
  [ $((seed % 3)) = 1 ] && shapes+=(--hairpins)
  python3 -I $R/docs/departures/scripts/fuzz7-gen.py "$seed" "${shapes[@]}" > "$D/g$seed.gfa"
  for v in "a:20:" "b:16:--stay 8" "c:32:--abridge-steps 3" "d:20:--stay 40" "e:64:--abridge-steps 2" \
           "f:8:--stay 40 --abridge-steps 1" "g:64:--abridge-bytes 300" "h:128:--abridge-bytes 600" \
           "i:24:--sequences --abridge-bytes 400" "j:3:--stay 0 --abridge-bytes 1" "k:1000:--stay 1000 --abridge-steps 1" \
           "l:5:--abridge-bytes 1" "m:2:--stay 1000 --abridge-steps 2"; do
    tag=${v%%:*}; rest=${v#*:}; tile=${rest%%:*}; read -r -a opts <<< "${rest#*:}"
    refs=R,Q
    one "fuzz$seed$tag" "$D/g$seed.gfa" "$refs" --tile "$tile" "${opts[@]}"
  done
done
ls $D/*.json | wc -l
