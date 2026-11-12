"""Units of a format 8 walk file, read through its directory and tables."""
import zlib


def gunzip(raw):
    out = []
    while raw:
        d = zlib.decompressobj(31)
        out.append(d.decompress(raw))
        raw = d.unused_data
    return b''.join(out).decode()


def units(path):
    """Yields (seq, start, end, kind, name, lines) for every unit a table lists."""
    data = open(path, 'rb').read()
    idx = open(path + '.idx').read().splitlines()
    for line in idx[2:]:
        if not line.startswith('#'):
            seq, off, length = line.rsplit('\t', 2)
            table = gunzip(data[int(off):int(off) + int(length)]).splitlines()[1:]
            for e in table:
                c = e.split('\t')
                text = gunzip(data[int(c[6]):int(c[6]) + int(c[7])])
                yield c[1], int(c[2]), int(c[3]), c[4], c[5], text.splitlines()


def dump(path, kinds):
    out = []
    for seq, start, end, kind, name, lines in units(path):
        if kind in kinds:
            out.extend(lines)
    return out


if __name__ == '__main__':
    import sys
    kinds = sys.argv[2].split(',') if len(sys.argv) > 2 else ['tile', 'departures', 'detail', 'blocks']
    print('\n'.join(dump(sys.argv[1], kinds)))
