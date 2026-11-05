// Bytes, requests and sequential round trips a browser pays per window for
// each candidate, through real HTTP range requests against server.mjs.
//
// usage: node measure.mjs SERVER CANDIDATES.json WINDOWS.jsonl OUT.jsonl [name ...]
//
// A candidate (JSON object in CANDIDATES.json):
//   name      label
//   kind      tabix | offset
//   walks     served path of the walk file; index: tbi | csi (tabix kind)
//   patch     true applies the one-line @gmod/tabix chunk-end fix
//   query     lookback  graph-walks 5's walk read (chunk before the drawn
//                       start, or before an overlapping #long pass)
//             reach1bp  chunks from the one holding drawn.start - reach,
//                       rows filed at 1 bp (query rounded to chunk starts)
//             reach     [drawn.start - reach, drawn.end), rows at real spans
//             cell      drawn extent rounded out to whole cells (native)
//   chunk     chunk or cell size
//   reach     bp a chunk's rows reach past its end (default: header maxnode)
//   departures {file, index} where records live (default: the walk file);
//             null for none
//   depReach  bp the departure read widens by (default: reach)
//   chunkIndex served path of the chunk table (offset kind)
//   stubs     true fetches native stub interiors as attach fetches
import fs from 'node:fs'
import zlib from 'node:zlib'
import { createRequire } from 'node:module'

const require = createRequire('/home/cdiesh/src/graph-walks/package.json')
const { TabixIndexedFile } = require('@gmod/tabix')

const [server, candidatesPath, windowsPath, outPath, ...only] = process.argv.slice(2)
const CONTEXT = 1000
const ATTACH_BP = 65536
const ATTACH_FETCHES = 8

const candidates = JSON.parse(fs.readFileSync(candidatesPath, 'utf8')).filter(
  c => only.length === 0 || only.includes(c.name),
)
const windows = fs
  .readFileSync(windowsPath, 'utf8')
  .split('\n')
  .filter(Boolean)
  .map(l => JSON.parse(l))

async function serverReads() {
  const res = await fetch(`${server}/__reads`)
  return res.json()
}

// sequential round trips: the longest chain of requests each starting after
// the one before it finished
function rounds(reads) {
  const sorted = [...reads].sort((a, b) => a.t0 - b.t0)
  const depth = []
  let max = 0
  for (let i = 0; i < sorted.length; i++) {
    let d = 1
    for (let j = 0; j < i; j++) {
      if (sorted[j].t1 <= sorted[i].t0) {
        d = Math.max(d, depth[j] + 1)
      }
    }
    depth.push(d)
    max = Math.max(max, d)
  }
  return max
}

const sum = (reads, key = 'bytes') => reads.reduce((a, r) => a + r[key], 0)

function patchChunkEnds(t) {
  const index = t.index
  const orig = index.blocksForRange.bind(index)
  index.blocksForRange = async (...args) => {
    const chunks = await orig(...args)
    for (const c of chunks) {
      if (c.maxv.dataPosition === 0) {
        c.endPosition = Math.min(c.endPosition, c.maxv.blockPosition)
      }
    }
    return chunks
  }
}

function openTabix(file, index, patch) {
  const t = new TabixIndexedFile({
    url: `${server}/${file}`,
    ...(index === 'csi'
      ? { csiUrl: `${server}/${file}.csi` }
      : { tbiUrl: `${server}/${file}.tbi` }),
  })
  if (patch) {
    patchChunkEnds(t)
  }
  return t
}

function parseHeader(lines, seq) {
  const header = { chunk: 65536, maxnode: undefined, long: [] }
  for (const line of lines) {
    const cols = line.split('\t')
    if (cols[0] === '#walks') {
      for (const tag of cols.slice(1)) {
        const [key, , value] = tag.split(':')
        if (key === 'chunk' || key === 'cell') {
          header.chunk = +value
        }
        if (key === 'maxnode') {
          header.maxnode = +value
        }
      }
    } else if (cols[0] === '#long' && cols[1] === seq) {
      header.long.push({ start: +cols[2], end: +cols[3] })
    }
  }
  return header
}

const chunkStart = (x, chunk, back = 0) =>
  Math.max(0, (Math.floor(x / chunk) - back) * chunk)

// the walk read's range for a window, by query mode
function walkRange(c, header, drawn) {
  const { chunk } = c
  const reach = c.reach ?? header.maxnode ?? chunk
  const over = header.long.filter(p => p.start < drawn.end && p.end > drawn.start)
  switch (c.query) {
    case 'lookback': {
      const back =
        header.long.length === 0 && header.maxnode !== undefined
          ? Math.max(1, Math.ceil(header.maxnode / chunk))
          : 1
      return [
        Math.min(
          chunkStart(drawn.start, chunk, header.long.length === 0 ? back : 1),
          ...over.map(p => chunkStart(p.start, chunk, 1)),
        ),
        drawn.end,
      ]
    }
    case 'reach1bp':
      return [
        Math.min(
          chunkStart(Math.max(0, drawn.start - reach), chunk),
          ...over.map(p => chunkStart(p.start, chunk)),
        ),
        drawn.end,
      ]
    case 'reach':
      return [
        Math.min(Math.max(0, drawn.start - reach), ...over.map(p => p.start)),
        drawn.end,
      ]
    case 'cell':
      return [chunkStart(drawn.start, chunk), Math.ceil(drawn.end / chunk) * chunk]
    case 'drawn':
      return [drawn.start, drawn.end]
    default:
      throw new Error(`unknown query ${c.query}`)
  }
}

// the range an attach fetch of the chunk holding `base` reads
function attachRange(c, header, base) {
  const { chunk } = c
  const reach = c.reach ?? header.maxnode ?? chunk
  const cs = chunkStart(base, chunk)
  switch (c.query) {
    case 'lookback': {
      const back =
        header.maxnode === undefined ? 1 : Math.max(1, Math.ceil(header.maxnode / chunk))
      return [chunkStart(cs, chunk, back), cs + 1]
    }
    case 'reach1bp':
      return [
        Math.min(
          chunkStart(Math.max(0, base - reach), chunk),
          ...header.long.filter(p => p.start <= base && p.end > base).map(p => chunkStart(p.start, chunk)),
        ),
        base + 1,
      ]
    case 'reach':
      return [
        Math.min(
          Math.max(0, base - reach),
          ...header.long.filter(p => p.start <= base && p.end > base).map(p => p.start),
        ),
        base + 1,
      ]
    default:
      throw new Error(`no attach rule for ${c.query}`)
  }
}

// departure rows wanting an attach fetch: own steps the graph holds, at most
// ATTACH_BP, with a leave piece in a chunk the walk read did not return
function attachBases(records, chunk, decoded) {
  const want = new Map()
  for (const cols of records) {
    const ownBp = +cols[6]
    const missingBp = +cols[7]
    if (ownBp > missingBp && ownBp <= ATTACH_BP) {
      const leavePos = +cols[8]
      const base = cols[9] === '-' ? leavePos : Math.max(0, leavePos - 1)
      const cs = chunkStart(base, chunk)
      if (!decoded.has(cs) && !want.has(cs)) {
        want.set(cs, base)
      }
    }
  }
  return [...want.values()].slice(0, ATTACH_FETCHES)
}

// native stubs: `*@start/steps/bp` alleles of V rows, interiors worth fetching
function stubStarts(vRows) {
  const want = new Set()
  for (const cols of vRows) {
    for (const allele of (cols[8] ?? '').split(';')) {
      const m = /^\*@(\d+)\/(\d+)\/(\d+)$/.exec(allele)
      if (m && +m[3] > 0 && +m[3] <= ATTACH_BP) {
        want.add(+m[1])
      }
    }
  }
  return [...want].slice(0, ATTACH_FETCHES)
}

// ---- offset-table reader ----

async function openOffset(c) {
  const res = await fetch(`${server}/${c.chunkIndex}`)
  const buf = Buffer.from(await res.arrayBuffer())
  const text = (c.chunkIndex.endsWith('.gz') ? zlib.gunzipSync(buf) : buf).toString()
  const entries = []
  let header
  for (const line of text.split('\n')) {
    if (!line) {
      continue
    }
    const [name, start, end, offset, size] = line.split('\t')
    const entry = { name, start: +start, end: +end, offset: +offset, size: +size }
    if (name === '#header') {
      header = entry
    } else {
      entries.push(entry)
    }
  }
  const head = await fetch(`${server}/${c.walks}`, {
    headers: { range: `bytes=${header.offset}-${header.offset + header.size - 1}` },
  })
  const headerLines = zlib
    .gunzipSync(Buffer.from(await head.arrayBuffer()))
    .toString()
    .split('\n')
    .filter(l => l.startsWith('#'))
  return { entries, headerLines }
}

function offsetRanges(entries, seq, from, to) {
  const hit = entries.filter(e => e.name === seq && e.end > from && e.start < to)
  const ranges = []
  for (const e of hit) {
    const last = ranges.at(-1)
    if (last && last.offset + last.size === e.offset) {
      last.size += e.size
      last.chunks.push(e.start)
    } else {
      ranges.push({ offset: e.offset, size: e.size, chunks: [e.start] })
    }
  }
  return ranges
}

async function offsetRead(c, entries, seq, from, to) {
  const ranges = offsetRanges(entries, seq, from, to)
  let lines = 0
  const chunks = new Set()
  await Promise.all(
    ranges.map(async r => {
      const res = await fetch(`${server}/${c.walks}`, {
        headers: { range: `bytes=${r.offset}-${r.offset + r.size - 1}` },
      })
      const text = zlib.gunzipSync(Buffer.from(await res.arrayBuffer())).toString()
      for (const line of text.split('\n')) {
        if (line) {
          lines++
          chunks.add(+line.split('\t', 2)[1])
        }
      }
    }),
  )
  return { lines, chunks }
}

// ---- S table reader (arbA's design): `seq start end kind name offset length`,
// tile and departures entries overlapping the drawn extent, touching byte
// ranges merged, departure lines deduped ----

async function openTable(c) {
  const res = await fetch(`${server}/${c.chunkIndex}`)
  const buf = Buffer.from(await res.arrayBuffer())
  const text = (c.chunkIndex.endsWith('.gz') ? zlib.gunzipSync(buf) : buf).toString()
  const entries = []
  let header
  for (const line of text.split('\n')) {
    if (!line) {
      continue
    }
    const [seq, start, end, kind, name, offset, size] = line.split('\t')
    const entry = { seq, start: +start, end: +end, kind, name, offset: +offset, size: +size }
    if (kind === 'header') {
      header = entry
    } else {
      entries.push(entry)
    }
  }
  entries.sort((a, b) => a.offset - b.offset)
  const head = await fetch(`${server}/${c.walks}`, {
    headers: { range: `bytes=${header.offset}-${header.offset + header.size - 1}` },
  })
  const headerLines = zlib
    .gunzipSync(Buffer.from(await head.arrayBuffer()))
    .toString()
    .split('\n')
    .filter(l => l.startsWith('#'))
  return { entries, headerLines }
}

function tableRanges(entries, seq, from, to, kinds) {
  const hit = entries.filter(
    e => e.seq === seq && kinds.includes(e.kind) && e.end > from && e.start < to,
  )
  const ranges = []
  for (const e of hit) {
    const last = ranges.at(-1)
    if (last && last.offset + last.size === e.offset) {
      last.size += e.size
      last.entries.push(e)
    } else {
      ranges.push({ offset: e.offset, size: e.size, entries: [e] })
    }
  }
  return ranges
}

async function tableRead(c, entries, seq, from, to, kinds) {
  const ranges = tableRanges(entries, seq, from, to, kinds)
  let lines = 0
  const tiles = new Set()
  const depLines = new Set()
  let depRows = 0
  await Promise.all(
    ranges.map(async r => {
      const res = await fetch(`${server}/${c.walks}`, {
        headers: { range: `bytes=${r.offset}-${r.offset + r.size - 1}` },
      })
      const buf = Buffer.from(await res.arrayBuffer())
      let at = 0
      for (const e of r.entries) {
        const text = zlib.gunzipSync(buf.subarray(at, at + e.size)).toString()
        at += e.size
        for (const line of text.split('\n')) {
          if (!line) {
            continue
          }
          lines++
          if (e.kind === 'departures') {
            depRows++
            depLines.add(line)
          } else {
            tiles.add(+e.name)
          }
        }
      }
    }),
  )
  return { lines, tiles, depLines, depRows }
}

// ---- driver ----

const out = fs.createWriteStream(outPath, { flags: 'a' })
for (const c of candidates) {
  await serverReads()
  let walks
  let deps
  let offset
  let headerLines
  if (c.kind === 'tabix') {
    walks = openTabix(c.walks, c.index, c.patch)
    headerLines = await walks.getHeaderLines()
  } else if (c.kind === 'table') {
    offset = await openTable(c)
    headerLines = offset.headerLines
  } else {
    offset = await openOffset(c)
    headerLines = offset.headerLines
  }
  if (c.departures === undefined) {
    deps = walks
  } else if (c.departures !== null) {
    deps = openTabix(c.departures.file, c.departures.index, c.patch)
    await deps.getHeaderLines()
  }
  const seq = windows[0].seq
  const header = parseHeader(headerLines, seq)
  if (c.longFile) {
    header.long = fs
      .readFileSync(`data/${c.longFile}`, 'utf8')
      .split('\n')
      .filter(Boolean)
      .map(l => l.split('\t'))
      .filter(x => x[0] === seq)
      .map(x => ({ start: +x[1], end: +x[2] }))
  }
  const openReads = await serverReads()
  const open = { requests: openReads.length, bytes: sum(openReads) }
  process.stderr.write(`${c.name}: open ${open.requests} requests ${open.bytes} bytes\n`)

  for (const w of windows) {
    if (w.seq !== seq) {
      throw new Error('one sequence per windows file')
    }
    walks?.clearChunkCache()
    deps?.clearChunkCache()
    const drawn = { start: Math.max(0, w.start - CONTEXT), end: w.end + CONTEXT }
    const reach = c.reach ?? header.maxnode ?? c.chunk
    const depReach = c.depReach ?? reach
    const extent = {
      start: Math.max(0, drawn.start - depReach),
      end: drawn.end + depReach,
    }
    const [from, to] = walkRange(c, header, drawn)
    const records = []
    const vRows = []
    let walkLines = 0
    let depLines = 0
    const decoded = new Set()
    const readWalk = async () => {
      if (c.kind === 'table') {
        const got = await tableRead(c, offset.entries, seq, drawn.start, drawn.end, ['tile', 'departures'])
        walkLines = got.lines - got.depRows
        for (const cs of got.tiles) {
          decoded.add(cs)
        }
        depLines = got.depRows
        for (const line of got.depLines) {
          const cols = line.split('\t')
          if (+cols[1] < drawn.end && +cols[2] > drawn.start) {
            records.push(cols)
          }
        }
      } else if (c.kind === 'offset') {
        const got = await offsetRead(c, offset.entries, seq, from, to)
        walkLines = got.lines
        for (const cs of got.chunks) {
          decoded.add(cs)
        }
      } else {
        await walks.getLines(seq, from, to, {
          lineCallback: line => {
            walkLines++
            const cols = line.split('\t')
            decoded.add(+cols[1])
            if (cols[3] === 'V' && cols[8]?.includes('*@')) {
              vRows.push(cols)
            }
          },
        })
      }
    }
    const readDeps = async () => {
      if (!deps) {
        return
      }
      const seen = new Set()
      const depName = seq + (c.departures?.suffix ?? '~departure')
      const depRange = c.strictDeps ? drawn : extent
      await deps.getLines(depName, depRange.start, depRange.end, {
        lineCallback: line => {
          depLines++
          const cols = line.split('\t')
          const key = cols.slice(4).join('\t')
          if (!seen.has(key)) {
            seen.add(key)
            if (cols.length < 16 || (+cols[14] < drawn.end && +cols[15] > drawn.start)) {
              records.push(cols)
            }
          }
        },
      })
    }
    // the walk and departure reads run concurrently in graph-walks; here one
    // after the other so each one's requests are known, with the round trips
    // of the longer chain counted
    const t0 = performance.now()
    await readWalk()
    const walkReads = await serverReads()
    await readDeps()
    const depReads = await serverReads()
    const phase1 = [...walkReads, ...depReads]
    const t1 = performance.now()
    // attach fetches, in parallel, each for the chunk of a record's leave
    let attachLines = 0
    let fetches = []
    if (c.stubs) {
      fetches = stubStarts(vRows).map(start => [start, start + 1])
    } else if (c.kind === 'table') {
      fetches = c.noAttach
        ? []
        : attachBases(records, c.chunk, decoded).map(base => [base, base + 1])
    } else if (deps && !c.noAttach) {
      fetches = attachBases(records, c.chunk, decoded).map(base =>
        attachRange(c, header, base),
      )
    }
    await Promise.all(
      fetches.map(async ([s, e]) => {
        if (c.kind === 'table') {
          const got = await tableRead(c, offset.entries, seq, s, e, ['tile'])
          attachLines += got.lines
        } else if (c.kind === 'offset') {
          const got = await offsetRead(c, offset.entries, seq, s, e)
          attachLines += got.lines
        } else {
          await walks.getLines(seq, s, e, {
            lineCallback: () => {
              attachLines++
            },
          })
        }
      }),
    )
    const phase2 = await serverReads()
    const t2 = performance.now()
    const all = [...phase1, ...phase2]
    const rounds1 = Math.max(rounds(walkReads), rounds(depReads))
    out.write(
      JSON.stringify({
        candidate: c.name,
        size: w.size,
        start: w.start,
        end: w.end,
        requests: all.length,
        bytes: sum(all),
        rounds: rounds1 + rounds(phase2),
        rounds1,
        walk: { requests: walkReads.length, bytes: sum(walkReads), lines: walkLines, chunks: decoded.size, from, to },
        dep: { requests: depReads.length, bytes: sum(depReads), lines: depLines, records: records.length },
        attach: { fetches: fetches.length, requests: phase2.length, bytes: sum(phase2), lines: attachLines },
        ms: [Math.round(t1 - t0), Math.round(t2 - t1)],
        open,
      }) + '\n',
    )
  }
  process.stderr.write(`${c.name}: done\n`)
}
out.end()
