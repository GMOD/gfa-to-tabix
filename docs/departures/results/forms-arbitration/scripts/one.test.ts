import { appendFileSync, readFileSync } from 'node:fs'
import { test } from 'vitest'

import { describeForm, haplotypeMarks, structuralForms } from '../structuralForms.ts'

import type { HaplotypeDepartures } from '../walkDepartures.ts'

const log = (s: string) => appendFileSync(process.env.OUT ?? '/dev/stdout', `${s}\n`)

test('one', () => {
  const w = process.env.WIN!
  const [s, e] = w.split('-').map(Number) as [number, number]
  const [lo, hi] = process.env.RANGE!.split('-').map(Number) as [number, number]
  const input = (JSON.parse(readFileSync(`${process.env.HOME}/src/arb-forms-opus/cache/${w}.json`, 'utf8')) as HaplotypeDepartures[]).filter(h => !h.haplotype.startsWith('CHM13'))
  const r = structuralForms(input, { window: { start: s, end: e }, floorBp: Number(process.env.FLOOR ?? 50), foldRareForms: process.env.KEEP !== '1' })
  r.sites.forEach((x, i) => {
    if (x.refEnd >= lo && x.refStart <= hi) {
      log(`site ${i} ${x.refStart}-${x.refEnd} ${x.edge ? 'E' : x.shared ? 'S' : 'I'} ${x.states.map(st => `${st.key}:${st.carriers.length}`).join(' ')}`)
    }
  })
  for (const name of process.env.HAP!.split(' ')) {
    const h = input.find(x => x.haplotype === name)!
    const f = r.forms.find(x => x.members.includes(name))
    log(`${name} ${f ? describeForm(f) : 'unplaced'} ${f?.key}`)
    for (const m of f?.marks ?? []) {
      if (m.refEnd >= lo && m.refStart <= hi) log(`  formmark ${m.kind} ${m.refStart}-${m.refEnd} ${m.delta} site ${m.site}`)
    }
    log(`  key at sites: ${r.sites.map((x, i) => (x.refEnd >= lo && x.refStart <= hi ? `${i}:${x.states.find(st => st.carriers.includes(name))?.key}` : '')).filter(Boolean).join(' ')}`)
    for (const m of haplotypeMarks(h.departures, { floorBp: r.floorBp, window: { start: s, end: e } })) {
      if (m.refEnd >= lo && m.refStart <= hi) log(`  ownmark ${m.kind} ${m.refStart}-${m.refEnd} ${m.delta}`)
    }
    for (const d of process.env.DEPS ? h.departures : []) {
      if (d.refEnd >= lo && d.refStart <= hi) log(`  dep ${d.refStart}-${d.refEnd} delta ${d.altLength - (d.refEnd - d.refStart)} inv ${d.invertedBp}`)
    }
  }
})
