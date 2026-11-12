#!/usr/bin/env python3
"""Shows that a writer stating a wrong hapBp is caught three ways.

Copies the repository to a scratch directory and, for each wrong hapBp below,
builds two writers there:
- one that takes the wrong value for the piece's bp, build check and all:
  the build must refuse every graph where the value is wrong;
- one that writes the wrong value on the `abridged` row past the build
  check, as a writer without the check would: `cargo test --test walks`
  must fail, and each file checker must fail a file it writes.

Prints a line per writer and exits 1 where a wrong value gets through.

Usage: broken-writers.py <repository> <scratch directory>
"""
import os
import pathlib
import shutil
import subprocess
import sys

REPO, SCRATCH = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2]).resolve()
SUM = '.iter().map(|&h| u64::from(lengths[(h >> 1) as usize])).sum::<u64>()'
LAST = 'piece.targets.iter().rposition(|t| *t != NONE).unwrap()'
FIRST = 'piece.targets.iter().position(|t| *t != NONE).unwrap()'
WRONG = {
    "format 7's bp, from the first step on R to the last": f'piece.handles[{FIRST}..={LAST}]{SUM}',
    'the span on S, end less start': (
        '{ let c = collapsed(&path, piece, lengths); c.blocks.iter().map(|b| b.span.1).max().unwrap() '
        '- c.blocks.iter().map(|b| b.span.0).min().unwrap() }'),
    'off by one': 'piece_bp(piece, lengths) + 1',
    "the bp of the line's next piece in the tile": 'piece_bp(alone.walks[(n + 1) % alone.walks.len()].0, lengths)',
    'the bp up to the last step on R, without the trailing run': f'piece.handles[..={LAST}]{SUM}',
}
LOOP = '        for (piece, walk, _) in &alone.walks {\n'
TRUE = '            let bp = piece_bp(piece, lengths);\n'
ROW = '&summary_row(piece, k, bp)'
CHECKERS = ['verify7', 'claims7', 'audit7', 'expand7', 'spec8', 'rebuild']
OPTIONS = [['--tile', '12', '--stay', '0', '--abridge-bytes', '1'], ['--tile', '10', '--abridge-steps', '1']]


def run(args, **kwargs):
    return subprocess.run(args, capture_output=True, text=True, errors='replace', **kwargs)


def fixtures(root):
    found = sorted(root.glob('tests/data/walks-*.gfa')) + sorted(root.glob('docs/walks-container/hapbp/*.gfa'))
    return found + [root / 'docs/departures/scripts/broken/blocks.gfa']


def reference(gfa):
    return 'GRCh38' if 'GRCh38' in gfa.read_text(errors='replace') else 'R'


def check(root, name, walks, gfa):
    scripts = root / 'docs/departures/scripts'
    args = {
        'verify7': [scripts / 'verify7.py', walks],
        'claims7': [scripts / 'claims7.py', walks, '--own'],
        'audit7': [scripts / 'audit7.py', walks, '--gfa', gfa, '--window', '64', '--point', '16'],
        'expand7': [scripts / 'expand7.py', walks],
        'spec8': [scripts / 'spec8.py', walks],
        'rebuild': [root / 'scripts/walks-truth.py', 'rebuild', walks, gfa],
    }[name]
    done = run(['python3', '-I'] + [str(a) for a in args])
    return done.returncode != 0 and 'Traceback' not in done.stdout + done.stderr


def builds(root):
    # every fixture under every option set: the files written, and the builds refused for a blocks row
    out, written, refused = SCRATCH / 'out', [], 0
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    for gfa in fixtures(root):
        for k, options in enumerate(OPTIONS):
            ref, prefix = reference(gfa), out / f'{gfa.stem}.{k}'
            done = run([str(SCRATCH / 'target/debug/gfa-to-tabix'), str(gfa), '--walks', '--refs', ref, *options,
                        '-o', str(prefix)])
            if done.returncode == 0:
                written.append((pathlib.Path(f'{prefix}.{ref}.walks.gz'), gfa))
            elif 'the blocks row does not read back as its piece' in done.stderr:
                refused += 1
            else:
                sys.exit(f'{gfa.name}: {done.stderr[-300:]}')
    return written, refused


def writer(routes, source):
    routes.write_text(source)
    done = run(['cargo', 'build', '--quiet', '--locked'], cwd=routes.parent.parent,
               env={**os.environ, 'CARGO_TARGET_DIR': str(SCRATCH / 'target')})
    if done.returncode:
        sys.exit(done.stderr[-2000:])


copy = SCRATCH / 'repo'
shutil.rmtree(copy, ignore_errors=True)
shutil.copytree(REPO, copy, ignore=shutil.ignore_patterns('target', '.git', '.claude'))
routes = copy / 'src/routes.rs'
source = routes.read_text()
if source.count(LOOP) != 1 or source.count(TRUE) != 1 or source.count(ROW) != 1:
    sys.exit('broken-writers.py: src/routes.rs no longer has the lines this script changes')
looped = source.replace(LOOP, LOOP.replace('(piece, walk, _) in &alone.walks', '(n, (piece, walk, _)) in alone.walks.iter().enumerate()'))
writer(routes, looped.replace(TRUE, TRUE + '            let _ = n;\n'))
written, refused = builds(copy)
passing = sum(not check(copy, name, walks, gfa) for walks, gfa in written for name in CHECKERS)
print(f'the writer as it is: {len(written)} files written, {refused} builds refused, '
      f'{passing} of {len(written) * len(CHECKERS)} checker runs pass')
through = len(written) * len(CHECKERS) - passing + refused
for what, wrong in WRONG.items():
    writer(routes, looped.replace(TRUE, f'            let bp = {wrong};\n            let _ = n;\n'))
    _, refused = builds(copy)
    print(f'hapBp as {what}')
    print(f'  with the build check: {refused} builds refused')
    writer(routes, looped.replace(TRUE, TRUE + '            let _ = n;\n').replace(ROW, f'&summary_row(piece, k, {wrong})'))
    tests = run(['cargo', 'test', '--quiet', '--locked', '--test', 'walks'], cwd=copy,
                env={**os.environ, 'CARGO_TARGET_DIR': str(SCRATCH / 'target')})
    result = next((line for line in tests.stdout.splitlines() if line.startswith('test result:')), 'no test result')
    written, _ = builds(copy)
    failing = {name: sum(check(copy, name, walks, gfa) for walks, gfa in written) for name in CHECKERS}
    print(f'  past the build check: {result.split(";")[0]}, {result.split(";")[1].strip() if ";" in result else ""}')
    print(f'  past the build check: of {len(written)} files, '
          + ', '.join(f'{name} fails {n}' for name, n in failing.items()))
    caught = refused > 0 and ' 0 failed' not in result and all(failing[name] for name in CHECKERS if name != 'verify7')
    through += not caught
sys.exit(1 if through else 0)
