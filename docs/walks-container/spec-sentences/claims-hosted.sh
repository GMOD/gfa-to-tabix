#!/usr/bin/env bash
# Runs claims7.py over a whole genome-wide walk file, a batch of sequences
# at a time with --seq, so every claim it checks within a sequence is
# checked on every sequence of the file: R4, R5, H1, H3, H4, K13, U1 and W2
# among them.
# - `plan` prints a batch a line, `<MB><TAB><sequence>...`, largest first:
#   the sequences packed into batches of at most <MB> of compressed units,
#   a larger sequence alone. The directory's table offsets give a
#   sequence's size. claims7.py reads the whole file once a run and holds
#   what the sequences it decodes take, which grows with their size
# - `run` starts the batches in the plan's order, at most <workers> at
#   once, each under a memory cap of 2 GB and 0.11 GB a MB of its units,
#   which the kernel holds it to, and only while the caps of those running
#   add up to at most <GB in flight>. The cap is from the 4.4 GB a review
#   measured for the 42 MB of GRCh38's chr21. A batch that has an exit
#   status or is marked running is skipped, so a run can be taken up
#   again. Each batch writes its output, its stderr, its exit status and
#   `seconds<TAB>peak KiB`
# - `sum` prints one line a batch, then each claim's count added up over
#   the batches
# Usage: claims-hosted.sh plan <walks.gz> <MB> > plan.txt
#        claims-hosted.sh run <scripts dir> <walks.gz> <plan.txt> <out dir> <workers> <GB in flight>
#        claims-hosted.sh sum <plan.txt> <out dir>
set -u
case $1 in
  plan)
    tail -n +3 "$2.idx" | grep -v '^#' | awk -F'\t' -v cap="$3" '
      { size[NR] = ($2 - prev) / 1e6; name[NR] = $1; prev = $2 + $3 }
      END {
        for (i = 1; i <= NR; i++) order[i] = i
        for (i = 2; i <= NR; i++) for (j = i; j > 1 && size[order[j]] > size[order[j - 1]]; j--) {
          t = order[j]; order[j] = order[j - 1]; order[j - 1] = t
        }
        for (i = 1; i <= NR; i++) {
          s = order[i]
          for (b = 1; b <= bins && held[b] + size[s] > cap; b++);
          if (b > bins) bins = b
          held[b] += size[s]; line[b] = line[b] "\t" name[s]
        }
        for (b = 1; b <= bins; b++) printf "%d%s\n", held[b] + 1, line[b]
      }' ;;
  run)
    S=$2 f=$3 plan=$4 out=$5 workers=$6 budget=$7
    mkdir -p "$out"
    n=0
    while IFS=$'\t' read -r -a batch; do
      n=$((n + 1))
      [ -e "$out/$n.rc" ] || [ -e "$out/$n.running" ] && continue
      cap=$((2 + (batch[0] * 11 + 99) / 100))
      until [ "$(ls "$out" | grep -c '\.running$')" -lt "$workers" ] &&
            [ $(($(cat "$out"/*.running 2> /dev/null | paste -sd+ -) + 0 + cap)) -le "$budget" ]; do
        sleep 10
      done
      echo "$cap" > "$out/$n.running"
      args=()
      for s in "${batch[@]:1}"; do args+=(--seq "$s"); done
      {
        /usr/bin/time -f '%e\t%M' -o "$out/$n.time" systemd-run --user --scope -q -p MemoryMax="${cap}G" -p MemorySwapMax=0 \
          python3 -I "$S/claims7.py" "$f" "${args[@]}" > "$out/$n.out" 2> "$out/$n.err"
        echo $? > "$out/$n.rc"
        rm "$out/$n.running"
      } &
    done < "$plan"
    wait ;;
  sum)
    plan=$2 out=$3
    printf 'batch\tsequences\tMB of units\texit\tseconds\tpeak KiB\tfirst sequence\n'
    n=0
    while IFS=$'\t' read -r -a batch; do
      n=$((n + 1))
      printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$n" "$((${#batch[@]} - 1))" "${batch[0]}" "$(cat "$out/$n.rc" 2> /dev/null || echo 'not run')" \
        "$(cat "$out/$n.time" 2> /dev/null || printf '\t')" "${batch[1]}"
    done < "$plan"
    printf 'cases\tclaim, over the batches that ran\n'
    cat "$out"/*.out | awk -F'\t' '/^[0-9]+\t/ { if (!($2 in sum)) order[++k] = $2; sum[$2] += $1 }
      END { for (i = 1; i <= k; i++) print sum[order[i]] "\t" order[i] }' ;;
esac
