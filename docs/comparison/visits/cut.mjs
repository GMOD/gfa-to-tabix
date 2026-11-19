#!/usr/bin/env node
// cut.mjs <graph-walks checkout> WALKS SEQ TILE OUTDIR OUT.tsv [--plant W] [--drill W,W,...]
//
// Cuts every window truth.py found reference nodes in (OUTDIR/*.bin), one tile each, with
// every haplotype, context 0 and no budgets, and sketches the visits the
// cut's fragments make to the window's reference nodes exactly as truth.py
// sketches the GFA's. --plant W drops one counted visit from window W, to
// prove the comparison fails; --swap W credits one to another haplotype,
// keeping the count, to prove the hashes are compared. Both act on a visit to
// a node the reference passes once. --drill writes OUTDIR/drill-cut.tsv.

import { open, readFile, writeFile } from 'node:fs/promises'
import { join, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

class LocalFile {
  constructor(path) {
    this.source = path
    this.handle = open(path, 'r')
  }
  async read(length, position = 0) {
    const buffer = new Uint8Array(length)
    const { bytesRead } = await (await this.handle).read(buffer, 0, length, position)
    return buffer.subarray(0, bytesRead)
  }
  readFile(options) {
    return readFile(this.source, options)
  }
  async stat() {
    return (await this.handle).stat()
  }
}

const [checkout, walks, seq, tileArg, outdir, outPath, ...rest] = process.argv.slice(2)
const tile = Number(tileArg)
const flag = name => (rest.includes(name) ? rest[rest.indexOf(name) + 1] : undefined)
const plant = flag('--plant') === undefined ? -1 : Number(flag('--plant'))
const swap = flag('--swap') === undefined ? -1 : Number(flag('--swap'))
const drill = new Set((flag('--drill') ?? '').split(',').filter(Boolean).map(Number))

const { WalkReader } = await import(pathToFileURL(join(resolve(checkout), 'src/index.ts')).href)

const bin = async name => {
  const b = await readFile(`${outdir}/${name}.bin`)
  return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength)
}
const offsets = new Int32Array(await bin('offsets'))
const wins = new Int32Array(await bin('wins'))
const multi = new Uint8Array(await bin('multi'))
const maxid = multi.length - 1
const hapNames = (await readFile(`${outdir}/haps.txt`, 'utf8')).trim().split('\n')
const hapIndex = new Map(hapNames.map((n, i) => [n, i]))

function fmix(h) {
  h ^= h >>> 16
  h = Math.imul(h, 0x85ebca6b)
  h ^= h >>> 13
  h = Math.imul(h, 0xc2b2ae35)
  h ^= h >>> 16
  return h >>> 0
}

const windows = [...new Set(wins)].sort((a, b) => a - b)
const reader = WalkReader.fromFilehandles({
  data: new LocalFile(walks),
  directory: new LocalFile(`${walks}.idx`),
})
const options = {
  context: 0,
  stepBudget: Infinity,
  byteBudget: Infinity,
  departureByteBudget: Infinity,
}

const rows = ['window\tpasses\tn\ts1\ts2']
const drillRows = []
let unknown = 0
for (const w of windows) {
  const { fragments } = await reader.cut(seq, { start: w * tile, end: (w + 1) * tile }, options)
  const n = [0, 0]
  const s1 = [0, 0]
  const s2 = [0, 0]
  const pairs = new Map()
  let dropPending = w === plant
  let swapPending = w === swap
  for (const f of fragments) {
    const hapName = f.name.split('#').slice(0, 2).join('#')
    const hap = hapIndex.get(hapName)
    if (hap === undefined) {
      unknown++
      continue
    }
    for (const id of f.ids) {
      if (id < 0 || id > maxid) {
        continue
      }
      let inWindow = false
      for (let i = offsets[id]; i < offsets[id + 1]; i++) {
        if (wins[i] === w) {
          inWindow = true
        }
      }
      if (!inWindow) {
        continue
      }
      const m = multi[id]
      if (m === 0 && dropPending) {
        dropPending = false
        continue
      }
      const h = m === 0 && swapPending ? (hap + 1) % hapNames.length : hap
      if (h !== hap) {
        swapPending = false
      }
      n[m]++
      s1[m] = (s1[m] + fmix((Math.imul(h, 0x9e3779b1) ^ id) >>> 0)) >>> 0
      s2[m] = (s2[m] + fmix(((Math.imul(id, 0xcc9e2d51) ^ h) ^ 0x1b873593) >>> 0)) >>> 0
      if (drill.has(w)) {
        const key = `${hapName}\t${id}`
        pairs.set(key, (pairs.get(key) ?? 0) + 1)
      }
    }
  }
  if (dropPending || swapPending) {
    throw new Error(`window ${w}: no single-pass visit to plant on`)
  }
  for (const m of [0, 1]) {
    if (n[m] > 0) {
      rows.push(`${w}\t${m ? 'multi' : 'single'}\t${n[m]}\t${s1[m]}\t${s2[m]}`)
    }
  }
  for (const [key, c] of pairs) {
    drillRows.push(`${w}\t${key}\t${c}`)
  }
}
await writeFile(outPath, `${rows.join('\n')}\n`)
if (drill.size) {
  await writeFile(`${outdir}/drill-cut.tsv`, `${drillRows.join('\n')}\n`)
}
console.error(`windows ${windows.length}, fragments of unknown haplotypes ${unknown}`)
process.exitCode = unknown > 0 ? 1 : 0
