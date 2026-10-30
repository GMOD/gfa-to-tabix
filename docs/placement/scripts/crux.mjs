// Compares what the JBrowse graph plugin draws for a window from a
// gfa-to-tabix format 2 index (RgfaTabixAdapter.getSubgraph -> rgfaCut) with
// what it draws from a walk file (WalkIndex.subgraph -> WalkReader.cut ->
// WalkGraph.tables), using @jbrowse/graph-walks itself.
//
// node crux.mjs --graph NAME --index F.graph.bed.gz --walks F.walks.bed.gz
//   --ref GRCh38#0#chr22 --windows windows.tsv --out OUT.jsonl
//   [--haps hosted|first8|HG002#1,...] [--modes hap8,hap8rows,all,allrows]

import { parseArgs } from 'node:util'
import fs from 'node:fs'

const GW = process.env.GRAPH_WALKS ?? new URL('../../../../graph-walks', import.meta.url).pathname
const { WalkReader, WALK_BUDGETS, walksKept, rgfaCut } = await import(
  `${GW}/esm/index.js`
)
const { TabixIndexedFile } = await import(
  `${GW}/node_modules/@gmod/tabix/esm/index.js`
)
const { LocalFile } = await import(
  `${GW}/node_modules/generic-filehandle2/esm/index.js`
)

// the hosted HPRC walk track's defaultHaplotypes, jbrowse-components
// demos/hprc/config.json
const HOSTED = [
  'HG00097#1',
  'HG00099#1',
  'HG00128#1',
  'HG00133#1',
  'HG01109#1',
  'HG01123#1',
  'HG01960#1',
  'HG02055#1',
]
// the plugin's walkReader.ts
const EXPAND_NAMED_MAX = 64
const BUDGET_SLOTS = { steps: 'walkStepBudget', bytes: 'walkByteBudget' }
// graph-walks walkReader.ts, for the reach a follow could have had
const FOLLOW_CHUNKS = 4

const { values: args } = parseArgs({
  options: {
    graph: { type: 'string' },
    index: { type: 'string' },
    walks: { type: 'string' },
    ref: { type: 'string' },
    windows: { type: 'string' },
    out: { type: 'string' },
    haps: { type: 'string', default: 'hosted' },
    modes: { type: 'string', default: 'hap8,hap8rows,all' },
    limit: { type: 'string' },
  },
})

class CountingFile {
  constructor(path) {
    this.file = new LocalFile(path)
    this.bytes = 0
  }
  async read(length, position, opts) {
    const buf = await this.file.read(length, position, opts)
    this.bytes += buf.length
    return buf
  }
  readFile(opts) {
    return this.file.readFile(opts)
  }
  stat() {
    return this.file.stat()
  }
  close() {
    return this.file.close()
  }
}

// A fresh TabixIndexedFile per cut, so no chunk cache carries between windows,
// with its index and header read before the count starts
async function openTabix(path) {
  const data = new CountingFile(path)
  const file = new TabixIndexedFile({
    filehandle: data,
    tbiFilehandle: new LocalFile(`${path}.tbi`),
  })
  await file.getHeaderLines()
  await file.getReferenceSequenceNames()
  data.bytes = 0
  return { file, data }
}

// Records the chunks a walk cut's reads decode, by the cs column of each row
// on the reference sequence
function recordingSource(file, refName, chunks) {
  return {
    getHeaderLines: o => file.getHeaderLines(o),
    getReferenceSequenceNames: o => file.getReferenceSequenceNames(o),
    bytesForRegions: (r, o) => file.bytesForRegions(r, o),
    getLines(seq, start, end, opts) {
      return file.getLines(seq, start, end, {
        ...opts,
        lineCallback: line => {
          const t1 = line.indexOf('\t')
          const t2 = line.indexOf('\t', t1 + 1)
          const cs = +line.slice(t1 + 1, t2)
          if (seq === refName) {
            chunks.add(cs)
          } else {
            chunks.add(`detail:${seq}`)
          }
          opts.lineCallback(line)
        },
      })
    },
  }
}

function parseGfa(text) {
  const nodes = new Map()
  const links = new Set()
  for (const line of text.split('\n')) {
    const f = line.split('\t')
    if (f[0] === 'S') {
      const tag = {}
      for (const t of f.slice(3)) {
        tag[t.slice(0, 2)] = t.slice(5)
      }
      nodes.set(f[1], {
        id: f[1],
        len: +tag.LN,
        seq: tag.SN,
        start: +tag.SO,
        rank: +tag.SR,
        carriers: tag.SM === undefined ? undefined : tag.SM.split(','),
        moved: tag.mv === '1',
      })
    } else if (f[0] === 'L') {
      links.add(pairKey(f[1], f[3]))
    }
  }
  return { nodes, links }
}

const pairKey = (a, b) => (a < b ? `${a}|${b}` : `${b}|${a}`)

async function indexCut(window) {
  const { file, data } = await openTabix(args.index)
  const t0 = performance.now()
  const gfa = await rgfaCut(
    { graph: file },
    { refName: args.ref, start: window.start, end: window.end },
    { hops: 1 },
  )
  const ms = performance.now() - t0
  return { ...parseGfa(gfa), ms, bytes: data.bytes }
}

// WalkIndex.subgraph with the plugin's default budgets; `walkRows` is the
// walk-rows layout, which lifts the step budget and reads a short named list's
// abridged rows in full
async function walkCut(window, haplotypes, walkRows) {
  const { file, data } = await openTabix(args.walks)
  const chunks = new Set()
  const reader = new WalkReader(recordingSource(file, args.ref, chunks))
  const header = await reader.header()
  data.bytes = 0
  const keep = walksKept(haplotypes, args.ref)
  const named =
    walkRows && keep && (haplotypes?.length ?? 0) <= EXPAND_NAMED_MAX
      ? keep
      : undefined
  const t0 = performance.now()
  try {
    const { graph, kept, fragments, skips } = await reader.cut(
      args.ref,
      window,
      {
        stepBudget: walkRows ? Infinity : WALK_BUDGETS.stepBudget,
        byteBudget: WALK_BUDGETS.byteBudget,
        budgetNames: BUDGET_SLOTS,
        keep,
        ...(named ? { expand: name => !!named(name) } : {}),
      },
    )
    const tables = graph.tables(kept, fragments, skips)
    const ms = performance.now() - t0
    const { names, lengths, ranks, refNames, refs, starts } = tables.nodes
    const nodes = new Map()
    for (let i = 0; i < lengths.length; i++) {
      nodes.set(names[i], {
        rank: ranks[i],
        seq: refNames[refs[i]],
        start: starts[i],
      })
    }
    const links = new Set()
    for (let k = 0; k < tables.links.from.length; k++) {
      links.add(
        pairKey(names[tables.links.from[k]], names[tables.links.to[k]]),
      )
    }
    const { chunk } = header
    const from = await reader.queryStart(window.start, {
      refName: args.ref,
      end: window.end,
    })
    const last = Math.floor((window.end - 1) / chunk) * chunk
    const w = tables.walks
    const abridged = []
    // fragments whose kept steps run to the edge of the rows read, the walk
    // going on in a chunk the follow rounds did not read
    const open = []
    const elsewhere = w.before.kindNames.indexOf('elsewhere')
    for (let p = 0; p < w.names.length; p++) {
      if (!Number.isNaN(w.abridgedSteps[p])) {
        abridged.push(w.names[p])
      }
      const cutOff = stops =>
        stops.kinds[p] === elsewhere && stops.trimmed[p] === 0
      if (cutOff(w.before) || cutOff(w.after)) {
        open.push(w.names[p])
      }
    }
    const sk = tables.skips
    const skipRows = sk.names.map((name, i) => [name, sk.starts[i], sk.ends[i]])
    return {
      nodes,
      links,
      ms,
      bytes: data.bytes,
      walkNames: w.names,
      abridged,
      open,
      skips: skipRows,
      chunk,
      readFrom: from,
      reachLo: from - FOLLOW_CHUNKS * chunk,
      reachHi: last + FOLLOW_CHUNKS * chunk,
      chunksRead: [...chunks].filter(c => typeof c === 'number').sort((a, b) => a - b),
      detailReads: [...chunks].filter(c => typeof c !== 'number').length,
    }
  } catch (error) {
    return {
      error: `${error.name}: ${error.message}`,
      ms: performance.now() - t0,
      bytes: data.bytes,
    }
  }
}

async function chooseHaplotypes() {
  const { file } = await openTabix(args.walks)
  const { haplotypes } = await new WalkReader(file).header()
  if (args.haps === 'first8') {
    return haplotypes.slice(0, 8)
  }
  const wanted = args.haps === 'hosted' ? HOSTED : args.haps.split(',')
  const chosen = wanted.filter(h => haplotypes.includes(h))
  for (const h of haplotypes) {
    if (chosen.length >= wanted.length) {
      break
    }
    if (!chosen.includes(h)) {
      chosen.push(h)
    }
  }
  return chosen
}

const haplotypeOf = name => name.split('#').slice(0, 2).join('#')

// `HG002#1` as the index's #samples names it, `HG002.1`
const indexSampleName = h => h.replace('#', '.')

function classify(window, indexNodes, walkNodes, selected, wk) {
  const walked = new Set(wk.walkNames.map(h => indexSampleName(haplotypeOf(h))))
  const skipping = new Set(wk.skips.map(([h]) => indexSampleName(haplotypeOf(h))))
  const sel = selected && new Set(selected.map(indexSampleName))
  const out = []
  for (const [id, n] of indexNodes) {
    if (walkNodes.has(id)) {
      continue
    }
    let cls
    let dist
    if (n.moved) {
      cls = 5
    } else if (n.rank === 0) {
      dist =
        n.seq !== args.ref
          ? Infinity
          : Math.max(0, n.start - window.end, window.start - (n.start + n.len))
      cls = dist >= 1e6 ? 1 : 2
    } else if (n.carriers === undefined) {
      cls = '3?'
    } else {
      cls =
        sel === undefined || n.carriers.some(c => sel.has(c)) ? 3 : 4
    }
    // what the walk view shows of a class 3 node's selected carriers: a walk
    // of one, whose drawn stretch the node lies off; only a skip row; nothing
    let sub
    if (cls === 3) {
      const mine = n.carriers.filter(c => sel === undefined || sel.has(c))
      sub = mine.some(c => walked.has(c))
        ? 'walked'
        : mine.some(c => skipping.has(c))
          ? 'skip'
          : 'none'
    }
    out.push({
      id,
      cls,
      rank: n.rank,
      seq: n.seq,
      start: n.start,
      len: n.len,
      dist: dist === Infinity ? 'other-seq' : dist,
      carriersSelected: sel && n.carriers?.filter(c => sel.has(c)),
      sub,
      nCarriers: n.carriers?.length,
    })
  }
  return out
}

function readWindows(path) {
  return fs
    .readFileSync(path, 'utf8')
    .split('\n')
    .filter(l => l && !l.startsWith('#'))
    .map(l => {
      const [stratum, start, end] = l.split('\t')
      return { stratum, start: +start, end: +end }
    })
}

const haps8 = await chooseHaplotypes()
const modes = {
  hap8: { haplotypes: haps8, walkRows: false },
  hap8rows: { haplotypes: haps8, walkRows: true },
  all: { haplotypes: undefined, walkRows: false },
  allrows: { haplotypes: undefined, walkRows: true },
}
const wanted = args.modes.split(',')
let windows = readWindows(args.windows)
if (args.limit) {
  windows = windows.slice(0, +args.limit)
}
const out = fs.createWriteStream(args.out)
out.write(
  `${JSON.stringify({ meta: { graph: args.graph, index: args.index, walks: args.walks, ref: args.ref, haps8, budgets: WALK_BUDGETS } })}\n`,
)
for (const window of windows) {
  const idx = await indexCut(window)
  for (const mode of wanted) {
    const { haplotypes, walkRows } = modes[mode]
    const wk = await walkCut(window, haplotypes, walkRows)
    const rec = {
      graph: args.graph,
      stratum: window.stratum,
      start: window.start,
      end: window.end,
      mode,
      index: {
        nodes: idx.nodes.size,
        links: idx.links.size,
        ms: idx.ms,
        bytes: idx.bytes,
      },
    }
    if (wk.error) {
      rec.walk = { error: wk.error, ms: wk.ms, bytes: wk.bytes }
    } else {
      const indexOnlyLinks = [...idx.links].filter(l => !wk.links.has(l))
      const walkOnlyLinks = [...wk.links].filter(l => !idx.links.has(l))
      const walkOnly = [...wk.nodes.keys()].filter(id => !idx.nodes.has(id))
      rec.walk = {
        nodes: wk.nodes.size,
        links: wk.links.size,
        ms: wk.ms,
        bytes: wk.bytes,
        walks: wk.walkNames.length,
        abridged: wk.abridged,
        open: wk.open,
        skips: wk.skips,
        walkHaps: [...new Set(wk.walkNames.map(haplotypeOf))],
        chunk: wk.chunk,
        readFrom: wk.readFrom,
        reachLo: wk.reachLo,
        reachHi: wk.reachHi,
        chunksRead: wk.chunksRead,
        detailReads: wk.detailReads,
      }
      rec.indexOnly = classify(window, idx.nodes, wk.nodes, haplotypes, wk)
      rec.walkOnly = {
        n: walkOnly.length,
        rank0: walkOnly.filter(id => wk.nodes.get(id).rank === 0).length,
      }
      rec.indexOnlyLinks = indexOnlyLinks.length
      // index-only links with both ends drawn by the walk reader
      rec.indexOnlyLinksBothDrawn = indexOnlyLinks.filter(l => {
        const [a, b] = l.split('|')
        return wk.nodes.has(a) && wk.nodes.has(b)
      }).length
      rec.walkOnlyLinks = walkOnlyLinks.length
    }
    out.write(`${JSON.stringify(rec)}\n`)
    const w = rec.walk
    console.error(
      `${args.graph} ${window.stratum} ${window.start} ${mode}: index ${idx.nodes.size}n/${idx.links.size}l ${idx.ms.toFixed(0)}ms; walk ${w.error ? w.error.slice(0, 80) : `${w.nodes}n/${w.links}l ${w.ms.toFixed(0)}ms io=${rec.indexOnly.length}`}`,
    )
  }
}
out.end()
