import { WalkReader } from '/home/cdiesh/src/graph-walks/src/index.ts'
import { LocalFile } from 'generic-filehandle2'
import {
  decodeChunk,
  chunkRef,
} from '/home/cdiesh/src/graph-walks/src/walkChunk.ts'
import { readFileSync } from 'node:fs'

const [which] = process.argv.slice(2)
const reader: any = WalkReader.open(which!, (p: string) => new LocalFile(p))
const file = reader.file
const sequences = readFileSync(`${which}.idx`, 'utf8')
  .split('\n')
  .filter(line => line !== '' && !line.startsWith('#'))
  .map(line => line.split('\t')[0]!)
const before: number[] = []
const after: number[] = []
const examples: { bp: number; text: string }[] = []
let pieces = 0
let lastOfLine = 0
let lastOfLineWithAfter = 0
const linePieces = new Map<string, number>()
const rowsOf: { key: string; piece: number; after: number }[] = []
for (const seq of sequences) {
  const units = await file.units(seq)
  const detailsOf = new Map<string, any[]>()
  for (const u of units) {
    if (u.kind === 'detail') {
      const cs = u.name.split(':')[0]
      detailsOf.set(cs, [...(detailsOf.get(cs) ?? []), u])
    }
  }
  for (const [cs, dets] of detailsOf) {
    const tile = units.find((u: any) => u.kind === 'tile' && u.name === cs)
    const [lines] = await file.read([tile])
    const ref = chunkRef(lines.map((l: string) => l.split('\t')))
    for (let i = 0; i < dets.length; i += 16) {
      const batch = dets.slice(i, i + 16)
      const read = await file.read(batch)
      batch.forEach((_: any, k: number) => {
        const detail = decodeChunk(
          read[k].map((l: string) => l.split('\t')),
          Number(cs),
          () => true,
          false,
          ref,
        )
        const length = (id: number) =>
          ref.lengths.get(id) ?? detail.chunk.lengths.get(id) ?? 0
        for (const walk of detail.rows as any[]) {
          const refStarts = walk.steps.refStarts
          let lead = 0
          let tail = 0
          let seen = false
          for (let j = 0; j < walk.n; j++) {
            const bp = length(walk.steps.ids[j])
            if (Number.isNaN(refStarts[j])) {
              lead += seen ? 0 : bp
              tail += bp
            } else {
              seen = true
              tail = 0
            }
          }
          pieces++
          const line = `${walk.name}\t${walk.fragStart}`
          linePieces.set(line, Math.max(linePieces.get(line) ?? 0, walk.piece))
          rowsOf.push({ key: line, piece: walk.piece, after: tail })
          if (lead > 0) {
            before.push(lead)
          }
          if (tail > 0) {
            after.push(tail)
            examples.push({
              bp: tail,
              text: `${seq} tile ${cs} ${walk.name} line ${walk.fragStart} piece ${walk.piece}: ${tail} bp after its last step on R`,
            })
          }
        }
      })
    }
  }
}
const quantiles = (xs: number[]) => {
  const sorted = Float64Array.from(xs).sort()
  const at = (p: number) => sorted[Math.min(sorted.length - 1, Math.floor(p * sorted.length))] ?? 0
  let sum = 0
  let over1k = 0
  for (const x of sorted) {
    sum += x
    over1k += x >= 1000 ? 1 : 0
  }
  return { n: sorted.length, sum, median: at(0.5), p90: at(0.9), p99: at(0.99), max: at(1), of1kbOrMore: over1k }
}
examples.sort((a, b) => b.bp - a.bp)
console.log(
  JSON.stringify(
    {
      file: which,
      pieces,
      ownBeforeFirstStepOnR: quantiles(before),
      ownAfterLastStepOnR: quantiles(after),
      largest: examples.slice(0, 8).map(e => e.text),
    },
    null,
    1,
  ),
)
