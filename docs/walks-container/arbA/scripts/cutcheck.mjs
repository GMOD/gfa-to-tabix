// graph-walks 5.0.2's own `cut` on each window: once over the shipped file as
// graph-walks 5 reads it, once over an S7 file through a source that
// addresses everything by the unit table. Compares fragments, departures and
// kept nodes. Adapted from arbB's harness/cutcheck.mjs.
// usage: node cutcheck.mjs <dataset files> <s7 prefix> <windows.jsonl> <out.jsonl> [every]
import fs from 'node:fs'
import zlib from 'node:zlib'
import { WalkReader } from '../gw/src/index.ts'
import { TabixIndexedFile } from '../h/node_modules/@gmod/tabix/esm/index.js'

const [files, prefix, windowsPath, outPath, everyArg] = process.argv.slice(2)
const every = +(everyArg ?? 1)
const SEQ = { mc22: 'GRCh38#0#chr22', pggbY: 'GRCh38#0#chrY' }[files]
const CONTEXT = 1000
const windows = fs.readFileSync(windowsPath, 'utf8').trim().split('\n').map(l => JSON.parse(l)).filter(w => w.i % every === 0 && (w.size < 1_000_000 || w.i % (every * 5) === 0))

const shipped = new TabixIndexedFile({ path: `in/${files}.bed.gz`, tbiPath: `in/${files}.bed.gz.tbi` })

function s7Source() {
  const file = `out/${files}/${prefix}.walks.gz`
  const fd = fs.openSync(file, 'r')
  const readRange = (off, len) => {
    const buf = Buffer.alloc(len)
    fs.readSync(fd, buf, 0, len, off)
    return zlib.gunzipSync(buf).toString().split('\n').filter(l => l && !l.startsWith('#unit'))
  }
  const dir = fs.readFileSync(file + '.idx', 'utf8').trim().split('\n').slice(1).map(l => l.split('\t'))
  const h = dir.find(c => c[0] === '#header')
  // graph-walks 5 refuses format 7; the rows it decodes are format 6's
  const header = readRange(+h[1], +h[2]).map(l => l.replace('format:i:7\ttile:i:', 'format:i:6\tchunk:i:'))
  const units = []
  for (const c of dir.filter(c => c[0] !== '#header')) {
    for (const l of readRange(+c[1], +c[2]).filter(l => l.startsWith('#entry'))) {
      const u = l.split('\t').slice(1)
      units.push({ seq: u[0], lo: +u[1], hi: +u[2], kind: u[3], name: u[4], off: +u[5], len: +u[6] })
    }
  }
  // graph-walks 5 names a chunk by its start; S7 names tiles by extent, so the
  // walk read maps to the tiles overlapping the drawn stretch and an attach
  // read [lookback, cs + 1) to the tile holding the leave base, which
  // graph-walks puts at the read's last base
  const state = { drawn: undefined, first: true }
  return {
    state,
    getHeaderLines: async () => header,
    getReferenceSequenceNames: async () => [...new Set(units.map(u => u.seq))],
    getLines: async (name, s, e, o) => {
      if (name.endsWith('~departure')) {
        const seq = name.slice(0, -'~departure'.length)
        const seen = new Set()
        for (const u of units) {
          if (u.seq === seq && u.kind === 'departures' && u.lo < e && u.hi > s) {
            for (const l of readRange(u.off, u.len)) {
              const c = l.split('\t')
              if (!seen.has(l) && +c[1] < state.drawn.end && +c[2] > state.drawn.start) {
                seen.add(l)
                o.lineCallback(`${name}\t${c.slice(1).join('\t')}`)
              }
            }
          }
        }
        return
      }
      if (name.includes('~')) {
        const [seq, cs] = name.split('~')
        const d = Math.floor(s / 16384)
        const u = units.find(u => u.seq === seq && u.kind === 'detail' && u.name === `${cs}:${d}`)
        for (const l of u ? readRange(u.off, u.len) : []) o.lineCallback(`${name}\t${s}\t${s + 1}\t${l.split('\t').slice(3).join('\t')}`)
        return
      }
      const hit = state.first
        ? units.filter(u => u.seq === name && u.kind === 'tile' && u.lo < state.drawn.end && u.hi > state.drawn.start)
        : units.filter(u => u.seq === name && u.kind === 'tile' && u.lo < e - 1 + 65536 && u.hi > s)
      state.first = false
      for (const u of hit) for (const l of readRange(u.off, u.len)) o.lineCallback(`${name}\t${u.name}\t${+u.name + 1}\t${l.split('\t').slice(3).join('\t')}`)
    },
  }
}

const stable = v => JSON.stringify(v, (k, x) => (k === 'trimmedBefore' || k === 'trimmedAfter' ? undefined : x instanceof Set ? [...x].sort() : x instanceof Map ? [...x.entries()].sort() : x))
const digest = cut => ({ fragments: cut.fragments.map(stable).sort(), departures: cut.departures.map(stable).sort(), kept: [...cut.kept].sort((a, b) => a - b) })
const only = (x, y) => {
  const s = new Set(y)
  return x.filter(v => !s.has(v)).length
}

const src = s7Source()
// BASELINE=units: the shipped file's own rows for the same units S7 selects,
// and the same departure lines, so the two cuts differ only if the rows do
function unitsBaseline(s7) {
  return {
    getHeaderLines: () => s7.getHeaderLines(),
    getReferenceSequenceNames: () => s7.getReferenceSequenceNames(),
    getLines: async (name, s, e, o) => {
      if (name.includes('~') && !name.endsWith('~departure')) return shipped.getLines(name, s, e, o)
      if (name.endsWith('~departure')) return s7.getLines(name, s, e, o)
      const names = []
      await s7.getLines(name, s, e, { lineCallback: l => names.push(+l.split('\t')[1]) })
      for (const cs of [...new Set(names)]) await shipped.getLines(name, cs, cs + 1, o)
    },
  }
}
const inner = s7Source()
const base = process.env.BASELINE === 'units' ? unitsBaseline(inner) : shipped
const a = new WalkReader(base)
const b = new WalkReader(src)
const lifted = { stepBudget: Infinity, byteBudget: Infinity, departureByteBudget: Infinity, attachFetches: 64 }
const out = fs.createWriteStream(outPath)
let same = 0
let n = 0
for (const w of windows) {
  const region = { refName: SEQ, start: w.start, end: w.end }
  src.state.drawn = { start: Math.max(0, w.start - CONTEXT), end: w.end + CONTEXT }
  src.state.first = true
  inner.state.drawn = src.state.drawn
  inner.state.first = true
  const row = { size: w.size, start: w.start, tag: w.tag }
  try {
    const x = digest(await a.cut(SEQ, region, lifted))
    const y = digest(await b.cut(SEQ, region, lifted))
    row.identical = stable(x) === stable(y)
    row.fragmentsIdentical = stable(x.fragments) === stable(y.fragments)
    row.fragments = x.fragments.length
    row.departures = x.departures.length
    if (!row.identical)
      row.diff = {
        fragments: [only(x.fragments, y.fragments), only(y.fragments, x.fragments)],
        departures: [only(x.departures, y.departures), only(y.departures, x.departures)],
        kept: [only(x.kept, y.kept), only(y.kept, x.kept)],
      }
    if (process.env.CUTDEBUG && !row.identical) {
      const ky = new Set(y.kept)
      console.error('KEPT SHIPPED ONLY', x.kept.filter(v => !ky.has(v)).slice(0, 5), 'drawn', src.state.drawn)
      const sx = new Set(y.departures)
      const sy = new Set(x.departures)
      console.error('SHIPPED ONLY', x.departures.filter(v => !sx.has(v)).slice(0, 1).map(v => v.slice(0, 700)))
      console.error('S7 ONLY', y.departures.filter(v => !sy.has(v)).slice(0, 1).map(v => v.slice(0, 700)))
    }
    if (row.identical) same++
  } catch (e) {
    row.error = String(e.message).slice(0, 160)
  }
  n++
  out.write(JSON.stringify(row) + '\n')
}
out.end()
console.error(`${prefix} ${files}: ${same}/${n} identical`)
