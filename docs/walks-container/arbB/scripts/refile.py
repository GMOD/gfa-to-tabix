"""Re-file a format 6 walks file's rows under another interval, same rows.

usage: bgzip -dc in.walks.bed.gz | python3 -I refile.py MODE ALIGN out.bed.gz [DEPCUT]

MODE  1bp     seq cs cs+1            (format 6 as shipped)
      span    seq cs cs+chunk        (the chunk's own span)
      extent  seq cs cs+chunk+maxnode (every base the chunk's rows can describe)
ALIGN 0       fill BGZF blocks to 65280 bytes as bgzip does
      1       also end a block where a chunk of the main sequence ends,
              (and where a sibling sequence starts), so each chunk starts
              on a block boundary

Only rows of sequences without '~' change; departure and detail records keep
their intervals. Header lines are kept and end their own block in both modes.
"""

import struct
import sys
import zlib

BLOCK = 65280
mode, align, out = sys.argv[1], sys.argv[2] == "1", sys.argv[3]
# DEPCUT: the bin sizes departure records are cut at, largest first, as
# log2 sizes; default the shipped Tabix sizes 26,23,20,17
cut = [1 << int(x) for x in (sys.argv[4] if len(sys.argv) > 4 else "26,23,20,17").split(",")]


def blocks(lo, hi):
    unit = cut[-1]
    at = lo // unit * unit
    end = (hi - 1) // unit * unit + unit
    while at < end:
        size = next((s for s in cut if at % s == 0 and at + s <= end), unit)
        yield max(lo, at), min(hi, at + size)
        at += size


held = {}


def flush_departures():
    rows = []
    for rest, (lo, hi, seq) in held.items():
        for a, b in blocks(lo, hi):
            rows.append((a, b, seq, rest))
    rows.sort(key=lambda r: (r[0], r[1]))
    for a, b, seq, rest in rows:
        w.write(b"\t".join((seq, str(a).encode(), str(b).encode(), rest)))
    held.clear()

EOF_BLOCK = bytes.fromhex("1f8b08040000000000ff0600424302001b0003000000000000000000")


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
        bsize = len(body) + 25
        self.f.write(
            b"\x1f\x8b\x08\x04\x00\x00\x00\x00\x00\xff\x06\x00BC\x02\x00"
            + struct.pack("<H", bsize)
            + body
            + struct.pack("<II", zlib.crc32(data) & 0xFFFFFFFF, len(data))
        )

    def close(self):
        self.flush()
        self.f.write(EOF_BLOCK)
        self.f.close()


w = Bgzf(out)
chunk = maxnode = None
at = None
for raw in sys.stdin.buffer:
    if raw.startswith(b"#"):
        if raw.startswith(b"#walks"):
            for tag in raw.split(b"\t"):
                if tag.startswith(b"chunk:i:"):
                    chunk = int(tag[8:])
                if tag.startswith(b"maxnode:i:"):
                    maxnode = int(tag[10:])
        w.write(raw)
        continue
    if at is None:
        w.flush()
    seq, cs, end, rest = raw.split(b"\t", 3)
    if held and not seq.endswith(b"~departure"):
        flush_departures()
    if seq.endswith(b"~departure"):
        lo, hi = int(cs), int(end)
        if rest in held:
            lo, hi = min(lo, held[rest][0]), max(hi, held[rest][1])
        held[rest] = (lo, hi, seq)
        continue
    key = seq if b"~" in seq else (seq, cs)
    if align and key != at:
        w.flush()
    at = key
    if b"~" not in seq:
        start = int(cs)
        end = {
            "1bp": start + 1,
            "span": start + chunk,
            "extent": start + chunk + maxnode,
        }[mode]
        raw = b"\t".join((seq, cs, str(end).encode(), rest))
    w.write(raw)
flush_departures()
w.close()
