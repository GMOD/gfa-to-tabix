#!/usr/bin/env bash
# Builds fuzz7.sh's random graphs under its six option sets and two byte
# budgets and runs
# claims7.py --own on each; prints per claim the files contradicting it and
# the cases, then one example file per claim.
# Usage: FUZZ_DIR=dir GFA_TO_TABIX=binary claims7-fuzz.sh [from] [to]
HERE=$(dirname "$(readlink -f "$0")")
G=$HERE/fuzz6-gen.py
C=$HERE/claims7.py
B=$(readlink -f "$(command -v "${GFA_TO_TABIX:?set GFA_TO_TABIX to the writer binary}")")
cd "${FUZZ_DIR:?set FUZZ_DIR to a scratch directory}"
from=${1:-1}; to=${2:-100}
for seed in $(seq $from $to); do
  python3 -I $G $seed > g$seed.gfa
  for v in "a:20:" "b:16:--stay 8" "c:32:--abridge-steps 3" "d:20:--stay 40" "e:64:--abridge-steps 2" "f:8:--stay 40 --abridge-steps 1" "g:64:--abridge-bytes 300" "h:128:--abridge-bytes 600"; do
    tag=${v%%:*}; rest=${v#*:}; tile=${rest%%:*}; opts=${rest#*:}
    if ! $B g$seed.gfa --walks --refs R --tile $tile $opts -o o$seed.$tag > o$seed.$tag.log 2>&1; then
      echo "seed $seed $tag BUILD: $(grep -v '^\[' o$seed.$tag.log | tail -1)"; continue
    fi
    python3 -I $C o$seed.$tag.R.walks.gz --own > c$seed.$tag.txt 2>&1 || echo "seed $seed $tag CRASH: $(tail -1 c$seed.$tag.txt)"
    rm -f o$seed.$tag.R.walks.gz o$seed.$tag.R.walks.gz.idx o$seed.$tag.log
  done
done
awk -F'\t' '/^[0-9]+\t[A-Z]/ { split($2, a, " "); n[a[1]] += $1; if ($1 > 0) { files[a[1]]++; if (!(a[1] in ex)) ex[a[1]] = FILENAME } }
  END { for (k in n) printf "%s\t%d cases in %d files, e.g. %s\n", k, n[k], files[k], ex[k] }' c*.txt | sort
echo done $from-$to
