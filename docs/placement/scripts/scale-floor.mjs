#!/usr/bin/env node
// scale-floor.mjs WALKS: how long graph-walks 9.0.0 takes to parse a sequence's
// table, to build maps of its detail and blocks units by name (which reader.cut
// does on every cut), and to cut a 10 kb window keeping 4 haplotypes
import { open, readFile } from 'node:fs/promises'
import { WalkReader, walksKept } from '@jbrowse/graph-walks'
class LocalFile {
  constructor(path) { this.source = path; this.handle = open(path, 'r') }
  async read(length, position = 0) { const b = new Uint8Array(length); const { bytesRead } = await (await this.handle).read(b, 0, length, position); return b.subarray(0, bytesRead) }
  readFile(o) { return readFile(this.source, o) }
  async stat() { return (await this.handle).stat() }
}
const walks = process.argv[2]
const seq = 'GRCh38#0#chr22'
const reader = WalkReader.fromFilehandles({ data: new LocalFile(walks), directory: new LocalFile(`${walks}.idx`) })
let t = performance.now()
const units = await reader.units(seq)
console.log('units', units.length, 'first units() ms', (performance.now() - t).toFixed(0))
for (let i = 0; i < 3; i++) {
  t = performance.now()
  const m = new Map(units.filter(u => u.kind === 'detail').map(u => [u.name, u]))
  const b = new Map(units.filter(u => u.kind === 'blocks').map(u => [u.name, u]))
  console.log('detail+blocks maps ms', (performance.now() - t).toFixed(0), m.size, b.size)
}
const keep = walksKept(['HG00097#1', 'HG002#1', 'NA19240#1', 'HG00733#1'], seq)
for (let i = 0; i < 3; i++) {
  t = performance.now()
  await reader.cut(seq, { start: 20540536, end: 20550536 }, { keep, stepBudget: Infinity, byteBudget: Infinity, departureByteBudget: Infinity })
  console.log('cut 10 kb haps4 ms', (performance.now() - t).toFixed(0))
}
