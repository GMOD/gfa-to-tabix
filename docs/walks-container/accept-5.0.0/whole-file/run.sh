#!/usr/bin/env bash
# The whole-file checks of ADR 0016 on the bytes jbrowse.org hosts, run on
# ada: for each file, that the local copy is the hosted one (its length
# against Content-Length, its S3 multipart ETag over 8 MiB parts against
# the hosted ETag, its .idx's sha256 against the hosted .idx's), then
# verify7.py over the whole file, and spec8.py where the file fits in
# memory, each under a memory cap with no swap and /usr/bin/time. pggb chrY
# on GRCh38 is not hosted and is checked as the one file here with
# revisited nodes. checkers.tsv names the two scripts by their git blob,
# which `git rev-parse HEAD:<path>` prints at any commit that holds the
# same script. table.py writes results.jsonl and README.md from what this
# leaves in the output directory.
# Usage: run.sh <gfa-to-tabix checkout> <output directory>
set -u
R=$(readlink -f "$1")
O=$(readlink -f "$2")
S=$R/docs/departures/scripts
G=$HOME/work/blocks/genome-5.0.0-hdr
U=https://jbrowse.org/demos/hprc
mkdir -p "$O"
for c in verify7 spec8; do
  echo "$c.py	$(git -C "$R" rev-parse HEAD:docs/departures/scripts/$c.py)"
done > "$O/checkers.tsv"
date -u +%F > "$O/date.txt"
cap() { local m=$1 t=$2; shift 2; systemd-run --user --scope -q -p MemoryMax="$m" -p MemorySwapMax=0 nice -n 10 /usr/bin/time -f '%e\t%M\t%x' -o "$t" "$@"; }
local_file() {
  case $1 in
    grch38) echo "$G/hprc-v2.1-mc-grch38.GRCh38.walks.gz" ;;
    chm13) echo "$G/hprc-v2.1-mc-chm13.CHM13.walks.gz" ;;
    chr6-sequences) echo "$G/hprc-v2.1-mc-grch38-chr6-sequences-f8.GRCh38.walks.gz" ;;
    chr20-sequences) echo "$HOME/work/chr20seq/hprc-v2.1-mc-grch38-chr20-sequences-f8.GRCh38.walks.gz" ;;
    pggbY) echo "$HOME/work/blocks/accept-5.0.0/4b14ee3/pggbY/pggbY.GRCh38.walks.gz" ;;
  esac
}
hosted_name() {
  case $1 in
    grch38) echo hprc-v2.1-mc-grch38-f8.GRCh38.walks.gz ;;
    chm13) echo hprc-v2.1-mc-chm13-f8.CHM13.walks.gz ;;
    chr6-sequences) echo hprc-v2.1-mc-grch38-chr6-sequences-f8.GRCh38.walks.gz ;;
    chr20-sequences) echo hprc-v2.1-mc-grch38-chr20-sequences-f8.GRCh38.walks.gz ;;
  esac
}
etag() {
  nice -n 10 python3 -I - "$1" <<'PY'
import hashlib, sys
digests = []
with open(sys.argv[1], 'rb') as f:
    while chunk := f.read(8 << 20):
        digests.append(hashlib.md5(chunk).digest())
print(f'{hashlib.md5(b"".join(digests)).hexdigest()}-{len(digests)}')
PY
}
printf 'file\thosted\tlocal bytes\thosted Content-Length\tlocal ETag, 8 MiB parts\thosted ETag\tlocal .idx sha256\thosted .idx sha256\tlocal sha256\n' > "$O/identity.tsv"
for f in grch38 chm13 chr6-sequences chr20-sequences pggbY; do
  l=$(local_file $f) h=$(hosted_name $f)
  if [ -n "$h" ]; then
    head=$(curl -sI -A curl "$U/$h")
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' $f "$U/$h" "$(stat -c %s "$l")" \
      "$(grep -i '^content-length:' <<< "$head" | tr -d '\r' | cut -d' ' -f2)" "$(etag "$l")" \
      "$(grep -i '^etag:' <<< "$head" | tr -d '\r"' | cut -d' ' -f2)" "$(sha256sum < "$l.idx" | cut -d' ' -f1)" \
      "$(curl -s -A curl "$U/$h.idx" | sha256sum | cut -d' ' -f1)" "$(nice -n 10 sha256sum < "$l" | cut -d' ' -f1)"
  else
    printf '%s\t%s\t%s\t.\t.\t.\t%s\t.\t%s\n' $f 'not hosted' "$(stat -c %s "$l")" "$(sha256sum < "$l.idx" | cut -d' ' -f1)" \
      "$(nice -n 10 sha256sum < "$l" | cut -d' ' -f1)"
  fi >> "$O/identity.tsv"
done
for f in grch38 chm13; do
  cap 1G "$O/verify7.$f.time" python3 -I "$S/verify7.py" "$(local_file $f)" > "$O/verify7.$f.json" 2> "$O/verify7.$f.err" &
done
for f in chr6-sequences chr20-sequences pggbY; do
  cap 1G "$O/verify7.$f.time" python3 -I "$S/verify7.py" "$(local_file $f)" > "$O/verify7.$f.json" 2> "$O/verify7.$f.err"
  cap 48G "$O/spec8.$f.time" python3 -I "$S/spec8.py" "$(local_file $f)" > "$O/spec8.$f.txt" 2> "$O/spec8.$f.err"
done
wait
touch "$O/done"
