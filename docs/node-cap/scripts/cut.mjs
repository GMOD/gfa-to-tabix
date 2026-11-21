// cut.mjs WALKS OUT.tsv RUNS HAPLOTYPES SPEC...: times graph-walks cutting each SPEC (chr:start:width) of a local walk file
// with the browser preset's context and links, the named haplotypes kept and every budget and node limit lifted, as a
// browser reader's cut with its refusals off. Each run opens a reader, warms it on a 10 kb window elsewhere, then times
// cutRegion (walk read, decode and tables) per spec, once the 1-minute load is under 4. Writes one row per spec and run.
import { createRequire } from 'node:module'
import { open, readFile, writeFile, appendFile } from 'node:fs/promises'
import { loadavg } from 'node:os'

const require = createRequire(`${process.env.GRAPH_WALKS_DIR ?? process.cwd()}/`)
const { WalkReader, CUT_PRESETS } = await import(require.resolve('@jbrowse/graph-walks'))
const pkgDir = require.resolve('@jbrowse/graph-walks').replace(/\/esm\/.*$/, '')
const version = JSON.parse(await readFile(`${pkgDir}/package.json`, 'utf8')).version

class LocalFile {
  constructor(path) {
    this.source = path
    this.handle = open(path, 'r')
  }
  async read(length, position = 0) {
    const buffer = new Uint8Array(length)
    const { bytesRead } = await (await this.handle).read(buffer, 0, length, position)
    return buffer.subarray(0, bytesRead)
  }
  readFile(options) {
    return readFile(this.source, options)
  }
  async stat() {
    return (await this.handle).stat()
  }
}

const [walks, out, runs, haps, ...specs] = process.argv.slice(2)
const haplotypes = haps.split(',')
const options = { ...CUT_PRESETS.figure, nodeLimit: Infinity, haplotypes }
const cols = ['graph_walks', 'spec', 'refName', 'start', 'end', 'run', 'load1', 'nodes', 'placeholders', 'links', 'walks', 'steps', 'cut_ms', 'heap_mb']
await writeFile(out, cols.join('\t') + '\n')
for (let run = 1; run <= Number(runs); run++) {
  const reader = WalkReader.fromFilehandles({ data: new LocalFile(walks), directory: new LocalFile(`${walks}.idx`) })
  for (const spec of specs) {
    const [refName, s, w] = spec.split(':')
    const start = Number(s)
    const end = start + Number(w)
    await reader.cutRegion({ refName, start: start > 2e6 ? start - 1e6 : start + 2e7, end: (start > 2e6 ? start - 1e6 : start + 2e7) + 1e4 }, options)
    globalThis.gc?.()
    while (loadavg()[0] >= 4) {
      await new Promise(r => setTimeout(r, 15_000))
    }
    const load1 = loadavg()[0].toFixed(2)
    const t = performance.now()
    const { tables } = await reader.cutRegion({ refName, start, end }, options)
    const ms = performance.now() - t
    const placeholders = tables.nodes.placeholders?.reduce((a, b) => a + b, 0) ?? 0
    const row = {
      graph_walks: version, spec, refName, start, end, run, load1,
      nodes: tables.nodes.names.length, placeholders, links: tables.links.from.length,
      walks: tables.walks.names.length, steps: tables.walks.steps.length,
      cut_ms: ms.toFixed(1), heap_mb: (process.memoryUsage().heapUsed / 1e6).toFixed(0),
    }
    await appendFile(out, cols.map(c => row[c]).join('\t') + '\n')
    process.stderr.write(`${cols.map(c => row[c]).join('\t')}\n`)
  }
}
