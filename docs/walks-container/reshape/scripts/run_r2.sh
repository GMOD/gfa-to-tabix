#!/bin/bash
cd ~/work/reshape
for d in "mc22 base.mc22" "pggbY base.pggbY" "pggbY r1.pggbY"; do
  set -- $d
  (ulimit -v 60000000; nice -n 10 python3 -I r2sim.py $1 out/$2.GRCh38.walks.gz out/r2.$2 > /dev/null)
  python3 -c "import json; d=json.load(open(\"out/r2.$2.json\")); print(d[\"file\"], {k:d[k] for k in (\"bytes_old\",\"bytes_new\",\"parts_new\",\"gap_units\",\"tile_text_added\",\"stats\",\"summary\")})"
done
