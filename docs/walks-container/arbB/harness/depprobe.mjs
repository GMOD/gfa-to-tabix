// For a window, what @gmod/tabix fetches for the `~departure` query on a
// Tabix file (bins, merged chunks, bytes, rows returned, rows overlapping)
// against what S's table holds for the same extent (entries, bytes, rows).
//
// usage: node depprobe.mjs DATADIR TABIXFILE SEQ START END [REACH]
import fs from 'node:fs'
import zlib from 'node:zlib'
import { createRequire } from 'node:module'

const require = createRequire('/home/cdiesh/src/graph-walks/package.json')
const { TabixIndexedFile } = require('@gmod/tabix')
const { LocalFile } = require('generic-filehandle2')

const [dataDir, file, seq, startArg, endArg, reachArg] = process.argv.slice(2)
const reach = +(reachArg ?? 0)
const drawn = { start: Math.max(0, +startArg - 1000), end: +endArg + 1000 }
const extent = { start: Math.max(0, drawn.start - reach), end: drawn.end + reach }

const t = new TabixIndexedFile({
  filehandle: new LocalFile(`${dataDir}/${file}`),
  csiFilehandle: new LocalFile(`${dataDir}/${file}.csi`),
})
const name = `${seq}~departure`
const chunks = await t.index.blocksForRange(name, extent.start, extent.end)
let fetched = 0
for (const c of chunks) {
  const end = c.maxv.dataPosition === 0 ? Math.min(c.endPosition, c.maxv.blockPosition) : c.endPosition
  const size = end - c.minv.blockPosition
  fetched += size
  console.log(`tabix chunk bin ${c.bin} ${c.minv.blockPosition}:${c.minv.dataPosition}..${c.maxv.blockPosition}:${c.maxv.dataPosition} bytes ${size}`)
}
let rows = 0
let overlapping = 0
const recs = new Set()
await t.getLines(name, extent.start, extent.end, {
  lineCallback: l => {
    rows++
    const c = l.split('\t')
    if (+c[1] < drawn.end && +c[2] > drawn.start) {
      overlapping++
    }
    recs.add(c.slice(4).join('\t'))
  },
})
console.log(`tabix: ${chunks.length} chunks, ${fetched} bytes fetched, ${rows} rows returned, ${overlapping} overlapping drawn, ${recs.size} records`)

const text = zlib.gunzipSync(fs.readFileSync(`${dataDir}/s.walks.idx.gz`)).toString()
let sBytes = 0
let sRows = 0
const sLines = new Set()
const fd = fs.openSync(`${dataDir}/s.walks.gz`, 'r')
for (const line of text.split('\n')) {
  if (!line) {
    continue
  }
  const [s, a, b, kind, nm, off, size] = line.split('\t')
  if (s === seq && kind === 'departures' && +b > drawn.start && +a < drawn.end) {
    sBytes += +size
    const buf = Buffer.alloc(+size)
    fs.readSync(fd, buf, 0, +size, +off)
    const lines = zlib.gunzipSync(buf).toString().split('\n').filter(Boolean)
    sRows += lines.length
    for (const l of lines) {
      sLines.add(l)
    }
    console.log(`S entry ${a}-${b} block ${nm} bytes ${size} rows ${lines.length}`)
  }
}
console.log(`S: ${sBytes} bytes, ${sRows} rows, ${sLines.size} distinct`)
