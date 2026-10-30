// node refvisits.mjs WALKS REFSEQ WINDOWS.tsv OUT.json [HAP,HAP...]
// For each window, the reference nodes the walk file's ref rows visit on the
// window plus graph-walks' 1 kb context, read the way the plugin's
// WalkIndex.referenceNodes reads them (from WalkReader.queryStart). A node the
// reference visits there belongs in a window's drawing whatever coordinate
// either file states for it. With haplotypes, also cuts each window as the
// plugin's graph layout does for them and lists the visited nodes the cut
// does not draw, under OUT.json's `undrawn`.
import fs from 'node:fs'

const GW = process.env.GRAPH_WALKS ?? new URL('../../../../graph-walks', import.meta.url).pathname
const { WalkReader, referenceNodes, walksKept, WALK_BUDGETS } = await import(`${GW}/esm/index.js`)
const { TabixIndexedFile } = await import(`${GW}/node_modules/@gmod/tabix/esm/index.js`)

const CONTEXT = 1000
const [walks, ref, windowsPath, outPath, haps] = process.argv.slice(2)
const file = new TabixIndexedFile({ path: walks })
const reader = new WalkReader(file)
const out = {}
const undrawn = {}
for (const line of fs.readFileSync(windowsPath, 'utf8').split('\n')) {
  if (!line || line.startsWith('#')) continue
  const [, s, e] = line.split('\t')
  const start = Math.max(0, +s - CONTEXT)
  const end = +e + CONTEXT
  const from = await reader.queryStart(start, { refName: ref, end })
  const rows = []
  await file.getLines(ref, from, end, {
    lineCallback: l => {
      const c = l.split('\t')
      if (c[3] === 'ref') rows.push(c)
    },
  })
  const ids = new Set()
  for (const n of referenceNodes(rows)) {
    if (n.refName === ref && n.end > start && n.start < end) ids.add(n.id)
  }
  out[s] = [...ids]
  if (haps) {
    try {
      const cut = await new WalkReader(file).cut(
        ref,
        { start: +s, end: +e },
        { ...WALK_BUDGETS, keep: walksKept(haps.split(','), ref) },
      )
      const t = cut.graph.tables(cut.kept, cut.fragments, cut.skips)
      const drawn = new Set(t.nodes.names.slice(0, t.nodes.lengths.length).map(Number))
      undrawn[s] = [...ids].filter(id => !drawn.has(id))
    } catch (error) {
      undrawn[s] = String(error.message)
    }
  }
}
fs.writeFileSync(outPath, JSON.stringify(haps ? { visits: out, undrawn } : out))
