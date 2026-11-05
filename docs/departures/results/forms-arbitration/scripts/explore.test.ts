import { appendFileSync, readFileSync } from 'node:fs'
import { test } from 'vitest'

import { describeForm, formTag, structuralForms } from '../structuralForms.ts'

import type { HaplotypeDepartures } from '../walkDepartures.ts'

const dir = process.env.CACHE ?? `${process.env.HOME}/src/arb-forms-opus/cache`
const wins = (process.env.WINS ?? '').split(' ').filter(Boolean)
const haps = (process.env.HAP ?? '').split(' ').filter(Boolean)
const log = (s: string) => appendFileSync(process.env.OUT ?? '/dev/stdout', `${s}\n`)

test('explore', { timeout: 3_600_000 }, () => {
  for (const w of wins) {
    const [s, e] = w.split('-').map(Number) as [number, number]
    const input = JSON.parse(readFileSync(`${dir}/${w}.json`, 'utf8')) as HaplotypeDepartures[]
    const r = structuralForms(input, { window: { start: s, end: e }, exclude: ['CHM13'] })
    log(`W ${w} placed ${r.placed} unplaced ${r.unplaced.length} rare ${r.rareCarriers.length} floor ${r.floorBp} minCarriers ${r.minCarriers}`)
    r.sites.forEach((x, i) => {
      log(`  site ${i} ${x.refStart}-${x.refEnd} ${x.edge ? 'E' : x.shared ? 'S' : 'I'} cov ${x.covered} ${x.states.slice(0, 8).map(st => `${st.key}:${st.carriers.length}`).join(' ')}${x.states.length > 8 ? ` ... (${x.states.length})` : ''}`)
    })
    for (const f of r.forms) {
      log(`  form ${f.members.length} ${formTag(f, r)} | ${describeForm(f)}`)
    }
    for (const name of haps) {
      const h = input.find(x => x.haplotype === name)
      const f = r.forms.find(x => x.members.includes(name))
      log(`  ${name}: ${f ? describeForm(f) : 'unplaced'} key ${f?.key}`)
      log(`    covered ${JSON.stringify(h?.covered)}`)
      for (const d of h?.departures ?? []) {
        const delta = d.altLength - (d.refEnd - d.refStart)
        if (Math.abs(delta) >= 50 || d.invertedBp >= 50 || d.refEnd - d.refStart > 5000) {
          log(`    dep ${d.refStart}-${d.refEnd} ref ${d.refEnd - d.refStart} alt ${d.altLength} delta ${delta} inv ${d.invertedBp} rep ${d.repeatedBp}${d.abridged ? ' abridged' : ''}`)
        }
      }
    }
  }
})
