// S: one BGZF file and one table. Tiles and detail records as O has them;
// departure records filed over their end nodes' true extent and listed in
// every block of an aligned tile pyramid they overlap, each block one table
// entry. usage: node sfinal.mjs <outdir> [tile]
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import zlib from 'node:zlib'
import { BgzfWriter } from './bgzf.mjs'

const [dir, tileArg, srcName = 'o', outName = 's'] = process.argv.slice(2)
const C = +(tileArg ?? 65536)
const U = C * +(process.env.UNIT ?? 1)
const SIZES = [U * 512, U * 64, U * 8, U]

const src = fs.readFileSync(`${dir}/${srcName}.walks.gz`)
const table = fs
  .readFileSync(`${dir}/${srcName}.walks.idx`, 'utf8')
  .trim()
  .split('\n')
  .map(l => l.split('\t'))
const text = e => zlib.gunzipSync(src.subarray(+e[5], +e[5] + +e[6])).toString()

// R's nodes per sequence, as starts and lengths sorted by start (a Map per
// node would pass V8's Map size limit on a genome)
const nodesBySeq = new Map()
for (const e of table.filter(e => e[3] === 'tile')) {
  if (!nodesBySeq.has(e[0])) nodesBySeq.set(e[0], [])
  const list = nodesBySeq.get(e[0])
  for (const l of text(e).split('\n')) {
    if (!l.startsWith('ref\t')) continue
    const c = l.split('\t')
    let at = +c[3]
    for (const n of c[7].split(',').map(Number)) {
      list.push(at, n)
      at += n
    }
  }
}
const sorted = new Map()
for (const [seq, list] of nodesBySeq) {
  const order = Array.from({ length: list.length / 2 }, (_, i) => i).sort((a, b) => list[2 * a] - list[2 * b])
  sorted.set(seq, { starts: Float64Array.from(order, i => list[2 * i]), lengths: Float64Array.from(order, i => list[2 * i + 1]) })
}
nodesBySeq.clear()
// the last node starting at or before `pos`
function before(r, pos) {
  let lo = 0
  let hi = r.starts.length
  while (lo < hi) {
    const mid = (lo + hi) >> 1
    if (r.starts[mid] <= pos) lo = mid + 1
    else hi = mid
  }
  return lo - 1
}

// departure records, one each, from the uncut file
const recs = new Map()
const dl = spawnSync('bgzip', ['-dc', `${dir}/depu.bed.gz`], { maxBuffer: 2 ** 31 }).stdout.toString().split('\n')
let missingNode = 0
for (const l of dl) {
  if (!l || l.startsWith('#')) continue
  const c = l.split('\t')
  const seq = c[0]
  const r = sorted.get(seq)
  const node = (pos, strand, leave) => {
    // a + leave or - rejoin ends at the breakpoint; the others start there
    const endsHere = (strand === '+') === leave
    const i = r ? before(r, endsHere ? pos - 1 : pos) : -1
    const ok = i >= 0 && (endsHere ? r.starts[i] + r.lengths[i] === pos : r.starts[i] === pos)
    if (!ok) {
      missingNode++
      return [pos, pos + 1]
    }
    return [r.starts[i], r.starts[i] + r.lengths[i]]
  }
  const [a0, a1] = node(+c[8], c[9], true)
  const [b0, b1] = node(+c[11], c[12], false)
  const lo = Math.min(a0, b0, +c[1])
  const hi = Math.max(a1, b1, +c[2])
  const body = c.slice(3).join('\t')
  if (!recs.has(seq)) recs.set(seq, [])
  recs.get(seq).push({ lo, hi, line: `${seq}\t${lo}\t${hi}\t${body}` })
}

function blocks(lo, hi, each) {
  let at = Math.floor(lo / U) * U
  const end = Math.floor((hi - 1) / U) * U + U
  while (at < end) {
    const size = SIZES.find(s => at % s === 0 && at + s <= end) ?? U
    each(at, size)
    at += size
  }
}

// entries per sequence, in start order: a tile, then the departure blocks
// starting with it, largest last
const w = new BgzfWriter(`${dir}/${outName}.walks.gz`)
const idx = []
const header = table.find(e => e[3] === 'header')
w.write(text(header))
w.flush()
idx.push(['*', 0, 0, 'header', '.', 0, w.offset].join('\t'))
const seqs = [...new Set(table.filter(e => e[0] !== '*').map(e => e[0]))]
let rows = 0
for (const seq of seqs) {
  const groups = new Map()
  for (const r of recs.get(seq) ?? []) {
    blocks(r.lo, r.hi, (at, size) => {
      const k = `${at}\t${size}`
      if (!groups.has(k)) groups.set(k, [])
      groups.get(k).push(r.line)
      rows++
    })
  }
  const items = []
  for (const e of table.filter(e => e[0] === seq && e[3] === 'tile')) items.push({ start: +e[4], order: 0, e })
  for (const [k, lines] of groups) {
    const [at, size] = k.split('\t').map(Number)
    items.push({ start: at, order: size, lines, at, size })
  }
  items.sort((a, b) => a.start - b.start || a.order - b.order)
  for (const it of items) {
    const start = w.offset
    if (it.e) {
      w.write(text(it.e))
      w.flush()
      idx.push([seq, it.e[1], it.e[2], 'tile', it.e[4], start, w.offset - start].join('\t'))
    } else {
      w.write(it.lines.join('\n') + '\n')
      w.flush()
      idx.push([seq, it.at, it.at + it.size, 'departures', it.size, start, w.offset - start].join('\t'))
    }
  }
}
for (const e of table.filter(e => e[3] === 'detail')) {
  const start = w.offset
  w.write(text(e))
  w.flush()
  idx.push([e[0], e[1], e[2], 'detail', e[4], start, w.offset - start].join('\t'))
}
w.close()
fs.writeFileSync(`${dir}/${outName}.walks.idx`, idx.join('\n') + '\n')
console.log(JSON.stringify({ records: [...recs.values()].reduce((s, r) => s + r.length, 0), rows, missingNode, entries: idx.length }))
