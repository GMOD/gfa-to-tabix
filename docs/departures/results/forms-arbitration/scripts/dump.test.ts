import { TabixIndexedFile } from '@gmod/tabix'
import { existsSync, writeFileSync } from 'node:fs'
import { test } from 'vitest'

import { WalkReader } from '../walkReader.ts'
import { formsCut } from '../walkDepartures.ts'

const path = process.env.F6!
const dir = process.env.CACHE!
const wins = (process.env.WINS ?? '').split(' ').filter(Boolean)

test('dump', { timeout: 3_600_000 }, async () => {
  for (const w of wins) {
    const file = `${dir}/${w}.json`
    if (!existsSync(file)) {
      const [s, e] = w.split('-').map(Number)
      const reader = new WalkReader(
        new TabixIndexedFile({ path, tbiPath: `${path}.tbi` }),
      )
      const haps = await formsCut(
        reader,
        { refName: 'chr22', start: s!, end: e! },
        { partial: false },
      )
      writeFileSync(file, JSON.stringify(haps))
    }
  }
})
