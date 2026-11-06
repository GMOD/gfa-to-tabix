import subprocess, json, sys, re, pathlib
GW = pathlib.Path(__file__).parent / 'gw'
M = [
 ('m01 dedupe departure lines', 'src/walkReader.ts', 'for (const line of new Set(lines)) {', 'for (const line of lines) {'),
 ('m02 keep lines overlapping D', 'src/walkReader.ts', "      cols[3] === 'departure' &&\n      +cols[1]! < span.end &&\n      +cols[2]! > span.start", "      cols[3] === 'departure'"),
 ('m03 skip length 0', 'src/walkReader.ts', '  unit.length > 0 && unit.start < span.end', '  unit.start < span.end'),
 ('m04 merge touching ranges', 'src/walkFile.ts', 'if (run && last && last.offset + last.length === unit.offset) {', 'if (false) {'),
 ('m05 refuse bytes mismatch', 'src/walkFile.ts', '} else if (size > 0 && directory.bytes !== size) {', '} else if (false) {'),
 ('m06 refuse #walks mismatch', 'src/walkFile.ts', "if (header[0] !== directory.walks.join('\\t')) {", 'if (false) {'),
 ('m07 refuse format != 7', 'src/walkFile.ts', '  if (format !== WALK_FORMAT) {', '  if (false) {'),
 ('m08 token split rounds down', 'src/walkChunk.ts', '      const r = d & 1\n      previous.id += (d - r) / 2', '      const r = Math.abs(d % 2)\n      previous.id += Math.trunc(d / 2)'),
 ('m09 @k exit tie later', 'src/walkChunk.ts', 'return after - i <= i - before ? after : before', 'return after - i < i - before ? after : before'),
 ('m10 :k default includes current', 'src/walkChunk.ts', 'if (forward && j >= i && this.handles[j] === target) {', 'if (forward && j > i && this.handles[j] === target) {'),
 ('m11 R in hapOffset order', 'src/walkChunk.ts', "rows.filter(c => c[3] === 'ref').sort((a, b) => +a[6]! - +b[6]!)", "rows.filter(c => c[3] === 'ref')"),
 ('m12 :k honoured', 'src/walkChunk.ts', '      copy === NONE ? path.reach(i!, h, target) : path.copy(target, copy)', '      path.reach(i!, h, target)'),
 ('m13 @k exit honoured', 'src/walkChunk.ts', '    i = copy === NONE ? path.nearest(h, i) : path.copy(h, copy)', '    i = path.nearest(h, i)'),
 ('m14 start@k honoured', 'src/walkChunk.ts', '  let i = startCopy === NONE ? path.first(h) : path.copy(h, startCopy)', '  let i = path.first(h)'),
 ('m15 abridged end nearest start', 'src/walkChunk.ts', '        ? path.nearest(h1, i0)', '        ? path.first(h1)'),
 ('m16 attach uses ownTiles', 'src/walkReader.ts', "u => u.kind === 'tile' && u.length > 0 && ownTiles.includes(Number(u.name)),", "u => false,"),
 ('m17 place: pass over window first', 'src/walkRows.ts', '  node.onWindow !== held.onWindow\n    ? node.onWindow\n    :', ''),
 ('m18 place: path sorting first', 'src/walkRows.ts', '        node.refName < held.refName ||\n', ''),
 ('m19 join only consecutive pieces', 'src/walkRows.ts', '        i === pieces.length ||\n        pieces[i]!.piece !== pieces[i - 1]!.piece + 1', '        i === pieces.length'),
 ('m20 holes squeezed', 'src/walkReader.ts', '          squeeze: squeezer(header.holes, refName),', ''),
 ('m21 attach skips tile already decoded for name', 'src/walkReader.ts', '          if (!decodedFor(unit, name)) {', '          if (true) {'),
 ('m22 tiles by extent not floor', 'src/walkReader.ts', "    const tiles = units.filter(u => u.kind === 'tile' && overlaps(u, drawn))", "    const tiles = units.filter(u => u.kind === 'tile' && u.length > 0 && Number(u.name) < drawn.end && Number(u.name) + tile > drawn.start)"),
 ('m23 fromSteps only within a piece', 'src/walkRows.ts', '    for (let p = 0; p + 1 < bounds.length; p++) {\n      let last = -1\n      for (let i = bounds[p]!; i < bounds[p + 1]!; i++) {\n        const start = refStarts[i]!', '    for (let p = 0; p < 1; p++) {\n      let last = -1\n      for (let i = 0; i < ids.length; i++) {\n        const start = refStarts[i]!'),
 ('m24 abridged stays abridged in attach', 'src/walkReader.ts', '        if (row.abridged && expand?.(row.name)) {', '        if (row.abridged && (only !== undefined || expand?.(row.name))) {'),
 ('m25 drawn widened by every pass (R1)', 'src/walkRows.ts', '  if (drawn) {\n    for (const run of runs) {', '  if (false) {\n    for (const run of runs) {'),
 ('m26 records keyed by name not text', 'src/walkReader.ts', 'const record = parseDepartureRow(cols)\n      if (keep', 'const record = parseDepartureRow(cols)\n      if (records.some(r => r.name === record.name && r.hapStart === record.hapStart)) continue\n      if (keep'),
 ('m27 detail decodes against tile R', 'src/walkReader.ts', '        opts.sequences,\n        ref,\n      )', '        opts.sequences,\n      )'),
 ('m28 header line 1 compare ignores bytes field position', 'src/walkFile.ts', "walks: fields.filter(f => !f.startsWith('bytes:i:')),", "walks: fields,"),
 ('m29 passes dot means all 1', 'src/walkChunk.ts', "field === '.' ? new Array<number>(n).fill(1) : numbers(field ?? '')", "numbers(field ?? '')"),
 ('m30 route tokens chained across rows', 'src/walkChunk.ts', '    } else if (cols[3] === \'route\') {\n      const entry = tokens(cols[4]!, previous, [])', '    } else if (cols[3] === \'route\') {\n      previous.id = 0\n      const entry = tokens(cols[4]!, previous, [])'),
 ('m31 ownBp>missingBp gate (0 bp own step)', 'src/walkRows.ts', 'if (d.ownBp > d.missingBp && d.ownBp <= attachBp) {', 'if (d.ownBp <= attachBp) {'),
 ('m32 blocks by overlap', 'src/walkReader.ts', "      u => u.kind === 'departures' && overlaps(u, drawn),\n    )\n    if (Number.isFinite(byteBudget)) {", "      u => u.kind === 'departures' && u.length > 0,\n    )\n    if (Number.isFinite(byteBudget)) {"),
 ('m33 refuse unit without #unit line', 'src/walkFile.ts', "if (!head?.startsWith('#unit\\t')) {", 'if (false) {'),
 ('m35 D includes context', 'src/walkReader.ts', '    const drawn = drawnSpan(region, context)\n    const tiles', '    const drawn = drawnSpan(region, 0)\n    const tiles'),
 ('m37 first route without entry emits interior first', 'src/walkChunk.ts', "    choices.length > 0 &&\n    orientedEntry(routeOf(choices[0]!), choices[1] === 1) === NONE", '    false'),
 ('m38 tail follows R the way the step reads it', 'src/walkChunk.ts', '    const forward = path.handles[i] === h\n    const j = i + (forward ? tail : -tail)', '    const forward = true\n    const j = i + (forward ? tail : -tail)'),
 ('m39 route flip', 'src/walkChunk.ts', "    const flip = choices[k + 1] === 1\n    const route = routeOf(index)", "    const flip = false\n    const route = routeOf(index)"),
]
files = ['src/walkReader.test.ts', 'src/walkRows.test.ts', 'src/walkDeparture.test.ts']
only = sys.argv[1:] 
for name, path, old, new in M:
    if only and not any(name.startswith(o) for o in only): continue
    p = GW / path
    text = p.read_text()
    if text.count(old) != 1:
        print(f'{name}: PATTERN COUNT {text.count(old)}'); continue
    p.write_text(text.replace(old, new))
    try:
        r = subprocess.run(['./node_modules/.bin/vitest', 'run', *files, '--reporter=json', '--outputFile', str(GW/'out.json')], cwd=GW, capture_output=True, text=True, timeout=300)
        try:
            j = json.loads((GW/'out.json').read_text())
            failed = [a['title'] for t in j['testResults'] for a in t['assertionResults'] if a['status'] != 'passed']
        except Exception as e:
            failed = ['PARSE ' + r.stdout[-300:] + r.stderr[-300:]]
    finally:
        p.write_text(text)
    print(f'{name}: {len(failed)} failing', json.dumps(failed[:4]))
