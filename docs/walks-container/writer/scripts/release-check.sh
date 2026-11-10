#!/usr/bin/env bash
# The release check of the walks writer on the real graphs, on ada: builds
# MC chr22 and pggb chrY on GRCh38 from a bundle of the commit to check,
# reports whether each data file is byte-identical to the previous build
# where one is given (a difference is a signal, not a failure), and runs every file check on it: verify7.py; claims7.py --own,
# audit7.py, and walks-truth.py rebuild over $SHARDS shards of the paths,
# 8 fed by each read of the GFA, the audit with the GFA. Each check's exit status is
# recorded, and `release.done` says PASSED or FAILED last.
# Usage, on ada:
#   git bundle create writer.bundle main   # locally, then scp it to ~/work/release/
#   SHARDS=24 [CLAIMS7=1] bash release-check.sh ~/work/release ~/work/arb-format-opus/in [previous dir]
# where the previous dir holds final.mc22.GRCh38.walks.gz and
# final.pggbY.GRCh38.walks.gz from the last run, or is left out. Without a
# writer.bundle, src/ is used as it is.
set -uo pipefail
W=$1 IN=$2 PREV=${3:-}
SHARDS=${SHARDS:-24}
cd "$W"
if [ -f writer.bundle ]; then rm -rf src && git clone -q -b main writer.bundle src; fi
git -C src log --oneline -1 > release.commit.txt
(cd src && cargo build --release -q) > release.build-binary.log 2>&1 || { echo FAILED > release.done; exit 1; }
B=$W/src/target/release/gfa-to-tabix
S=$W/src/docs/departures/scripts
T=$W/src/scripts/walks-truth.py
cap() { systemd-run --user --scope -q -p MemoryMax=$1 -p MemorySwapMax=0 "${@:2}"; }
status=0
for d in mc22 pggbY; do
  G=$IN/$d.gfa
  cap 30G /usr/bin/time -f "$d: %e s, %M KB peak" $B "$G" --walks --refs GRCh38 -o release.$d > release.$d.build.log 2>&1 || { status=1; continue; }
  F=release.$d.GRCh38.walks.gz
  if [ -n "$PREV" ] && [ -f "$PREV/final.$d.GRCh38.walks.gz" ]; then
    if cmp "$F" "$PREV/final.$d.GRCh38.walks.gz" > release.$d.cmp.txt 2>&1; then echo "byte-identical to $PREV" >> release.$d.cmp.txt
    else echo "DIFFERS from $PREV" >> release.$d.cmp.txt; fi
  fi
  cap 10G python3 -I "$S/verify7.py" "$F" > release.$d.verify7.txt 2>&1 || { echo "verify7 exit $?" >> release.$d.verify7.txt; status=1; }
  for check in rebuild audit7 ${CLAIMS7:+claims7}; do
    [ -f release.$d.$check.txt ] && grep -q ", 0 failed;" release.$d.$check.txt && continue
    case $check in
      rebuild) n=1; at_once=1; limit=60G ;;
      audit7) n=1; at_once=1; limit=60G ;;
      claims7) n=$SHARDS; at_once=4; limit=28G ;;
    esac
    for i in $(seq 0 $((n - 1))); do
      out=release.$d.$check.$i.txt
      case $check in
        claims7) (cap $limit python3 -I "$S/claims7.py" "$F" --own --shard $i/$n > $out 2>&1; echo $? > $out.rc) & ;;
        audit7) (cap $limit python3 -I "$S/audit7.py" "$F" --gfa "$G" > $out 2>&1; echo $? > $out.rc) & ;;
        rebuild) (cap $limit python3 -I "$T" rebuild "$F" "$G" --shards $SHARDS --jobs 8 > $out 2>&1; echo $? > $out.rc) & ;;
      esac
      [ $(( (i + 1) % at_once )) = 0 ] && wait
    done
    wait
    failed=0
    for i in $(seq 0 $((n - 1))); do
      [ "$(cat release.$d.$check.$i.txt.rc)" = 0 ] && ! grep -q Traceback release.$d.$check.$i.txt || failed=$((failed + 1))
    done
    {
      echo "# $check on $F, $n shards, $failed failed; a shard's exit status, then its last line"
      for i in $(seq 0 $((n - 1))); do echo "shard $i: exit $(cat release.$d.$check.$i.txt.rc): $(tail -1 release.$d.$check.$i.txt)"; done
      echo "# lines of any shard that aren't a 0 count, a comment or a summary:"
      grep -hvE '^0'$'\t''|^#|^\S+: shard' release.$d.$check.[0-9]*.txt | sort | uniq -c | sort -rn | head -40
    } > release.$d.$check.txt
    [ $failed = 0 ] || status=1
  done
done
ls -l release.*.walks.gz release.*.walks.gz.idx > release.sizes.txt
[ $status = 0 ] && echo PASSED > release.done || echo FAILED > release.done
cat release.done
exit $status
