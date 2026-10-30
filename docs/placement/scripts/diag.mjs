// node diag.mjs INDEX WALKS REFSEQ START END [HAP,HAP...]
// For one window: the index cut's links from a node the walk cut draws to an
// index-only node, and whether any walk in the chunks the walk cut read steps
// across that link (both orientations), with the walk's name. Decodes every
// walk of the read chunks with graph-walks' decodeChunk.
const GW = process.env.GRAPH_WALKS ?? new URL('../../../../graph-walks', import.meta.url).pathname
const { WalkReader, rgfaCut, walksKept, joinPieces, WALK_BUDGETS } = await import(`${GW}/esm/index.js`)
const { decodeChunk } = await import(`${GW}/esm/walkChunk.js`)
const { TabixIndexedFile } = await import(`${GW}/node_modules/@gmod/tabix/esm/index.js`)

const [index, walks, ref, s, e, haps] = process.argv.slice(2)
const window = { start: +s, end: +e }
const haplotypes = haps ? haps.split(',') : undefined
const gfa = await rgfaCut({ graph: new TabixIndexedFile({ path: index }) }, { refName: ref, ...window })
const idx = new Map()
const idxLinks = []
for (const line of gfa.split('\n')) {
  const f = line.split('\t')
  if (f[0] === 'S') idx.set(f[1], line)
  if (f[0] === 'L') idxLinks.push([f[1], f[3]])
}
const file = new TabixIndexedFile({ path: walks })
const chunks = new Set()
const source = {
  getHeaderLines: o => file.getHeaderLines(o),
  getReferenceSequenceNames: o => file.getReferenceSequenceNames(o),
  bytesForRegions: (r, o) => file.bytesForRegions(r, o),
  getLines: (seq, a, b, o) =>
    file.getLines(seq, a, b, { ...o, lineCallback: l => { if (seq === ref) chunks.add(+l.split('\t')[1]); o.lineCallback(l) } }),
}
const cut = await new WalkReader(source).cut(ref, window, {
  ...WALK_BUDGETS,
  keep: walksKept(haplotypes, ref),
})
const t = cut.graph.tables(cut.kept, cut.fragments, cut.skips)
const drawn = new Set(t.nodes.names.slice(0, t.nodes.lengths.length))
const frontier = idxLinks.filter(([a, b]) => drawn.has(a) !== drawn.has(b))
console.log(`index ${idx.size} nodes, walk ${drawn.size}; ${frontier.length} index links from a drawn node to an index-only one; chunks read ${[...chunks].sort((a, b) => a - b).join(',')}`)
// every walk of the read chunks, every haplotype
const rows = []
for (const cs of [...chunks].sort((a, b) => a - b)) {
  const held = []
  await file.getLines(ref, cs, cs + 1, { lineCallback: l => { const c = l.split('\t'); if (+c[1] === cs) held.push(c) } })
  rows.push(...decodeChunk(held, undefined).rows)
}
const steps = new Map()
for (const run of joinPieces(rows)) {
  for (let i = 1; i < run.ids.length; i++) {
    const k = [run.ids[i - 1], run.ids[i]].sort((a, b) => a - b).join('|')
    if (!steps.has(k)) steps.set(k, new Set())
    steps.get(k).add(run.name.split('#').slice(0, 2).join('#'))
  }
}
let walked = 0
const walkers = new Map()
for (const [a, b] of frontier) {
  const k = [+a, +b].sort((x, y) => x - y).join('|')
  const who = steps.get(k)
  if (who) {
    walked++
    for (const h of who) walkers.set(h, (walkers.get(h) ?? 0) + 1)
  }
}
console.log(`${walked} of them stepped across by some walk in the read chunks; by haplotype: ${[...walkers].sort((x, y) => y[1] - x[1]).slice(0, 12).map(([h, n]) => `${h}:${n}`).join(' ')}`)
const sample = frontier.slice(0, 5).map(([a, b]) => (drawn.has(a) ? b : a))
for (const id of sample) console.log(idx.get(id).slice(0, 160))
