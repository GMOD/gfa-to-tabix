// Format 6 as graph-walks 5.0.2 reads it: WalkReader.cut over @gmod/tabix and
// RemoteFile against a range-logging server. Per window, the read alone
// (attachFetches 0) and the read with attach fetches (graph-walks' default).
// usage: node f6.mjs <windows.jsonl> <out.jsonl> [set,...]
import fs from 'node:fs'
import { TabixIndexedFile } from './gw/node_modules/@gmod/tabix/esm/index.js'
import { RemoteFile } from './gw/node_modules/generic-filehandle2/esm/index.js'
import { WalkReader } from './gw/src/walkReader.ts'
import { rangeServer } from './rangeServer.mjs'

const [windowsPath, outPath, setsArg] = process.argv.slice(2)
const FILES = {
  grch38: 'genome3/hprc-v2.1-mc-grch38.GRCh38.walks.bed.gz',
  chm13: 'genome3/hprc-v2.1-mc-chm13.CHM13.walks.bed.gz',
}
const LIFTED = { stepBudget: Infinity, byteBudget: Infinity, departureByteBudget: Infinity }
const sets = setsArg ? new Set(setsArg.split(',')) : undefined
const windows = fs
  .readFileSync(windowsPath, 'utf8')
  .trim()
  .split('\n')
  .map(l => JSON.parse(l))
  .filter(w => !sets || sets.has(w.set))

const srv = await rangeServer(`${process.env.HOME}/work`)
const open = genome => {
  const url = srv.base + FILES[genome]
  const tabix = new TabixIndexedFile({
    filehandle: new RemoteFile(url, { fetch: srv.timedFetch }),
    tbiFilehandle: new RemoteFile(`${url}.tbi`, { fetch: srv.timedFetch }),
  })
  return { tabix, reader: new WalkReader(tabix) }
}
const shape = cut => ({
  fragments: cut.fragments.length,
  steps: cut.fragments.reduce((s, f) => s + f.ids.length, 0),
  departures: cut.departures.length,
})
const cutWindow = (reader, w, attachFetches) =>
  reader.cut(w.seq, { start: w.start, end: w.end }, { ...LIFTED, attachFetches })

const out = fs.createWriteStream(outPath)
const readers = new Map()
for (const w of windows) {
  const rec = { ...w }
  if (w.set === 'first') {
    const { reader } = open(w.genome)
    const m0 = srv.mark()
    await reader.header()
    rec.open = srv.since(m0)
    const m1 = srv.mark()
    const t0 = performance.now()
    rec.cut = shape(await cutWindow(reader, w, undefined))
    rec.ms = performance.now() - t0
    rec.window = srv.since(m1)
    rec.total = srv.since(m0)
  } else {
    const key = `${w.genome}|${w.seq}`
    if (!readers.has(key)) {
      const r = open(w.genome)
      await r.reader.header()
      readers.set(key, r)
    }
    const { tabix, reader } = readers.get(key)
    tabix.clearChunkCache()
    const m0 = srv.mark()
    await cutWindow(reader, w, 0)
    rec.read = srv.since(m0)
    tabix.clearChunkCache()
    const m1 = srv.mark()
    const t0 = performance.now()
    rec.cut = shape(await cutWindow(reader, w, undefined))
    rec.ms = performance.now() - t0
    rec.withAttach = srv.since(m1)
  }
  out.write(JSON.stringify(rec) + '\n')
}
out.end()
srv.close()
