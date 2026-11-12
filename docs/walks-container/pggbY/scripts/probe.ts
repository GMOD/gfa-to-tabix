// For one window: the reference nodes the loaded cut keeps and the unloaded
// one doesn't (and back), with where each cut places them and which
// fragments and departures hold them; and, for --departure NAME@HAPSTART,
// that record's fields and the nodes and links around its ends.
//   node probe.ts FILE --at seq:start-end [--contained] [--context 1000]
//     [--departure NAME@HAPSTART]
import { LocalFile } from 'generic-filehandle2'

import { WalkReader } from '../src/index.ts'

const flag = (name: string) => {
  const at = process.argv.indexOf(`--${name}`)
  return at < 0 ? undefined : process.argv[at + 1]
}
const path = process.argv[2] ?? ''
const [, refName = '', s = '0', e = '0'] =
  /^(.*):(\d+)-(\d+)$/.exec(flag('at') ?? '') ?? []
const window = { start: Number(s), end: Number(e) }
const contained = process.argv.includes('--contained')
const context = Number(flag('context') ?? 1000)
const departure = flag('departure')

const reader = WalkReader.fromFilehandles({
  data: new LocalFile(path),
  directory: new LocalFile(`${path}.idx`),
})
const opts = {
  context,
  contained,
  stepBudget: Infinity,
  byteBudget: Infinity,
  departureByteBudget: Infinity,
}
const unloaded = await reader.cut(refName, window, opts)
const loaded = await reader.cut(refName, window, { ...opts, expand: () => true })
type Cut = typeof unloaded

const onRef = (cut: Cut) =>
  new Set(
    [...cut.kept].filter(id => {
      const node = cut.graph.nodes.get(id)
      return node?.rank === 0 && !node.placeholder
    }),
  )
const describe = (cut: Cut, id: number) => {
  const node = cut.graph.nodes.get(id)
  const inFragments = cut.fragments
    .filter(f => f.ids.includes(id))
    .map(f => {
      const i = f.ids.indexOf(id)
      const around = [...f.ids].slice(Math.max(0, i - 3), i + 4)
      const starts = [...f.refStarts].slice(Math.max(0, i - 3), i + 4)
      return `${f.name}@${f.hapStart}${f.abridged === undefined ? '' : ' (abridged)'} ids ${around} refStarts ${starts}`
    })
  const inDepartures = cut.departures
    .filter(d => d.steps?.ids.includes(id))
    .map(d => `${d.name}@${d.hapStart}`)
  return { node, inFragments: inFragments.slice(0, 5), fragments: inFragments.length, inDepartures: inDepartures.slice(0, 5) }
}
const a = onRef(unloaded)
const b = onRef(loaded)
for (const id of b) {
  if (!a.has(id)) {
    console.log('loaded only', id, JSON.stringify({ loaded: describe(loaded, id), unloaded: describe(unloaded, id) }))
  }
}
for (const id of a) {
  if (!b.has(id)) {
    console.log('unloaded only', id, JSON.stringify({ unloaded: describe(unloaded, id), loaded: describe(loaded, id) }))
  }
}
if (departure) {
  const [name, hap] = departure.split('@')
  for (const [label, cut] of [['unloaded', unloaded], ['loaded', loaded]] as const) {
    for (const d of cut.departures.filter(x => x.name === name && x.hapStart === Number(hap))) {
      const { steps, ...rest } = d
      console.log(label, 'record', JSON.stringify(rest), 'steps', JSON.stringify(steps ? { ids: [...steps.ids].slice(0, 12), rev: [...steps.rev].slice(0, 12), n: steps.ids.length } : null))
      const near = [...cut.graph.nodes].filter(
        ([, n]) => n.rank === 0 && !n.placeholder && (n.end === d.leavePos || n.start === d.leavePos || n.end === d.rejoinPos || n.start === d.rejoinPos),
      )
      console.log(label, 'nodes at the ends', JSON.stringify(near))
      const kept = cut.kept
      console.log(label, 'end nodes kept', JSON.stringify(near.map(([id]) => [id, kept.has(id)])))
      const own = steps?.ids[0]
      const tables = cut.graph.tables(cut.kept, cut.fragments, cut.departures, cut.gaps)
      const names = tables.nodes.names
      const touching: string[] = []
      for (let k = 0; k < tables.links.from.length; k++) {
        const from = names[tables.links.from[k]!]
        const to = names[tables.links.to[k]!]
        if (from === String(own) || to === String(own)) {
          touching.push(`${from} ${to} strands ${tables.links.strands[k]}`)
        }
      }
      console.log(label, 'links touching own step', own, JSON.stringify(touching))
      for (const f of cut.fragments.filter(x => x.name === name)) {
        const i = f.ids.indexOf(own ?? -1)
        console.log(label, 'fragment', f.hapStart, f.hapEnd, 'own step at', i, i >= 0 ? JSON.stringify([...f.ids].slice(Math.max(0, i - 2), i + 3)) : '', 'refStarts', i >= 0 ? JSON.stringify([...f.refStarts].slice(Math.max(0, i - 2), i + 3)) : '')
      }
    }
  }
}
