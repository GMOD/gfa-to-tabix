// printWalkForms.ts' JSON lines from the cached cuts, and the checker's counts
import { appendFileSync, readFileSync } from 'node:fs'
import { test } from 'vitest'

import { formContradictions } from '../formsCheck.ts'
import { structuralForms } from '../structuralForms.ts'

import type { HaplotypeDepartures } from '../walkDepartures.ts'

const dir = process.env.GATE!
const out = process.env.OUT!
const check = process.env.CHECK!
const windows = readFileSync(process.env.WINDOWS!, 'utf8').trim().split('\n')
const floorBp = process.env.FLOOR === 'auto' ? 'auto' : Number(process.env.FLOOR)
const keep = process.env.KEEP === '1'

test('gateforms', { timeout: 3_600_000 }, () => {
  const totals = new Map<string, number>()
  for (const line of windows) {
    const [name = ''] = line.split(/\s+/)
    const cached = JSON.parse(readFileSync(`${dir}/${name}.json`, 'utf8')) as {
      chrom: string
      window: { start: number; end: number }
      haplotypes: HaplotypeDepartures[]
      spans: Record<string, unknown>
    }
    const { chrom, window, spans } = cached
    const haplotypes = cached.haplotypes.filter(h => !h.haplotype.startsWith('CHM13'))
    const result = structuralForms(haplotypes, { window, floorBp, exclude: ['CHM13'], foldRareForms: !keep })
    const sites = result.informative.map(i => result.sites[i]!)
    const marks = result.forms.flatMap(f => f.marks)
    const extent = [...sites, ...marks]
    appendFileSync(out, `${JSON.stringify({
      name,
      chrom,
      ...window,
      rowSpan: [
        Math.min(window.start, ...extent.map(m => m.refStart)),
        Math.max(window.end, ...extent.map(m => m.refEnd)),
      ],
      floorBp: result.floorBp,
      unplaced: result.unplaced,
      rareCarriers: result.rareCarriers,
      lanes: result.forms.length,
      forms: result.forms.map(f => ({
        members: f.members,
        deltas: f.marks.map(m => m.delta),
        marks: f.marks.map(m => ({ kind: m.kind, bp: m.delta, start: m.refStart, end: m.refEnd })),
        unsized: f.states.filter(st => st === '.' || st === '~' || st === '*').length,
      })),
      spans,
    })}\n`)
    const bad = formContradictions(haplotypes, result, { window })
    const wrong = new Set(bad.filter(b => b.kind !== 'hidden').map(b => b.haplotype))
    const other = result.forms.filter(f => f.key === '*').reduce((n, f) => n + f.members.length, 0)
    const rarer = result.forms.filter(f => f.states.includes('~')).reduce((n, f) => n + f.members.length, 0)
    const kinds = new Map<string, number>()
    for (const b of bad) {
      kinds.set(b.kind, (kinds.get(b.kind) ?? 0) + 1)
    }
    totals.set('wrong', (totals.get('wrong') ?? 0) + wrong.size)
    totals.set('other', (totals.get('other') ?? 0) + other)
    totals.set('rarer', (totals.get('rarer') ?? 0) + rarer)
    totals.set('forms', (totals.get('forms') ?? 0) + result.forms.length - (other > 0 ? 1 : 0))
    totals.set('placed', (totals.get('placed') ?? 0) + result.placed)
    appendFileSync(check, `${name} floor ${result.floorBp} placed ${result.placed} forms ${result.forms.length - (other > 0 ? 1 : 0)} other ${other} rarer ${rarer} wrong ${wrong.size} ${[...kinds].map(([k, v]) => `${k} ${v}`).join(' ')}\n`)
  }
  appendFileSync(check, `TOTAL ${[...totals].map(([k, v]) => `${k} ${v}`).join(' ')}\n`)
})
