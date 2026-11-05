import { createRequire } from 'node:module'
const require = createRequire('/home/cdiesh/src/graph-walks/package.json')
const { TabixIndexedFile } = require('@gmod/tabix')
const { LocalFile } = require('generic-filehandle2')
const [file, seq, lo, hi] = process.argv.slice(2)
const t = new TabixIndexedFile({ filehandle: new LocalFile(file), csiFilehandle: new LocalFile(file + '.csi') })
const data = await t.index.parse()
const refId = data.refNameToId?.[seq] ?? data.refIdToName?.indexOf(seq)
const ba = data.indices(refId)
console.log('minShift', data.minShift, 'depth', data.depth)
const rows = []
for (const [bin, chunks] of Object.entries(ba.binIndex)) {
  for (const c of chunks) {
    if (c.minv.blockPosition >= +lo && c.minv.blockPosition <= +hi) {
      rows.push([c.minv.blockPosition, +bin, c.maxv.blockPosition - c.minv.blockPosition, c.maxv.blockPosition])
    }
  }
}
rows.sort((a, b) => a[0] - b[0])
for (const r of rows) console.log(`offset ${r[0]} bin ${r[1]} bytes ${r[2]} end ${r[3]}`)
