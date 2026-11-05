// Correctness: graph-walks 5.0.2's own `cut` on each window, once as shipped
// (format 6 file, chunk-before rule) and once through a candidate's file and
// query procedure, comparing fragments, departures and kept nodes.
//
// usage: node cutcheck.mjs DATADIR WINDOWS.jsonl CAND OUT.jsonl [maxPerSize]
//   CAND  f6p | t64 | t16 | o
import fs from 'node:fs'
import zlib from 'node:zlib'
import { createRequire } from 'node:module'
import { WalkReader } from '/home/cdiesh/src/graph-walks/esm/index.js'

const require = createRequire('/home/cdiesh/src/graph-walks/package.json')
const { TabixIndexedFile } = require('@gmod/tabix')
const { LocalFile } = require('generic-filehandle2')

const [dataDir, windowsPath, cand, outPath, maxArg] = process.argv.slice(2)
const maxPerSize = +(maxArg ?? 60)
const CONTEXT = 1000
const REACH = +(process.env.REACH ?? 1024)
const CHUNK = cand === 't16' ? 16384 : 65536
const CONTEXT_S = 1000

const windows = fs
  .readFileSync(windowsPath, 'utf8')
  .split('\n')
  .filter(Boolean)
  .map(l => JSON.parse(l))
const perSize = new Map()
const sample = windows.filter(w => {
  const n = perSize.get(w.size) ?? 0
  perSize.set(w.size, n + 1)
  return n < maxPerSize
})

function tabix(file, index) {
  return new TabixIndexedFile({
    filehandle: new LocalFile(`${dataDir}/${file}`),
    ...(index === 'csi'
      ? { csiFilehandle: new LocalFile(`${dataDir}/${file}.csi`) }
      : { tbiFilehandle: new LocalFile(`${dataDir}/${file}.tbi`) }),
  })
}

const chunkStart = (x, chunk = CHUNK) => Math.max(0, Math.floor(x / chunk) * chunk)

// the shipped reader over the shipped file
function shippedSource() {
  const t = tabix(process.env.BASE ?? 'f6.bed.gz', 'tbi')
  return {
    getHeaderLines: o => t.getHeaderLines(o),
    getReferenceSequenceNames: o => t.getReferenceSequenceNames(o),
    getLines: (name, s, e, o) => t.getLines(name, s, e, o),
  }
}

// a candidate's source: the reader's walk read [chunk before, end) becomes
// the candidate's query; its attach reads [lookback, cs + 1) become
// [cs - reach, cs + 1) (a superset of the exact [base - reach, base + 1));
// departure and detail reads pass through
function candidateSource(current) {
  let t
  let deps
  let depName = name => name
  let offset
  let table
  if (cand === 's' || cand === 's7') {
    const text = zlib.gunzipSync(fs.readFileSync(`${dataDir}/${cand}.walks.idx.gz`)).toString()
    const entries = []
    let header
    for (const line of text.split('\n')) {
      if (!line) {
        continue
      }
      const [seq, start, end, kind, name, off, size] = line.split('\t')
      const entry = { seq, start: +start, end: +end, kind, name, offset: +off, size: +size }
      if (kind === 'header') {
        header = entry
      } else {
        entries.push(entry)
      }
    }
    const fd = fs.openSync(`${dataDir}/${cand}.walks.gz`, 'r')
    const readRange = (off, size) => {
      const buf = Buffer.alloc(size)
      fs.readSync(fd, buf, 0, size, off)
      return zlib.gunzipSync(buf).toString()
    }
    table = { entries, header, readRange }
  } else if (cand === 'o') {
    const text = zlib.gunzipSync(fs.readFileSync(`${dataDir}/o.walks.idx.gz`)).toString()
    const entries = []
    let header
    for (const line of text.split('\n')) {
      if (!line) {
        continue
      }
      const [name, start, end, off, size] = line.split('\t')
      const entry = { name, start: +start, end: +end, offset: +off, size: +size }
      if (name === '#header') {
        header = entry
      } else {
        entries.push(entry)
      }
    }
    const fd = fs.openSync(`${dataDir}/o.walks.bgz`, 'r')
    const readRange = (off, size) => {
      const buf = Buffer.alloc(size)
      fs.readSync(fd, buf, 0, size, off)
      return zlib.gunzipSync(buf).toString()
    }
    offset = { entries, header, readRange }
    deps = tabix('o.departures.bed.gz', 'tbi')
    depName = name => name.replace('~departure', '')
  } else {
    t = tabix(`${cand}.bed.gz`, cand === 't64' || cand === 't64b' ? 'csi' : 'tbi')
    deps = t
  }
  const walkQuery = (name, s, e) => {
    const { drawn, walkRead } = current
    const main = walkRead.count === 0
    walkRead.count++
    const cs = main ? undefined : e - 1
    switch (cand) {
      case 'f6p':
        return main
          ? [chunkStart(Math.max(0, drawn.start - REACH)), e]
          : [chunkStart(Math.max(0, cs - REACH)), e]
      case 't64':
      case 't64b':
      case 't16':
      case 'o':
        return main ? [Math.max(0, drawn.start - REACH), e] : [Math.max(0, cs - REACH), e]
      case 's':
      case 's7':
        // an attach read names the leave base's chunk; the tile holding the
        // piece is the one whose extent contains the base, so take every
        // tile whose extent touches the chunk (a superset of the exact tile)
        return main ? [drawn.start, e] : [Math.max(0, cs - REACH), cs + CHUNK]
      default:
        throw new Error(cand)
    }
  }
  return {
    getHeaderLines: async o =>
      table
        ? table.readRange(table.header.offset, table.header.size).split('\n').filter(l => l.startsWith('#'))
        : offset
          ? offset
              .readRange(offset.header.offset, offset.header.size)
              .split('\n')
              .filter(l => l.startsWith('#'))
          : t.getHeaderLines(o),
    getReferenceSequenceNames: async o =>
      table
        ? [...new Set(table.entries.map(e => e.seq))]
        : offset
          ? [...new Set(offset.entries.map(e => e.name))]
          : t.getReferenceSequenceNames(o),
    getLines: async (name, s, e, o) => {
      if (table) {
        if (name.includes('~departure')) {
          const seq = name.replace('~departure', '')
          const seen = new Set()
          for (const entry of table.entries) {
            if (entry.seq === seq && entry.kind === 'departures' && entry.end > s && entry.start < e) {
              for (const line of table.readRange(entry.offset, entry.size).split('\n')) {
                if (line && !seen.has(line)) {
                  seen.add(line)
                  const cols = line.split('\t')
                  if (+cols[1] < e && +cols[2] > s) {
                    o.lineCallback(line)
                  }
                }
              }
            }
          }
          return
        }
        if (name.includes('~')) {
          const [seq, cs] = name.split('~')
          const d = Math.floor(s / 16384)
          for (const entry of table.entries) {
            if (entry.seq === seq && entry.kind === 'detail' && entry.name === `${cs}:${d}`) {
              for (const line of table.readRange(entry.offset, entry.size).split('\n')) {
                if (line) {
                  o.lineCallback(`${name}\t${s}\t${s + 1}\t${line}`)
                }
              }
            }
          }
          return
        }
        const [qs, qe] = walkQuery(name, s, e)
        let n = 0
        const names = []
        for (const entry of table.entries) {
          if (entry.seq === name && entry.kind === 'tile' && entry.end > qs && entry.start < qe) {
            names.push(entry.name)
            for (const line of table.readRange(entry.offset, entry.size).split('\n')) {
              if (line) {
                n++
                const body = cand === 's7' ? line.split('\t').slice(3).join('\t') : line
                o.lineCallback(`${name}\t${entry.name}\t${+entry.name + 1}\t${body}`)
              }
            }
          }
        }
        if (process.env.CUTDEBUG) {
          process.stderr.write(`S read asked [${s}, ${e}) -> [${qs}, ${qe}) tiles ${names.join(',')} rows ${n}\n`)
        }
        return
      }
      if (name.includes('~departure')) {
        // rows filed at a pyramid block's extent carry the record's own
        // extent as two trailing columns; a reader keeps the records that
        // touch its extent
        return deps.getLines(depName(name), s, e, {
          ...o,
          lineCallback: line => {
            const cols = line.split('\t')
            if (cols.length < 16 || (+cols[14] < e && +cols[15] > s)) {
              o.lineCallback(line)
            }
          },
        })
      }
      if (name.includes('~')) {
        if (offset) {
          const rec = Math.floor(s / 16384)
          for (const entry of offset.entries) {
            if (entry.name === name && entry.start === rec) {
              for (const line of offset.readRange(entry.offset, entry.size).split('\n')) {
                if (line) {
                  const cols = line.split('\t')
                  cols.splice(2, 0, String(+cols[1] + 1))
                  o.lineCallback(cols.join('\t'))
                }
              }
            }
          }
          return
        }
        return t.getLines(name, s, e, o)
      }
      const [qs, qe] = walkQuery(name, s, e)
      if (offset) {
        for (const entry of offset.entries) {
          if (entry.name === name && entry.end > qs && entry.start < qe) {
            for (const line of offset.readRange(entry.offset, entry.size).split('\n')) {
              if (line) {
                const cols = line.split('\t')
                cols.splice(2, 0, String(+cols[1] + 1))
                o.lineCallback(cols.join('\t'))
              }
            }
          }
        }
        return
      }
      return t.getLines(name, qs, qe, o)
    },
  }
}

function stable(value) {
  return JSON.stringify(value, (k, v) =>
    k === 'trimmedBefore' || k === 'trimmedAfter'
      ? undefined
      : v instanceof Set
        ? [...v].sort()
        : v instanceof Map
          ? [...v.entries()].sort()
          : v,
  )
}

function digest(cut) {
  const fragments = cut.fragments.map(stable).sort()
  const departures = cut.departures.map(stable).sort()
  const kept = [...cut.kept].sort((a, b) => a - b)
  return { fragments, departures, kept }
}

function diffSummary(a, b) {
  const only = (x, y) => x.filter(v => !y.includes(v)).length
  return {
    fragments: [only(a.fragments, b.fragments), only(b.fragments, a.fragments)],
    departures: [only(a.departures, b.departures), only(b.departures, a.departures)],
    kept: [only(a.kept, b.kept), only(b.kept, a.kept)],
  }
}

const current = { drawn: null, walkRead: { count: 0 } }
const shipped = new WalkReader(shippedSource())
const candidate = new WalkReader(candidateSource(current))
const lifted = {
  stepBudget: Infinity,
  byteBudget: Infinity,
  departureByteBudget: Infinity,
  attachFetches: 64,
}
const out = fs.createWriteStream(outPath)
let same = 0
let n = 0
for (const w of sample) {
  const region = { refName: w.seq, start: w.start, end: w.end }
  current.drawn = { start: Math.max(0, w.start - CONTEXT), end: w.end + CONTEXT }
  current.walkRead = { count: 0 }
  let a
  let b
  let error
  try {
    a = digest(await shipped.cut(w.seq, region, lifted))
    current.walkRead = { count: 0 }
    b = digest(await candidate.cut(w.seq, region, lifted))
  } catch (e) {
    error = String(e.message).slice(0, 120)
  }
  n++
  const row = { cand, size: w.size, start: w.start, end: w.end }
  if (error) {
    row.error = error
  } else {
    const identical =
      stable(a.fragments) === stable(b.fragments) &&
      stable(a.departures) === stable(b.departures) &&
      stable(a.kept) === stable(b.kept)
    row.identical = identical
    row.fragments = a.fragments.length
    row.departures = a.departures.length
    row.kept = a.kept.length
    if (!identical) {
      row.diff = diffSummary(a, b)
      if (process.env.CUTDEBUG) {
        const onlyA = a.departures.filter(v => !b.departures.includes(v))
        const onlyB = b.departures.filter(v => !a.departures.includes(v))
        process.stderr.write(`departures only shipped (${onlyA.length}): ${onlyA.slice(0, 2).map(v => v.slice(0, 400)).join('\n')}\n`)
        process.stderr.write(`departures only candidate (${onlyB.length}): ${onlyB.slice(0, 2).map(v => v.slice(0, 400)).join('\n')}\n`)
        const keptA = a.kept.filter(v => !b.kept.includes(v))
        const keptB = b.kept.filter(v => !a.kept.includes(v))
        process.stderr.write(`kept only shipped: ${keptA.length}, ids ${keptA.slice(0, 5).join(',')}..${keptA.slice(-3).join(',')}\n`)
        process.stderr.write(`kept only candidate: ${keptB.length}, ids ${keptB.slice(0, 5).join(',')}\n`)
      }
    } else {
      same++
    }
  }
  out.write(JSON.stringify(row) + '\n')
  if (n % 20 === 0) {
    process.stderr.write(`${cand}: ${same}/${n} identical\n`)
  }
}
out.end()
process.stderr.write(`${cand}: ${same}/${n} identical\n`)
