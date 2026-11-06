// Which format 6 chunks hold a path's steps through given nodes.
// usage: node whereSteps.mjs <walks.bed.gz> <seq> <from> <to> <path> <node,...>
import { TabixIndexedFile } from './h/node_modules/@gmod/tabix/esm/index.js'
import { decodeChunk } from './gw/src/walkChunk.ts'

const [file, seq, from, to, path, nodeList] = process.argv.slice(2)
const nodes = new Set(nodeList.split(',').map(Number))
const t = new TabixIndexedFile({ path: file, tbiPath: `${file}.tbi` })
const byChunk = new Map()
await t.getLines(seq, +from, +to, {
  lineCallback: l => {
    const c = l.split('\t')
    if (!byChunk.has(c[1])) byChunk.set(c[1], [])
    byChunk.get(c[1]).push(c)
  },
})
for (const [cs, rows] of byChunk) {
  for (const r of decodeChunk(rows, name => name === path).rows) {
    const hits = [...r.steps.ids].filter(id => nodes.has(id))
    if (hits.length) console.log(cs, r.name, 'piece', r.piece, 'abridged', Boolean(r.abridged), 'holds', hits.join(','))
  }
}
