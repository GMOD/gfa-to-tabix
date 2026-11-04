# A random GFA: a reference whose path passes some nodes several times (tandem
# and dispersed copies), and haplotypes that follow stretches of it, jump
# forward and back, invert, and add nodes of their own, in one or more W lines
import random, sys
seed = int(sys.argv[1]); random.seed(seed)
n_unique = random.randint(20, 80)
lengths = {i: random.choice([0, 1, 2, 3, 5, 8, 13, 30]) if random.random() < 0.9 else random.randint(40, 200) for i in range(1, n_unique + 1)}
ref = []
for i in range(1, n_unique + 1):
    ref.append(i)
    if random.random() < 0.25 and len(ref) > 2:   # tandem repeat of the last few
        k = random.randint(1, 3)
        for _ in range(random.randint(1, 3)):
            ref += ref[-k:]
    if random.random() < 0.1 and len(ref) > 5:    # dispersed copy
        j = random.randrange(len(ref) - 1)
        ref += ref[j:j + random.randint(1, 3)]
nid = n_unique + 1
haps = []
for h in range(random.randint(3, 12)):
    steps = []
    i = random.randrange(len(ref) // 3 + 1)
    rev = False
    while len(steps) < random.randint(5, 3 * len(ref)) and 0 <= i < len(ref):
        steps.append((ref[i], rev))
        r = random.random()
        if r < 0.06:
            i += random.randint(2, 30)
        elif r < 0.10:
            i -= random.randint(1, 20)
        elif r < 0.13:
            for _ in range(random.randint(1, 4)):
                lengths[nid] = random.choice([1, 4, 20, 300])
                steps.append((nid, False)); nid += 1
            i += 1
        elif r < 0.15:
            rev = not rev
        else:
            i += -1 if rev else 1
    if rev:
        pass
    haps.append(steps)
print('H\tVN:Z:1.1')
for i, n in sorted(lengths.items()):
    print(f'S\t{i}\t*\tLN:i:{n}')
def w(sample, hap, contig, start, steps):
    end = start + sum(lengths[s] for s, _ in steps)
    print(f'W\t{sample}\t{hap}\t{contig}\t{start}\t{end}\t' + ''.join(('<' if r else '>') + str(s) for s, r in steps))
    return end
w('R', 0, 'chr', 0, [(s, False) for s in ref])
for k, steps in enumerate(haps):
    if not steps:
        continue
    if random.random() < 0.3 and len(steps) > 4:
        cut = random.randrange(1, len(steps) - 1)
        end = w(f'H{k}', 1, 'c', 0, steps[:cut])
        w(f'H{k}', 1, 'c', end + random.choice([1, 7, 100]), steps[cut:])
    else:
        w(f'H{k}', 1, 'c', random.choice([0, 50]), steps)
