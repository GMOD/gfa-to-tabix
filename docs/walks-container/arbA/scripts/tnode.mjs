// T with S's departures: records filed over their end nodes, recut at the
// CSI's bin sizes. usage: node tnode.mjs <outdir> [chunk]
import { spawn } from 'node:child_process'
import fs from 'node:fs'
import readline from 'node:readline'
import zlib from 'node:zlib'
import { BgzfWriter } from './bgzf.mjs'

const [dir, chunkArg] = process.argv.slice(2)
const C = +(chunkArg ?? 65536)
const SIZES = [C * 512, C * 64, C * 8, C]
const src = fs.readFileSync(`${dir}/s.walks.gz`)
const recs = new Map()
for (const l of fs.readFileSync(`${dir}/s.walks.idx`, 'utf8').trim().split('\n')) {
  const e = l.split('\t')
  if (e[3] !== 'departures') continue
  for (const line of zlib.gunzipSync(src.subarray(+e[5], +e[5] + +e[6])).toString().split('\n')) {
    if (!line) continue
    const c = line.split('\t')
    if (!recs.has(c[0])) recs.set(c[0], new Map())
    recs.get(c[0]).set(c.slice(3).join('\t'), [+c[1], +c[2]])
  }
}
const LEVELS = process.env.LEVELS === '1'
const FLUSH = process.env.FLUSH === '1'
const w = new BgzfWriter(`${dir}/${FLUSH ? 'tlb' : LEVELS ? 'tl' : 'tn'}.bed.gz`)
const rl = readline.createInterface({ input: spawn('bgzip', ['-dc', `${dir}/t.bed.gz`]).stdout })
let key
for await (const line of rl) {
  if (line.startsWith('#')) {
    w.write(line + '\n')
    continue
  }
  const c = line.split('\t', 3)
  if (c[0].endsWith('~departure')) continue
  const k = `${c[0]}\t${c[1]}`
  if (k !== key) {
    w.flush()
    key = k
  }
  w.write(line + '\n')
}
for (const [seq, m] of recs) {
  const rows = []
  for (const [body, [lo, hi]] of m) {
    let at = Math.floor(lo / C) * C
    const end = Math.floor((hi - 1) / C) * C + C
    while (at < end) {
      const size = SIZES.find(s => at % s === 0 && at + s <= end) ?? C
      rows.push([Math.max(lo, at), Math.min(hi, at + size), body, LEVELS ? 3 - SIZES.indexOf(size) : '', at])
      at += size
    }
  }
  rows.sort((x, y) => String(x[3]).localeCompare(String(y[3])) || (FLUSH ? x[4] - y[4] : 0) || x[0] - y[0] || x[1] - y[1])
  let level
  let block
  for (const [a, b, body, L, at] of rows) {
    if (L !== level || (FLUSH && at !== block)) {
      w.flush()
      level = L
      block = at
    }
    w.write(`${seq}~departure${L}\t${a}\t${b}\t${body}\n`)
  }
}
w.close()
