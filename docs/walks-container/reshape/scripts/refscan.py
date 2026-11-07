# Per tile of a format 7 file: the reference bp, the bp on nodes the
# reference passes more than once, and the most-passed node with its pass
# count and offset. Also, file-wide, every revisited node's stretch on the
# reference (offsets of each pass) for the nodes passed most.
# usage: refscan.py <file.walks.gz> <out.tsv>
import gzip, sys, collections
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from r2sim import table, read_unit


def tokens(s):
    out, prev = [], 0
    for t in s.split(','):
        t = int(t)
        prev += t >> 1
        out.append((prev, t & 1))
    return out


if __name__ == '__main__':
    path, outp = sys.argv[1:3]
    passes_of = {}
    offsets = collections.defaultdict(list)
    with open(outp, 'w') as f:
        f.write('seq\ttile\tref_bp\trevisited_bp\tmax_passes\tnode\tnode_offset\tnode_bp\n')
        for e in table(path):
            if e['kind'] != 'tile':
                continue
            ref_bp = rev_bp = 0
            best = (0, None, None, None)
            for l in read_unit(path, e['off'], e['len']).split('\n'):
                c = l.split('\t')
                if len(c) > 11 and c[3] == 'ref':
                    at = int(c[6])
                    lens = [int(x) for x in c[10].split(',')]
                    ps = [1] * len(lens) if c[11] == '.' else [int(x) for x in c[11].split(',')]
                    for (node, _), n, p in zip(tokens(c[9]), lens, ps):
                        ref_bp += n
                        if p > 1:
                            rev_bp += n
                            passes_of[node] = (p, n)
                            offsets[node].append(at)
                            if p > best[0]:
                                best = (p, node, at, n)
                        at += n
            f.write(f"{e['seq']}\t{e['name']}\t{ref_bp}\t{rev_bp}\t{best[0]}\t{best[1]}\t{best[2]}\t{best[3]}\n")
    top = sorted(passes_of.items(), key=lambda kv: (-kv[1][0] * kv[1][1], kv[0]))[:40]
    with open(outp + '.nodes', 'w') as f:
        f.write('node\tpasses\tnode_bp\tpass_bp_total\tfirst\tlast\tpass offsets (first 12)\n')
        for node, (p, n) in top:
            o = sorted(offsets[node])
            f.write(f"{node}\t{p}\t{n}\t{p * n}\t{o[0]}\t{o[-1]}\t{','.join(map(str, o[:12]))}\n")
    print(len(passes_of), 'revisited nodes seen on ref rows', file=sys.stderr)
