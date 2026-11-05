import { appendFileSync, readFileSync } from 'node:fs'
import { test } from 'vitest'

import { formContradictions } from '../formsCheck.ts'
import { describeForm, haplotypeMarks, structuralForms } from '../structuralForms.ts'

import type { HaplotypeDepartures } from '../walkDepartures.ts'

const log = (s: string) => appendFileSync(process.env.OUT!, `${s}\n`)
test('gateone', () => {
  const c = JSON.parse(readFileSync(`${process.env.HOME}/src/arb-forms-opus/gatecache/${process.env.NAME}.json`, 'utf8')) as { window: { start: number; end: number }; haplotypes: HaplotypeDepartures[] }
  const haplotypes = c.haplotypes.filter(h => !h.haplotype.startsWith('CHM13'))
  const r = structuralForms(haplotypes, { window: c.window, floorBp: Number(process.env.FLOOR), foldRareForms: process.env.KEEP !== '1' })
  for (const b of formContradictions(haplotypes, r, { window: c.window })) {
    const site = r.sites[b.site]!
    const f = r.forms.find(x => x.members.includes(b.haplotype))!
    log(`${b.kind} ${b.haplotype} site ${b.site} ${site.refStart}-${site.refEnd} stated ${b.stated} own ${b.own} | ${describeForm(f)}`)
    const st = site.states.find(s => s.carriers.includes(b.haplotype))
    log(`  own state ${st?.key} stated marks ${JSON.stringify(site.states.find(s => s.key === f.states[r.informative.indexOf(b.site)])?.marks.map(m => [m.refStart, m.refEnd, m.delta]))}`)
    const h = haplotypes.find(x => x.haplotype === b.haplotype)!
    for (const m of haplotypeMarks(h.departures, { floorBp: r.floorBp, window: c.window })) {
      if (m.refEnd >= site.refStart - 500 && m.refStart <= site.refEnd + 500) log(`  ownmark ${m.kind} ${m.refStart}-${m.refEnd} ${m.delta}`)
    }
    for (const d of h.departures) {
      if (d.refEnd >= site.refStart - 100 && d.refStart <= site.refEnd + 100) log(`  dep ${d.refStart}-${d.refEnd} ${d.altLength - (d.refEnd - d.refStart)}`)
    }
  }
})
