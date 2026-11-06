// Bytes and requests graph-walks 6's cut makes on a format 7 file, on arbiter
// A's seeded windows (measure.mjs: mulberry32(seed * 1000 + size), 300 per
// size): the first read (tiles and departure blocks over the window and its
// context) and the attach fetches, budgets lifted, attachFetches 8.
// usage: node measure7.mjs <mc22|pggbY> <out.jsonl> [sizes]
import fs from 'node:fs'
import { LocalFile } from './gw6/node_modules/generic-filehandle2/esm/index.js'
import { WalkReader } from './gw6/src/index.ts'

const [dataset, outPath, sizesArg] = process.argv.slice(2)
const DATASETS = {
  mc22: { seq: 'GRCh38#0#chr22', range: [10_510_000, 50_790_000], seed: 22 },
  pggbY: { seq: 'GRCh38#0#chrY', range: [2_781_480, 26_673_214], seed: 24 },
}
const ds = DATASETS[dataset]
const S7 = process.env.S7 ? process.env.S7.replace("{d}", dataset) : `../arb-arbA/out/${dataset}/s7.walks.gz`
const CONTEXT = 1000
function mulberry32(a) {
  return () => {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}
const windows = []
for (const size of (sizesArg ?? '1000,10000,100000,1000000').split(',').map(Number)) {
  const rnd = mulberry32(ds.seed * 1000 + size)
  for (let i = 0; i < 300; i++) {
    const s = Math.floor(ds.range[0] + rnd() * (ds.range[1] - ds.range[0] - size))
    windows.push({ size, i, start: s, end: s + size })
  }
}
class Counted extends LocalFile {
  reads = []
  async read(length, position = 0, opts) {
    this.reads.push([position, length])
    return super.read(length, position, opts)
  }
}
const data = new Counted(S7)
const directory = new Counted(`${S7}.idx`)
const reader = WalkReader.fromFilehandles({ data, directory })
const [, units] = await Promise.all([reader.header(), reader.units(ds.seq)])
const dirBytes = fs.statSync(`${S7}.idx`).size
const out = fs.createWriteStream(outPath)
out.write(JSON.stringify({ open: { requests: data.reads.length + 1, bytes: dirBytes + data.reads.reduce((s, [, l]) => s + l, 0) } }) + '\n')
const lifted = { stepBudget: Infinity, byteBudget: Infinity, departureByteBudget: Infinity, links: false }
for (const w of windows) {
  const drawn = { start: Math.max(0, w.start - CONTEXT), end: w.end + CONTEXT }
  const selected = units
    .filter(u => (u.kind === 'tile' || u.kind === 'departures') && u.length > 0 && u.start < drawn.end && u.end > drawn.start)
    .sort((a, b) => a.offset - b.offset)
  let runs = 0
  let last
  for (const u of selected) {
    if (!last || last.offset + last.length !== u.offset) runs++
    last = u
  }
  const split = { tile: 0, departures: 0 }
  for (const u of selected) split[u.kind] += u.length
  const row = { size: w.size, i: w.i, start: w.start, read: { requests: runs, bytes: split.tile + split.departures, ...split } }
  data.reads = []
  try {
    await reader.cut(ds.seq, w, lifted)
    const bytes = data.reads.reduce((s, [, l]) => s + l, 0)
    row.total = { requests: data.reads.length, bytes, trips: data.reads.length > runs ? 2 : 1 }
  } catch (e) {
    row.error = String(e.message).slice(0, 200)
  }
  out.write(JSON.stringify(row) + '\n')
}
out.end()
