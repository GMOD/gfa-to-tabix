// printWalkForms.ts' cuts and truth-span nets, cached per window
import { TabixIndexedFile } from '@gmod/tabix'
import { existsSync, readFileSync, writeFileSync } from 'node:fs'
import { test } from 'vitest'

import { STRUCTURAL_BP } from '../structuralForms.ts'
import { WalkReader } from '../walkReader.ts'
import { formsCut } from '../walkDepartures.ts'

import type { HaplotypeDepartures } from '../walkDepartures.ts'

const path = process.env.WALKS!
const dir = process.env.GATE!
const windows = readFileSync(process.env.WINDOWS!, 'utf8').trim().split('\n')
const truthSpans = new Map<string, Set<string>>()
const [header = '', ...rows] = readFileSync(process.env.TRUTH!, 'utf8').trim().split('\n')
const col = Object.fromEntries(header.split('\t').map((c, i) => [c, i]))
for (const row of rows) {
  const c = row.split('\t')
  if (c[col.status!] === 'ok') {
    const name = c[col.window!]!
    const spans = truthSpans.get(name) ?? new Set()
    spans.add(`${c[col.ws!]}-${c[col.we!]}`)
    truthSpans.set(name, spans)
  }
}
type Window = { start: number; end: number }
const covers = (h: HaplotypeDepartures, a: number, b: number) =>
  a >= b || h.covered.some(([s, e]) => s <= a && e >= b)
function joined(h: HaplotypeDepartures) {
  const out: { refStart: number; refEnd: number; delta: number }[] = []
  let lastAbridged = true
  for (const d of h.departures) {
    const delta = d.altLength - (d.refEnd - d.refStart)
    const last = out.at(-1)
    if (last && !lastAbridged && !d.abridged && d.refStart - last.refEnd < STRUCTURAL_BP) {
      last.refEnd = Math.max(last.refEnd, d.refEnd)
      last.delta += delta
    } else {
      out.push({ refStart: d.refStart, refEnd: d.refEnd, delta })
    }
    lastAbridged = !!d.abridged
  }
  return out
}
function spanNets(h: HaplotypeDepartures, ws: number, we: number, window: Window) {
  let net: number | null = covers(h, ws, we) ? 0 : null
  let beyond: number | null = covers(h, ws, window.start) && covers(h, window.end, we) ? 0 : null
  for (const g of joined(h)) {
    const point = g.refStart === g.refEnd
    if (!(point ? g.refStart < ws || g.refStart > we : g.refEnd <= ws || g.refStart >= we)) {
      const inside = g.refStart >= ws && g.refEnd <= we
      net = inside && net !== null ? net + g.delta : null
      if (g.refEnd < window.start || g.refStart > window.end) {
        beyond = inside && beyond !== null ? beyond + g.delta : null
      }
    }
  }
  return { net, beyond }
}

test('gatedump', { timeout: 7_200_000 }, async () => {
  const reader = new WalkReader(new TabixIndexedFile({ path, tbiPath: `${path}.tbi` }))
  for (const line of windows) {
    const [name = '', chrom = '', s, e] = line.split(/\s+/)
    const file = `${dir}/${name}.json`
    if (!existsSync(file)) {
      const window: Window = { start: Number(s), end: Number(e) }
      const t0 = performance.now()
      const haplotypes = await formsCut(reader, { refName: chrom, ...window })
      const spans: Record<string, Record<string, ReturnType<typeof spanNets>>> = {}
      for (const span of truthSpans.get(name) ?? []) {
        const [ws, we] = span.split('-').map(Number) as [number, number]
        const hs = await formsCut(reader, { refName: chrom, start: ws, end: we })
        spans[span] = Object.fromEntries(hs.map(h => [h.haplotype, spanNets(h, ws, we, window)]))
      }
      writeFileSync(file, JSON.stringify({ name, chrom, window, haplotypes, spans }))
      writeFileSync(`${dir}/log.txt`, `${name} ${Math.round(performance.now() - t0)} ms\n`, { flag: 'a' })
    }
  }
})
