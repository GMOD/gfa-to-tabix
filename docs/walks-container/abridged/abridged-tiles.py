import sys, gzip
path = sys.argv[1]
idx = open(path + '.idx').read().splitlines()
f = open(path, 'rb')
specs = []
for line in idx[2:]:
    seq, off, ln = line.split('\t')
    f.seek(int(off)); t = gzip.decompress(f.read(int(ln))).decode()
    tiles = sorted({l.split('\t')[5].split(':')[0] for l in t.splitlines() if l.startswith('#entry') and l.split('\t')[4] == 'detail'}, key=int)
    specs += [f"{seq},{cs}" for cs in tiles]
print('\n'.join(specs))
