// graph-walks 6's cut over a format 7 file against graph-walks 5.0.2's cut
// over the format 6 rows of the same units (arbiter A's BASELINE=units, from
// docs/walks-container/arbA/scripts/cutcheck.mjs), and against arbiter A's
// copy of 5.0.2 with the attach-decode fix. Compares fragments (without
// trimmedBefore/After), departures and kept nodes, and counts graph-walks 6's
// reads per window.
// usage: node cut7check.mjs <mc22|pggbY> <windows.jsonl> <out.jsonl>
import fs from 'node:fs'
import zlib from 'node:zlib'
import { LocalFile } from './gw6/node_modules/generic-filehandle2/esm/index.js'
import { WalkReader as Reader6 } from './gw6/src/index.ts'
import { WalkReader as Reader5 } from './gw5/src/index.ts'
import { WalkReader as Reader5fixed } from '../arb-arbA/gw/src/index.ts'
import { TabixIndexedFile } from './gw5/node_modules/@gmod/tabix/esm/index.js'

const [files, windowsPath, outPath] = process.argv.slice(2)
const SEQ = { mc22: 'GRCh38#0#chr22', pggbY: 'GRCh38#0#chrY' }[files]
const CONTEXT = 1000
const S7 = process.env.S7 ? process.env.S7.replace("{d}", files) : `../arb-arbA/out/${files}/s7.walks.gz`
const windows = fs.readFileSync(windowsPath, 'utf8').trim().split('\n').map(l => JSON.parse(l)).filter(w => w.size < 1_000_000)
const shipped = new TabixIndexedFile({ path: `../arb-arbA/in/${files}.bed.gz`, tbiPath: `../arb-arbA/in/${files}.bed.gz.tbi` })

// arbiter A's s7Source and unitsBaseline, unchanged in what they select
function s7Source() {
  const fd = fs.openSync(S7, 'r')
  const readRange = (off, len) => {
    const buf = Buffer.alloc(len)
    fs.readSync(fd, buf, 0, len, off)
    return zlib.gunzipSync(buf).toString().split('\n').filter(l => l && !l.startsWith('#unit'))
  }
  const dir = fs.readFileSync(S7 + '.idx', 'utf8').trim().split('\n').slice(1).map(l => l.split('\t'))
  const h = dir.find(c => c[0] === '#header')
  const header = readRange(+h[1], +h[2]).map(l => l.replace('format:i:7\ttile:i:', 'format:i:6\tchunk:i:'))
  const units = []
  for (const c of dir.filter(c => c[0] !== '#header')) {
    for (const l of readRange(+c[1], +c[2]).filter(l => l.startsWith('#entry'))) {
      const u = l.split('\t').slice(1)
      units.push({ seq: u[0], lo: +u[1], hi: +u[2], kind: u[3], name: u[4], off: +u[5], len: +u[6] })
    }
  }
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
      const hit = state.first
        ? units.filter(u => u.seq === name && u.kind === 'tile' && u.lo < state.drawn.end && u.hi > state.drawn.start)
        : units.filter(u => u.seq === name && u.kind === 'tile' && u.lo < e - 1 + 65536 && u.hi > s)
      state.first = false
      for (const u of hit) for (const l of readRange(u.off, u.len)) o.lineCallback(`${name}\t${u.name}\t${+u.name + 1}\t${l.split('\t').slice(3).join('\t')}`)
    },
  }
}
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

class Counted extends LocalFile {
  reads = []
  async read(length, position = 0, opts) {
    this.reads.push([position, length])
    return super.read(length, position, opts)
  }
}

// graph-walks 5 names a detail record by its sibling sequence and d × 16384,
// graph-walks 6 by its unit's name, cs:d; both become cs:d
const detailName = x => (x.refName.includes('~') ? `${x.refName.split('~')[1]}:${x.start / 16384}` : x.name)
const stable = v => JSON.stringify(v, (k, x) => (k === 'trimmedBefore' || k === 'trimmedAfter' ? undefined : k === 'detail' ? detailName(x) : x instanceof Set ? [...x].sort() : x instanceof Map ? [...x.entries()].sort() : ArrayBuffer.isView(x) ? [...x] : x))
const digest = cut => ({ fragments: cut.fragments.map(stable).sort(), departures: cut.departures.map(stable).sort(), kept: [...cut.kept].sort((a, b) => a - b) })
const onlyIn = (x, y) => {
  const s = new Set(y)
  return x.filter(v => !s.has(v))
}
const compare = (x, y) => {
  const out = { identical: stable(x) === stable(y) }
  if (!out.identical) {
    out.fragments = [onlyIn(x.fragments, y.fragments).length, onlyIn(y.fragments, x.fragments).length]
    out.departures = [onlyIn(x.departures, y.departures).length, onlyIn(y.departures, x.departures).length]
    out.kept = [onlyIn(x.kept, y.kept).length, onlyIn(y.kept, x.kept).length]
    const name = v => JSON.parse(v).name
    out.names = [...new Set([...onlyIn(x.fragments, y.fragments), ...onlyIn(y.fragments, x.fragments), ...onlyIn(x.departures, y.departures), ...onlyIn(y.departures, x.departures)].map(name))].slice(0, 6)
    out.depOnlyBase = onlyIn(x.departures, y.departures).slice(0, 2).map(v => v.slice(0, 400))
    out.depOnly6 = onlyIn(y.departures, x.departures).slice(0, 2).map(v => v.slice(0, 400))
  }
  return out
}

const lifted = { stepBudget: Infinity, byteBudget: Infinity, departureByteBudget: Infinity, attachFetches: 64 }
const data = new Counted(S7)
const reader6 = Reader6.fromFilehandles({ data, directory: new LocalFile(`${S7}.idx`) })
await reader6.header()
const units = await reader6.units(SEQ)
data.reads = []
const src = s7Source()
const srcFixed = s7Source()
const reader5 = new Reader5(unitsBaseline(src))
const reader5fixed = new Reader5fixed(unitsBaseline(srcFixed))
const out = fs.createWriteStream(outPath)
const tally = { n: 0, same5: 0, sameFixed: 0, errors: 0 }
for (const w of windows) {
  const region = { start: w.start, end: w.end }
  const row = { size: w.size, i: w.i, start: w.start, tag: w.tag }
  try {
    for (const s of [src, srcFixed]) {
      s.state.drawn = { start: Math.max(0, w.start - CONTEXT), end: w.end + CONTEXT }
      s.state.first = true
    }
    const base = digest(await reader5.cut(SEQ, region, lifted))
    for (const s of [src, srcFixed]) s.state.first = true
    const fixed = digest(await reader5fixed.cut(SEQ, region, lifted))
    data.reads = []
    const mine = digest(await reader6.cut(SEQ, region, lifted))
    row.reads = data.reads.length
    row.bytes = data.reads.reduce((s, [, l]) => s + l, 0)
    row.first = await reader6.bytesFor(SEQ, region)
    row.fragments = mine.fragments.length
    row.departures = mine.departures.length
    row.vs5 = compare(base, mine)
    row.vsFixed = compare(fixed, mine)
    tally.same5 += row.vs5.identical
    tally.sameFixed += row.vsFixed.identical
  } catch (e) {
    row.error = String(e.stack).slice(0, 400)
    tally.errors++
  }
  tally.n++
  out.write(JSON.stringify(row) + '\n')
}
out.end()
console.log(JSON.stringify({ files, windows: windowsPath, units: units.length, ...tally }))
