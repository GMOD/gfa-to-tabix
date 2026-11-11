import gzip, sys, collections
det = collections.defaultdict(list); ext = {}; unit = None
with gzip.open(sys.argv[1], 'rt') as f:
    for line in f:
        c = line.rstrip('\n').split('\t')
        if c[0] == '#unit':
            unit = (c[1], c[4], c[5])
            if c[4] == 'detail': ext[(c[1], c[5])] = (int(c[2]), int(c[3]))
            continue
        if line[0] != '#' and c[3] == 'walk' and unit[1] == 'detail':
            det[(unit[0], unit[2])].append((int(c[1]), int(c[2])))
single = multi = single_diff = multi_diff = 0
for k, spans in det.items():
    hull = (min(a for a, b in spans), max(b for a, b in spans))
    if len(spans) == 1:
        single += 1; single_diff += hull != ext[k]
    else:
        multi += 1; multi_diff += hull != ext[k]
print(f"{sys.argv[1].split('/')[-1]}: detail units {len(ext)}, with walk rows {len(det)}; single-piece {single}, extent != span {single_diff}; multi-piece {multi}, extent != hull {multi_diff}")
