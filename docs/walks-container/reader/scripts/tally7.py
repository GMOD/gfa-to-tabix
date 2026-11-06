# Final counts of cut7check/diff7/diff7v: windows identical to graph-walks
# 5.0.2 and to the attach-decode-fixed copy once abridged detail names are
# normalised, and the class of every difference.
# usage: python3 tally7.py <dataset> <set>   (set: random96 or targets0)
import json, sys
from collections import Counter

d, w = sys.argv[1:3]
RES = sys.argv[3] if len(sys.argv) > 3 else 'res'
short = 'random' if w == 'random96' else 'targets'
main = [json.loads(l) for l in open(f'{RES}/{d}.{w}.jsonl')]
key = lambda r: (r['size'], r['start'])
diff = {key(r): r for r in map(json.loads, open(f'{RES}/d.{d}.{short}.jsonl'))}
try:
    dv = {key(r): r for r in map(json.loads, open(f'{RES}/dv.{d}.{short}.jsonl'))}
except FileNotFoundError:
    dv = {}
same5 = sameFixed = 0
cls = Counter()
for r in main:
    x = diff.get(key(r))
    v5 = x['vs5']['identical'] if x else r['vs5']['identical']
    vf = x['vsFixed']['identical'] if x else r['vsFixed']['identical']
    same5 += v5
    sameFixed += vf
    if not v5:
        c = x['class5']
        only_steps = not (c['fragmentsOnlyBase'] or c['fragmentsOnly6'] or c['recordsOnlyBase'] or c['recordsOnly6'] or c['stepsDiffer'] or c['stepsOnlyBase'] or c['keptOnly6Unexplained'] or c['keptOnlyBase'])
        cls['vs5: 6 attaches own steps 5.0.2 lost, nothing else' if only_steps else 'vs5: other'] += 1
        cls['vs5: windows with steps only in 6'] += c['stepsOnly6'] > 0
        cls['vs5: windows with steps only in 5.0.2'] += c['stepsOnlyBase'] > 0
    if not vf:
        c = x['classFixed']
        cls['vsFixed: matches with 5.0.2 attach extent' if dv.get(key(r), {}).get('vsFixed', {}).get('identical') else 'vsFixed: unexplained'] += 1
        cls['vsFixed: windows with steps only in 6'] += c['stepsOnly6'] > 0
        cls['vsFixed: windows with steps only in fixed'] += c['stepsOnlyBase'] > 0
print(json.dumps({'dataset': d, 'set': w, 'windows': len(main), 'identical5': same5, 'identicalFixed': sameFixed, **cls}))
