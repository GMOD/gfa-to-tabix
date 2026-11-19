#!/usr/bin/env node
// sub.mjs <graph-walks checkout> WALKS SEQ TILE OUTDIR K
//
// Trimming inside a tile: for K windows spread over the sequence, cuts a
// 1 kb stretch at an offset inside the tile and the whole tile, both with
// every haplotype, context 0 and no budgets, and compares, per
// (haplotype, node), the visits each makes to nodes the reference sample
// passes once whose interval overlaps the stretch. The whole-tile cut is the
// one cut.mjs proves equal to the GFA. Exits 1 on any difference.
// PLANT_SHIFT=N cuts each stretch N bp short at its start, to prove that.

import { open, readFile } from 'node:fs/promises'
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

const [checkout, walks, seq, tileArg, outdir, kArg] = process.argv.slice(2)
const tile = Number(tileArg)
const { WalkReader } = await import(pathToFileURL(join(resolve(checkout), 'src/index.ts')).href)
const bin = async name => {
  const b = await readFile(`${outdir}/${name}.bin`)
  return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength)
}
const wins = new Int32Array(await bin('wins'))
const multi = new Uint8Array(await bin('multi'))
const start = new Float64Array(await bin('start'))
const length = new Float64Array(await bin('length'))
const windows = [...new Set(wins)].sort((a, b) => a - b)
const reader = WalkReader.fromFilehandles({
  data: new LocalFile(walks),
  directory: new LocalFile(`${walks}.idx`),
})
const options = { context: 0, stepBudget: Infinity, byteBudget: Infinity, departureByteBudget: Infinity }

async function visits(cutStart, cutEnd, a, b) {
  const { fragments } = await reader.cut(seq, { start: cutStart, end: cutEnd }, options)
  const counts = new Map()
  for (const f of fragments) {
    const hap = f.name.split('#').slice(0, 2).join('#')
    for (const id of f.ids) {
      if (id >= 0 && id < multi.length && multi[id] === 0 && start[id] >= 0 && start[id] < b && start[id] + length[id] > a) {
        const key = `${hap}\t${id}`
        counts.set(key, (counts.get(key) ?? 0) + 1)
      }
    }
  }
  return counts
}

const k = Number(kArg)
const shift = Number(process.env.PLANT_SHIFT ?? 0)
let differing = 0
let pairs = 0
for (let i = 0; i < k; i++) {
  const w = windows[Math.floor((i * windows.length) / k)]
  const a = w * tile + ((w * 7919) % (tile - 1000))
  const b = a + 1000
  const sub = await visits(a + shift, b, a, b)
  const whole = await visits(w * tile, (w + 1) * tile, a, b)
  const keys = new Set([...sub.keys(), ...whole.keys()])
  let bad = 0
  for (const key of keys) {
    if (sub.get(key) !== whole.get(key)) {
      bad++
      if (bad <= 3) {
        console.log(`  ${seq}:${a}-${b} ${key}: stretch ${sub.get(key) ?? 0}, tile ${whole.get(key) ?? 0}`)
      }
    }
  }
  pairs += keys.size
  differing += bad
  if (bad) {
    console.log(`window ${w} stretch ${a}-${b}: ${bad} of ${keys.size} pairs differ`)
  }
}
console.log(`stretches ${k}, (haplotype, node) pairs ${pairs}, differing ${differing}`)
process.exitCode = differing || !pairs ? 1 : 0
