import gzip, re, subprocess, sys
path = sys.argv[1]
units, cur = {}, None
with gzip.open(path, 'rt') as f:
    for line in f:
        c = line.rstrip('\n').split('\t')
        if c[0] == '#unit':
            cur = c[5] if c[4] == 'blocks' else None
            if cur is not None:
                units[cur] = [line]
        elif cur is not None:
            units[cur].append(line)
tok = re.compile(r'(-?\d+)([+-])(\d+)(?::(\d+))?$')
def rows(lines):
    for line in lines[1:]:
        c = line.rstrip('\n').split('\t')
        blocks, at = [], 0
        for t in c[9].split(','):
            d, sign, length, own = tok.match(t).groups()
            begin = at + int(d)
            length = int(length)
            at = begin - length if sign == '-' else begin + length
            blocks.append((int(d), begin, sign, length, int(own or 0)))
        yield c, blocks
def current(c, blocks):
    return '\t'.join(c)
def walk(c, blocks):
    items = [c[7]] if c[7] != '0' else []
    for k, (d, begin, sign, length, own) in enumerate(blocks):
        if own:
            items.append(str(own))
        items.append(f"{d}{'<' if sign == '-' else '>'}{length}")
    if c[8] != '0':
        items.append(c[8])
    return '\t'.join(c[:7] + [','.join(items)])
def absolute(c, blocks):
    return '\t'.join(c[:9] + [','.join(f"{begin}{sign}{length}{':' + str(own) if own else ''}" for d, begin, sign, length, own in blocks)])
def walk_absolute(c, blocks):
    items = [c[7]] if c[7] != '0' else []
    for d, begin, sign, length, own in blocks:
        if own:
            items.append(str(own))
        items.append(f"{begin}{'<' if sign == '-' else '>'}{length}")
    if c[8] != '0':
        items.append(c[8])
    return '\t'.join(c[:7] + [','.join(items)])
def bgzf(text):
    return len(subprocess.run(['bgzip', '-l', '9', '-c'], input=text.encode(), capture_output=True).stdout)
total = {}
worst = {}
for name, lines in units.items():
    parsed = list(rows(lines))
    for label, f in (('current', current), ('own as items', walk), ('absolute begins', absolute), ('own as items, absolute', walk_absolute)):
        text = lines[0] + ''.join(f(c, b) + '\n' for c, b in parsed)
        raw, z = len(text), bgzf(text)
        t = total.setdefault(label, [0, 0]); t[0] += raw; t[1] += z
        worst[label] = max(worst.get(label, 0), z)
for label, (raw, z) in total.items():
    print(f"{label}: raw {raw} bgzf {z} largest unit {worst[label]}")
