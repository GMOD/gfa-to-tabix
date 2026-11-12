#!/bin/bash
# hapBp with the real writer on HPRC v2.1 Minigraph-Cactus chr22: the build,
# its bytes against the format 8 file written before the column, and the
# file checkers that read a whole chromosome
# Usage: ada-chr22.sh <fresh directory holding src>
D=$1
S=$D/src
B=$HOME/work/blocks
cap() { "$B/genome-accept/cap.sh" "$@"; }
mkdir -p "$D/chr22"
cd "$D/chr22" || exit 2
uptime
echo "=== build"
cap 8G "$S/target/release/gfa-to-tabix" "$HOME/work/arb-format-opus/in/mc22.gfa" --walks --refs GRCh38 -o "$D/chr22/hapbp" 2>&1 | tail -3 | cut -c1-300
ls -l hapbp.GRCh38.walks.gz "$B/chr22/f8.GRCh38.walks.gz"
echo "=== bytes"
cap 8G python3 -I "$S/docs/walks-container/hapbp/scripts/column-bytes.py" "$B/chr22/f8.GRCh38.walks.gz" hapbp.GRCh38.walks.gz
echo "=== exit $? : column-bytes"
echo "=== verify7"
cap 8G python3 -I "$S/docs/departures/scripts/verify7.py" hapbp.GRCh38.walks.gz | tail -2 | cut -c1-400
echo "=== exit ${PIPESTATUS[0]} : verify7"
echo "=== expand7"
cap 16G python3 -I "$S/docs/departures/scripts/expand7.py" hapbp.GRCh38.walks.gz | tail -3
echo "=== exit ${PIPESTATUS[0]} : expand7"
echo "=== against-format7"
cap 16G python3 -I "$S/docs/walks-container/abridged/against-format7.py" hapbp.GRCh38.walks.gz "$B/chr22/old.GRCh38.walks.gz" | tail -4 | cut -c1-400
echo "=== exit ${PIPESTATUS[0]} : against-format7"
echo "=== spec8"
cap 48G python3 -I "$S/docs/departures/scripts/spec8.py" hapbp.GRCh38.walks.gz > spec8.txt 2>&1
echo "=== exit $? : spec8"
grep -n 'hapBp\|leading or trailing\|whole abridged\|== disagreed\|== agreed\|abridged rows\|abridged tiles' spec8.txt | cut -c1-200
tail -4 spec8.txt | cut -c1-300
echo "=== claims7"
cap 48G python3 -I "$S/docs/departures/scripts/claims7.py" hapbp.GRCh38.walks.gz > claims7.txt 2>&1
echo "=== exit $? : claims7"
grep -P '^[1-9][0-9]*\t|\t(A9|A1[0-3]) |^#|Traceback|Error|Killed' claims7.txt | cut -c1-200
echo "=== chr22 done"
