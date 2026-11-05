"""T64b: T64's tiles with departure records filed per pyramid block: every
row of a record carries the extent of the aligned block it is listed in
(the index's bin), so a block's rows are contiguous in start order, each
block ends a BGZF block, and a bin's chunk is exactly one block. Records
are S's lines (end-node extents), so the departure query needs no reach.

usage: bgzip -dc t64.bed.gz | python3 -I build_t64b.py S.departures.txt OUT.bed.gz [LEVELS]
  LEVELS  log2 block sizes, largest first; default 25,22,19,16
"""
import struct
import sys
import zlib
from collections import defaultdict

BLOCK = 65280
EOF_BLOCK = bytes.fromhex("1f8b08040000000000ff0600424302001b0003000000000000000000")
deps_path, out = sys.argv[1], sys.argv[2]
levels = [1 << int(x) for x in (sys.argv[3] if len(sys.argv) > 3 else "25,22,19,16").split(",")]
unit = levels[-1]


class Bgzf:
    def __init__(self, path):
        self.f = open(path, "wb")
        self.buf = bytearray()

    def write(self, data):
        self.buf += data
        while len(self.buf) >= BLOCK:
            self.block(bytes(self.buf[:BLOCK]))
            del self.buf[:BLOCK]

    def flush(self):
        while self.buf:
            self.block(bytes(self.buf[:BLOCK]))
            del self.buf[:BLOCK]

    def block(self, data):
        c = zlib.compressobj(6, zlib.DEFLATED, -15)
        body = c.compress(data) + c.flush()
        self.f.write(
            b"\x1f\x8b\x08\x04\x00\x00\x00\x00\x00\xff\x06\x00BC\x02\x00"
            + struct.pack("<H", len(body) + 25)
            + body
            + struct.pack("<II", zlib.crc32(data) & 0xFFFFFFFF, len(data))
        )

    def close(self):
        self.flush()
        self.f.write(EOF_BLOCK)
        self.f.close()


def blocks(lo, hi):
    at = lo // unit * unit
    end = (hi - 1) // unit * unit + unit
    while at < end:
        size = next((s for s in levels if at % s == 0 and at + s <= end), unit)
        yield at, size
        at += size


groups = defaultdict(lambda: defaultdict(list))
for line in open(deps_path):
    cols = line.rstrip("\n").split("\t")
    seq, lo, hi = cols[0], int(cols[1]), int(cols[2])
    body = "\t".join(cols[3:] + [cols[1], cols[2]])
    for at, size in blocks(lo, hi):
        groups[seq][(at, size)].append(body)


def write_departures(w, seq):
    rows = 0
    for (at, size) in sorted(groups[seq], key=lambda k: (k[0], -k[1])):
        for body in groups[seq][(at, size)]:
            w.write(f"{seq}~departure\t{at}\t{at + size}\t{body}\n".encode())
            rows += 1
        w.flush()
    return rows


w = Bgzf(out)
at = None
written = set()
rows = 0
for raw in sys.stdin.buffer:
    if raw.startswith(b"#"):
        w.write(raw)
        continue
    seq = raw.split(b"\t", 1)[0]
    if seq.endswith(b"~departure"):
        continue
    if b"~" in seq:
        base = seq.rsplit(b"~", 1)[0].decode()
        if base not in written:
            w.flush()
            rows += write_departures(w, base)
            written.add(base)
    key = (seq, raw.split(b"\t", 2)[1])
    if key != at:
        w.flush()
        at = key
    w.write(raw)
w.flush()
for base in groups:
    if base not in written:
        rows += write_departures(w, base)
w.close()
print(f"departure rows {rows}")
