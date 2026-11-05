import { appendFileSync, readFileSync } from 'node:fs'
import { test } from 'vitest'

import { formContradictions } from '../formsCheck.ts'
import { formTag, structuralForms } from '../structuralForms.ts'

import type { HaplotypeDepartures } from '../walkDepartures.ts'

const dir = process.env.CACHE ?? `${process.env.HOME}/src/arb-forms-opus/cache`
const wins = (process.env.WINS ?? '').split(' ').filter(Boolean)
const log = (s: string) => appendFileSync(process.env.OUT ?? '/dev/stdout', `${s}\n`)
const floors = (process.env.FLOORS ?? 'auto').split(' ')
const detail = Number(process.env.DETAIL ?? 0)

test('check', { timeout: 3_600_000 }, () => {
  const totals = new Map<string, number>()
  for (const floor of floors) {
    for (const w of wins) {
      const [s, e] = w.split('-').map(Number) as [number, number]
      const window = { start: s, end: e }
      const input = (JSON.parse(readFileSync(`${dir}/${w}.json`, 'utf8')) as HaplotypeDepartures[]).filter(h => !h.haplotype.startsWith('CHM13'))
      const r = structuralForms(input, { window, floorBp: floor === 'auto' ? 'auto' : Number(floor), foldRareForms: process.env.KEEP !== '1' })
      const bad = formContradictions(input, r, { window })
      const kinds = new Map<string, Set<string>>()
      for (const b of bad) {
        kinds.set(b.kind, (kinds.get(b.kind) ?? new Set()).add(b.haplotype))
      }
      const wrong = new Set(bad.filter(b => b.kind !== 'hidden').map(b => b.haplotype))
      totals.set('wrong', (totals.get('wrong') ?? 0) + wrong.size)
      for (const [k, v] of kinds) {
        totals.set(k, (totals.get(k) ?? 0) + v.size)
      }
      const tags = r.forms.slice(0, 6).map(f => `${f.members.length} ${formTag(f, r)}`).join('; ')
      const other = r.forms.filter(f => f.key === '*').reduce((n, f) => n + f.members.length, 0)
      const rarer = r.forms.filter(f => f.states.includes('~')).reduce((n, f) => n + f.members.length, 0)
      const nocall = r.forms.filter(f => f.states.includes('.')).reduce((n, f) => n + f.members.length, 0)
      log(`${w} floor ${r.floorBp} placed ${r.placed} forms ${r.forms.length - (other > 0 ? 1 : 0)} other ${other} rarer ${rarer} nocall ${nocall} rare ${r.rareCarriers.length} wrong ${wrong.size} ${[...kinds].map(([k, v]) => `${k} ${v.size}`).join(' ')} | ${tags}`)
      for (const b of bad.slice(0, detail)) {
        const f = r.forms.find(x => x.members.includes(b.haplotype))!
        log(`    ${b.kind} ${b.haplotype} site ${b.site} ${b.site >= 0 ? `${r.sites[b.site]!.refStart}-${r.sites[b.site]!.refEnd}` : ''} stated ${b.stated} own ${b.own} in ${formTag(f, r)}`)
      }
    }
  }
  log(`TOTAL ${[...totals].map(([k, v]) => `${k} ${v}`).join(' ')}`)
})
