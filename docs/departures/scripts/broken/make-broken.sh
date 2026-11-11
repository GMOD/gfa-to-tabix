#!/usr/bin/env bash
# Writes the broken walk files of the blocks unit, and rewrites the six
# abridged ones from files that hold blocks units, with broken/corrupt.py.
# Usage: make-broken.sh <repo> <scratch dir>
set -eu
REPO=$1
W=$2
BIN=$REPO/target/debug/gfa-to-tabix
BROKEN=$REPO/docs/departures/scripts/broken
DATA=$REPO/tests/data
mkdir -p "$W"
"$BIN" "$BROKEN/blocks.gfa" --walks --refs R --tile 36 --abridge-bytes 1 -o "$W/b" > /dev/null 2>&1
"$BIN" "$DATA/walks-two-refs.gfa" --walks --refs GRCh38 --tile 1000 --abridge-steps 1 -o "$W/t2" > /dev/null 2>&1
"$BIN" "$DATA/walks-contig-ends.gfa" --walks --refs R --tile 10 --abridge-bytes 1 -o "$W/ce" > /dev/null 2>&1
"$BIN" "$DATA/walks-contig-ends.gfa" --walks --refs R --tile 10 --abridge-steps 1 -o "$W/cs" > /dev/null 2>&1
B=$W/b.R.walks.gz
T2=$W/t2.GRCh38.walks.gz
CE=$W/ce.R.walks.gz
CS=$W/cs.R.walks.gz
corrupt() {
  local name=$1 base=$2
  python3 -I "$BROKEN/corrupt.py" "$base" "$BROKEN/$name.walks.gz" "${@:3}"
}
G=GRCh38#0#chr

corrupt abridged-bp "$CS" $'abridged\tL#1#c\t0\t30\t0\t5\t12\t' $'abridged\tL#1#c\t0\t30\t0\t5\t13\t'
corrupt abridged-end "$CS" $'R#0#c\t12\t24\tabridged\tL#1#c\t0\t30\t0\t5\t12\t6\t8\t0' $'R#0#c\t12\t18\tabridged\tL#1#c\t0\t30\t0\t5\t6\t6\t6\t0'
corrupt abridged-hapoffset "$CS" $'abridged\tL#1#c\t0\t30\t' $'abridged\tL#1#c\t0\t31\t'
corrupt abridged-nsteps "$CS" $'abridged\tL#1#c\t0\t30\t0\t5\t' $'abridged\tL#1#c\t0\t30\t0\t7\t'
corrupt abridged-start "$CS" $'R#0#c\t12\t24\tabridged\tL#1#c\t0\t30\t0\t5\t12\t6\t8\t0' $'R#0#c\t18\t24\tabridged\tL#1#c\t0\t36\t0\t5\t6\t8\t8\t0'
corrupt detail-interior-flipped "$CE" $'route\t.\t22,2,2\t-20' $'route\t.\t22,3,2\t-20'

corrupt blocks-own "$B" '24+12:10' '24+12:11'
corrupt blocks-strand "$B" '0-12,24+12:10' '-12+12,12+12:10'
corrupt blocks-moved "$B" '0-12,24+12:10' '6-12,18+12:10'
corrupt blocks-unmerged "$B" '24+12:10' '24+6:10,0+6'
corrupt blocks-first "$B" '0+12,0-12,' '12-12,12-12,'
corrupt blocks-last "$B" '-24+6' '-18-6'
corrupt blocks-own-zero "$B" '0+12,0-12,' '0+12,0-12:0,'

H=$G$'\t0\t30\tblocks\tH#1#h\t100\t0\t0+18,0+12:3\n'
D=$G$'\t0\t30\tblocks\tD#1#d\t0\t0\t0+24,-24+30\n'
corrupt blocks-merged "$T2" '0+6,6+18:6' '0+30'
corrupt blocks-row-dropped "$T2" "$D" ''
corrupt blocks-rows-swapped "$T2" "$H$D" "$D$H"
corrupt blocks-row-twice "$T2" "$H" "$H$H"
corrupt blocks-row-span "$T2" $'\t0\t30\tblocks\tH#1#h' $'\t0\t24\tblocks\tH#1#h'

U10=$'#unit\tR#0#c\t12\t24\tblocks\t10\n'
L10=$'R#0#c\t12\t24\tblocks\tL#1#c\t0\t0\t12+12\n'
M10=$'R#0#c\t12\t18\tblocks\tM#1#c\t0\t1\t12+6\n'
D100=$'#unit\tR#0#c\t12\t24\tdetail\t10:0\n'
U20=$'#unit\tR#0#c\t24\t30\tblocks\t20\n'
L20=$'R#0#c\t24\t30\tblocks\tL#1#c\t0\t1\t24+6\n'
M0=$'R#0#c\t0\t12\tblocks\tM#1#c\t0\t0\t0+12\n'
corrupt blocks-unit-wide "$CE" "$U10" $'#unit\tR#0#c\t12\t30\tblocks\t10\n'
corrupt blocks-unit-dropped "$CE" "$U10$L10$M10" ''
corrupt blocks-unit-early "$CE" "$U10$L10$M10" '' "$D100" "$U10$L10$M10$D100"
corrupt blocks-unit-empty "$CE" "$L20" ''
corrupt blocks-row-misfiled "$CE" "$M10" '' "$U20" $'#unit\tR#0#c\t12\t30\tblocks\t20\n'"$M10"
corrupt blocks-foreign-row "$CE" "$M0" "$M0"$'R#0#c\t0\t12\twalk\tM#1#c\t0\t0\t0\t2\t2\t.\n'
corrupt blocks-unit-stray "$CS" "$M10" "$M10"$'#unit\tR#0#c\t0\t12\tblocks\t0\n'"$M0"
