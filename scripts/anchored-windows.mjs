// node scripts/anchored-windows.mjs GRAPH_WALKS PREFIX SEQ SPAN [WINDOW_BP] [N]
//
// For N random windows (default 50 of 10 kb) on SEQ, between 0 and SPAN: the
// compressed bytes @gmod/tabix reads from PREFIX.segs.bed.gz and
// PREFIX.links.bed.gz, and the subgraph graph-walks' anchoredCut keeps.
// GRAPH_WALKS is a graph-walks checkout with its node_modules installed; Node
// imports its TypeScript source directly.
import { createRequire } from 'node:module'
import { pathToFileURL } from 'node:url'

const [graphWalks, prefix, seq, span, windowBp = '10000', n = '50'] =
  process.argv.slice(2)
const require = createRequire(`${graphWalks}/package.json`)
const { TabixIndexedFile } = require('@gmod/tabix')
const { LocalFile } = require('generic-filehandle2')
const { anchoredCut, parseLinkLine, parseSegmentRow } = await import(
  pathToFileURL(`${graphWalks}/src/rgfaBed.ts`).href
)

class Counting extends LocalFile {
  bytes = 0
  async read(length, position, opts) {
    const bytes = await super.read(length, position, opts)
    this.bytes += bytes.length
    return bytes
  }
}

// a fresh file per read, so no window reads from another's cache
async function read(path, start, end) {
  const filehandle = new Counting(path)
  const file = new TabixIndexedFile({
    filehandle,
    tbiFilehandle: new LocalFile(`${path}.tbi`),
  })
  const lines = []
  await file.getLines(seq, start, end, { lineCallback: l => lines.push(l) })
  return { lines, bytes: filehandle.bytes }
}

let seed = 7
const random = () => {
  seed = (seed * 1103515245 + 12345) % 2 ** 31
  return seed / 2 ** 31
}

const rows = []
for (let k = 0; k < +n; k++) {
  const start = Math.floor(random() * (+span - +windowBp))
  const end = start + +windowBp
  const segs = await read(`${prefix}.segs.bed.gz`, start, end)
  const links = await read(`${prefix}.links.bed.gz`, start, end)
  const under = new Map(
    segs.lines.map(l => parseSegmentRow(l).segment).map(s => [s.id, s]),
  )
  const cut = anchoredCut(under, links.lines.map(parseLinkLine), {
    refName: seq,
    start,
    end,
  })
  const far = [...cut.segments.values()].filter(
    s => s.refName === seq && (s.end < start - 1e5 || s.start > end + 1e5),
  )
  rows.push([segs.bytes, links.bytes, cut.segments.size, far.length])
}
const median = i => rows.map(r => r[i]).sort((a, b) => a - b)[rows.length >> 1]
console.log(
  `${prefix}: median of ${n} windows of ${windowBp} bp: nodes ${(median(0) / 1e3).toFixed(1)} KB, links ${(median(1) / 1e3).toFixed(1)} KB read; cut keeps ${median(2)} nodes, ${median(3)} of them over 100 kb outside the window`,
)
