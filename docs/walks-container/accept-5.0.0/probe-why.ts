const [repo, walks] = process.argv.slice(2)
const { WalkReader, walksKept } = await import(`${repo}/src/index.ts`)
const { LocalFile } = await import(`${repo}/node_modules/generic-filehandle2/esm/index.js`)
const refName = 'CHM13#0#chr1'
const window = { start: 16394106, end: 16395106 }
const pairs = [[2032104, 2032108], [2033985, 2033988]]
const reader0 = WalkReader.open(walks, (p: string) => new LocalFile(p))
const header = await reader0.header()
console.log('tile', header.tile)
const batch = header.haplotypes.slice(0, 64)
const idOf = (h: number) => Math.floor(h / 2)
for (const loaded of [false, true]) {
  const reader = WalkReader.open(walks, (p: string) => new LocalFile(p))
  const cut = await reader.cut(refName, window, {
    keep: walksKept(batch, refName),
    context: 1000,
    stepBudget: Infinity,
    byteBudget: Infinity,
    departureByteBudget: Infinity,
    ...(loaded ? { expand: () => true } : {}),
  })
  console.log(`== ${loaded ? 'loaded' : 'unloaded'}: ${cut.fragments.length} fragments, ${cut.departures.length} departures, chunks ${cut.graph.chunks.length}`)
  for (const [x, y] of pairs) {
    for (const id of [x, y]) {
      const n = cut.graph.nodes.get(id)
      console.log(`  node ${id} kept ${cut.kept.has(id)} ${n?.refName}:${n?.start}-${n?.end} rank ${n?.rank} onWindow ${n?.onWindow}`)
      let nf = 0
      for (const f of cut.fragments) {
        const at = f.ids.indexOf(id)
        if (at >= 0 && nf++ < 4) {
          console.log(`    in fragment ${f.name} hap ${f.hapStart}-${f.hapEnd} at step ${at}/${f.ids.length} next ${f.ids[at + 1]} prev ${f.ids[at - 1]} refStart ${f.refStarts[at]} abridged ${f.abridged?.length ?? 0}`)
        }
      }
      console.log(`    fragments holding it: ${nf}`)
      let nd = 0
      for (const d of cut.departures) {
        const at = d.steps ? d.steps.ids.indexOf(id) : -1
        if (at >= 0 && nd++ < 4) {
          console.log(`    in departure ${d.name} leave ${d.leavePos} rejoin ${d.rejoinPos} ownBp ${d.ownBp} fromSteps ${d.fromSteps} steps ${d.steps.ids.length} at ${at}`)
        }
      }
      console.log(`    departures holding it: ${nd}`)
    }
    cut.graph.chunks.forEach((chunk: any, c: number) => {
      const { path, routes, walks: rowsOf } = chunk
      const hs = path.handles
      for (let k = 1; k < hs.length; k++) {
        if (idOf(hs[k - 1]) === x && idOf(hs[k]) === y) console.log(`  chunk ${c}: R walks ${x}->${y}`)
      }
      routes.forEach((r: any, index: number) => {
        const seq = [r.entry, ...r.interior, r.exit]
        for (let k = 1; k < seq.length; k++) {
          const a = idOf(seq[k - 1]), b = idOf(seq[k])
          if ((a === x && b === y) || (a === y && b === x)) {
            const takers = rowsOf.filter((w: any) => { for (let j = 0; j < w.choices.length; j += 4) { if (w.choices[j] === index) return true } return false })
            console.log(`  chunk ${c} (${rowsOf.length} walk rows, path ${path.starts[0]}-${path.end(hs.length - 1)}): route ${index} interior ${r.interior.length} links ${a}->${b}; takers ${takers.map((w: any) => `${w.cols[4]} piece ${w.cols[7]} span ${w.cols[1]}-${w.cols[2]} hapOffset ${w.cols[6]}`).join('; ')}`)
          }
        }
      })
    })
  }
}
