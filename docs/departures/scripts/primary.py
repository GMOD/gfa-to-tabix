#!/usr/bin/env python3
# Chains each contig's lifted alignment blocks (walks-truth.py lift output)
# into one primary projection: the non-overlapping set of blocks with the
# most aligned bp, a transition between blocks costing nothing when it keeps
# the same target, strand and co-linear position, and `--jump` bp otherwise.
# Usage: primary.py lift.tsv > lift.primary.tsv
import argparse
import collections
import sys

ap = argparse.ArgumentParser()
ap.add_argument('lift')
ap.add_argument('--jump', type=int, default=20000)
ap.add_argument('--slack', type=int, default=1000)
ap.add_argument('--window', type=int, default=48)
args = ap.parse_args()

by = collections.defaultdict(list)
for line in open(args.lift):
    c = line.rstrip('\n').split('\t')
    by[c[0]].append((int(c[1]), int(c[2]), c[3], int(c[4]), int(c[5]), c[6] == '+'))

out = sys.stdout
kept_total = 0
dropped_total = 0
for q, blocks in by.items():
    blocks.sort()
    n = len(blocks)
    best = [0.0] * n
    back = [-1] * n
    # blocks finished so far, by end, with the running best score among them
    by_end = []
    prefix_best = []
    prefix_arg = []
    import bisect
    ends = []
    order = sorted(range(n), key=lambda i: blocks[i][1])
    pos_in_order = {i: k for k, i in enumerate(order)}
    done = 0
    for i in sorted(range(n), key=lambda i: blocks[i][0]):
        lo, hi, t, ta, tb, fwd = blocks[i]
        length = hi - lo
        # admit every block whose end is at or before lo
        while done < n and blocks[order[done]][1] <= lo:
            j = order[done]
            ends.append(blocks[j][1])
            by_end.append(j)
            score = best[j]
            if not prefix_best or score > prefix_best[-1]:
                prefix_best.append(score)
                prefix_arg.append(j)
            else:
                prefix_best.append(prefix_best[-1])
                prefix_arg.append(prefix_arg[-1])
            done += 1
        score = float(length)
        prev = -1
        if by_end:
            score = prefix_best[-1] - args.jump + length
            prev = prefix_arg[-1]
            for j in by_end[-args.window:]:
                jlo, jhi, jt, jta, jtb, jfwd = blocks[j]
                if jt != t or jfwd != fwd:
                    continue
                gap = lo - jhi
                expected = jtb + gap if fwd else jta - gap
                actual = ta if fwd else tb
                if abs(actual - expected) <= args.slack + gap // 10:
                    cand = best[j] + length
                    if cand > score:
                        score = cand
                        prev = j
        best[i] = score
        back[i] = prev
    i = max(range(n), key=lambda i: best[i])
    chain = []
    while i >= 0:
        chain.append(i)
        i = back[i]
    chain.reverse()
    kept_total += len(chain)
    dropped_total += n - len(chain)
    for i in chain:
        lo, hi, t, ta, tb, fwd = blocks[i]
        out.write(f'{q}\t{lo}\t{hi}\t{t}\t{ta}\t{tb}\t{"+" if fwd else "-"}\n')
print(f'kept {kept_total} blocks, dropped {dropped_total}', file=sys.stderr)
