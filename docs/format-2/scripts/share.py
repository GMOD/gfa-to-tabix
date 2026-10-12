"""How much a chunk's choices share across haplotypes, in several layouts,
and which per-row fields cost the most. Implied counts are left out.

usage: share.py DIR mb [mb ...] [--sub 50,100,200] [--json out.jsonl]
"""
import json
import lzma
import os
import random
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eval_routes import CHUNK, Encoder, canon, decode, gz, hap_of, rows, sort_key  # noqa: E402

FIELDS = ["hap", "contig", "frag", "off", "piece", "start", "span", "tags"]


def xz(text):
    return len(lzma.compress(text.encode(), preset=9 | lzma.PRESET_EXTREME))


def runs_of(walk_rows):
    by_path = defaultdict(list)
    for r in walk_rows:
        if not r[3].startswith("GRCh38#"):
            by_path[(r[3], r[4])].append(r)
    out = []
    for (name, frag), rs in by_path.items():
        rs.sort(key=lambda r: int(r[6]))
        from_ = 0
        for k in range(1, len(rs) + 1):
            if k == len(rs) or int(rs[k][6]) != int(rs[k - 1][6]) + 1:
                piece = rs[from_:k]
                H = []
                for r in piece:
                    H.extend(decode(r[8]))
                tags = [c for c in piece[0][9:] if c.startswith("pv:")] + [c for c in piece[-1][9:] if c.startswith("nx:")]
                out.append(dict(name=name, frag=int(frag), off=int(piece[0][5]), piece=int(piece[0][6]), H=H, tags=tags))
                from_ = k
    return out


def delta_tokens(ids):
    prev = 0
    toks = []
    for v in ids:
        toks.append(str(2 * ((v >> 1) - prev) + (v & 1)))
        prev = v >> 1
    return ",".join(toks) or "."


def rle(ids):
    ids = sorted(set(ids))
    out = []
    prev = -1
    k = 0
    while k < len(ids):
        j = k
        while j + 1 < len(ids) and ids[j + 1] == ids[j] + 1:
            j += 1
        out.append(f"{ids[k] - prev - 1}+{j - k + 1}")
        prev = ids[j]
        k = j + 1
    return ",".join(out)


def measure_set(encoded, start, hap_ids):
    count = Counter(canon(route)[0] for e in encoded for route, _, _ in e["choices"])
    rid = {k: i for i, k in enumerate(sorted(count, key=sort_key))}
    prefix = f"chr22\t{start}\t{start + 1}\t"

    def text(lines):
        return "".join(prefix + line + "\n" for line in lines)

    seqs = []
    for e in encoded:
        ids = []
        for route, _, _ in e["choices"]:
            key, flip = canon(route)
            ids.append(2 * rid[key] + flip)
        seqs.append(ids)
    fields = [
        {
            "hap": str(hap_ids[hap_of(e["name"])]),
            "contig": e["name"].split("#", 2)[2],
            "frag": str(e["frag"]),
            "off": str(e["off"]),
            "piece": str(e["piece"]),
            "start": str(e["start_h"]),
            "span": str(e["end_h"] - e["start_h"]),
            "tags": "\t".join(e["tags"]),
        }
        for e in encoded
    ]

    def meta(drop=None):
        return ["\t".join(f[k] for k in FIELDS if k != drop) for f in fields]

    tok = [delta_tokens(s) for s in seqs]
    full = [m + "\t" + t for m, t in zip(meta(), tok)]
    order = sorted(range(len(seqs)), key=lambda i: seqs[i])
    rank = {i: k for k, i in enumerate(order)}
    carriers = defaultdict(list)
    for i, s in enumerate(seqs):
        for v in s:
            carriers[v >> 1].append(rank[i])
    site_plain = []
    for r in range(len(rid)):
        ids = sorted(set(carriers[r]))
        site_plain.append(",".join(str(b - a) for a, b in zip([-1] + ids, ids)))
    meta_gz = gz(text(meta()))
    return {
        "runs": len(encoded),
        "routes": len(rid),
        "route_uses": sum(len(s) for s in seqs),
        "distinct_seqs": len(set(map(tuple, seqs))),
        "choices_gz": gz(text(full)),
        "choices_sorted_gz": gz(text(full[i] for i in order)),
        "meta_gz": meta_gz,
        "tok_gz": gz(text(tok)),
        "tok_sorted_gz": gz(text(tok[i] for i in order)),
        "tok_xz": xz(text(tok)),
        "site_plain_gz": gz(text(site_plain)),
        "site_rle_gz": gz(text(rle(carriers[r]) for r in range(len(rid)))),
        **{f"meta_saved_without_{k}": meta_gz - gz(text(meta(k))) for k in FIELDS},
        "meta_saved_without_contig_frag": meta_gz
        - gz(text("\t".join(f[k] for k in FIELDS if k not in ("contig", "frag")) for f in fields)),
    }


def measure(d, start, subs, seed=1):
    walk_rows = rows(d, "walks", start)
    ref_path = []
    for r in sorted((r for r in walk_rows if r[3].startswith("GRCh38#")), key=lambda r: int(r[6])):
        ref_path.extend(decode(r[8]))
    enc = Encoder(ref_path)
    encoded = []
    for run in runs_of(walk_rows):
        e = enc.encode(run["H"])
        if e is not None:
            encoded.append(dict(run, start_h=e[0], choices=e[1], end_h=e[2]))
    haps = sorted({hap_of(e["name"]) for e in encoded})
    hap_ids = {h: i for i, h in enumerate(haps)}
    out = {"chunk_mb": round(start / 1e6, 3), "haps": len(haps), "all": measure_set(encoded, start, hap_ids)}
    rng = random.Random(seed)
    for n in subs:
        if n < len(haps):
            sub = set(rng.sample(haps, n))
            out[f"sub{n}"] = measure_set([e for e in encoded if hap_of(e["name"]) in sub], start, hap_ids)
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    d = args.pop(0)
    subs, jpath, mbs = [], None, []
    while args:
        a = args.pop(0)
        if a == "--sub":
            subs = [int(x) for x in args.pop(0).split(",")]
        elif a == "--json":
            jpath = args.pop(0)
        else:
            mbs.append(float(a))
    for mb in mbs:
        m = measure(d, int(mb * 1e6) // CHUNK * CHUNK, subs)
        print(json.dumps(m), flush=True)
        if jpath:
            with open(jpath, "a") as f:
                f.write(json.dumps(m) + "\n")
