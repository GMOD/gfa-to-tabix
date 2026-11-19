#!/usr/bin/env bash
# Writes every broken walk file of cases.tsv: each a file the writer at
# target/debug wrote, corrupted by broken/corrupt.py, or, for hole-inside
# and hole-trailing, the text an earlier writer wrote, packed by it.
# Usage: make-broken.sh <repo> <scratch dir>
set -eu
REPO=$1
W=$2
BIN=$REPO/target/debug/gfa-to-tabix
BROKEN=$REPO/docs/departures/scripts/broken
DATA=$REPO/tests/data
HAPBP=$REPO/docs/walks-container/hapbp
mkdir -p "$W"
build() {
  local out=$1 gfa=$2 ref=$3
  "$BIN" "$gfa" --walks --refs "$ref" "${@:4}" -o "$W/$out" > /dev/null 2>&1
}
build t0 "$DATA/walks-two-refs.gfa" GRCh38 --tile 10 --stay 0
build t311 "$DATA/walks-two-refs.gfa" GRCh38 --tile 10
build rr "$DATA/walks-records.gfa" R --tile 10
build rp "$DATA/walks-repeat.gfa" R --tile 10
build sq "$DATA/walks-sequences.gfa" R --tile 10 --sequences
build b "$BROKEN/blocks.gfa" R --tile 36 --abridge-bytes 1
build t2 "$DATA/walks-two-refs.gfa" GRCh38 --tile 1000 --abridge-steps 1
build t10 "$DATA/walks-two-refs.gfa" GRCh38 --tile 10 --abridge-bytes 1
build ce "$DATA/walks-contig-ends.gfa" R --tile 10 --abridge-bytes 1
build cs "$DATA/walks-contig-ends.gfa" R --tile 10 --abridge-steps 1
build rc "$DATA/walks-records.gfa" R --tile 1000 --abridge-steps 1
build tp "$HAPBP/two-pieces.gfa" R --tile 12 --stay 0 --abridge-bytes 1
T0=$W/t0.GRCh38.walks.gz
T311=$W/t311.GRCh38.walks.gz
RR=$W/rr.R.walks.gz
RP=$W/rp.R.walks.gz
SQ=$W/sq.R.walks.gz
B=$W/b.R.walks.gz
T2=$W/t2.GRCh38.walks.gz
T10=$W/t10.GRCh38.walks.gz
CE=$W/ce.R.walks.gz
CS=$W/cs.R.walks.gz
RC=$W/rc.R.walks.gz
TP=$W/tp.R.walks.gz
corrupt() {
  local name=$1 base=$2
  python3 -I "$BROKEN/corrupt.py" "$base" "$BROKEN/$name.walks.gz" "${@:3}"
}
# packs a walk file's text, given with a space for each tab and no tables
pack() {
  tr ' ' '\t' | gzip > "$W/$1.txt.gz"
  corrupt "$1" "$W/$1.txt.gz"
}
G=GRCh38#0#chr

# rows, units and header lines of files with no abridged tile
I6=$G$'\t0\t18\tdeparture\tI#1#i\t6\t0\t0\t6\t+\t1\t18\t-\t1\t.\n'
Q6=$G$'\t0\t18\tdeparture\tQ#0#chr\t6\t6\t0\t6\t+\t1\t12\t+\t1\t0\n'
D24=$G$'\t0\t24\tdeparture\tD#1#d\t24\t0\t0\t24\t+\t1\t0\t+\t1\t.\n'
I18=$G$'\t6\t24\tdeparture\tI#1#i\t18\t0\t0\t6\t-\t1\t18\t+\t1\t.\n'
H118=$G$'\t12\t24\tdeparture\tH#1#h\t118\t3\t0\t18\t+\t1\t18\t+\t1\t10\n'
WD=$G$'\t0\t12\twalk\tD#1#d\t0\t24\t2\t2\t2\t.\n'
WH=$G$'\t0\t12\twalk\tH#1#h\t100\t100\t0\t2\t2\t.\n'
corrupt block-misaligned "$T0" $'#unit\t'$G$'\t10\t20\tdepartures' $'#unit\t'$G$'\t10\t19\tdepartures'
corrupt empty-block "$T0" --append $'#unit\t'$G$'\t30\t40\tdepartures\t.\n'
corrupt format-7 "$T0" 'format:i:8' 'format:i:7'
corrupt g1-walk-order "$T0" "$WD$WH" "$WH$WD"
corrupt hap-dup "$T0" $'#haplotype\tD#1\n' $'#haplotype\tD#1\n#haplotype\tD#1\n'
corrupt hap-missing "$T0" $'#haplotype\tD#1\n' ''
corrupt hapstart-wrong-G "$RR" --all $'G#1#g\t12\t18\t18\t' $'G#1#g\t13\t18\t18\t'
corrupt hdr-len-idx-only "$T0" --header 100
corrupt header-len-100 "$T0" $'#reference\tGRCh38' $'reference\tGRCh38' --header 100
corrupt header-len-right-ctl "$T0" $'#reference\tGRCh38' $'reference\tGRCh38'
corrupt hole-bogus "$T0" $'#reference\tGRCh38\n' $'#reference\tGRCh38\n#hole\t'$G$'\t3\t5\n'
corrupt interior-flipped "$T311" $'\t0\t12\troute\t.\t13\t-9' $'\t0\t12\troute\t.\t12\t-9'
corrupt last-piece-dropped "$T0" $G$'\t12\t24\twalk\tD#1#d\t0\t36\t3\t2\t6\t.\n' ''
corrupt missing-understated "$RR" --all $'H#1#h\t12\t28\t22\t' $'H#1#h\t12\t28\t0\t'
corrupt missing-understated-G "$RR" --all $'G#1#g\t12\t18\t18\t' $'G#1#g\t12\t18\t5\t'
corrupt nodes-extra "$T0" $'\t0\t12\tnodes\t6\t6' $'\t0\t12\tnodes\t5,1\t3,6'
corrupt ownbp-overstated-G "$RR" --all $'G#1#g\t12\t18\t18\t' $'G#1#g\t12\t30\t18\t'
corrupt owntiles-wrong "$T0" --all $'Q#0#chr\t6\t6\t0\t6\t+\t1\t12\t+\t1\t0\n' $'Q#0#chr\t6\t6\t0\t6\t+\t1\t12\t+\t1\t10\n'
corrupt passes-second-row "$RP" $'\tref\tR#0#chr\t0\t12\t1\t2\t6,-2\t6,6\t2,2' $'\tref\tR#0#chr\t0\t12\t1\t2\t6,-2\t6,6\t2,3'
corrupt point "$T0" $'\t0\t10\tdepartures\t.\n'"$I6" $'\t0\t10\tdepartures\t.\n'"$I6"$G$'\t5\t5\tdeparture\tI#1#i\t6\t0\t0\t6\t+\t1\t18\t-\t1\t.\n'
corrupt record-bogus-path "$T0" --all "$Q6" "$Q6"$G$'\t0\t18\tdeparture\tZ#1#z\t6\t6\t0\t6\t+\t1\t12\t+\t1\t.\n'
corrupt record-dropped "$T0" --all "$Q6" ''
corrupt entry-dropped "$T0" --drop-entry $'#entry\t'$G$'\t10\t20\tdepartures\t.\t'
corrupt line-before-walks "$T0" --prepend-header $'#future\tx'
corrupt entry-start-not-integer "$T0" --table $'#entry\t'$G$'\t10\t20\tdepartures' $'#entry\t'$G$'\t1e1\t20\tdepartures'
corrupt record-leavepasses "$T0" --all $'Q#0#chr\t6\t6\t0\t6\t+\t1\t12' $'Q#0#chr\t6\t6\t0\t6\t+\t2\t12'
corrupt record-within-piece "$T0" "$I18"$'#unit\t'$G$'\t24\t30\ttile' "$I18$H118"$'#unit\t'$G$'\t24\t30\ttile' \
  $'\t20\t30\tdepartures\t.\n'"$D24$I18" $'\t20\t30\tdepartures\t.\n'"$D24$I18$H118"
corrupt ref-lengths "$T0" $'\t12\t24\tref\t'$G$'\t0\t12\t1\t2\t6,2\t6,6' $'\t12\t24\tref\t'$G$'\t0\t12\t1\t2\t6,2\t5,7'
corrupt ref-strand-flipped "$T311" $'\t0\t24\t2\t1\t10\t6\t.' $'\t0\t24\t2\t1\t11\t6\t.' \
  $'D#1#d\t0\t48\t4\t1\t10\t.' $'D#1#d\t0\t48\t4\t1\t11\t.' $'H#1#h\t100\t127\t2\t1\t10\t.' $'H#1#h\t100\t127\t2\t1\t11\t.' \
  $'I#1#i\t0\t24\t4\t1\t10\t.' $'I#1#i\t0\t24\t4\t1\t11\t.' $'Q#0#chr\t0\t24\t2\t1\t10\t.' $'Q#0#chr\t0\t24\t2\t1\t11\t.'
corrupt reference-wrong "$T0" $'#reference\tGRCh38' $'#reference\tCHM13'
corrupt sqbad "$SQ" $'R#0#chr1\t0\t8\tref\tR#0#chr1\t0\t0\t0\t2\t18,2\t4,4\t.\tSQ:Z:ACGAAACT' $'R#0#chr1\t0\t8\tref\tR#0#chr1\t0\t0\t0\t2\t18,2\t4,4\t.\tSQ:Z:CCGAAACT'
corrupt seq-piece-number "$SQ" $'R#0#chr10\t0\t8\twalk\tH#1#h\t0\t16\t2\t2\t10\t.' $'R#0#chr10\t0\t8\twalk\tH#1#h\t0\t16\t20\t2\t10\t.'
corrupt seq-piece-offset "$SQ" $'R#0#chr10\t0\t8\twalk\tH#1#h\t0\t16\t2\t2\t10\t.' $'R#0#chr10\t0\t8\twalk\tH#1#h\t0\t17\t2\t2\t10\t.'
corrupt seq-bases-missing "$SQ" $'R#0#chr10\t0\t8\tref\tR#0#chr10\t0\t0\t0\t2\t10,2\t4,4\t.\tSQ:Z:TAACATAC' $'R#0#chr10\t0\t8\tref\tR#0#chr10\t0\t0\t0\t2\t10,2\t4,4\t.'
corrupt tag-malformed "$T0" $'\t2,2\t6,6\t.\n' $'\t2,2\t6,6\t.\tzz\n'
corrupt table-S-wrong "$T0" --table $'\t0\t30\ttable\t.\n' $'\t0\t40\ttable\t.\n'
corrupt table-named "$T0" --table $'\ttable\t.\n' $'\ttable\tx\n'
corrupt u2-leading-zero "$T0" $'\t12\t24\ttile\t10\n' $'\t12\t24\ttile\t010\n'
corrupt walk-span-wrong "$T0" $'\t12\t24\twalk\tD#1#d\t0\t12\t' $'\t12\t18\twalk\tD#1#d\t0\t12\t'
corrupt walks-differ-ctl "$T0" 'stay:i:0' 'stay:i:5' --idx 'stay:i:5' 'stay:i:0'
corrupt walks-differ-len100 "$T0" 'stay:i:0' 'stay:i:5' --idx 'stay:i:5' 'stay:i:0' --header 100
corrupt wide "$T0" $'\t0\t12\ttile\t0\n' $'\t0\t15\ttile\t0\n' $'\t0\t12\tref\t' $'\t0\t15\tref\t' $'\t0\t12\tnodes\t' $'\t0\t15\tnodes\t' \
  $'\t0\t12\troute\t' $'\t0\t15\troute\t' $'\t0\t12\twalk\tD#1#d\t0\t0\t' $'\t0\t15\twalk\tD#1#d\t0\t0\t' \
  $'\t0\t12\twalk\tD#1#d\t0\t24\t' $'\t0\t15\twalk\tD#1#d\t0\t24\t' $'\t0\t12\twalk\tH#1#h\t' $'\t0\t15\twalk\tH#1#h\t' \
  $'\t6\t12\twalk\tI#1#i\t' $'\t6\t15\twalk\tI#1#i\t'

# what a writer since repaired wrote for broken/hole-inside.gfa and
# broken/hole-trailing.gfa at --tile 4, in format 8's header
pack hole-inside << 'EOF'
#walks format:i:8 tile:i:4 revisited:i:0 stay:i:311 abridge:i:1000000 abridgebytes:i:3000000 graph:Z:b99446c7ac2291d3 leftout:i:0
#reference R
#haplotype H#1
#hole R#0#chr 10 20
#unit R#0#chr 0 10 tile 0
R#0#chr 0 10 ref R#0#chr 0 0 0 1 2 10 .
R#0#chr 0 10 walk H#1#h 0 0 0 1 2 .
#unit R#0#chr 0 4 departures .
R#0#chr 0 16 departure H#1#h 10 0 0 10 + 1 15 + 1 .
#unit R#0#chr 4 8 departures .
R#0#chr 0 16 departure H#1#h 10 0 0 10 + 1 15 + 1 .
#unit R#0#chr 8 12 departures .
R#0#chr 0 16 departure H#1#h 10 0 0 10 + 1 15 + 1 .
#unit R#0#chr 15 16 tile 12
R#0#chr 15 16 ref R#0#chr 15 15 0 1 4 0 .
R#0#chr 15 15 walk H#1#h 0 10 1 1 4 .
#unit R#0#chr 12 16 departures .
R#0#chr 0 16 departure H#1#h 10 0 0 10 + 1 15 + 1 .
R#0#chr 15 25 departure H#1#h 10 0 0 15 + 1 20 + 1 .
#unit R#0#chr 16 20 departures .
R#0#chr 15 25 departure H#1#h 10 0 0 15 + 1 20 + 1 .
#unit R#0#chr 20 25 tile 20
R#0#chr 20 25 ref R#0#chr 20 20 0 1 6 5 .
R#0#chr 20 25 walk H#1#h 0 10 2 1 6 .
#unit R#0#chr 20 24 departures .
R#0#chr 15 25 departure H#1#h 10 0 0 15 + 1 20 + 1 .
#unit R#0#chr 24 28 departures .
R#0#chr 15 25 departure H#1#h 10 0 0 15 + 1 20 + 1 .
EOF
pack hole-trailing << 'EOF'
#walks format:i:8 tile:i:4 revisited:i:0 stay:i:311 abridge:i:1000000 abridgebytes:i:3000000 graph:Z:62d264cc33d360d1 leftout:i:0
#reference R
#haplotype H#1
#unit R#0#chr 0 10 tile 0
R#0#chr 0 10 ref R#0#chr 0 0 0 1 2 10 .
R#0#chr 0 10 walk H#1#h 0 0 0 1 2 .
#unit R#0#chr 0 4 departures .
R#0#chr 0 20 departure H#1#h 10 0 0 10 + 1 20 + 1 .
#unit R#0#chr 4 8 departures .
R#0#chr 0 20 departure H#1#h 10 0 0 10 + 1 20 + 1 .
#unit R#0#chr 8 12 departures .
R#0#chr 0 20 departure H#1#h 10 0 0 10 + 1 20 + 1 .
#unit R#0#chr 12 16 departures .
R#0#chr 0 20 departure H#1#h 10 0 0 10 + 1 20 + 1 .
#unit R#0#chr 16 20 departures .
R#0#chr 0 20 departure H#1#h 10 0 0 10 + 1 20 + 1 .
#unit R#0#chr 19 20 tile 20
R#0#chr 19 20 ref R#0#chr 20 20 0 1 4 0 .
R#0#chr 20 20 walk H#1#h 0 10 1 1 4 .
EOF

# abridged rows and detail units
AL=$'R#0#c\t12\t24\tabridged\tL#1#c\t0\t0\t0\t5\t42\t0\n'
AM=$'R#0#c\t12\t18\tabridged\tM#1#c\t0\t12\t1\t4\t36\t1\n'
corrupt abridged-detail "$CS" "$AL" $'R#0#c\t12\t24\tabridged\tL#1#c\t0\t0\t0\t5\t42\t1\n'
corrupt abridged-hapoffset "$CS" "$AL" $'R#0#c\t12\t24\tabridged\tL#1#c\t0\t1\t0\t5\t42\t0\n'
corrupt abridged-hapoffset-later "$CS" "$AM" $'R#0#c\t12\t18\tabridged\tM#1#c\t0\t13\t1\t4\t36\t1\n'
corrupt abridged-nsteps "$CS" "$AL" $'R#0#c\t12\t24\tabridged\tL#1#c\t0\t0\t0\t7\t42\t0\n'
corrupt abridged-span "$CS" "$AL" $'R#0#c\t12\t18\tabridged\tL#1#c\t0\t0\t0\t5\t42\t0\n'
corrupt abridged-thirteen-columns "$CS" "$AL" $'R#0#c\t12\t24\tabridged\tL#1#c\t0\t30\t0\t5\t12\t6\t8\t0\n'
corrupt abridged-ten-columns "$CS" "$AL" $'R#0#c\t12\t24\tabridged\tL#1#c\t0\t0\t0\t5\t0\n'

# hapBp, and the attach rule it serves
AH=$'R#0#c\t0\t36\tabridged\tH#1#c\t0\t0\t0\t11\t'
corrupt hapbp-format7 "$B" "${AH}109" "${AH}52"
corrupt hapbp-span "$B" "${AH}109" "${AH}36"
corrupt hapbp-off-by-one "$B" "${AH}109" "${AH}110"
corrupt hapbp-zero "$B" "${AH}109" "${AH}0"
corrupt hapbp-next-piece "$CS" "$AL" $'R#0#c\t12\t24\tabridged\tL#1#c\t0\t0\t0\t5\t6\t0\n'
corrupt hapbp-to-last-on-r "$TP" $'abridged\tH#1#c\t0\t0\t0\t2\t16\t0' $'abridged\tH#1#c\t0\t0\t0\t2\t6\t0'
corrupt attach-overlap-mid-run "$T2" $'#unit\t'$G$'\t0\t30\tdetail\t0:0\n' \
  $'#unit\t'$G$'\t0\t1000\tdepartures\t.\n'$G$'\t12\t24\tdeparture\tH#1#h\t118\t3\t0\t18\t+\t1\t18\t+\t1\t0\n#unit\t'$G$'\t0\t30\tdetail\t0:0\n'
corrupt attach-overlap-short "$TP" --all $'departure\tH#1#c\t6\t31\t14\t' $'departure\tH#1#c\t7\t30\t14\t'
corrupt detail-interior-flipped "$CE" $'route\t.\t22,2,2\t-20' $'route\t.\t22,3,2\t-20'

# blocks rows and units
L=$'\t7,0+12,0-12,10,24+12,-24+6,50\n'
corrupt blocks-own "$B" ',10,24+12' ',11,24+12'
corrupt blocks-strand "$B" '0-12,10,24+12' '-12+12,10,12+12'
corrupt blocks-moved "$B" '0-12,10,24+12' '6-12,10,18+12'
corrupt blocks-unmerged "$B" '24+12' '24+6,0+6'
corrupt blocks-first "$B" '0+12,0-12,' '12-12,12-12,'
corrupt blocks-last "$B" '-24+6' '-18-6'
corrupt blocks-minus-zero "$B" '0-12' '-0-12'
corrupt blocks-trailing-dropped "$B" "$L" $'\t7,0+12,0-12,10,24+12,-24+6\n'
corrupt blocks-trailing-off "$B" "$L" $'\t7,0+12,0-12,10,24+12,-24+6,51\n'
corrupt blocks-leading-off "$B" "$L" $'\t8,0+12,0-12,10,24+12,-24+6,50\n'
corrupt blocks-ends-swapped "$B" "$L" $'\t50,0+12,0-12,10,24+12,-24+6,7\n'
corrupt blocks-run-leading-zero "$B" "$L" $'\t07,0+12,0-12,10,24+12,-24+6,50\n'
corrupt blocks-run-zero "$B" "$L" $'\t7,0+12,0,0-12,10,24+12,-24+6,50\n'
corrupt blocks-runs-adjacent "$B" "$L" $'\t7,0+12,0-12,4,6,24+12,-24+6,50\n'
corrupt blocks-ten-columns "$B" "$L" $'\t7\t50\t0+12,0-12,24+12:10,-24+6\n'

H=$G$'\t0\t30\tblocks\tH#1#h\t100\t0\t0+18,3,0+12\n'
D=$G$'\t0\t30\tblocks\tD#1#d\t0\t0\t0+24,-24+30\n'
corrupt blocks-merged "$T2" '0+6,6,6+18' '0+30'
corrupt blocks-row-dropped "$T2" "$D" ''
corrupt blocks-rows-swapped "$T2" "$H$D" "$D$H"
corrupt blocks-row-twice "$T2" "$H" "$H$H"
corrupt blocks-row-span "$T2" $'\t0\t30\tblocks\tH#1#h' $'\t0\t24\tblocks\tH#1#h'
corrupt blocks-trailing-dropped-mid "$T10" $'blocks\tQ#0#chr\t0\t0\t0+6,6\n' $'blocks\tQ#0#chr\t0\t0\t0+6\n'
corrupt blocks-trailing-over-record "$RC" $'blocks\tG#1#g\t0\t0\t0+12\n' $'blocks\tG#1#g\t0\t0\t0+12,19\n'

U10=$'#unit\tR#0#c\t12\t24\tblocks\t10\n'
L10=$'R#0#c\t12\t24\tblocks\tL#1#c\t0\t0\t30,12+12\n'
M10=$'R#0#c\t12\t18\tblocks\tM#1#c\t0\t1\t12+6,30\n'
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
corrupt blocks-leading-later "$CE" "$L20" $'R#0#c\t24\t30\tblocks\tL#1#c\t0\t1\t1,24+6\n'

# the files an independent reviewer of format 8 broke by hand, from graphs of
# its own, each the writer's file with a few rows changed
build tie100 "$BROKEN/tie.gfa" R --tile 100
build tie100a "$BROKEN/tie.gfa" R --tile 100 --abridge-bytes 1
build tie10 "$BROKEN/tie.gfa" R --tile 10
build follow100 "$BROKEN/follow.gfa" R --tile 100
build follow100a "$BROKEN/follow.gfa" R --tile 100 --abridge-bytes 1
build follow100s "$BROKEN/follow.gfa" R --tile 100 --sequences
build follow100sa "$BROKEN/follow.gfa" R --tile 100 --sequences --abridge-bytes 1
build repeat100 "$BROKEN/repeat.gfa" R --tile 100
build refgap100 "$BROKEN/ref-gap.gfa" R --tile 100
build endsoff10 "$BROKEN/ends-off.gfa" R --tile 10
build jumps100 "$BROKEN/jumps.gfa" R --tile 100
build far10 "$BROKEN/far.gfa" R --tile 10
build shared10 "$BROKEN/shared.gfa" R --tile 10
for base in tie100 tie100a tie10 follow100 follow100a follow100s follow100sa repeat100 refgap100 endsoff10 jumps100 far10 shared10; do
  declare "${base^^}=$W/$base.R.walks.gz"
done
corrupt placement-other-copy "$TIE100" --all $'R#0#c\t0\t18\twalk\tB#1#c\t0\t0\t0\t2\t3\t6@0' $'R#0#c\t12\t30\twalk\tB#1#c\t0\t0\t0\t2\t3\t6'
corrupt placement-other-copy-abridged "$TIE100A" --all $'R#0#c\t0\t18\twalk\tB#1#c\t0\t0\t0\t2\t3\t0@0' $'R#0#c\t12\t30\twalk\tB#1#c\t0\t0\t0\t2\t3\t0' --all $'R#0#c\t0\t18\troute\t3\t.\t3' $'R#0#c\t12\t30\troute\t3\t.\t3' --all $'#unit\tR#0#c\t0\t18\tdetail\t0:4' $'#unit\tR#0#c\t12\t30\tdetail\t0:4' --all $'R#0#c\t0\t18\tabridged\tB#1#c' $'R#0#c\t12\t30\tabridged\tB#1#c' --all $'R#0#c\t0\t18\tblocks\tB#1#c\t0\t0\t18-6,-6-6' $'R#0#c\t12\t30\tblocks\tB#1#c\t0\t0\t18-6,18-6'
corrupt on-reference-as-interior "$FOLLOW100" --all $'R#0#c\t0\t36\tnodes\t11,2,1\t10,20,30' $'R#0#c\t0\t36\tnodes\t3,8,2,1\t6,10,20,30' --all $'R#0#c\t0\t36\troute\t4\t22,2\t-18' $'R#0#c\t0\t36\troute\t4\t2\t2\nR#0#c\t0\t36\troute\t-4\t22,2\t-18' --all $'R#0#c\t0\t36\twalk\tA#1#c\t0\t0\t0\t6\t2\t.' $'R#0#c\t0\t36\twalk\tA#1#c\t0\t0\t0\t6\t2\t0' --all $'R#0#c\t0\t36\twalk\tB#1#c\t0\t0\t0\t7\t2\t0,3' $'R#0#c\t0\t36\twalk\tB#1#c\t0\t0\t0\t7\t2\t2,3'
corrupt on-reference-as-interior-abridged "$FOLLOW100A" --all $'#unit\tR#0#c\t0\t36\tdetail\t0:1\nR#0#c\t0\t36\twalk\tA#1#c\t0\t0\t0\t6\t2\t.' $'#unit\tR#0#c\t0\t36\tdetail\t0:1\nR#0#c\t0\t36\tnodes\t3\t6\nR#0#c\t0\t36\troute\t4\t2\t2\nR#0#c\t0\t36\twalk\tA#1#c\t0\t0\t0\t6\t2\t0' --all $'R#0#c\t0\t36\tblocks\tA#1#c\t0\t0\t0+36' $'R#0#c\t0\t36\tblocks\tA#1#c\t0\t0\t0+12,6,6+18'
corrupt interior-lengths-traded "$FOLLOW100" --all $'R#0#c\t0\t36\tnodes\t11,2,1\t10,20,30' $'R#0#c\t0\t36\tnodes\t11,2,1\t10,25,25'
corrupt interior-lengths-traded-abridged "$FOLLOW100A" --all $'R#0#c\t0\t36\tnodes\t11,2,1\t10,20,30' $'R#0#c\t0\t36\tnodes\t11,2,1\t10,25,25'
corrupt line-end-longer "$FOLLOW100" --all $'R#0#c\t0\t36\tnodes\t11,2,1\t10,20,30' $'R#0#c\t0\t36\tnodes\t11,2,1\t17,20,30'
corrupt line-end-longer-abridged "$FOLLOW100A" --all $'R#0#c\t0\t36\tnodes\t11,2,1\t10,20,30' $'R#0#c\t0\t36\tnodes\t11,2,1\t17,20,30' --all $'R#0#c\t0\t36\tblocks\tB#1#c\t0\t0\t0+12,50,12+12,10' $'R#0#c\t0\t36\tblocks\tB#1#c\t0\t0\t0+12,50,12+12,17'
corrupt nodes-bases "$FOLLOW100S" --all $'10,20,30\tSQ:Z:ACGTACGTAC' $'10,20,30\tSQ:Z:TCGTACGTAC'
corrupt nodes-bases-abridged "$FOLLOW100SA" --all $'10,20,30\tSQ:Z:ACGTACGTAC' $'10,20,30\tSQ:Z:TCGTACGTAC'
corrupt passes-understated "$REPEAT100" --all $'1,3,3,1,3,3,1,3,3,1' $'1,2,2,1,2,2,1,2,2,1'
corrupt passes-once-as-twice "$REPEAT100" --all $'1,3,3,1,3,3,1,3,3,1' $'1,3,3,2,3,3,1,3,3,1' $'revisited:i:2' $'revisited:i:3'
corrupt passes-twice-as-once "$RP" $'\t2,2\t6,6\t1,2' $'\t2,2\t6,6\t.' $'\t6,-2\t6,6\t2,2' $'\t6,-2\t6,6\t2,1' $'revisited:i:2' $'revisited:i:1'
corrupt passes-once-per-sequence "$SHARED10" $'\t2,2\t5,5\t1,2' $'\t2,2\t5,5\t.' $'\t4,2\t5,5\t2,1' $'\t4,2\t5,5\t.' $'revisited:i:1' $'revisited:i:0'
corrupt other-tile-as-interior "$FAR10" $'\t6,2\t5,5\t.\n' $'\t6,2\t5,5\t.\nR#0#c2\t0\t10\tnodes\t5,1\t5,5\nR#0#c2\t0\t10\troute\t.\t13,-1\t-1\n' $'R#0#c2\t0\t10\twalk\tA#1#c\t0\t10\t1\t2\t6\t.' $'R#0#c2\t0\t10\twalk\tA#1#c\t0\t10\t1\t4\t6\t1' $'R#0#c2\t10\t20\twalk\tA#1#c\t0\t20\t2\t2\t10\t.\n' ''
corrupt other-sequence-as-interior "$FAR10" $'\t10,2\t5,5\t.\n' $'\t10,2\t5,5\t.\nR#0#c2\t10\t20\tnodes\t1,1\t5,5\nR#0#c2\t10\t20\troute\t.\t5,-1\t11\n' $'R#0#c2\t10\t20\twalk\tB#1#c\t0\t10\t1\t2\t10\t.' $'R#0#c2\t10\t20\twalk\tB#1#c\t0\t10\t1\t4\t10\t1' $'R#0#c1\t0\t10\twalk\tB#1#c\t0\t20\t2\t2\t2\t.\n' ''
corrupt other-sequence-as-interior-revisited "$SHARED10" $'\t2,2\t5,5\t1,2\n' $'\t2,2\t5,5\t1,2\nR#0#c1\t0\t10\tnodes\t3\t5\nR#0#c1\t0\t10\troute\t.\t7\t-1\n' $'R#0#c1\t0\t10\twalk\tA#1#c\t0\t0\t0\t2\t2\t.' $'R#0#c1\t0\t10\twalk\tA#1#c\t0\t0\t0\t3\t2\t1' $'R#0#c2\t5\t10\twalk\tA#1#c\t0\t10\t1\t1\t6\t.\n' ''
corrupt tag-twice "$FAR10" --tag zz:i:1 --tag zz:i:2
corrupt tile-missing "$FAR10" $'tile:i:10\t' ''
corrupt revisited-zero "$TIE100" $'revisited:i:1' $'revisited:i:0'
corrupt record-passes "$TIE10" --all $'R#0#c\t12\t30\tdeparture\tA#1#c\t6\t0\t0\t18\t+\t1\t24\t+\t2\t.' $'R#0#c\t12\t30\tdeparture\tA#1#c\t6\t0\t0\t18\t+\t2\t24\t+\t2\t.'
corrupt record-stretch-short "$TIE10" --all $'R#0#c\t0\t18\tdeparture\tB#1#c\t6\t0\t0\t12\t-\t1\t6\t-\t2\t.' $'R#0#c\t6\t18\tdeparture\tB#1#c\t6\t0\t0\t12\t-\t1\t6\t-\t2\t.'
corrupt ref-rows-swapped "$REFGAP100" --all $'R#0#c\t0\t48\tref\tR#0#c\t0\t0\t0\t3\t2,2,2\t6,6,6\t.\nR#0#c\t0\t48\tref\tR#0#c\t30\t30\t0\t3\t8,2,2\t6,6,6\t.' $'R#0#c\t0\t48\tref\tR#0#c\t30\t30\t0\t3\t8,2,2\t6,6,6\t.\nR#0#c\t0\t48\tref\tR#0#c\t0\t0\t0\t3\t2,2,2\t6,6,6\t.'
corrupt piece-walk-and-abridged "$FOLLOW100A" --all $'R#0#c\t0\t36\tabridged\tB#1#c\t0\t0\t0\t7\t84\t0' $'R#0#c\t0\t36\twalk\tA#1#c\t0\t0\t0\t6\t2\t.\nR#0#c\t0\t36\tabridged\tB#1#c\t0\t0\t0\t7\t84\t0'
corrupt default-copy-named "$TIE100" --all $'R#0#c\t12\t30\twalk\tA#1#c\t0\t0\t0\t2\t2\t0' $'R#0#c\t12\t30\twalk\tA#1#c\t0\t0\t0\t2\t2\t0@1'
corrupt costliest-not-first "$FOLLOW100A" --all $'R#0#c\t0\t36\tabridged\tB#1#c\t0\t0\t0\t7\t84\t0\nR#0#c\t0\t36\tabridged\tA#1#c\t0\t0\t0\t6\t36\t1' $'R#0#c\t0\t36\tabridged\tA#1#c\t0\t0\t0\t6\t36\t0\nR#0#c\t0\t36\tabridged\tB#1#c\t0\t0\t0\t7\t84\t1' --all $'#unit\tR#0#c\t0\t36\tdetail\t0:0' $'#unit\tR#0#c\t0\t36\tdetail\t0:9' --all $'#unit\tR#0#c\t0\t36\tdetail\t0:1' $'#unit\tR#0#c\t0\t36\tdetail\t0:0' --all $'#unit\tR#0#c\t0\t36\tdetail\t0:9' $'#unit\tR#0#c\t0\t36\tdetail\t0:1' --all $'R#0#c\t0\t36\tblocks\tB#1#c\t0\t0\t0+12,50,12+12,10\nR#0#c\t0\t36\tblocks\tA#1#c\t0\t0\t0+36' $'R#0#c\t0\t36\tblocks\tA#1#c\t0\t0\t0+36\nR#0#c\t0\t36\tblocks\tB#1#c\t0\t0\t0+12,50,12+12,10'
corrupt revisited-as-interior "$TIE100" --all $'R#0#c\t0\t30\troute\t2\t.\t2' $'R#0#c\t0\t30\tnodes\t2\t6\nR#0#c\t0\t30\troute\t2\t.\t2' --all $'R#0#c\t0\t30\troute\t1\t.\t3' $'R#0#c\t0\t30\troute\t1\t.\t3\nR#0#c\t0\t30\troute\t.\t-1\t-1' --all $'R#0#c\t12\t30\twalk\tA#1#c\t0\t0\t0\t2\t2\t0' $'R#0#c\t12\t18\twalk\tA#1#c\t0\t0\t0\t2\t2\t11'
corrupt node-two-lengths "$ENDSOFF10" --all $'R#0#c\t0\t12\tnodes\t11,1,1,1,1,1\t10,7,20,30,3,1' $'R#0#c\t0\t12\tnodes\t11,1,1,1,1,1\t10,9,20,30,3,1'
corrupt piece-split-at-jump "$JUMPS100" --all $'R#0#c\t0\t36\twalk\tC#1#c\t0\t0\t0\t4\t2\t4,5,-4' $'R#0#c\t0\t6\twalk\tC#1#c\t0\t0\t0\t1\t2\t.\nR#0#c\t0\t36\twalk\tC#1#c\t0\t6\t1\t3\t12\t9,-4'
corrupt missing-overstated "$ENDSOFF10" --all $'departure\tG#1#c\t31\t72\t39\t24' $'departure\tG#1#c\t31\t72\t60\t24'
corrupt nodes-bases-missing "$FOLLOW100SA" --all $'10,20,30\tSQ:Z:ACGTACGTACACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTAC' $'10,20,30'
corrupt revisited-count "$REPEAT100" $'revisited:i:2' $'revisited:i:7'
corrupt graph-other "$T311" $'graph:Z:7619ff637c3b074b' $'graph:Z:7619ff637c3b074c'
corrupt graph-uppercase "$T311" $'graph:Z:7619ff637c3b074b' $'graph:Z:7619FF637C3B074B'
corrupt leftout-other "$T311" $'leftout:i:1' $'leftout:i:0'
corrupt leftout-twice "$T311" $'leftout:i:1' $'leftout:i:1\tleftout:i:1'

# the forbidden variants of repack.py on a file with every kind of unit, as
# it writes them, tables and directory included
FORBIDDEN="tag-unit-tile tag-unit-table tag-entry dir-tag-seq-line dir-tag-header-line row-new-kind-in-tile
  row-new-kind-in-departures row-new-kind-in-detail row-new-kind-in-blocks unit-new-kind-no-seq gzip-not-bgzf
  tag-row-walk-underscore unit-new-kind-other-seq"
python3 -I "$BROKEN/../repack.py" "$T10" "$W/repack" $FORBIDDEN > /dev/null
for v in $FORBIDDEN; do
  cp "$W/repack/$v/f.walks.gz" "$BROKEN/$v.walks.gz"
  cp "$W/repack/$v/f.walks.gz.idx" "$BROKEN/$v.walks.gz.idx"
done

# what the page's sentences on tags, numbers, lines and names keep out of
# format 8 (ADR 0017), and budgets a header states over rows that break them
build edge100 "$BROKEN/edge.gfa" R --tile 100
EDGE100=$W/edge100.R.walks.gz
E=9007199254740
corrupt budget-bytes-over "$T0" 'abridgebytes:i:3000000' 'abridgebytes:i:10'
corrupt budget-steps-over "$T0" 'abridge:i:1000000' 'abridge:i:1'
corrupt budget-put-back "$T10" 'abridgebytes:i:1' 'abridgebytes:i:3000000'
corrupt walks-bytes-tag "$T0" 'leftout:i:1' $'leftout:i:1\tbytes:i:7'
corrupt reference-twice "$T0" $'#reference\tGRCh38\n' $'#reference\tGRCh38\n#reference\tGRCh38\n'
corrupt header-empty-line "$T0" $'#reference\tGRCh38\n' $'#reference\tGRCh38\n\n'
corrupt field-empty "$T0" $'#haplotype\tD#1\n' $'#haplotype\tD#1\t\n'
corrupt directory-empty-line "$T0" --idx $'#header\t0\t' $'\n#header\t0\t'
corrupt unit-line-inside-unit "$T0" $'#unit\t'$G$'\t0\t12\ttile\t0\n' $'#unit\t'$G$'\t0\t30\tfuture\tx\n#units of a later kind\n#unit\t'$G$'\t0\t12\ttile\t0\n'
corrupt departures-unit-empty "$T0" $'#unit\t'$G$'\t12\t24\ttile\t10\n' $'#unit\t'$G$'\t0\t80\tdepartures\t.\n#unit\t'$G$'\t12\t24\ttile\t10\n'
corrupt number-leading-zero "$T0" "$WH" $G$'\t0\t12\twalk\tH#1#h\t100\t0100\t0\t2\t2\t.\n'
corrupt number-plus-sign "$T0" --all $'Q#0#chr\t6\t6\t0\t6\t+' $'Q#0#chr\t6\t+6\t0\t6\t+'
corrupt token-minus-zero "$TIE100" --all $'R#0#c\t12\t30\twalk\tA#1#c\t0\t0\t0\t2\t2\t0' $'R#0#c\t12\t30\twalk\tA#1#c\t0\t0\t0\t2\t2\t-0'
corrupt tag-type-letter "$T0" 'revisited:i:0' 'revisited:Z:0'
corrupt tile-zero "$T0" 'tile:i:10' 'tile:i:0'
corrupt tile-past-2-40 "$T0" 'tile:i:10' 'tile:i:1099511627777'
corrupt length-zero "$T0" $'\t0\t12\tnodes\t6\t6' $'\t0\t12\tnodes\t6\t0'
corrupt ref-rows-overlap "$REFGAP100" --all $'ref\tR#0#c\t30\t30\t0\t3\t' $'ref\tR#0#c\t12\t12\t0\t3\t'
corrupt past-2-53-line-end "$EDGE100" "${E}974"$'\t'"${E}974" "${E}975"$'\t'"${E}975"
corrupt past-2-53-stated "$EDGE100" "${E}974"$'\t'"${E}974" "${E}993"$'\t'"${E}993"
corrupt name-space "$T0" --all 'H#1' 'H #1'
corrupt name-cr "$T0" --all 'H#1' $'H\r#1'
corrupt name-e9 "$T0" --all 'H#1' $'H\xe9#1'
corrupt name-del "$T0" --all "$G" "$G"$'\x7f'
corrupt reference-haplotype "$T0" $'#reference\tGRCh38\n' $'#reference\tGRCh38#0\n'

# the reference as whole haplotypes, the default occurrences left unnamed, and the places an independent
# reviewer found no planted file for: a name in rows alone, each kind of empty unit, a number in each place
# the page names one, a field, a tag's type, 2^53 at a record's own sequence and breakpoint, and #reference
sed -e $'s/^W\tHG002\t2\t/W\tHG002z\t2\t/' -e $'s/^W\tHG002\t1\talt1\t/W\tHG002y\t1\talt1\t/' "$BROKEN/hapref-alt.gfa" > "$W/hapref-alt-standin.gfa"
build hapalt "$W/hapref-alt-standin.gfa" HG002 --tile 10
corrupt reference-haplotype-walk "$W/hapalt.HG002.walks.gz" --all 'HG002z#2' 'HG002#2' --all 'HG002y#1' 'HG002#1'
corrupt default-start-named "$TIE100" --all $'walk\tE#1#c\t0\t0\t0\t5\t4\t7,' $'walk\tE#1#c\t0\t0\t0\t5\t4@0\t7,'
corrupt default-leave-named "$TIE100" --all $'walk\tE#1#c\t0\t0\t0\t5\t4\t7,' $'walk\tE#1#c\t0\t0\t0\t5\t4\t7:0,'
corrupt name-hash-rows "$T0" --all $'\tH#1#h\t' $'\t#H#1#h\t'
corrupt name-del-rows "$T0" --all $'\tH#1#h\t' $'\tH\x7f#1#h\t'
corrupt name-hash-haplotype "$T0" $'#haplotype\tH#1\n' $'#haplotype\t#H#1\n'
corrupt tile-empty "$T0" $'#unit\t'$G$'\t20\t30\tdepartures\t.\n'"$D24$I18" $'#unit\t'$G$'\t20\t30\tdepartures\t.\n'"$D24$I18"$'#unit\t'$G$'\t30\t30\ttile\t30\n'
corrupt detail-unit-empty "$T10" $'#unit\t'$G$'\t0\t12\tdetail\t0:2\n'$G$'\t0\t12\twalk\tH#1#h\t100\t100\t0\t2\t2\t.\n' $'#unit\t'$G$'\t0\t12\tdetail\t0:2\n'
corrupt table-empty "$T0" --empty-table 'GRCh38#0#chs'
corrupt number-tag-leading-zero "$T0" 'tile:i:10' 'tile:i:010'
corrupt number-tag-minus "$T0" 'leftout:i:1' 'leftout:i:-1'
corrupt number-start-leading-zero "$T0" $G$'\t0\t6\twalk\tI#1#i' $G$'\t00\t6\twalk\tI#1#i'
corrupt number-nsteps-space "$T0" $'walk\tI#1#i\t0\t0\t0\t1\t2\t.' $'walk\tI#1#i\t0\t0\t0\t 1\t2\t.'
corrupt number-length-leading-zero "$T0" $'ref\t'$G$'\t0\t24\t2\t1\t10\t6\t.' $'ref\t'$G$'\t0\t24\t2\t1\t10\t06\t.'
corrupt number-unit-leading-zero "$T0" $'#unit\t'$G$'\t24\t30\ttile\t20\n' $'#unit\t'$G$'\t024\t30\ttile\t20\n'
corrupt number-entry-length-leading-zero "$T0" --table $'tile\t20\t' $'tile\t20\t0'
corrupt field-empty-row "$T0" $'walk\tI#1#i\t0\t0\t0\t1\t2\t.\n' $'walk\tI#1#i\t0\t0\t0\t1\t2\t.\t\tzz:i:1\n'
corrupt directory-field-empty "$T0" --idx $'#header\t0\t' $'#header\t\t0\t'
corrupt tag-graph-i "$T0" 'graph:Z:7619ff637c3b074b' 'graph:i:5'
corrupt past-2-53-own-end "$T0" --all $'departure\tD#1#d\t24\t0\t0\t24' $'departure\tD#1#d\t9007199254740992\t1\t0\t24'
corrupt past-2-53-breakpoint "$T0" --all $'departure\tD#1#d\t24\t0\t0\t24\t+\t1\t0\t' $'departure\tD#1#d\t24\t0\t0\t24\t+\t1\t9007199254740993\t'
corrupt reference-none "$T0" $'#reference\tGRCh38\n' ''
corrupt unit-line-in-header "$T0" $'#haplotype\tD#1\n' $'#unitx\tD#1\n#haplotype\tD#1\n'
corrupt ref-rows-overlap-tiles "$T0" $'ref\t'$G$'\t0\t24\t2\t1\t10\t6\t.' $'ref\t'$G$'\t0\t23\t2\t1\t10\t7\t.' --all $G$'\t24\t30\t' $G$'\t23\t30\t'
build turn100 "$BROKEN/turn.gfa" R --tile 100
corrupt flip-of-own-flip "$W/turn100.R.walks.gz" --all $'walk\tA#1#c\t0\t0\t0\t4\t2\t0' $'walk\tA#1#c\t0\t0\t0\t4\t2\t1'
D01=$'#unit\t'$G$'\t0\t12\tdetail\t0:1\n'$G$'\t0\t12\twalk\tD#1#d\t0\t0\t0\t2\t2\t.\n'$G$'\t0\t12\twalk\tD#1#d\t0\t24\t2\t2\t2\t.\n'
D02=$'#unit\t'$G$'\t0\t12\tdetail\t0:2\n'$G$'\t0\t12\twalk\tH#1#h\t100\t100\t0\t2\t2\t.\n'
corrupt detail-units-swapped "$T10" "$D01$D02" "$D02$D01"
