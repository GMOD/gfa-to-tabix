"""Write a CSI for a bgzipped BED-like file without htslib's bin folding:
every bin keeps its own chunks (one per contiguous run of its rows). The
tabix aux block (format, columns, sequence names) is copied from an existing
CSI of the same file, so the reference ids match.

usage: csi_write.py FILE.bed.gz EXISTING.csi OUT.csi [MIN_SHIFT] [DEPTH]
"""
import gzip
import struct
import sys
import zlib
from collections import defaultdict

path, existing, out = sys.argv[1:4]
min_shift = int(sys.argv[4]) if len(sys.argv) > 4 else 16
depth = int(sys.argv[5]) if len(sys.argv) > 5 else 5

old = gzip.open(existing).read()
_, _, l_aux = struct.unpack("<iii", old[4:16])
aux = old[16:16 + l_aux]
names = [n.decode() for n in aux[28:].split(b"\x00") if n]
ref_id = {n: i for i, n in enumerate(names)}


def reg2bin(beg, end):
    end -= 1
    s = min_shift
    t = ((1 << (depth * 3)) - 1) // 7
    for l in range(depth, 0, -1):
        if beg >> s == end >> s:
            return t + (beg >> s)
        s += 3
        t -= 1 << ((l - 1) * 3)
    return 0


def bin_start(b):
    level = 0
    while b >= ((1 << ((level + 1) * 3)) - 1) // 7:
        level += 1
    first = ((1 << (level * 3)) - 1) // 7
    return (b - first) << (min_shift + 3 * (depth - level))


bins = defaultdict(lambda: defaultdict(list))
lidx = defaultdict(dict)
f = open(path, "rb")
coff = 0
carry = b""
carry_voff = 0
rows = 0
while True:
    hdr = f.read(18)
    if len(hdr) < 18:
        break
    bsize = struct.unpack("<H", hdr[16:18])[0] + 1
    body = f.read(bsize - 18)
    data = zlib.decompress(body[:-8], -15)
    if not data:
        coff += bsize
        continue
    buf = carry + data
    ncarry = len(carry)
    start = 0
    while True:
        nl = buf.find(b"\n", start)
        if nl < 0:
            break
        line = buf[start:nl]
        voff = carry_voff if start < ncarry else (coff << 16) | (start - ncarry)
        end_in_block = nl + 1 - ncarry
        end_voff = ((coff + bsize) << 16) if end_in_block >= len(data) else (coff << 16) | end_in_block
        start = nl + 1
        if not line or line.startswith(b"#"):
            continue
        cols = line.split(b"\t", 3)
        rid = ref_id[cols[0].decode()]
        beg, end = int(cols[1]), int(cols[2])
        b = reg2bin(beg, end)
        chunks = bins[rid][b]
        if chunks and chunks[-1][1] == voff:
            chunks[-1][1] = end_voff
        else:
            chunks.append([voff, end_voff])
        rows += 1
        lin = lidx[rid]
        for i in range(beg >> min_shift, ((end - 1) >> min_shift) + 1):
            if i not in lin or voff < lin[i]:
                lin[i] = voff
    carry = buf[start:]
    carry_voff = (coff << 16) | (start - ncarry) if start >= ncarry else carry_voff
    coff += bsize

o = bytearray()
o += b"CSI\x01" + struct.pack("<iii", min_shift, depth, l_aux) + aux
o += struct.pack("<i", len(names))
for rid in range(len(names)):
    rbins = bins.get(rid, {})
    lin = lidx.get(rid, {})
    filled = []
    cur = 0
    for i in range(max(lin) + 1 if lin else 0):
        if i in lin:
            cur = lin[i]
        filled.append(cur)
    o += struct.pack("<i", len(rbins))
    for b in sorted(rbins):
        leaf = bin_start(b) >> min_shift
        loff = filled[leaf] if leaf < len(filled) else (filled[-1] if filled else 0)
        chunks = rbins[b]
        o += struct.pack("<IQi", b, loff, len(chunks))
        for u, v in chunks:
            o += struct.pack("<QQ", u, v)
with open(out, "wb") as g:
    g.write(gzip.compress(bytes(o), 6))
print(f"rows {rows}, bins {sum(len(v) for v in bins.values())}, chunks {sum(len(c) for v in bins.values() for c in v.values())}")
