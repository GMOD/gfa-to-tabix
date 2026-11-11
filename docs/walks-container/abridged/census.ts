import { WalkReader } from '/home/cdiesh/src/graph-walks/src/index.ts'
import { decodeChunk } from '/home/cdiesh/src/graph-walks/src/walkChunk.ts'
import { readFileSync, createWriteStream } from 'node:fs'
const which = process.argv[2]!
const url = which === 'chm13'
  ? 'https://jbrowse.org/demos/hprc/hprc-v2.1-mc-chm13.CHM13.walks.gz'
  : 'https://jbrowse.org/demos/hprc/hprc-v2.1-mc-grch38.GRCh38.walks.gz'
const reader: any = WalkReader.open(url)
const file = reader.file
const c0 = JSON.parse(readFileSync(`census0-${which}.json`, 'utf8'))
const out = createWriteStream(`census-${which}.tsv`)
const sample = which === 'chm13' ? 'CHM13#' : 'GRCh38#'
for (const seq of Object.keys(c0)) {
  const { tiles, details } = c0[seq]
  if (tiles.length === 0) continue
  const du = new Map(details.map((d: any) => [d[0], d]))
  const units = await file.units(seq)
  for (const t of tiles) {
    const unit = units.find((u: any) => u.kind === 'tile' && u.name === t.name)
    const [lines] = await file.read([unit])
    const rows = lines.map((l: string) => l.split('\t'))
    const names = new Set(rows.filter((c: string[]) => c[3] === 'abridged').map((c: string[]) => c[4]))
    const dec = decodeChunk(rows, Number(t.name), (n: string) => names.has(n))
    const len = (id: number) => { const n = dec.nodes.get(id); return n ? n.end - n.start : 0 }
    const ab = dec.rows.filter((r: any) => r.abridged)
    const per = new Map<string, number>()
    for (const r of ab) per.set(r.abridged.detail.name, (per.get(r.abridged.detail.name) ?? 0) + 1)
    const walkNames = new Set(dec.rows.filter((r: any) => !r.abridged).map((r: any) => r.name))
    for (const r of ab) {
      const [a, b] = r.steps.refStarts
      const lo = Math.min(a, b), hi = Math.max(a + len(r.steps.ids[0]), b + len(r.steps.ids[1]))
      const d: any = du.get(r.abridged.detail.name)
      out.write([seq, t.name, t.start, t.end, r.name, r.fragStart, r.piece, r.hapOffset, r.abridged.bp, r.abridged.steps, a, b, r.steps.against[0], r.steps.against[1],
        r.steps.ids[0] === r.steps.ids[1] ? 1 : 0, lo, hi, r.abridged.detail.name, d?.[1], d?.[2], per.get(r.abridged.detail.name), r.name.startsWith(sample) ? 1 : 0, walkNames.has(r.name) ? 1 : 0, r.steps.rev[0], r.steps.rev[1]].join('\t') + '\n')
    }
  }
  console.error(seq, tiles.length)
}
out.end()
