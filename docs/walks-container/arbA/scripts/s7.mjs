// S7: S with every data line starting `seq start end`, the true extent of
// what it describes, and the unit table split into one section per
// sequence at the end of the data file, found through a tiny directory.
// usage: node s7.mjs <outdir>
//   reads o.walks.gz/.idx (format 6 rows, key columns dropped) and
//   s.walks.gz/.idx (its departure groups); writes s7.walks.gz and
//   s7.walks.gz.idx
import fs from 'node:fs'
import zlib from 'node:zlib'
import { chunkRef, decodeChunk } from '../gw/src/walkChunk.ts'
import { BgzfWriter } from './bgzf.mjs'

const [dir] = process.argv.slice(2)
const OUT = process.env.OUT ?? 's7'
const read = name => ({
  data: fs.readFileSync(`${dir}/${name}.walks.gz`),
  table: fs
    .readFileSync(`${dir}/${name}.walks.idx`, 'utf8')
    .trim()
    .split('\n')
    .map(l => l.split('\t')),
})
const o = read('o')
const s = read('s')
const text = (src, e) => zlib.gunzipSync(src.data.subarray(+e[5], +e[5] + +e[6])).toString()
const linesOf = (src, e) => text(src, e).split('\n').filter(Boolean)


// The leading `seq start end` of each row: a walk or abridged piece's span on
// R (first base of its first placed step to last base of its last); the
// unit's extent for its dictionary rows (`ref`, `nodes`, `route`). The unit's
// extent is the union of its ref rows' spans and its pieces' spans.
function extents(rows, decoded, lengthOf) {
  const spanOfSteps = st => {
    let lo = Infinity
    let hi = -Infinity
    for (let k = 0; k < st.ids.length; k++) {
      const r = st.refStarts[k]
      if (Number.isFinite(r)) {
        lo = Math.min(lo, r)
        hi = Math.max(hi, r + lengthOf(st.ids[k]))
      }
    }
    return [lo, hi]
  }
  let unit = [Infinity, -Infinity]
  const grow = ([a, b]) => {
    if (Number.isFinite(a)) unit = [Math.min(unit[0], a), Math.max(unit[1], b)]
  }
  const walkRows = decoded.rows.filter(r => !r.isRef)
  let w = 0
  const own = rows.map(c => {
    if (c[0] === 'ref') {
      const start = +c[3]
      grow([start, start + c[7].split(',').reduce((a, b) => a + +b, 0)])
      return undefined
    }
    if (c[0] === 'walk' || c[0] === 'abridged') {
      const span = spanOfSteps(walkRows[w++].steps)
      grow(span)
      return span
    }
    return undefined
  })
  return { rows: own.map(e => e ?? unit), unit }
}

function decodeTile(rows, ref) {
  const withKey = rows.map(c => ['.', '0', '1', ...c])
  const decoded = decodeChunk(withKey, undefined, false, ref)
  const nRef = ref ? 0 : rows.filter(c => c[0] === 'ref').length
  decoded.rows.forEach((r, i) => {
    r.isRef = i < nRef
  })
  return { decoded, withKey }
}

const bad = name => /[\t\n]/.test(name) || name.startsWith('#')
const w = new BgzfWriter(`${dir}/${OUT}.walks.gz.tmp`)
const directory = []
const header = text(o, o.table.find(e => e[3] === 'header'))
  .split('\n')
  .filter(l => l && !l.startsWith('#long'))
  .map(l => (l.startsWith('#walks') ? l.replace('format:i:6\tchunk:i:', 'format:i:7\ttile:i:').replace(/\tmaxnode:i:\d+/, '') : l))
const walksLine = header[0]
w.write(header.join('\n') + '\n')
w.flush()
directory.push(['#header', 0, w.offset].join('\t'))
const seqs = [...new Set(o.table.filter(e => e[0] !== '*').map(e => e[0]))]
let checked = 0
// one unit: an in-stream `#unit` line, its rows, ended on a gzip member
function unit(units, seq, lo, hi, kind, name, lines) {
  const start = w.offset
  w.write(['#unit', seq, lo, hi, kind, name].join('\t') + '\n')
  for (const l of lines) w.write(l + '\n')
  w.flush()
  units.push([seq, lo, hi, kind, name, start, w.offset - start])
}
for (const seq of seqs) {
  if (bad(seq)) throw new Error(`a sequence name with a tab, newline or leading #: ${seq}`)
  const units = []
  const refs = new Map()
  const items = []
  for (const e of o.table.filter(e => e[0] === seq && e[3] === 'tile')) items.push({ start: +e[4], order: 0, e })
  for (const e of s.table.filter(e => e[0] === seq && e[3] === 'departures')) items.push({ start: +e[1], order: +e[4], e, dep: true })
  items.sort((a, b) => a.start - b.start || a.order - b.order)
  for (const it of items) {
    if (it.dep) {
      unit(units, seq, it.e[1], it.e[2], 'departures', it.e[4], linesOf(s, it.e))
      continue
    }
    const cs = +it.e[4]
    const rows = linesOf(o, it.e).map(l => l.split('\t'))
    const { decoded, withKey } = decodeTile(rows)
    const ext = extents(rows, decoded, id => decoded.chunk.lengths.get(id))
    const details = new Map()
    for (const c of rows) {
      if (c[0] === 'abridged') details.set(c[1], +c[9])
      if (c[0] === 'walk' || c[0] === 'abridged' || c[0] === 'ref') if (bad(c[1])) throw new Error(`a path name with a tab, newline or leading #: ${c[1]}`)
    }
    if (details.size) refs.set(cs, { ref: chunkRef(withKey), details })
    if (ext.unit[0] !== +it.e[1] || ext.unit[1] !== +it.e[2]) throw new Error(`tile ${cs} extent differs from O's`)
    checked++
    unit(units, seq, ext.unit[0], ext.unit[1], 'tile', cs, rows.map((c, k) => [seq, ...ext.rows[k], ...c].join('\t')))
  }
  for (const e of o.table.filter(e => e[0] === seq && e[3] === 'detail')) {
    const [cs, path] = [+e[4].split(':')[0], e[4].slice(e[4].indexOf(':') + 1)]
    const held = refs.get(cs)
    const d = held.details.get(path)
    const rows = linesOf(o, e).map(l => l.split('\t'))
    const { decoded } = decodeTile(rows, held.ref)
    const ext = extents(rows, decoded, id => decoded.chunk.lengths.get(id) ?? held.ref.lengths.get(id))
    unit(units, seq, ext.unit[0], ext.unit[1], 'detail', `${cs}:${d}`, rows.map((c, k) => [seq, ...ext.rows[k], ...c].join('\t')))
  }
  // the sequence's unit table: a unit of kind `table`, listing every unit
  // before it in file order
  const hi = Math.max(0, ...units.map(u => +u[2]))
  const tableStart = w.offset
  unit([], seq, 0, hi, 'table', '.', units.map(u => ['#entry', ...u].join('\t')))
  directory.push([seq, tableStart, w.offset - tableStart].join('\t'))
}
w.close()
const bytes = fs.statSync(`${dir}/${OUT}.walks.gz.tmp`).size
fs.renameSync(`${dir}/${OUT}.walks.gz.tmp`, `${dir}/${OUT}.walks.gz`)
fs.writeFileSync(`${dir}/${OUT}.walks.gz.idx.tmp`, [`${walksLine}\tbytes:i:${bytes}`, ...directory].join('\n') + '\n')
fs.renameSync(`${dir}/${OUT}.walks.gz.idx.tmp`, `${dir}/${OUT}.walks.gz.idx`)
console.log(JSON.stringify({ tiles: checked, sequences: directory.length - 1, bytes }))
