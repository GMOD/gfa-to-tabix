import gzip, sys, collections
ab = {}; det = {}; unit = None; seqlen = {}
with gzip.open(sys.argv[1], 'rt') as f:
    for line in f:
        c = line.rstrip('\n').split('\t')
        if c[0] == '#unit':
            unit = (c[4], c[5])
            if c[4] == 'table': seqlen[c[1]] = int(c[3])
            continue
        if line[0] == '#': continue
        if c[3] == 'abridged':
            ab[(c[0], unit[1], c[12], c[4], c[5], c[7])] = (int(c[1]), int(c[2]))
        elif c[3] == 'walk' and unit[0] == 'detail':
            cs, dd = unit[1].split(':')
            det[(c[0], cs, dd, c[4], c[5], c[7])] = (int(c[1]), int(c[2]))
gaps = collections.defaultdict(list); haps = collections.Counter(); seqs = collections.Counter()
for key, (s, e) in ab.items():
    t0, t1 = det[key]
    for a, b in ((t0, min(s, t1)), (max(e, t0), t1)):
        if b > a:
            gaps[key[0]].append((a, b)); haps[key[3].rsplit('#', 1)[0]] += 1; seqs[key[0]] += 1
union = 0
for seq, iv in gaps.items():
    iv.sort(); cur = None
    for a, b in iv:
        if cur and a <= cur[1]: cur[1] = max(cur[1], b)
        else:
            if cur: union += cur[1] - cur[0]
            cur = [a, b]
    if cur: union += cur[1] - cur[0]
total = sum(seqlen.values())
print(f"{sys.argv[1].split('/')[-1]}: reference {total} bp; union of missed stretches {union} bp ({100*union/total:.3f}%); haplotypes affected {len(haps)}; top sequences {seqs.most_common(6)}")
