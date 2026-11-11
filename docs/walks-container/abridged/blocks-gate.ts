import { WalkReader } from '/home/cdiesh/src/graph-walks/src/index.ts'
import { LocalFile } from 'generic-filehandle2'
import { decodeChunk, chunkRef } from '/home/cdiesh/src/graph-walks/src/walkChunk.ts'
import { writeFileSync, appendFileSync } from 'node:fs'
import { gzipSync } from 'node:zlib'
const [which, outName, ...specs] = process.argv.slice(2)
const reader: any = WalkReader.open(which, (p: string) => new LocalFile(p))
const file = reader.file
for (const spec of specs) {
  const [seq, cs, flags = ''] = spec.split(',') as [string, string, string?]
  const forms = flags.includes('f'), save = flags.includes('s')
  const units = await file.units(seq)
  const t = units.find((u: any) => u.kind === 'tile' && u.name === cs)
  const dets = units.filter((u: any) => u.kind === 'detail' && u.name.startsWith(cs + ':'))
  const [lines] = await file.read([t])
  const rows = lines.map((l: string) => l.split('\t'))
  const dec = decodeChunk(rows, Number(cs), () => true)
  const ref = chunkRef(rows)
  const ab = dec.rows.filter((r: any) => r.abridged)
  const tlen = (id: number) => { const n = dec.nodes.get(id); return n ? n.end - n.start : 0 }
  const byDetail = new Map<string, any[]>()
  for (const r of ab) { const k = r.abridged.detail.name; byDetail.set(k, [...(byDetail.get(k) ?? []), r]) }
  const col = new Map<string, string>()
  let nBlocks = 0, maxBlocks = 0, beyond = 0, multi = 0, sumBad = 0, steps = 0, fetchMs = 0, decodeMs = 0, mixed = 0, missing = 0, endMismatch = 0
  const sigs: { a: Map<number, string>, b: Map<number, string> }[] = []
  const wins: number[] = []
  for (let s = t.start; s < t.end - 1000; s += 4096) wins.push(s)
  const groups = wins.map(() => new Map<string, Map<string, number>>())
  for (let i = 0; i < dets.length; i += 16) {
    const batch = dets.slice(i, i + 16)
    const t0 = performance.now()
    const read = await file.read(batch)
    fetchMs += performance.now() - t0
    batch.forEach((du: any, k: number) => {
      const t1 = performance.now()
      const dd = decodeChunk(read[k].map((l: string) => l.split('\t')), Number(cs), () => true, false, ref)
      decodeMs += performance.now() - t1
      const len = (id: number) => ref.lengths.get(id) ?? dd.chunk.lengths.get(id) ?? 0
      const rs0 = byDetail.get(du.name) ?? []
      if (rs0.length > 1) multi += rs0.length
      for (const r of rs0) {
        const w: any = dd.rows.find((x: any) => x.name === r.name && x.fragStart === r.fragStart && x.piece === r.piece)
        if (!w) { missing++; continue }
        steps += w.n
        const [a, b] = r.steps.refStarts
        const lo = Math.min(a, b), hi = Math.max(a + tlen(r.steps.ids[0]), b + tlen(r.steps.ids[1]))
        const blocks: number[][] = []
        let hap = w.hapOffset, prevOn = false
        const rs = w.steps.refStarts
        for (let j = 0; j < w.n; j++) {
          const L = len(w.steps.ids[j])
          if (!Number.isNaN(rs[j])) {
            const ag = w.steps.against[j]
            const last = blocks.at(-1)
            if (prevOn && last && last[2] === ag && (ag ? rs[j] + L === last[0] : rs[j] === last[1])) {
              if (ag) last[0] = rs[j]; else last[1] = rs[j] + L
              last[4] = hap + L
            } else blocks.push([rs[j], rs[j] + L, ag, hap, hap + L])
            prevOn = true
          } else prevOn = false
          hap += L
        }
        const toks: string[] = []
        let prev = 0, hprev = -1, bmin = Infinity, bmax = -Infinity, sum = 0, st = new Set<number>()
        for (const bl of blocks) {
          const beg = bl[2] ? bl[1]! : bl[0]!, end = bl[2] ? bl[0]! : bl[1]!
          const own = hprev < 0 ? 0 : bl[3]! - hprev
          toks.push(`${beg - prev}${bl[2] ? '-' : '+'}${bl[1]! - bl[0]!}${own ? ':' + own : ''}`)
          sum += bl[1]! - bl[0]! + own
          prev = end; hprev = bl[4]!; bmin = Math.min(bmin, bl[0]!); bmax = Math.max(bmax, bl[1]!); st.add(bl[2]!)
        }
        if (sum !== r.abridged.bp) sumBad++
        if (blocks.length && (blocks[0]![3] !== r.hapOffset)) endMismatch++
        if (bmin < lo || bmax > hi) beyond++
        if (st.size > 1) mixed++
        nBlocks += blocks.length; maxBlocks = Math.max(maxBlocks, blocks.length)
        col.set(`${r.name}\t${r.fragStart}\t${r.piece}`, toks.join(','))
        if (forms) {
          const ids = w.steps.ids, rev = w.steps.rev, agn = w.steps.against
          wins.forEach((s, wi) => {
            const e = s + 1000
            let i0 = -1, i1 = -1
            for (let j = 0; j < w.n; j++) if (!Number.isNaN(rs[j]) && rs[j] < e && rs[j] + len(ids[j]) > s) { if (i0 < 0) i0 = j; i1 = j }
            if (i0 >= 0) {
              const A: string[] = [], B: string[] = []
              let own = 0, ownIds: string[] = []
              for (let j = i0; j <= i1; j++) {
                if (Number.isNaN(rs[j])) { own += len(ids[j]); ownIds.push(`${ids[j]}${rev[j] ? '-' : '+'}`) }
                else {
                  if (ownIds.length) { A.push(`o${own}`); B.push(`o${ownIds.join('')}`); own = 0; ownIds = [] }
                  const tok = `r${rs[j]}${agn[j] ? '-' : '+'}${len(ids[j])}`
                  A.push(tok); B.push(tok)
                }
              }
              const g = groups[wi]!
              const ka = A.join(','), kb = B.join(',')
              const m = g.get(ka) ?? new Map<string, number>()
              m.set(kb, (m.get(kb) ?? 0) + 1); g.set(ka, m)
            }
          })
        }
      }
    })
  }
  const text = (withCol: boolean) => lines.map((l: string) => { const c = l.split('\t'); const x = c[3] === 'abridged' ? col.get(`${c[4]}\t${c[5]}\t${c[7]}`) : undefined; return withCol && x !== undefined ? `${l}\t${x}` : l }).join('\n') + '\n'
  const base = text(false), plus = text(true)
  const gzBase = gzipSync(Buffer.from(base), { level: 6 }).length, gzPlus = gzipSync(Buffer.from(plus), { level: 6 }).length
  if (save) writeFileSync(`tile-${which}-${seq.split('#')[2]}-${cs}.txt`, plus)
  let fw = 0, fGroups = 0, fSplit = 0, fPieces = 0, fMinor = 0, fOwnPieces = 0
  if (forms) for (const g of groups) { fw++; for (const [ka, m] of g) { const n = [...m.values()].reduce((x, y) => x + y, 0); fGroups++; fPieces += n; if (ka.includes('o')) fOwnPieces += n; if (m.size > 1) { fSplit++; fMinor += n - Math.max(...m.values()) } } }
  const unitRows: string[] = []
  for (const r of ab) {
    const x = col.get(`${r.name}\t${r.fragStart}\t${r.piece}`)
    if (x !== undefined) unitRows.push(`${seq}\t${r.name}\t${r.fragStart}\t${r.piece}\t${x}`)
  }
  const blocksGz = gzipSync(Buffer.from(unitRows.join('\n') + '\n'), { level: 6 }).length
  const res = { blocksGz, which, seq, cs, ext: [t.start, t.end], tileBytes: t.length, detailUnits: dets.length, detailBytes: dets.reduce((a: number, u: any) => a + u.length, 0), pieces: ab.length, tagged: col.size, missing, multi, beyond, mixed, sumBad, endMismatch, steps, nBlocks, maxBlocks, rawBase: base.length, rawPlus: plus.length, gzBase, gzPlus, addGz: gzPlus - gzBase, fetchMs: Math.round(fetchMs), decodeMs: Math.round(decodeMs),
    forms: forms ? { windows: fw, groups: fGroups, pieceWindows: fPieces, pieceWindowsWithOwn: fOwnPieces, groupsHidingDistinctOwn: fSplit, minorityPieces: fMinor } : undefined }
  appendFileSync(outName!, JSON.stringify(res) + '\n')
  console.error(JSON.stringify(res))
}
