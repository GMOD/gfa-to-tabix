#!/usr/bin/env bash
# claims-genome.sh <grch38|chm13> <GB a MB> <base GB>: claims7.py --seq on
# every reference sequence of one 5.0.0 genome file, the largest first, each
# under its own memory cap. A sequence's memory is estimated from its
# compressed bytes by the two numbers given, which a measured run sets.
# Sequences under 2 MB are checked several to a run, up to 40 MB a run.
# Runs go together while their estimates add up to at most the GB in
# claims.budget (60), at most claims.jobs (10) at once, and none starts
# unless its estimate and 25 GB is available.
set +u
in=$1 per_mb=$2 base=$3
case $in in grch38) ref=GRCh38 ;; chm13) ref=CHM13 ;; esac
A=~/work/blocks/accept-5.0.0
S=$A/g2t/docs/departures/scripts
N=~/work/blocks/genome-5.0.0/hprc-v2.1-mc-$in.$ref.walks.gz
C=$A/claims/$in
mkdir -p $C
python3 -I - $N $per_mb $base > $C/runs.tsv <<'PY'
import sys
lines = [l.split('\t') for l in open(sys.argv[1] + '.idx', encoding='utf-8', errors='surrogateescape').read().splitlines()]
per_mb, base = float(sys.argv[2]), float(sys.argv[3])
at = int(lines[1][2])
sized = []
for c in lines[2:]:
    if not c[0].startswith('#'):
        end = int(c[1]) + int(c[2])
        sized.append((end - at, c[0]))
        at = end
sized.sort(reverse=True)
runs, small, small_bytes = [], [], 0
for size, seq in sized:
    if size >= 2e6:
        runs.append((size, [seq]))
    else:
        if small and small_bytes + size > 40e6:
            runs.append((small_bytes, small))
            small, small_bytes = [], 0
        small.append(seq)
        small_bytes += size
if small:
    runs.append((small_bytes, small))
for k, (size, seqs) in enumerate(runs):
    print(k, size, int(per_mb * size / 1e6 + base) + 1, *seqs, sep='\t')
PY
declare -A est_of
reap() { local p; for p in "${!est_of[@]}"; do kill -0 $p 2>/dev/null || unset "est_of[$p]"; done; }
total() { local s=0 p; for p in "${!est_of[@]}"; do s=$((s + est_of[$p])); done; echo $s; }
while IFS=$'\t' read -r k size est seqs <&3; do
  if [ ! -f $C/$k.done ]; then
    while :; do
      reap
      n=${#est_of[@]}
      budget=$(cat $A/claims/claims.budget 2>/dev/null || echo 60)
      jobs=$(cat $A/claims/claims.jobs 2>/dev/null || echo 10)
      avail=$(free -g | awk '/^Mem:/ {print $7}')
      [ $n -lt $jobs ] && { [ $n = 0 ] || [ $(($(total) + est)) -le $budget ]; } && [ $avail -ge $((est + 25)) ] && break
      sleep 20
    done
    capg=$((est * 3 / 2))
    [ $capg -lt 6 ] && capg=6
    args=()
    IFS=$'\t' read -r -a names <<< "$seqs"
    for s in "${names[@]}"; do args+=(--seq "$s"); done
    ( systemd-run --user --scope -q -p MemoryMax=${capg}G -p MemorySwapMax=0 nice -n 10 \
        /usr/bin/time -f "%e s, %M KB peak, exit %x" python3 -I $S/claims7.py $N "${args[@]}" > $C/$k.txt 2>&1
      echo "exit $?" > $C/$k.done ) &
    est_of[$!]=$est
  fi
done 3< $C/runs.tsv
wait
cat $C/[0-9]*.txt | awk -F'\t' '/^[0-9]+\t/ { if (!($2 in sum)) order[++k] = $2; sum[$2] += $1 }
  END { for (i = 1; i <= k; i++) print sum[order[i]] "\t" order[i] }' > $C/claims.txt
planned=$(wc -l < $C/runs.tsv)
finished=$(ls $C/[0-9]*.done 2>/dev/null | wc -l)
passed=$(grep -l '^exit 0$' $C/[0-9]*.done 2>/dev/null | wc -l)
claims=$(wc -l < $C/claims.txt)
above=$(grep -cvE '^0'$'\t' $C/claims.txt)
{
  echo "runs: $finished of $planned, exit 0 in $passed"
  echo "sequences: $(cut -f4- $C/runs.tsv | tr '\t' '\n' | wc -l)"
  echo "claims: $claims, with a count above 0: $above"
  if [ "$planned" -gt 0 ] && [ "$finished" = "$planned" ] && [ "$passed" = "$planned" ] && [ "$claims" -gt 0 ] && [ "$above" = 0 ]; then
    echo PASSED
  else
    echo FAILED
  fi
} > $C/summary.txt
touch $C/all.done
