"""Per-chunk compressed byte spans from the .tbi indexes: which chunks are the
worst, and how the three files split between GRCh38 and CHM13."""
import gzip
import struct
import sys
import os

DIR = sys.argv[1]
CHUNK = 65536


def read_tbi(path):
    data = gzip.open(path).read()
    at = 0

    def u32():
        nonlocal at
        v = struct.unpack_from("<I", data, at)[0]
        at += 4
        return v

    def u64():
        nonlocal at
        v = struct.unpack_from("<Q", data, at)[0]
        at += 8
        return v

    assert data[:4] == b"TBI\x01"
    at = 4
    n_ref = u32()
    _fmt, _c, _b, _e, _meta, _skip = [u32() for _ in range(6)]
    l_nm = u32()
    names = data[at : at + l_nm].split(b"\0")[:-1]
    at += l_nm
    refs = {}
    for r in range(n_ref):
        n_bin = u32()
        bins = {}
        for _ in range(n_bin):
            b = u32()
            n_chunk = u32()
            bins[b] = [(u64(), u64()) for _ in range(n_chunk)]
        n_intv = u32()
        intv = [u64() for _ in range(n_intv)]
        refs[names[r].decode()] = (bins, intv)
    return refs, len(data)


def coffset(v):
    return v >> 16


for kind in ["walks", "nodes", "links"]:
    path = f"{DIR}/chr22.{kind}.bed.gz"
    size = os.path.getsize(path)
    refs, tbi_raw = read_tbi(path + ".tbi")
    print(f"== {kind}: file {size/1e6:.1f} MB, tbi raw {tbi_raw} B, tbi gz {os.path.getsize(path+'.tbi')} B")
    for name, (bins, intv) in refs.items():
        # every row of a chunk is filed at cs..cs+1 so lives in one leaf bin
        # (bin 4681 + cs>>14); the chunk list of that bin bounds its bytes
        spans = []
        for b, chunks in bins.items():
            if b < 4681:
                continue
            cs = (b - 4681) << 14
            lo = min(c[0] for c in chunks)
            hi = max(c[1] for c in chunks)
            spans.append((cs, coffset(lo), coffset(hi)))
        spans.sort()
        total = coffset(max(hi for _, _, hi in spans)) if False else 0
        first = min(lo for _, lo, _ in spans)
        last = max(hi for _, _, hi in spans)
        approx = [(cs, hi - lo) for cs, lo, hi in spans]
        approx.sort(key=lambda x: -x[1])
        n = len(spans)
        sizes = sorted(b for _, b in approx)
        med = sizes[n // 2]
        p90 = sizes[int(n * 0.9)]
        p99 = sizes[int(n * 0.99)]
        print(
            f"  {name}: {n} chunks, bytes {first/1e6:.1f}-{last/1e6:.1f} MB "
            f"(~{(last-first)/1e6:.1f} MB), per-chunk median {med/1e3:.0f} KB p90 {p90/1e3:.0f} KB p99 {p99/1e3:.0f} KB"
        )
        print("    worst 8:", ", ".join(f"{cs/1e6:.2f}Mb={b/1e6:.2f}MB" for cs, b in approx[:8]))
        if name.startswith("GRCh38") and kind == "walks":
            with open(f"{DIR.rstrip('/')}/../../../chunks_grch38_walks.tsv".replace("/../../../", "/"), "w") if False else open(os.devnull, "w") as f:
                pass
            out = sys.argv[2] if len(sys.argv) > 2 else None
            if out:
                with open(out, "w") as f:
                    for cs, lo, hi in spans:
                        f.write(f"{cs}\t{hi-lo}\n")
