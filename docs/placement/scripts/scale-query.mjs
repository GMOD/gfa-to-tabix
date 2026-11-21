#!/usr/bin/env node
// scale-query.mjs SEQUENCE CENTERS SIZES KEEP RUNS OUT.tsv NAME=WALKS...
//
// Times graph-walks 9.0.0 cutting windows of each walk file from local disk,
// for the haplotypes KEEP names (comma-separated sample#hap), the same with
// those walks expanded where abridged (read whole from their detail units,
// as the plugin's synteny track does), and for every haplotype: each window SIZES bp wide (comma-separated) centred on each of
// CENTERS, with CUT_PRESETS.figure (the browser's context, no budget). Each
// file has one reader, open for every cut, so a cut reads its window's units
// and not the table. One untimed pass first, which also records whether
// CUT_PRESETS.browser refuses the cut, and with what. Then RUNS rounds; in
// each, every window, and within it the files and the three haplotype sets in
// an order that rotates from window to window and round to round, each cut
// started at a 1-minute load below LOAD_MAX (default 3). Writes one row per cut: its wall ms,
// graph.tables' ms, the compressed bytes it read, its steps, nodes,
// placeholder nodes (abridged pieces), fragments and departures, and the
// load before it. SETS (comma-separated haps4, haps4x, all) limits the sets.

import { open, readFile, writeFile } from 'node:fs/promises'
import { loadavg } from 'node:os'

import { CUT_PRESETS, WalkReader, isPlaceholder, walksKept } from '@jbrowse/graph-walks'

class LocalFile {
  constructor(path) {
    this.source = path
    this.handle = open(path, 'r')
    this.bytes = 0
  }
  async read(length, position = 0) {
    const buffer = new Uint8Array(length)
    const { bytesRead } = await (await this.handle).read(buffer, 0, length, position)
    this.bytes += bytesRead
    return buffer.subarray(0, bytesRead)
  }
  readFile(options) {
    return readFile(this.source, options)
  }
  async stat() {
    return (await this.handle).stat()
  }
}

const [sequence, centersText, sizesText, keepText, runsText, outPath, ...graphs] = process.argv.slice(2)
const centers = centersText.split(',').map(Number)
const sizes = sizesText.split(',').map(Number)
const runs = Number(runsText)
const allSets = [
  { name: 'haps4', keep: walksKept(keepText.split(','), sequence), expand: undefined },
  { name: 'haps4x', keep: walksKept(keepText.split(','), sequence), expand: walksKept(keepText.split(','), sequence) },
  { name: 'all', keep: undefined, expand: undefined },
]
const sets = process.env.SETS ? allSets.filter(set => process.env.SETS.split(',').includes(set.name)) : allSets
const files = graphs.map(g => {
  const [name, walks] = g.split('=')
  const data = new LocalFile(walks)
  return { name, data, reader: WalkReader.fromFilehandles({ data, directory: new LocalFile(`${walks}.idx`) }) }
})
const windows = centers.flatMap(center => sizes.map(size => ({ center, size })))
const regionOf = w => ({ start: w.center - w.size / 2, end: w.center + w.size / 2 })

const loadMax = Number(process.env.LOAD_MAX ?? 3)

async function quiet() {
  while (loadavg()[0] >= loadMax) {
    process.stderr.write(`load ${loadavg()[0].toFixed(2)}, waiting\n`)
    await new Promise(r => setTimeout(r, 20000))
  }
  return loadavg()[0].toFixed(2)
}

async function measure(file, set, w) {
  file.data.bytes = 0
  const began = performance.now()
  const cut = await file.reader.cut(sequence, regionOf(w), { ...CUT_PRESETS.figure, keep: set.keep, expand: set.expand })
  const cutMs = performance.now() - began
  const bytes = file.data.bytes
  const t = performance.now()
  cut.graph.tables(cut.kept, cut.fragments, cut.departures)
  const tablesMs = performance.now() - t
  const ids = [...cut.graph.nodes.keys()]
  return {
    cut_ms: cutMs.toFixed(1),
    tables_ms: tablesMs.toFixed(1),
    bytes,
    steps: cut.fragments.reduce((n, f) => n + f.ids.length, 0),
    nodes: ids.filter(id => !isPlaceholder(id)).length,
    placeholders: ids.filter(id => isPlaceholder(id)).length,
    fragments: cut.fragments.length,
    departures: cut.departures.length,
  }
}

async function browserVerdict(file, set, w) {
  try {
    await file.reader.cut(sequence, regionOf(w), { ...CUT_PRESETS.browser, keep: set.keep, expand: set.expand })
    return 'fits'
  } catch (error) {
    return `${error.name}: ${String(error.message).replaceAll('\t', ' ').slice(0, 200)}`
  }
}

const cols = ['graph', 'center', 'size', 'set', 'run', 'load1', 'cut_ms', 'tables_ms', 'bytes', 'steps', 'nodes', 'placeholders', 'fragments', 'departures', 'browser']
const out = [cols.join('\t')]
const verdicts = new Map()
for (const w of windows) {
  for (const file of files) {
    for (const set of sets) {
      const key = `${file.name}\t${w.center}\t${w.size}\t${set.name}`
      verdicts.set(key, await browserVerdict(file, set, w))
      const row = { graph: file.name, center: w.center, size: w.size, set: set.name, run: 0, load1: loadavg()[0].toFixed(2), ...(await measure(file, set, w)), browser: verdicts.get(key) }
      out.push(cols.map(c => row[c] ?? '').join('\t'))
    }
  }
  process.stderr.write(`warm ${w.center} ${w.size}\n`)
}
await writeFile(outPath, `${out.join('\n')}\n`)
const pairs = files.flatMap(file => sets.map(set => ({ file, set })))
for (let r = 0; r < runs; r++) {
  for (const [i, w] of windows.entries()) {
    for (let k = 0; k < pairs.length; k++) {
      const { file, set } = pairs[(k + r + i) % pairs.length]
      const load1 = await quiet()
      const key = `${file.name}\t${w.center}\t${w.size}\t${set.name}`
      const row = { graph: file.name, center: w.center, size: w.size, set: set.name, run: r + 1, load1, ...(await measure(file, set, w)), browser: verdicts.get(key) }
      out.push(cols.map(c => row[c] ?? '').join('\t'))
    }
  }
  await writeFile(outPath, `${out.join('\n')}\n`)
  process.stderr.write(`run ${r + 1} done\n`)
}
