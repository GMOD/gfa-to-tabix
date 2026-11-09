// node hosted-cuts.mjs GRAPH_WALKS URL WINDOWS.tsv [all]
//
// Cuts each window of WINDOWS.tsv (sequence, start, end) from the walk file
// at URL with graph-walks' WalkReader, keeping eight HPRC haplotypes or, with
// `all`, every one, under the reader's default budgets. Prints per window the
// time, the range requests and compressed bytes the cut read after the
// sequence's table, what the cut holds, and the error where a budget stopped
// it. GRAPH_WALKS is a graph-walks checkout with its node_modules installed.
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { pathToFileURL } from 'node:url'

const [graphWalks, url, windows, mode = 'eight'] = process.argv.slice(2)
const require = createRequire(`${graphWalks}/package.json`)
const { RemoteFile } = require('generic-filehandle2')
const { WalkReader, walksKept } = await import(
  pathToFileURL(`${graphWalks}/src/index.ts`).href
)

const read = { requests: 0, bytes: 0 }
class Counting extends RemoteFile {
  async read(length, position, opts) {
    read.requests++
    read.bytes += length
    return super.read(length, position, opts)
  }
}

const eight = [
  'HG00097#1',
  'HG00099#1',
  'HG00128#1',
  'HG00133#1',
  'HG01109#1',
  'HG01123#1',
  'HG01960#1',
  'HG02055#1',
]
const reader = WalkReader.open(url, location => new Counting(location))
console.log(
  [
    'seq',
    'start',
    'end',
    'kept',
    'ms',
    'requests',
    'KB',
    'nodes',
    'links',
    'walks',
    'steps',
    'error',
  ].join('\t'),
)
for (const line of readFileSync(windows, 'utf8').trim().split('\n')) {
  const [seq, start, end] = line.split('\t')
  await reader.units(seq)
  const before = { ...read }
  const from = performance.now()
  const cut = await reader
    .cut(
      seq,
      { start: +start, end: +end },
      { keep: mode === 'all' ? undefined : walksKept(eight, seq) },
    )
    .then(
      ({ graph, kept, fragments, departures }) =>
        graph.tables(kept, fragments, departures),
      error => error,
    )
  const held =
    cut instanceof Error
      ? ['', '', '', '', `${cut.name}: ${cut.message.slice(0, 80)}`]
      : [
          cut.nodes.names.length,
          cut.links.from.length,
          cut.walks.names.length,
          cut.walks.steps.length,
          '',
        ]
  console.log(
    [
      seq,
      start,
      end,
      mode,
      Math.round(performance.now() - from),
      read.requests - before.requests,
      ((read.bytes - before.bytes) / 1e3).toFixed(1),
      ...held,
    ].join('\t'),
  )
}
