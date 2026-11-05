// Rewrites a format 6 walks file into every candidate's layout, row for row.
// usage: node build.mjs <in.walks.bed.gz> <outdir> [chunk] [only=f6p,t,o,s]
import { spawn } from 'node:child_process'
import fs from 'node:fs'
import readline from 'node:readline'
import { chunkRef, decodeChunk } from '../gw/src/walkChunk.ts'
import { BgzfWriter } from './bgzf.mjs'
import { Ref, decodeIds, encodeIds, encodeWalk, decodeWalk } from './scodec.mjs'

const [input, outdir, chunkArg, onlyArg] = process.argv.slice(2)
const C = +(chunkArg ?? 65536)
const only = new Set((onlyArg ?? 'f6p,t,o,onochain,oabs,sabs,srel').split(','))
fs.mkdirSync(outdir, { recursive: true })
const on = k => only.has(k)

const out = {}
if (on('f6p')) out.f6p = new BgzfWriter(`${outdir}/f6p.bed.gz`)
if (on('t')) out.t = new BgzfWriter(`${outdir}/t.bed.gz`)
for (const m of ['o', 'onochain', 'oabs', 'sabs', 'srel']) {
  if (on(m)) {
    out[m] = new BgzfWriter(`${outdir}/${m}.walks.gz`)
    out[m + 'Idx'] = []
  }
}
const dep = on('o')
if (dep) {
  out.dep = new BgzfWriter(`${outdir}/dep.bed.gz`)
  out.depu = new BgzfWriter(`${outdir}/depu.bed.gz`)
}

const header = []
const refs = new Map() // `${seq}~${cs}` -> { gw, ref, details: Map(detail -> path) }
const stats = { chunks: 0, details: 0, departures: 0, checked: 0 }

function entry(idx, w, seq, lo, hi, kind, name, start) {
  idx.push([seq, lo, hi, kind, name, start, w.offset - start].join('\t'))
}

function emitRows(w, lines) {
  for (const l of lines) w.write(l + '\n')
}

function sLines(mode, seq, cs, rows, decoded, ref, abridgedOf) {
  const lines = []
  let lo = Infinity
  let hi = -Infinity
  const nRef = rows.filter(c => c[3] === 'ref').length
  for (const c of rows) {
    if (c[3] === 'ref') {
      const { ids, rev } = decodeIds(c[9], 'rel')
      const lengths = c[10].split(',').map(Number)
      const start = +c[6]
      const end = start + lengths.reduce((a, b) => a + b, 0)
      lo = Math.min(lo, start)
      hi = Math.max(hi, end)
      lines.push(['R', seq, start, end, c[4], c[5], c[7], encodeIds(ids, rev, mode), c[10], c[11]].join('\t'))
    } else if (c[3] === 'nodes') {
      const field = mode === 'abs' ? decodeNodeIds(c[4]).join(',') : c[4]
      lines.push(['N', seq, cs, cs + C, field, c[5]].join('\t'))
    }
  }
  const walkRows = decoded.rows.slice(abridgedOf ? 0 : nRef)
  for (const row of walkRows) {
    if (row.abridged) {
      const s = row.steps
      const ends = [0, 1].map(k => s.refStarts[k] + ref.lengths[ref.index(s.refStarts[k], s.ids[k])])
      const x = Math.min(s.refStarts[0], s.refStarts[1])
      const y = Math.max(...ends)
      lo = Math.min(lo, x)
      hi = Math.max(hi, y)
      lines.push(['A', seq, x, y, row.name, row.fragStart, row.hapOffset, row.piece, row.abridged.steps, row.abridged.bp].join('\t'))
      continue
    }
    const { walk, lo: a, hi: b } = encodeWalk(row.steps, ref, mode, cs)
    const back = decodeWalk(walk, ref, mode, cs)
    for (let k = 0; k < row.steps.ids.length; k++) {
      const same =
        back.ids[k] === row.steps.ids[k] &&
        back.rev[k] === row.steps.rev[k] &&
        (Number.isNaN(back.refStarts[k]) ? Number.isNaN(row.steps.refStarts[k]) : back.refStarts[k] === row.steps.refStarts[k])
      if (!same || back.ids.length !== row.steps.ids.length) throw new Error(`S ${mode} round trip differs: ${row.name} ${cs} step ${k}`)
    }
    stats.checked++
    lo = Math.min(lo, a)
    hi = Math.max(hi, b)
    lines.push(['W', seq, a, b, row.name, row.fragStart, row.hapOffset, row.piece, walk].join('\t'))
  }
  return { lines, lo, hi }
}

function decodeNodeIds(field) {
  let id = 0
  return field.split(',').map(t => (id += +t))
}

function refOf(rows) {
  const ref = new Ref()
  const refRows = rows.filter(c => c[3] === 'ref').sort((a, b) => +a[6] - +b[6])
  for (const c of refRows) {
    const { ids, rev } = decodeIds(c[9], 'rel')
    ref.add(ids, rev, c[10].split(',').map(Number), +c[6])
  }
  return ref
}

function extentOf(decoded, ref) {
  let lo = Infinity
  let hi = -Infinity
  for (const row of decoded.rows) {
    const s = row.steps
    for (let k = 0; k < s.ids.length; k++) {
      const r = s.refStarts[k]
      if (Number.isFinite(r)) {
        lo = Math.min(lo, r)
        hi = Math.max(hi, r + ref.lengths[ref.index(r, s.ids[k])])
      }
    }
  }
  return [lo, hi]
}

function mainChunk(seq, cs, lines) {
  stats.chunks++
  const rows = lines.map(l => l.split('\t'))
  if (out.f6p) {
    out.f6p.flush()
    emitRows(out.f6p, lines)
  }
  if (out.t) {
    out.t.flush()
    emitRows(out.t, rows.map(c => [c[0], cs, cs + C, ...c.slice(3)].join('\t')))
  }
  const needDecode = O_KINDS.some(k => out[k]) || out.sabs || out.srel
  if (!needDecode) return
  const decoded = decodeChunk(rows, undefined)
  const ref = refOf(rows)
  const abridged = rows.filter(c => c[3] === 'abridged')
  if (abridged.length) {
    const details = new Map()
    for (const c of abridged) details.set(+c[12], c[4])
    refs.set(`${seq}~${cs}`, { gw: chunkRef(rows), ref, details })
  }
  const ext = extentOf(decoded, ref)
  for (const k of O_KINDS) {
    if (!out[k]) continue
    out[k].flush()
    const start = out[k].offset
    emitRows(out[k], recode(k, rows).map(c => c.slice(3).join('\t')))
    out[k].flush()
    entry(out[k + 'Idx'], out[k], seq, ext[0], ext[1], 'tile', cs, start)
  }
  for (const m of ['sabs', 'srel']) {
    if (!out[m]) continue
    const { lines: sl, lo, hi } = sLines(m === 'sabs' ? 'abs' : 'rel', seq, cs, rows, decoded, ref)
    out[m].flush()
    const start = out[m].offset
    emitRows(out[m], sl)
    out[m].flush()
    entry(out[m + 'Idx'], out[m], seq, lo, hi, 'tile', cs, start)
  }
}

function detailRecord(sib, a, lines) {
  stats.details++
  const rows = lines.map(l => l.split('\t'))
  const tilde = sib.lastIndexOf('~')
  const seq = sib.slice(0, tilde)
  const cs = +sib.slice(tilde + 1)
  const d = a / 16384
  if (out.f6p) {
    out.f6p.flush()
    emitRows(out.f6p, lines)
  }
  if (out.t) {
    out.t.flush()
    emitRows(out.t, rows.map(c => [c[0], d * C, d * C + C, ...c.slice(3)].join('\t')))
  }
  const held = refs.get(sib)
  if (!held) return
  const path = held.details.get(d)
  const decoded = needDetailDecode() ? decodeChunk(rows, undefined, false, held.gw) : undefined
  const ext = decoded ? extentOf(decoded, held.ref) : undefined
  for (const k of O_KINDS) {
    if (!out[k]) continue
    out[k].flush()
    const start = out[k].offset
    emitRows(out[k], recode(k, rows).map(c => c.slice(3).join('\t')))
    out[k].flush()
    entry(out[k + 'Idx'], out[k], seq, ext[0], ext[1], 'detail', `${cs}:${path}`, start)
  }
  for (const m of ['sabs', 'srel']) {
    if (!out[m]) continue
    const { lines: sl, lo, hi } = sLines(m === 'sabs' ? 'abs' : 'rel', seq, cs, rows.filter(c => c[3] !== 'nodes'), decoded, held.ref, true)
    // a detail record's off-R node lengths: its own nodes row
    const nodes = rows.find(c => c[3] === 'nodes')
    const nl = nodes ? ['N', seq, cs, cs + C, m === 'sabs' ? decodeNodeIds(nodes[4]).join(',') : nodes[4], nodes[5]].join('\t') : undefined
    out[m].flush()
    const start = out[m].offset
    if (nl) out[m].write(nl + '\n')
    emitRows(out[m], sl)
    out[m].flush()
    entry(out[m + 'Idx'], out[m], seq, lo, hi, 'detail', `${cs}:${path}`, start)
  }
}

const O_KINDS = ['o', 'onochain', 'oabs']
const needDetailDecode = () => Boolean(O_KINDS.some(k => out[k]) || out.sabs || out.srel)

// format 6 rows with a dependency removed: `onochain` starts each route
// row's delta tokens from 0; `oabs` writes every id and route index absolute
function chainTokens(field, prev) {
  if (field === '.') return []
  return field.split(',').map(t => {
    const d = +t
    const r = d & 1
    prev.id += (d - r) / 2
    return prev.id * 2 + r
  })
}
function deltaTokens(handles, prev) {
  if (!handles.length) return '.'
  return handles
    .map(h => {
      const r = h & 1
      const id = (h - r) / 2
      const t = 2 * (id - prev.id) + r
      prev.id = id
      return t
    })
    .join(',')
}
function recode(kind, rows) {
  if (kind === 'o') return rows
  const prev = { id: 0 }
  return rows.map(c => {
    if (c[3] === 'route') {
      const hs = [4, 5, 6].map(k => chainTokens(c[k], prev))
      if (kind === 'onochain') {
        const p = { id: 0 }
        return [...c.slice(0, 4), ...hs.map(h => deltaTokens(h, p))]
      }
      return [...c.slice(0, 4), ...hs.map(h => (h.length ? h.join(',') : '.'))]
    }
    if (kind !== 'oabs') return c
    if (c[3] === 'ref') {
      const hs = chainTokens(c[9], { id: 0 })
      return [...c.slice(0, 9), hs.join(','), ...c.slice(10)]
    }
    if (c[3] === 'nodes') {
      let id = 0
      return [...c.slice(0, 4), c[4] === '.' ? '.' : c[4].split(',').map(t => (id += +t)).join(','), ...c.slice(5)]
    }
    if (c[3] === 'walk' && c[10] !== '.') {
      let route = 0
      const toks = c[10].split(',').map(t => {
        const m = /^(-?\d+)(.*)$/.exec(t)
        const d = +m[1]
        const f = d & 1
        route += (d - f) / 2
        return `${2 * route + f}${m[2]}`
      })
      return [...c.slice(0, 10), toks.join(','), ...c.slice(11)]
    }
    return c
  })
}

const CSI_SIZES = [C * 512, C * 64, C * 8, C]
function csiBlocks(lo, hi, each) {
  const unit = C
  let at = Math.floor(lo / unit) * unit
  const end = Math.floor((hi - 1) / unit) * unit + unit
  while (at < end) {
    const size = CSI_SIZES.find(s => at % s === 0 && at + s <= end) ?? unit
    each(Math.max(lo, at), Math.min(hi, at + size))
    at += size
  }
}

function departures(sib, lines) {
  stats.departures += lines.length
  const seq = sib.slice(0, sib.lastIndexOf('~'))
  if (out.f6p) {
    out.f6p.flush()
    emitRows(out.f6p, lines)
  }
  const records = new Map()
  for (const l of lines) {
    const c = l.split('\t')
    const key = c.slice(3).join('\t')
    const r = records.get(key)
    if (r) {
      r[0] = Math.min(r[0], +c[1])
      r[1] = Math.max(r[1], +c[2])
    } else records.set(key, [+c[1], +c[2]])
  }
  if (out.t) {
    const cut = []
    for (const [key, [lo, hi]] of records) csiBlocks(lo, hi, (a, b) => cut.push([a, b, key]))
    cut.sort((x, y) => x[0] - y[0] || x[1] - y[1])
    out.t.flush()
    emitRows(out.t, cut.map(([a, b, key]) => `${sib}\t${a}\t${b}\t${key}`))
  }
  if (dep) {
    out.dep.flush()
    emitRows(out.dep, lines.map(l => seq + l.slice(sib.length)))
    const whole = [...records].map(([key, [lo, hi]]) => [lo, hi, key]).sort((x, y) => x[0] - y[0] || x[1] - y[1])
    out.depu.flush()
    emitRows(out.depu, whole.map(([a, b, key]) => `${seq}\t${a}\t${b}\t${key}`))
  }
}

function finishHeader() {
  const text = header.join('\n') + '\n'
  for (const k of ['f6p', 't']) {
    if (out[k]) {
      out[k].write(text)
      out[k].flush()
    }
  }
  for (const k of [...O_KINDS, 'sabs', 'srel']) {
    if (!out[k]) continue
    const h = O_KINDS.includes(k) ? text : text.replace('format:i:6', `format:i:7\ttile:i:${C}`)
    out[k].write(h)
    out[k].flush()
    out[k + 'Idx'].push(['*', 0, 0, 'header', '.', 0, out[k].offset].join('\t'))
  }
  if (dep) {
    for (const k of ['dep', 'depu']) {
      out[k].write(header.filter(l => l.startsWith('#walks') || l.startsWith('#reference')).join('\n') + '\n')
      out[k].flush()
    }
  }
}

const proc = spawn('bgzip', ['-dc', '-@', '4', input])
const rl = readline.createInterface({ input: proc.stdout, crlfDelay: Infinity })
let group
let headerDone = false
function closeGroup() {
  if (!group) return
  if (group.kind === 'main') mainChunk(group.seq, group.a, group.lines)
  else if (group.kind === 'detail') detailRecord(group.seq, group.a, group.lines)
  else departures(group.seq, group.lines)
  group = undefined
}
for await (const line of rl) {
  if (line.startsWith('#')) {
    header.push(line)
    continue
  }
  if (!headerDone) {
    finishHeader()
    headerDone = true
  }
  const t1 = line.indexOf('\t')
  const t2 = line.indexOf('\t', t1 + 1)
  const seq = line.slice(0, t1)
  const a = +line.slice(t1 + 1, t2)
  const kind = seq.endsWith('~departure') ? 'dep' : seq.includes('~') ? 'detail' : 'main'
  const same = group && group.seq === seq && (kind === 'dep' || group.a === a)
  if (!same) {
    closeGroup()
    group = { kind, seq, a, lines: [] }
  }
  group.lines.push(line)
}
closeGroup()
for (const [k, w] of Object.entries(out)) {
  if (w instanceof BgzfWriter) w.close()
  else fs.writeFileSync(`${outdir}/${k.replace('Idx', '')}.walks.idx`, w.join('\n') + '\n')
}
console.log(JSON.stringify(stats))
