import { LocalFile } from 'generic-filehandle2'

import { walkFileOf } from './testing.ts'
import { WalkReader } from './walkReader.ts'

import type { WalkDeparture } from './walkDeparture.ts'
import type { WalkFragment } from './walkRows.ts'

const DATA = new URL('../test_data/', import.meta.url).pathname

const inline = (lines: string[]) => {
  const { data, directory } = walkFileOf(lines)
  return WalkReader.fromFilehandles({ data, directory })
}

const fragment = (f: WalkFragment) =>
  `${f.name} ${f.hapStart}-${f.hapEnd} ${[...f.ids].map((id, k) => (f.rev[k] ? '<' : '>') + id).join('')}`

const departure = (d: WalkDeparture) =>
  `${d.name} ${d.hapStart} own ${d.ownBp} ${d.leavePos}->${d.rejoinPos} ${d.fromSteps ? 'steps' : 'record'} ${d.steps ? [...d.steps.ids].map((id, k) => (d.steps!.rev[k] ? '<' : '>') + id).join('') : '-'}`

// Twelve 4 bp reference nodes in 16 bp tiles:
//   W R 0 chr >1>2>...>12
//   W H 1 h   >5>6>7>11>13>12>14>6>7>8   13, 14 own; pieces in tiles 16, 32, 16
//   W G 1 g   >1>15>6>7>8                15 own; pieces in tiles 0, 16
const far = [
  '#walks format:i:7 tile:i:16',
  '#reference R',
  '#haplotype G#1',
  '#haplotype H#1',
  'R#0#chr 0 ref R#0#chr 0 0 0 4 2,2,2,2 4,4,4,4 .',
  'R#0#chr 0 nodes 15 4',
  'R#0#chr 0 route 2 28 .',
  'R#0#chr 0 walk G#1#g 0 0 0 2 2 0',
  'R#0#chr 16 ref R#0#chr 0 16 1 4 10,2,2,2 4,4,4,4 .',
  'R#0#chr 16 walk G#1#g 0 8 1 3 12 .',
  'R#0#chr 16 walk H#1#h 0 0 0 3 10 .',
  'R#0#chr 16 walk H#1#h 0 28 2 3 12 .',
  'R#0#chr 32 ref R#0#chr 0 32 2 4 18,2,2,2 4,4,4,4 .',
  'R#0#chr 32 nodes 13,1 4,4',
  'R#0#chr 32 route 22 4 -2',
  'R#0#chr 32 route 0 4 .',
  'R#0#chr 32 walk H#1#h 0 12 1 4 22 0,2',
  'R#0#chr 0 24 departure G#1#g 4 4 0 4 + 1 20 + 1 0',
  'R#0#chr 20 48 departure H#1#h 24 4 0 48 + 1 20 + 1 32',
  'R#0#chr 24 44 departure H#1#h 12 0 0 28 + 1 40 + 1 .',
]

test('attach fetch: what a cut of 20-28 returns for H', async () => {
  const cut = async (opts: object) => {
    const { fragments, departures } = await inline(far).cut(
      'R#0#chr',
      { start: 20, end: 28 },
      { context: 0, ...opts },
    )
    return {
      fragments: fragments.filter(f => f.name === 'H#1#h').map(fragment),
      departures: departures.filter(d => d.name === 'H#1#h').map(departure),
    }
  }
  const results = {
    defaults: await cut({}),
    noFetch: await cut({ attachFetches: 0 }),
    oneFetchAll: await cut({ attachFetches: 1 }),
    oneFetchHOnly: await cut({
      attachFetches: 1,
      keep: (n: string) => n !== 'G#1#g',
    }),
  }
  console.log(JSON.stringify(results, null, 1))
})

// Eight 4 bp reference nodes in 16 bp tiles; G jumps back from 6 to 1 over
// node 9 of 0 bp, an own step filed in the leave's tile 16:
//   W R 0 chr >1>2>...>8
//   W G 1 g   >5>6>9>1>2
const zero = [
  '#walks format:i:7 tile:i:16',
  '#reference R',
  '#haplotype G#1',
  'R#0#chr 0 ref R#0#chr 0 0 0 4 2,2,2,2 4,4,4,4 .',
  'R#0#chr 0 walk G#1#g 0 8 1 2 2 .',
  'R#0#chr 16 ref R#0#chr 0 16 1 4 10,2,2,2 4,4,4,4 .',
  'R#0#chr 16 nodes 9 0',
  'R#0#chr 16 route 12 6 .',
  'R#0#chr 16 walk G#1#g 0 0 0 3 10 0',
  'R#0#chr 0 24 departure G#1#g 8 0 0 24 + 1 0 + 1 16',
]

test('a 0 bp own step: is it attached?', async () => {
  for (const [start, end] of [
    [0, 8],
    [0, 32],
  ]) {
    const { departures } = await inline(zero).cut(
      'R#0#chr',
      { start: start!, end: end! },
      { context: 0 },
    )
    console.log(start, end, departures.map(departure))
  }
})

// Reference lines 0-8 and 40-48, a hole between; H jumps from 1 to 4
//   R nodes 1 0-4, 2 4-8, 3 40-44, 4 44-48
//   W H 1 h >1>4
const hole = [
  '#walks format:i:7 tile:i:16',
  '#reference R',
  '#haplotype H#1',
  '#hole R#0#chr 8 40',
  'R#0#chr 0 ref R#0#chr 0 0 0 2 2,2 4,4 .',
  'R#0#chr 0 walk H#1#h 0 0 0 1 2 .',
  'R#0#chr 32 ref R#0#chr 40 40 0 2 6,2 4,4 .',
  'R#0#chr 32 walk H#1#h 0 4 1 1 8 .',
  'R#0#chr 0 48 departure H#1#h 4 0 0 4 + 1 44 + 1 .',
]

test('a window inside a hole: the record over it', async () => {
  for (const [start, end] of [
    [16, 24],
    [0, 48],
  ]) {
    const { departures } = await inline(hole).cut(
      'R#0#chr',
      { start: start!, end: end! },
      { context: 0 },
    )
    console.log(start, end, departures.map(departure))
  }
})

test('referenceNodes over a node the reference passes twice', async () => {
  const path = `${DATA}loop.R.walks.gz`
  const walks = WalkReader.fromFilehandles({
    data: new LocalFile(path),
    directory: new LocalFile(`${path}.idx`),
  })
  const nodes = await walks.referenceNodes('R#0#chr', { start: 0, end: 36 })
  console.log(nodes.map(n => `${n.id}@${n.start}-${n.end}`).join(' '))
})
