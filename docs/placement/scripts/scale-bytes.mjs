#!/usr/bin/env node
// scale-bytes.mjs SEQUENCE WINDOWS.tsv SIZES OUT_WINDOWS.tsv OUT_FILES.tsv NAME=WALKS...
//
// Per walk file: its size, its .idx's, the compressed bytes of its header
// unit and of the sequence's table, which a reader fetches whole before its
// first cut, and its units' count and compressed bytes by kind, with the
// quantiles of a unit's compressed bytes (OUT_FILES). Per file, window and size (bp, comma-separated): the window
// centred in the tile each WINDOWS.tsv start begins, widened by the browser
// preset's context; the compressed bytes of the tiles, their blocks units
// and the departure blocks over it, their bytes gunzipped, and
// reader.bytesFor's total, which adds the tiles fetched to attach
// (OUT_WINDOWS). Needs @jbrowse/graph-walks 9.0.0 and @gmod/bgzf-filehandle.

import { statSync } from 'node:fs'
import { open, readFile, writeFile } from 'node:fs/promises'

import { unzip } from '@gmod/bgzf-filehandle'
import { WALK_CONTEXT, WalkReader } from '@jbrowse/graph-walks'

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

const [sequence, windowsPath, sizesText, outWindows, outFiles, ...graphs] = process.argv.slice(2)
const sizes = sizesText.split(',').map(Number)
const [header, ...lines] = (await readFile(windowsPath, 'utf8')).trim().split('\n')
const startColumn = header.split('\t').indexOf('start')
const starts = lines.map(line => Number(line.split('\t')[startColumn]))

const quantile = (sorted, q) => sorted[Math.min(sorted.length - 1, Math.floor(q * sorted.length))]
const overlaps = (u, span) => u.length > 0 && u.start < span.end && u.end > span.start
const sum = units => units.reduce((n, u) => n + u.length, 0)

const windowRows = [['graph', 'center', 'size', 'tiles', 'tile_bytes', 'blocks_bytes', 'departure_bytes', 'tile_text_bytes', 'bytes_for'].join('\t')]
const fileRows = [['graph', 'data_bytes', 'idx_bytes', 'header_bytes', 'table_bytes', 'kind', 'units', 'bytes', 'p50', 'p90', 'p99', 'max'].join('\t')]

for (const graph of graphs) {
  const [name, walks] = graph.split('=')
  const data = new LocalFile(walks)
  const reader = WalkReader.fromFilehandles({ data, directory: new LocalFile(`${walks}.idx`) })
  const units = await reader.units(sequence)
  const { tile } = await reader.header()
  const dataBytes = statSync(walks).size
  const idxBytes = statSync(`${walks}.idx`).size
  const directory = (await readFile(`${walks}.idx`, 'utf8')).split('\n').map(line => line.split('\t'))
  const headerBytes = directory.find(cols => cols[0] === '#header')[2]
  const tableBytes = directory.find(cols => cols[0] === sequence)[2]
  for (const kind of [...new Set(units.map(u => u.kind))].toSorted()) {
    const lengths = units.filter(u => u.kind === kind).map(u => u.length).toSorted((a, b) => a - b)
    const total = lengths.reduce((a, b) => a + b, 0)
    const qs = [0.5, 0.9, 0.99].map(q => quantile(lengths, q))
    fileRows.push([name, dataBytes, idxBytes, headerBytes, tableBytes, kind, lengths.length, total, ...qs, lengths.at(-1)].join('\t'))
  }
  for (const start of starts) {
    const center = start + tile / 2
    for (const size of sizes) {
      const region = { start: center - size / 2, end: center + size / 2 }
      const drawn = { start: region.start - WALK_CONTEXT, end: region.end + WALK_CONTEXT }
      const tiles = units.filter(u => u.kind === 'tile' && overlaps(u, drawn))
      const names = new Set(tiles.map(u => u.name))
      const blocks = units.filter(u => u.kind === 'blocks' && names.has(u.name))
      const departures = units.filter(u => u.kind === 'departures' && overlaps(u, drawn))
      let text = 0
      for (const u of tiles) {
        text += (await unzip(await data.read(u.length, u.offset))).length
      }
      const bytesFor = await reader.bytesFor(sequence, region, { departureByteBudget: Infinity })
      windowRows.push([name, center, size, tiles.length, sum(tiles), sum(blocks), sum(departures), text, bytesFor].join('\t'))
    }
  }
  process.stderr.write(`${name} done\n`)
}
await writeFile(outWindows, `${windowRows.join('\n')}\n`)
await writeFile(outFiles, `${fileRows.join('\n')}\n`)
