#!/usr/bin/env node
// walk-time.mjs <graph-walks checkout> WALKS SEQUENCE WINDOWS.tsv OUT.tsv [--sequences]
//
// Times @jbrowse/graph-walks, the reader of walk format 8, cutting each
// window of WINDOWS.tsv (windows.py's, one tile at each `start`) from the
// walk file WALKS, a local path or an http(s) URL it reads by range request:
// every haplotype, context 0 and no budget, so no window is refused, and
// abridged pieces left unexpanded, as a viewer first draws them. --sequences
// asks for node bases, from a --sequences file.
//
// Per window, each the median of three runs after one untimed pass over
// every window:
//   open_cut_ms  a new reader: the directory, the header unit and the
//                sequence's table, then the cut
//   cut_ms       the cut on a reader that is open and has cut another window
//   tables_ms    graph.tables on the cut's result, the node, link and walk
//                tables a viewer draws from
// and what the cut returned: fragments, steps, departures, the placeholder
// steps that stand for runs of an abridged piece, the distinct nodes the
// fragments step on, and a SHA-1 of their ids, sorted as strings and joined
// by newlines, to compare with windows.py's of gfaidx's segments.

import { createHash } from 'node:crypto'
import { open, readFile, writeFile } from 'node:fs/promises'
import { join, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

class LocalFile {
  constructor(path) {
    this.source = path
    this.handle = open(path, 'r')
  }

  async read(length, position = 0) {
    const buffer = new Uint8Array(length)
    const { bytesRead } = await (
      await this.handle
    ).read(buffer, 0, length, position)
    return buffer.subarray(0, bytesRead)
  }

  readFile(options) {
    return readFile(this.source, options)
  }

  async stat() {
    return (await this.handle).stat()
  }

  async close() {
    await (await this.handle).close()
  }
}

const [checkout, walks, sequence, windowsPath, outPath, flag] =
  process.argv.slice(2)
const { WalkReader, isPlaceholder } = await import(
  pathToFileURL(join(resolve(checkout), 'src/index.ts')).href
)
const remote = /^https?:/.test(walks)
const directory = remote
  ? await (await fetch(`${walks}.idx`)).text()
  : await readFile(`${walks}.idx`, 'utf8')
const tile = Number(/\ttile:i:(\d+)/.exec(directory)[1])
const [header, ...lines] = (await readFile(windowsPath, 'utf8'))
  .trim()
  .split('\n')
const startColumn = header.split('\t').indexOf('start')
const starts = lines.map(line => Number(line.split('\t')[startColumn]))
const options = {
  context: 0,
  stepBudget: Infinity,
  byteBudget: Infinity,
  departureByteBudget: Infinity,
  sequences: flag === '--sequences',
}

async function withLocalReader(run) {
  const files = {
    data: new LocalFile(walks),
    directory: new LocalFile(`${walks}.idx`),
  }
  const result = await run(WalkReader.fromFilehandles(files))
  await files.data.close()
  await files.directory.close()
  return result
}

const withReader = run =>
  remote ? run(WalkReader.open(walks)) : withLocalReader(run)

const region = start => ({ start, end: start + tile })

async function timed(run) {
  const began = performance.now()
  const result = await run()
  return { ms: performance.now() - began, result }
}

const median = values => values.toSorted((a, b) => a - b)[values.length >> 1]

async function measure(start, other) {
  const fresh = await timed(() =>
    withReader(reader => reader.cut(sequence, region(start), options)),
  )
  const warm = await withReader(async reader => {
    await reader.cut(sequence, region(other), options)
    return timed(() => reader.cut(sequence, region(start), options))
  })
  const { graph, kept, fragments, departures } = warm.result
  const tables = await timed(() => graph.tables(kept, fragments, departures))
  const stepped = new Set()
  for (const f of fragments) {
    for (const id of f.ids) {
      stepped.add(id)
    }
  }
  const ids = [...stepped].filter(id => !isPlaceholder(id)).map(String)
  return {
    openCut: fresh.ms,
    cut: warm.ms,
    tables: tables.ms,
    fragments: fragments.length,
    steps: fragments.reduce((n, f) => n + f.ids.length, 0),
    placeholders: fragments.reduce(
      (n, f) => n + f.ids.filter(isPlaceholder).length,
      0,
    ),
    nodes: ids.length,
    nodesSha1: createHash('sha1').update(ids.toSorted().join('\n')).digest('hex'),
    departures: departures.length,
  }
}

const others = starts.map((_, i) => starts[(i + 1) % starts.length])
for (const [i, start] of starts.entries()) {
  await measure(start, others[i])
}
const rows = [
  [
    'start',
    'open_cut_ms',
    'cut_ms',
    'tables_ms',
    'fragments',
    'steps',
    'placeholders',
    'nodes',
    'departures',
    'nodes_sha1',
  ].join('\t'),
]
for (const [i, start] of starts.entries()) {
  const runs = []
  for (let n = 0; n < 3; n++) {
    runs.push(await measure(start, others[i]))
  }
  const last = runs[2]
  rows.push(
    [
      start,
      median(runs.map(r => r.openCut)).toFixed(1),
      median(runs.map(r => r.cut)).toFixed(1),
      median(runs.map(r => r.tables)).toFixed(1),
      last.fragments,
      last.steps,
      last.placeholders,
      last.nodes,
      last.departures,
      last.nodesSha1,
    ].join('\t'),
  )
}
await writeFile(outPath, `${rows.join('\n')}\n`)
