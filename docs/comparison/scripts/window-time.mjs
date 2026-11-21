#!/usr/bin/env node
// window-time.mjs <graph-walks checkout> WINDOWS.tsv SEQUENCE OUT.tsv
//   --walks FILE --walks-bases FILE [--http URL]
//   --gfaidx BIN INDEX REGION_NAME [--reference SAMPLE] [--runs N] [--max-load L]
//
// Times each window of WINDOWS.tsv (windows.py's, one tile at each `start`)
// in every case below, interleaved: each run goes over every window, and
// within a window the order of the cases rotates from run to run and window
// to window. One untimed pass over every window in every case comes first,
// and each case is timed three times (--runs) per window.
//
// Cases:
//   walks        @jbrowse/graph-walks cutting the tile from the walk file:
//                every haplotype, context 0 and no budget, so no window is
//                refused, and abridged pieces left unexpanded, as a viewer
//                first draws them
//   walks_bases  the same from the walk file with bases, asking for them
//   browser      CUT_PRESETS.browser on the walk file, every haplotype: 1 kb
//                of context either side and the default budgets, as JBrowse's
//                graph plugin and BandageJS cut. A window over a budget is
//                refused, with a RegionTooLargeError or DepartureReadError,
//                and its row records the refusal and the time it took
//   http         the walks case from the http(s) URL, by range request
//   gfaidx       `gfaidx get_region --mode all --with_coords` as windows.py
//                runs it, the whole command from process start to the GFA on
//                disk
//   gfaidx_gap   the same with --haplotype_gap 10kb
//
// For a walk case, per window and run:
//   open_ms    a new reader: the directory, the header unit and the
//              sequence's table, then the cut
//   cut_ms     the cut on a reader that is open and has cut another window
//   tables_ms  graph.tables on that cut's result, the node, link and walk
//              tables a viewer draws from
//   bytes, ranges  what the open reader read from local disk for the cut
// and what the cut returned: fragments, steps, departures, the placeholder
// steps that stand for runs of an abridged piece, the distinct nodes the
// fragments step on, and a SHA-1 of their ids, sorted as strings and joined
// by newlines, to compare with windows.py's of gfaidx's segments.
//
// Before each window it waits while /proc/loadavg's 1-minute load is at or
// over --max-load (3); after 6 hours of waiting in one stretch it accepts
// load under --max-load plus 1. Each row records the load it began at.

import { spawnSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { existsSync, rmSync, statSync } from 'node:fs'
import { open, readFile, writeFile } from 'node:fs/promises'
import { join, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

class LocalFile {
  constructor(path, log) {
    this.source = path
    this.log = log
    this.handle = open(path, 'r')
  }

  async read(length, position = 0) {
    const buffer = new Uint8Array(length)
    const { bytesRead } = await (
      await this.handle
    ).read(buffer, 0, length, position)
    this.log.push([position, position + bytesRead])
    return buffer.subarray(0, bytesRead)
  }

  readFile(options) {
    return readFile(this.source, options)
  }

  async stat() {
    return (await this.handle).stat()
  }

  async close() {
    await (await this.handle).close()
  }
}

function flag(argv, name, count = 1) {
  const at = argv.indexOf(name)
  return at < 0 ? [] : argv.slice(at + 1, at + 1 + count)
}

const argv = process.argv.slice(2)
const [checkout, windowsPath, sequence, outPath] = argv
const [walks] = flag(argv, '--walks')
const [walksBases] = flag(argv, '--walks-bases')
const [url] = flag(argv, '--http')
const [gfaidxBin, gfaidxIndex, regionName] = flag(argv, '--gfaidx', 3)
const [reference] = flag(argv, '--reference')
const runs = Number(flag(argv, '--runs')[0] ?? 3)
const maxLoad = Number(flag(argv, '--max-load')[0] ?? 3)

const { WalkReader, isPlaceholder, CUT_PRESETS } = await import(
  pathToFileURL(join(resolve(checkout), 'src/index.ts')).href
)
const tile = Number(
  /\ttile:i:(\d+)/.exec(await readFile(`${walks}.idx`, 'utf8'))[1],
)
const [header, ...lines] = (await readFile(windowsPath, 'utf8'))
  .trim()
  .split('\n')
const startColumn = header.split('\t').indexOf('start')
const starts = lines.map(line => Number(line.split('\t')[startColumn]))
const others = starts.map((_, i) => starts[(i + 1) % starts.length])
const region = start => ({ start, end: start + tile })
const unbounded = {
  context: 0,
  stepBudget: Infinity,
  byteBudget: Infinity,
  departureByteBudget: Infinity,
}

async function withReader(source, run) {
  const log = []
  if (/^https?:/.test(source)) {
    return run(WalkReader.open(source), log)
  }
  const files = {
    data: new LocalFile(source, log),
    directory: new LocalFile(`${source}.idx`, log),
  }
  try {
    return await run(WalkReader.fromFilehandles(files), log)
  } finally {
    await files.data.close()
    await files.directory.close()
  }
}

function merged(intervals) {
  const out = []
  for (const [lo, hi] of intervals.toSorted((a, b) => a[0] - b[0])) {
    const last = out.at(-1)
    if (last && lo <= last[1]) {
      last[1] = Math.max(last[1], hi)
    } else if (hi > lo) {
      out.push([lo, hi])
    }
  }
  return out
}

const isRefusal = e =>
  e?.regionTooLarge === true || e?.name === 'DepartureReadError'

async function timed(run) {
  const began = performance.now()
  try {
    const result = await run()
    return { ms: performance.now() - began, result }
  } catch (e) {
    if (!isRefusal(e)) {
      throw e
    }
    return { ms: performance.now() - began, refusal: e }
  }
}

async function measureWalk(source, options, start, other) {
  const fresh = await timed(() =>
    withReader(source, reader => reader.cut(sequence, region(start), options)),
  )
  const warm = await withReader(source, async (reader, log) => {
    await reader.cut(sequence, region(other), options).catch(e => {
      if (!isRefusal(e)) {
        throw e
      }
    })
    const from = log.length
    const cut = await timed(() =>
      reader.cut(sequence, region(start), options),
    )
    return { ...cut, reads: merged(log.slice(from)) }
  })
  const row = {
    open_ms: fresh.ms.toFixed(1),
    cut_ms: warm.ms.toFixed(1),
    bytes: /^https?:/.test(source)
      ? ''
      : warm.reads.reduce((n, [lo, hi]) => n + hi - lo, 0),
    ranges: /^https?:/.test(source) ? '' : warm.reads.length,
  }
  if (warm.refusal) {
    return {
      ...row,
      status: 'refused',
      refusal: `${warm.refusal.name}: ${warm.refusal.message}`,
    }
  }
  const { graph, kept, fragments, departures, gaps } = warm.result
  const tables = await timed(() =>
    graph.tables(kept, fragments, departures, gaps),
  )
  const stepped = new Set()
  for (const f of fragments) {
    for (const id of f.ids) {
      stepped.add(id)
    }
  }
  const ids = [...stepped].filter(id => !isPlaceholder(id)).map(String)
  return {
    ...row,
    status: 'ok',
    tables_ms: tables.ms.toFixed(1),
    fragments: fragments.length,
    steps: fragments.reduce((n, f) => n + f.ids.length, 0),
    placeholders: fragments.reduce(
      (n, f) => n + f.ids.filter(isPlaceholder).length,
      0,
    ),
    nodes: ids.length,
    departures: departures.length,
    nodes_sha1: createHash('sha1')
      .update(ids.toSorted().join('\n'))
      .digest('hex'),
  }
}

const gfa = resolve(`${outPath}.region.gfa`)

function measureGfaidx(start, extra) {
  const command = [
    'get_region',
    gfaidxIndex,
    `${regionName}:${start}-${start + tile}`,
    gfa,
    '--mode',
    'all',
    '--with_coords',
    ...(reference ? ['--reference', reference] : []),
    ...extra,
  ]
  if (existsSync(gfa)) {
    rmSync(gfa)
  }
  const began = performance.now()
  const done = spawnSync(gfaidxBin, command, { stdio: 'ignore' })
  const ms = performance.now() - began
  return {
    open_ms: ms.toFixed(1),
    status: done.status === 0 ? 'ok' : `exit ${done.status ?? done.signal}`,
    gfa_bytes: existsSync(gfa) ? statSync(gfa).size : 0,
  }
}

const cases = [
  ['walks', (s, o) => measureWalk(walks, unbounded, s, o)],
  [
    'walks_bases',
    (s, o) =>
      measureWalk(walksBases, { ...unbounded, sequences: true }, s, o),
  ],
  ['browser', (s, o) => measureWalk(walks, CUT_PRESETS.browser, s, o)],
  ...(url ? [['http', (s, o) => measureWalk(url, unbounded, s, o)]] : []),
  ['gfaidx', s => measureGfaidx(s, [])],
  ['gfaidx_gap', s => measureGfaidx(s, ['--haplotype_gap', '10kb'])],
]

async function load1() {
  return Number((await readFile('/proc/loadavg', 'utf8')).split(' ')[0])
}

async function quiet() {
  const began = Date.now()
  let load = await load1()
  while (load >= (Date.now() - began > 6 * 3600e3 ? maxLoad + 1 : maxLoad)) {
    process.stderr.write(`${new Date().toISOString()} load ${load}, waiting\n`)
    await new Promise(r => setTimeout(r, 30000))
    load = await load1()
  }
  return load
}

process.stderr.write(`${new Date().toISOString()} untimed pass\n`)
for (const [i, start] of starts.entries()) {
  await quiet()
  for (const [, run] of cases) {
    await run(start, others[i])
  }
}

const cols = [
  'start',
  'case',
  'run',
  'load1',
  'status',
  'open_ms',
  'cut_ms',
  'tables_ms',
  'bytes',
  'ranges',
  'fragments',
  'steps',
  'placeholders',
  'nodes',
  'departures',
  'nodes_sha1',
  'gfa_bytes',
  'refusal',
]
const out = [cols.join('\t')]
for (let r = 0; r < runs; r++) {
  for (const [i, start] of starts.entries()) {
    const load = await quiet()
    for (let k = 0; k < cases.length; k++) {
      const [name, run] = cases[(k + r + i) % cases.length]
      const row = {
        start,
        case: name,
        run: r + 1,
        load1: load,
        ...(await run(start, others[i])),
      }
      out.push(cols.map(c => row[c] ?? '').join('\t'))
    }
  }
  await writeFile(outPath, `${out.join('\n')}\n`)
  process.stderr.write(`${new Date().toISOString()} run ${r + 1} done\n`)
}
if (existsSync(gfa)) {
  rmSync(gfa)
}
