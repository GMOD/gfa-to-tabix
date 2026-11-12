import { WalkReader } from '/home/cdiesh/src/graph-walks/src/index.ts'
import { LocalFile } from 'generic-filehandle2'
import {
  decodeChunk,
  chunkRef,
} from '/home/cdiesh/src/graph-walks/src/walkChunk.ts'
import { readFileSync } from 'node:fs'

const [which, ...only] = process.argv.slice(2)
const reader: any = WalkReader.open(which!, (p: string) => new LocalFile(p))
const file = reader.file
const header = await reader.header()
const sequences = readFileSync(`${which}.idx`, 'utf8')
  .split('\n')
  .filter(line => line !== '' && !line.startsWith('#'))
  .map(line => line.split('\t')[0]!)
  .filter(seq => only.length === 0 || only.includes(seq))
const total = {
  file: which,
  format: header.format,
  sequences: sequences.length,
  abridgedTiles: 0,
  blocksUnits: 0,
  blocksBytes: 0,
  largestBlocksUnit: 0,
  pieces: 0,
  rowsEqual: 0,
  rowsDiffer: 0,
  rowsMissing: 0,
  rowsExtra: 0,
  endsDiffer: 0,
  orderDiffers: 0,
  hullDiffers: 0,
  unitHullDiffers: 0,
  blocksUnitWithoutAbridgedTile: 0,
}
const examples: string[] = []

for (const seq of sequences) {
  const units = await file.units(seq)
  const blocksUnits = new Map<string, any>(
    units.filter((u: any) => u.kind === 'blocks').map((u: any) => [u.name, u]),
  )
  const detailsOf = new Map<string, any[]>()
  for (const u of units) {
    if (u.kind === 'detail') {
      const cs = u.name.split(':')[0]
      detailsOf.set(cs, [...(detailsOf.get(cs) ?? []), u])
    }
  }
  for (const name of blocksUnits.keys()) {
    if (!detailsOf.has(name)) {
      total.blocksUnitWithoutAbridgedTile++
    }
  }
  for (const [cs, dets] of detailsOf) {
    total.abridgedTiles++
    const tile = units.find((u: any) => u.kind === 'tile' && u.name === cs)
    const [lines] = await file.read([tile])
    const rows = lines.map((l: string) => l.split('\t'))
    const decoded = decodeChunk(rows, Number(cs), () => true)
    const ref = chunkRef(rows)
    const abridged = decoded.rows.filter((r: any) => r.abridged)
    const byDetail = new Map<string, any[]>()
    for (const r of abridged) {
      const k = r.abridged.detail.name
      byDetail.set(k, [...(byDetail.get(k) ?? []), r])
    }
    const expected = new Map<
      string,
      { list: string; lo: number; hi: number; before: number; after: number }
    >()
    for (let i = 0; i < dets.length; i += 16) {
      const batch = dets.slice(i, i + 16)
      const read = await file.read(batch)
      batch.forEach((unit: any, k: number) => {
        const detail = decodeChunk(
          read[k].map((l: string) => l.split('\t')),
          Number(cs),
          () => true,
          false,
          ref,
        )
        const length = (id: number) =>
          ref.lengths.get(id) ?? detail.chunk.lengths.get(id) ?? 0
        for (const row of byDetail.get(unit.name) ?? []) {
          const walk: any = detail.rows.find(
            (x: any) =>
              x.name === row.name &&
              x.fragStart === row.fragStart &&
              x.piece === row.piece,
          )
          if (walk) {
            const refStarts = walk.steps.refStarts
            let first = -1
            let last = -1
            for (let j = 0; j < walk.n; j++) {
              if (!Number.isNaN(refStarts[j])) {
                first = first < 0 ? j : first
                last = j
              }
            }
            let before = 0
            let after = 0
            for (let j = 0; j < walk.n; j++) {
              const bp = length(walk.steps.ids[j])
              before += j < first ? bp : 0
              after += j > last ? bp : 0
            }
            const runs: { begin: number; end: number; own: number }[] = []
            let own = 0
            let adjacent = false
            for (let j = first; j <= last; j++) {
              const bp = length(walk.steps.ids[j])
              if (Number.isNaN(refStarts[j])) {
                own += bp
                adjacent = false
              } else {
                const against = Boolean(walk.steps.against[j])
                const begin = against ? refStarts[j] + bp : refStarts[j]
                const end = against ? refStarts[j] : refStarts[j] + bp
                const run = runs.at(-1)
                if (
                  run &&
                  adjacent &&
                  run.end === begin &&
                  run.begin > run.end === against
                ) {
                  run.end = end
                } else {
                  runs.push({ begin, end, own })
                }
                own = 0
                adjacent = true
              }
            }
            let at = 0
            let lo = Infinity
            let hi = -Infinity
            const tokens = runs.map(run => {
              const against = run.begin > run.end
              const token = `${run.begin - at}${against ? '-' : '+'}${Math.abs(run.end - run.begin)}${run.own ? `:${run.own}` : ''}`
              at = run.end
              lo = Math.min(lo, run.begin, run.end)
              hi = Math.max(hi, run.begin, run.end)
              return token
            })
            expected.set(`${row.name}\t${row.fragStart}\t${row.piece}`, {
              list: tokens.join(','),
              lo,
              hi,
              before,
              after,
            })
          }
        }
      })
    }
    total.pieces += abridged.length
    const unit = blocksUnits.get(cs)
    const written: string[][] = unit
      ? (await file.read([unit]))[0]
          .map((l: string) => l.split('\t'))
          .filter((c: string[]) => c[3] === 'blocks')
      : []
    if (unit) {
      total.blocksUnits++
      total.blocksBytes += unit.length
      total.largestBlocksUnit = Math.max(total.largestBlocksUnit, unit.length)
    }
    const seen = new Set<string>()
    let lo = Infinity
    let hi = -Infinity
    for (const c of written) {
      const key = `${c[4]}\t${c[5]}\t${c[6]}`
      const want = expected.get(key)
      seen.add(key)
      lo = Math.min(lo, Number(c[1]))
      hi = Math.max(hi, Number(c[2]))
      if (!want) {
        total.rowsExtra++
      } else if (want.list === c[9]) {
        total.rowsEqual++
        if (want.lo !== Number(c[1]) || want.hi !== Number(c[2])) {
          total.hullDiffers++
        }
        if (want.before !== Number(c[7]) || want.after !== Number(c[8])) {
          total.endsDiffer++
          if (examples.length < 5) {
            examples.push(
              `${seq} ${cs} ${key.replaceAll('\t', ' ')}: written ${c[7]} before and ${c[8]} after, decoded ${want.before} and ${want.after}`,
            )
          }
        }
      } else {
        total.rowsDiffer++
        if (examples.length < 5) {
          examples.push(
            `${seq} ${cs} ${key.replaceAll('\t', ' ')}: written ${(c[9] ?? c[7] ?? "").slice(0, 120)} decoded ${want.list.slice(0, 120)}`,
          )
        }
      }
    }
    for (const key of expected.keys()) {
      if (!seen.has(key)) {
        total.rowsMissing++
      }
    }
    if (unit && (unit.start !== lo || unit.end !== hi)) {
      total.unitHullDiffers++
    }
    const tileOrder = rows
      .filter((c: string[]) => c[3] === 'abridged')
      .map((c: string[]) => `${c[4]}\t${c[5]}\t${c[7]}`)
    const unitOrder = written.map(c => `${c[4]}\t${c[5]}\t${c[6]}`)
    if (tileOrder.join('\n') !== unitOrder.join('\n')) {
      total.orderDiffers++
    }
  }
}
console.log(JSON.stringify({ ...total, examples }, null, 1))
