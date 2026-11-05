// Forms of MC chr22 windows as structuralForms gives them. Copy into
// graph-walks' src/ and run:
// F6=<walks.bed.gz> OUT=<file> WINS="start-end ..." [HAP="name ..."] npx vitest run src/forms-probe.test.ts
import { TabixIndexedFile } from '@gmod/tabix'
import { appendFileSync } from 'node:fs'
import { test } from 'vitest'
import { WalkReader } from './walkReader.ts'
import { formsCut } from './walkDepartures.ts'
import { structuralForms, formTag } from './structuralForms.ts'

const path = process.env.F6!
const outFile = process.env.OUT!
const out = (s: string) => appendFileSync(outFile, `${s}\n`)
const wins = (process.env.WINS ?? '').split(' ')
test('probe', { timeout: 1_200_000 }, async () => {
  for (const w of wins) {
    const [s, e] = w.split('-').map(Number) as [number, number]
    const reader = new WalkReader(new TabixIndexedFile({ path, tbiPath: `${path}.tbi` }))
    const haps = await formsCut(reader, { refName: 'chr22', start: s, end: e }, { partial: false })
    const t0 = performance.now()
    const r = structuralForms(haps, { window: { start: s, end: e }, exclude: ["CHM13"] })
    out(`  structuralForms ${Math.round(performance.now() - t0)} ms, marks ${haps.reduce((n, h) => n + h.departures.length, 0)} departures`)
    const tags = new Map<string, number>()
    for (const f of r.forms) {
      tags.set(formTag(f, r), (tags.get(formTag(f, r)) ?? 0) + f.members.length)
    }
    out(`W ${s}-${e} placed ${r.placed} unplaced ${r.unplaced.length} rare ${r.rareCarriers.length}`)
    out(`  sites ${r.sites.map((x, i) => `${x.refStart}-${x.refEnd}${x.edge ? 'E' : x.shared ? 'S' : r.informative.includes(i) ? 'I' : ''}:${x.covered}:${x.states.length}`).join(' ')}`)
    out(`  forms ${[...tags].sort((a, b) => b[1] - a[1]).slice(0, 8).map(([t, n]) => `${n} ${t}`).join('; ')}`)
    for (const name of (process.env.HAP ?? '').split(' ').filter(Boolean)) {
      const f = r.forms.find(x => x.members.includes(name))
      out(`  ${name}: ${f ? formTag(f, r) : 'unplaced'} key ${f?.key}`)
    }
  }
})
