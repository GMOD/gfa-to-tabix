// node passcount.mjs WALKS REFSEQ OUT.json [NAME:LO-HI ...]   (Mb)
// How many rows a walk file would gain if every chunk a path crosses without
// a piece of its own said so ("passes this chunk off its reference"). A
// piece's nx tag names the chunk of the path's next piece; every chunk
// strictly between the two is crossed, and needs a row where the path has no
// piece of its own. Counts the paths so crossing each chunk of REFSEQ, the skip rows the file already has there, and reports
// medians and maxima per region (whole sequence when none given).
import { spawn } from 'node:child_process'
import fs from 'node:fs'
import readline from 'node:readline'

const [walks, ref, outPath, ...regions] = process.argv.slice(2)
const CHUNK = 65536
const crossDiff = new Map()
const skips = new Map()
const longCross = new Map()
const byPath = new Map()
// the chunks each path has a piece in, which need no row
const pieces = new Map()
const add = (m, k, v) => m.set(k, (m.get(k) ?? 0) + v)
const unzip = spawn('bgzip', ['-@', '4', '-dc', walks], { stdio: ['ignore', 'pipe', 'inherit'] })
const lines = readline.createInterface({ input: unzip.stdout, crlfDelay: Infinity })
let maxCs = 0
for await (const line of lines) {
  if (line.charCodeAt(0) === 35) continue
  const t1 = line.indexOf('\t')
  if (line.slice(0, t1) !== ref) continue
  const t2 = line.indexOf('\t', t1 + 1)
  const t3 = line.indexOf('\t', t2 + 1)
  const t4 = line.indexOf('\t', t3 + 1)
  const kind = line.slice(t3 + 1, t4)
  const cs = +line.slice(t1 + 1, t2)
  maxCs = Math.max(maxCs, cs)
  if (kind === 'skip') {
    add(skips, cs, 1)
    continue
  }
  if (kind !== 'walk' && kind !== 'abridged') continue
  {
    const t5 = line.indexOf('\t', t4 + 1)
    const path = line.slice(t4 + 1, t5)
    let held = pieces.get(path)
    if (!held) pieces.set(path, (held = new Set()))
    held.add(cs)
  }
  const at = line.indexOf('\tnx:')
  if (at < 0) continue
  const end = line.indexOf('\t', at + 1)
  const tag = line.slice(at + 1, end < 0 ? undefined : end)
  let nx
  if (tag[3] === 'i') nx = +tag.slice(5)
  else {
    const colon = tag.lastIndexOf(':')
    if (tag.slice(5, colon) !== ref) continue
    nx = +tag.slice(colon + 1)
  }
  const [a, b] = cs < nx ? [cs, nx] : [nx, cs]
  if (b - a > CHUNK) {
    const t5 = line.indexOf('\t', t4 + 1)
    const path = line.slice(t4 + 1, t5)
    let list = byPath.get(path)
    if (!list) byPath.set(path, (list = []))
    list.push(a + CHUNK, b, b - a > 33 * CHUNK ? 1 : 0)
  }
}
// one row per path per chunk at most: merge each path's crossings first;
// `long` counts paths crossing a chunk by a jump past the 32 chunks skip rows
// cover, which no skip row marks
for (const [path, list] of byPath) {
  const held = pieces.get(path) ?? new Set()
  const mark = (diff, from, to) => {
    for (let c = from; c < to; c += CHUNK) {
      if (!held.has(c)) {
        add(diff, c, 1)
        add(diff, c + CHUNK, -1)
      }
    }
  }
  for (const [diff, longOnly] of [[crossDiff, false], [longCross, true]]) {
    const iv = []
    for (let i = 0; i < list.length; i += 3) {
      if (!longOnly || list[i + 2]) iv.push([list[i], list[i + 1]])
    }
    iv.sort((x, y) => x[0] - y[0])
    let cur
    for (const [x, y] of iv) {
      if (cur && x <= cur[1]) cur[1] = Math.max(cur[1], y)
      else {
        if (cur) mark(diff, cur[0], cur[1])
        cur = [x, y]
      }
    }
    if (cur) mark(diff, cur[0], cur[1])
  }
}
const perChunk = []
let run = 0
let runLong = 0
for (let c = 0; c <= maxCs; c += CHUNK) {
  run += crossDiff.get(c) ?? 0
  runLong += longCross.get(c) ?? 0
  perChunk.push({ c, cross: run, long: runLong, skip: skips.get(c) ?? 0 })
}
const spans = regions.length
  ? regions.map(r => {
      const [n, s] = r.split(':')
      const [lo, hi] = s.split('-').map(x => +x * 1e6)
      return { n, lo, hi }
    })
  : [{ n: 'all', lo: 0, hi: Infinity }]
const med = xs => {
  const s = [...xs].sort((a, b) => a - b)
  return s.length ? s[s.length >> 1] : 0
}
const summary = {}
for (const { n, lo, hi } of spans) {
  const cs = perChunk.filter(p => p.c + CHUNK > lo && p.c < hi)
  summary[n] = {
    chunks: cs.length,
    crossMedian: med(cs.map(p => p.cross)),
    crossMax: Math.max(0, ...cs.map(p => p.cross)),
    beyondSkipMedian: med(cs.map(p => p.long)),
    beyondSkipMax: Math.max(0, ...cs.map(p => p.long)),
    skipRowsMedian: med(cs.map(p => p.skip)),
    skipRowsMax: Math.max(0, ...cs.map(p => p.skip)),
  }
  console.log(n, JSON.stringify(summary[n]))
}
fs.writeFileSync(outPath, JSON.stringify({ summary, perChunk }))
