#!/usr/bin/env bash
# Runs claims7.py on a walk file a sequence at a time, with --seq on each
# sequence its directory lists, and adds up each claim's count over the
# runs. A file with no sequence is checked whole. Prints the output of each
# run that fails, then the counts, and exits 1 where a run failed.
# Usage: claims7-seqs.sh walks.gz [claims7.py options]
set -u
HERE=$(dirname "$(readlink -f "$0")")
f=${1:?the walk file}
shift
dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT
tail -n +3 "$f.idx" | grep -v '^#' | cut -f1 > "$dir/seqs"
status=0
n=0
run() {
  n=$((n + 1))
  python3 -I "$HERE/claims7.py" "$f" "$@" > "$dir/$n" 2>&1 || { status=1; echo "== ${*: -1}"; grep -vE '^0'$'\t' "$dir/$n"; }
}
if [ -s "$dir/seqs" ]; then
  while IFS= read -r seq; do
    run "$@" --seq "$seq"
  done < "$dir/seqs"
else
  run "$@"
fi
cat "$dir"/[0-9]* | awk -F'\t' '/^[0-9]+\t/ { if (!($2 in sum)) order[++k] = $2; sum[$2] += $1 }
  END { for (i = 1; i <= k; i++) print sum[order[i]] "\t" order[i] }'
echo "# claims7-seqs.sh: $n runs of $f"
exit $status
