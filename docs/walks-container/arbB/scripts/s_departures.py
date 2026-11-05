"""Distinct departure lines of an S file (end-node extents), one per record.
usage: s_departures.py S.walks.gz S.walks.idx OUT.txt"""
import gzip, sys, zlib
gz, idx, out = sys.argv[1:4]
f = open(gz, 'rb')
seen = set()
n = 0
with open(out, 'w') as o:
    for line in open(idx):
        cols = line.rstrip('\n').split('\t')
        if cols[3] != 'departures':
            continue
        f.seek(int(cols[5]))
        buf = f.read(int(cols[6]))
        text = gzip.decompress(buf).decode()
        for l in text.split('\n'):
            if l and l not in seen:
                seen.add(l)
                o.write(l + '\n')
                n += 1
print(n, 'distinct departure lines')
