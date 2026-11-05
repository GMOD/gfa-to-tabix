import { createRequire } from 'node:module'
const require = createRequire('/home/cdiesh/src/graph-walks/package.json')
const { TabixIndexedFile } = require('@gmod/tabix')
const { LocalFile } = require('generic-filehandle2')
const [file, seq, ...bins] = process.argv.slice(2)
const t = new TabixIndexedFile({ filehandle: new LocalFile(file), csiFilehandle: new LocalFile(file + '.csi') })
const data = await t.index.parse()
const refId = data.refNameToId?.[seq] ?? data.refIdToName?.indexOf(seq)
const ba = data.indices(refId)
for (const bin of bins) {
  const chunks = ba.binIndex[+bin] ?? []
  console.log(`bin ${bin}: ${chunks.length} raw chunks: ` + chunks.map(c => `${c.minv.blockPosition}:${c.minv.dataPosition}..${c.maxv.blockPosition}:${c.maxv.dataPosition} (${c.maxv.blockPosition - c.minv.blockPosition} B)`).join('  '))
}
