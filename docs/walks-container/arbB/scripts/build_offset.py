"""Candidate O: the same rows in a BGZF file addressed by a chunk table, no
coordinates on the rows, departures in an honest Tabix file of their own.

usage: bgzip -dc in.walks.bed.gz | python3 -I build_offset.py OUTPREFIX

Writes
  OUTPREFIX.walks.bgz       header, then each chunk's rows as `seq cs kind ...`
                            (detail records as `seq~cs rec kind ...`), every
                            chunk and record a whole run of BGZF blocks
  OUTPREFIX.walks.idx       `name start end offset size`: `#header`, one line
                            per chunk (`seq cs cs+chunk`), one per detail
                            record (`seq~cs rec rec+1`); compressed byte
                            offsets, so a chunk is one range request, or
                            `tail -c +offset+1 | head -c size | bgzip -d`
  OUTPREFIX.departures.bed  departure rows as `seq a b departure ...` for
                            bgzip + tabix -p bed
"""
import struct
import sys
import zlib

BLOCK = 65280
EOF_BLOCK = bytes.fromhex("1f8b08040000000000ff0600424302001b0003000000000000000000")
prefix = sys.argv[1]


class Bgzf:
    def __init__(self, path):
        self.f = open(path, "wb")
        self.buf = bytearray()
        self.offset = 0

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
        out = (
            b"\x1f\x8b\x08\x04\x00\x00\x00\x00\x00\xff\x06\x00BC\x02\x00"
            + struct.pack("<H", bsize)
            + body
            + struct.pack("<II", zlib.crc32(data) & 0xFFFFFFFF, len(data))
        )
        self.f.write(out)
        self.offset += len(out)

    def close(self):
        self.flush()
        self.f.write(EOF_BLOCK)
        self.f.close()


w = Bgzf(prefix + ".walks.bgz")
idx = open(prefix + ".walks.idx", "w")
deps = open(prefix + ".departures.bed", "w")
chunk = None
at = None
start = 0


def entry(key, offset, size):
    name, pos = key
    if "~" in name:
        rec = pos // 16384
        idx.write(f"{name}\t{rec}\t{rec + 1}\t{offset}\t{size}\n")
    else:
        idx.write(f"{name}\t{pos}\t{pos + chunk}\t{offset}\t{size}\n")


for raw in sys.stdin.buffer:
    if raw.startswith(b"#"):
        if raw.startswith(b"#walks"):
            for tag in raw.split(b"\t"):
                if tag.startswith(b"chunk:i:"):
                    chunk = int(tag[8:])
        w.write(raw)
        continue
    seq, cs, end, rest = raw.split(b"\t", 3)
    if seq.endswith(b"~departure"):
        deps.write(f"{seq[:-10].decode()}\t{cs.decode()}\t{end.decode()}\t{rest.decode()}")
        continue
    key = (seq.decode(), int(cs))
    if key != at:
        w.flush()
        if at is None:
            idx.write(f"#header\t0\t0\t0\t{w.offset}\n")
        else:
            entry(at, start, w.offset - start)
        at = key
        start = w.offset
    w.write(b"\t".join((seq, cs, rest)))
w.flush()
entry(at, start, w.offset - start)
w.close()
idx.close()
deps.close()
