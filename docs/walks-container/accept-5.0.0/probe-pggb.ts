const [repo, walks] = process.argv.slice(2)
const { WalkReader, walksKept } = await import(`${repo}/src/index.ts`)
const { LocalFile } = await import(`${repo}/node_modules/generic-filehandle2/esm/index.js`)
const refName = 'CHM13#0#chrY'
const cases = [
  { window: { start: 21057922, end: 21058922 }, pair: [236875, 240661] },
  { window: { start: 62015270, end: 62016270 }, pair: [1078384, 1308720] },
]
const reader0 = WalkReader.open(walks, (p: string) => new LocalFile(p))
const header = await reader0.header()
const batch = header.haplotypes.slice(0, 64)
const idOf = (h: number) => Math.floor(h / 2)
for (const { window, pair: [x, y] } of cases) {
  const reader = WalkReader.open(walks, (p: string) => new LocalFile(p))
  const cut = await reader.cut(refName, window, {
    keep: walksKept(batch, refName), context: 1000, stepBudget: Infinity, byteBudget: Infinity, departureByteBudget: Infinity, expand: () => true,
  })
  console.log(`== ${window.start}: ${cut.fragments.length} fragments, ${cut.departures.length} departures, chunks ${cut.graph.chunks.length}`)
  for (const id of [x, y]) {
    const n = cut.graph.nodes.get(id)
    const inFr = cut.fragments.filter((f: any) => f.ids.includes(id)).map((f: any) => f.name)
    const inDep = cut.departures.filter((d: any) => d.steps?.ids.includes(id)).map((d: any) => d.name)
    console.log(`  node ${id} kept ${cut.kept.has(id)} ${n?.refName}:${n?.start}-${n?.end} rank ${n?.rank} passes ${n?.passes} onWindow ${n?.onWindow}; fragments ${inFr.length} ${inFr.slice(0, 3)}; departures ${inDep.length} ${inDep.slice(0, 3)}`)
  }
  cut.graph.chunks.forEach((chunk: any, c: number) => {
    const { path, routes, walks: rowsOf } = chunk
    const hs = path.handles
    for (let k = 1; k < hs.length; k++) {
      const a = idOf(hs[k - 1]), b = idOf(hs[k])
      if ((a === x && b === y) || (a === y && b === x)) console.log(`  chunk ${c}: R walks it`)
    }
    routes.forEach((r: any, index: number) => {
      const seq = [r.entry, ...r.interior, r.exit]
      for (let k = 1; k < seq.length; k++) {
        const a = idOf(seq[k - 1]), b = idOf(seq[k])
        if ((a === x && b === y) || (a === y && b === x)) {
          const takers = rowsOf.filter((w: any) => { for (let j = 0; j < w.choices.length; j += 4) { if (w.choices[j] === index) return true } return false })
          console.log(`  chunk ${c} (${rowsOf.length} walk rows, refLengths ${chunk.refLengths !== undefined}, path ${path.starts[0]}-${path.end(hs.length - 1)}): route ${index} interior ${r.interior.length}, link at ${k - 1}->${k} of ${seq.length - 1}; takers ${takers.map((w: any) => `${w.cols[4]} piece ${w.cols[7]} span ${w.cols[1]}-${w.cols[2]} hapOffset ${w.cols[6]}`).join('; ')}`)
          for (const w of takers) {
            const fr = cut.fragments.filter((f: any) => f.name === w.cols[4])
            console.log(`    ${w.cols[4]} fragments: ${fr.map((f: any) => `${f.hapStart}-${f.hapEnd} steps ${f.ids.length} trimmed ${f.trimmedBefore}/${f.trimmedAfter}`).join(' | ')}`)
          }
        }
      }
    })
  })
}
