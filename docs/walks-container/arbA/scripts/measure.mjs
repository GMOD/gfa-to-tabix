// One harness for every candidate: a static server logging every range, each
// candidate's query procedure over HTTP, and (on a sample) the rebuilt paths
// compared with format 6's own decode.
// usage: node measure.mjs <dataset> <out.jsonl> [cands] [checkEvery]
import fs from 'node:fs'
import http from 'node:http'
import path from 'node:path'
import zlib from 'node:zlib'
import { unzip } from '../h/node_modules/@gmod/bgzf-filehandle/esm/index.js'
import { TabixIndexedFile as StockTabix } from '../h/node_modules/@gmod/tabix/esm/index.js'
import { TabixIndexedFile as PatchedTabix } from '../h/tabix-patched/esm/index.js'
import { decodeChunk } from '../gw/src/walkChunk.ts'
import { Ref, decodeIds, decodeWalk } from './scodec.mjs'

const [dataset, outPath, candArg, checkArg] = process.argv.slice(2)
const ROOT = process.env.ROOT ?? path.resolve(import.meta.dirname, '..')
const CONTEXT = 1000

const DATASETS = {
  mc22: { seq: 'GRCh38#0#chr22', range: [10_510_000, 50_790_000], seed: 22 },
  pggbY: { seq: 'GRCh38#0#chrY', range: [2_781_480, 26_673_214], seed: 24 },
  pggbYall: { seq: 'GRCh38#0#chrY', range: [2_800_000, 56_800_000], seed: 25, files: 'pggbY' },
}
const ds = DATASETS[dataset]
const SEQ = ds.seq
const FILES = ds.files ?? dataset
const ORIG = `in/${FILES}.bed.gz`
const ATTACH = process.env.ATTACH === '1'
const ATTACH_BP = 65_536
const ATTACH_FETCHES = 8
// graph-walks' attach rule: records with own steps the graph holds, at most
// ATTACH_BP, whose leave piece's chunk the read lacks; one fetch per chunk
function attachBases(depLines, has) {
  const want = new Map()
  const seen = new Set()
  for (const l of depLines) {
    const c = l.split('\t')
    const key = c.slice(3).join('\t')
    if (seen.has(key)) continue
    seen.add(key)
    const own = +c[6]
    const missing = +c[7]
    if (own > missing && own <= ATTACH_BP) {
      const leave = +c[8]
      const base = c[9] === '-' ? leave : Math.max(0, leave - 1)
      const k = has(base)
      if (k !== true && !want.has(k)) want.set(k, base)
    }
  }
  return [...want.values()].slice(0, ATTACH_FETCHES)
}

// ---- static server with a range log
const log = []
const server = http.createServer((req, res) => {
  const file = path.join(ROOT, decodeURIComponent(req.url.slice(1)))
  let stat
  try {
    stat = fs.statSync(file)
  } catch {
    res.writeHead(404)
    res.end()
    return
  }
  const m = /bytes=(\d+)-(\d*)/.exec(req.headers.range ?? '')
  const start = m ? +m[1] : 0
  const end = m && m[2] !== '' ? Math.min(+m[2], stat.size - 1) : stat.size - 1
  const t0 = performance.now()
  const fd = fs.openSync(file, 'r')
  const buf = Buffer.alloc(Math.max(0, end - start + 1))
  fs.readSync(fd, buf, 0, buf.length, start)
  fs.closeSync(fd)
  log.push({ file: req.url, start, end, bytes: buf.length, t0 })
  res.writeHead(m ? 206 : 200, {
    'content-length': buf.length,
    'content-range': `bytes ${start}-${end}/${stat.size}`,
    'accept-ranges': 'bytes',
  })
  res.end(buf)
})
server.keepAliveTimeout = 3_600_000
await new Promise(r => server.listen(0, '127.0.0.1', r))
const BASE = `http://127.0.0.1:${server.address().port}/`
// requests timed on the client: round trips in sequence
const timeline = []
const realFetch = globalThis.fetch
globalThis.fetch = async (url, opts) => {
  const t0 = performance.now()
  let r
  for (let k = 0; ; k++) {
    try {
      r = await realFetch(url, opts)
      break
    } catch (e) {
      if (k === 3) throw e
    }
  }
  const buf = await r.arrayBuffer()
  timeline.push({ t0, t1: performance.now() })
  return new Response(buf, { status: r.status, headers: r.headers })
}
function depth(tl) {
  const s = [...tl].sort((a, b) => a.t0 - b.t0)
  const d = s.map(() => 1)
  for (let j = 0; j < s.length; j++)
    for (let i = 0; i < j; i++) if (s[i].t1 <= s[j].t0) d[j] = Math.max(d[j], d[i] + 1)
  return Math.max(0, ...d)
}

// ---- header facts from the shipped file
const { headerLines } = await (async () => {
  const t = new StockTabix({ path: path.join(ROOT, ORIG) })
  return { headerLines: (await t.getHeader()).split('\n') }
})()
const C = +/chunk:i:(\d+)/.exec(headerLines[0])[1]
const MAXNODE = +/maxnode:i:(\d+)/.exec(headerLines[0])[1]
const LONG = headerLines
  .filter(l => l.startsWith('#long'))
  .map(l => l.split('\t'))
  .filter(c => c[1] === SEQ)
  .map(c => ({ start: +c[2], end: +c[3] }))
// the longest reference node no #long line lists
const REACH = +(process.env.REACH ?? MAXNODE)

const longOver = (s, e) => LONG.filter(p => p.start < e && p.end > s)
const floorTo = (x, u) => Math.max(0, Math.floor(x / u) * u)
function depExtent(D) {
  let a = D.start - REACH
  let b = D.end + REACH
  for (const p of longOver(D.start, D.end)) {
    a = Math.min(a, p.start)
    b = Math.max(b, p.end)
  }
  return [Math.max(0, a), b]
}

// ---- candidates
function tabixCand(name, file, idx, { patched = true, csi = false, sib = true, chunk = C, query, strict = false, shipped = false, plainReach = false, levels }) {
  const T = patched ? PatchedTabix : StockTabix
  let t
  return {
    name,
    rows: 'f6',
    strictDeps: strict,
    async open() {
      t = new T({ url: BASE + file, [csi ? 'csiUrl' : 'tbiUrl']: BASE + idx })
      await t.getHeader()
    },
    async window(D) {
      t.clearChunkCache()
      const [w0, w1] = query(D, chunk)
      const [d0, d1] = strict
        ? [D.start, D.end]
        : shipped
          ? [Math.max(0, D.start - MAXNODE), D.end + MAXNODE]
          : plainReach
            ? [Math.max(0, D.start - REACH), D.end + REACH]
            : depExtent(D)
      const walk = []
      const dep = []
      const sibs = levels ? levels.map(L => `${SEQ}~departure${L}`) : [`${SEQ}~departure`]
      const t0 = log.length
      await Promise.all([
        t.getLines(SEQ, w0, w1, { lineCallback: l => walk.push(l) }),
        ...(sib ? sibs.map(q => t.getLines(q, d0, d1, { lineCallback: l => dep.push(l) })) : []),
      ])
      const phase1 = log.length - t0
      let attach
      if (ATTACH) {
        const read = new Set(walk.map(l => +l.split('\t', 2)[1]))
        const bases = attachBases(dep, b => (read.has(floorTo(b, chunk)) ? true : floorTo(b, chunk)))
        const a0 = log.length
        await Promise.all(bases.map(b => t.getLines(SEQ, Math.max(0, b - REACH), b + 1, { lineCallback: () => {} })))
        attach = { fetches: bases.length, bytes: log.slice(a0).reduce((x, r) => x + r.bytes, 0) }
      }
      void phase1
      return { walk, dep, attach }
    },
  }
}

const a0Query = D => {
  let from = floorTo(D.start, C) - C
  for (const p of longOver(D.start, D.end)) from = Math.min(from, floorTo(p.start, C) - C)
  return [Math.max(0, from), D.end]
}
const narrowQuery = (D, chunk) => {
  let from = floorTo(D.start - REACH, chunk)
  for (const p of longOver(D.start, D.end)) from = Math.min(from, floorTo(p.start, chunk))
  return [from, D.end]
}

function tableCand(name, dir, prefix, rows, depFile = 'dep') {
  let entries
  let dep
  return {
    name,
    rows,
    async open() {
      const text = new TextDecoder().decode(zlib.gunzipSync(new Uint8Array(await (await fetch(BASE + `${dir}/${prefix}.walks.idx.gz`)).arrayBuffer())))
      const all = text.trim().split('\n').map(l => l.split('\t'))
      const h = all.find(c => c[3] === 'header')
      await fetch(BASE + `${dir}/${prefix}.walks.gz`, { headers: { range: `bytes=${h[5]}-${+h[5] + +h[6] - 1}` } })
      entries = all
        .filter(c => c[0] === SEQ && c[3] === 'tile')
        .map(c => ({ lo: +c[1], hi: +c[2], cs: +c[4], off: +c[5], len: +c[6] }))
      dep = new PatchedTabix({ url: BASE + `${dir}/${depFile}.bed.gz`, tbiUrl: BASE + `${dir}/${depFile}.bed.gz.tbi` })
      await dep.getHeader()
    },
    async window(D) {
      dep.clearChunkCache()
      const hit = entries.filter(e => e.lo < D.end && e.hi > D.start)
      const ranges = []
      for (const e of hit) {
        const last = ranges.at(-1)
        if (last && last.off + last.len === e.off) {
          last.len += e.len
          last.tiles.push(e)
        } else ranges.push({ off: e.off, len: e.len, tiles: [e] })
      }
      const [d0, d1] = depExtent(D)
      const depLines = []
      const tiles = []
      await Promise.all([
        ...ranges.map(async r => {
          const res = await fetch(BASE + `${dir}/${prefix}.walks.gz`, { headers: { range: `bytes=${r.off}-${r.off + r.len - 1}` } })
          const buf = new Uint8Array(await res.arrayBuffer())
          let at = 0
          for (const e of r.tiles) {
            const text = new TextDecoder().decode(await unzip(buf.subarray(at, at + e.len)))
            tiles.push({ cs: e.cs, lines: text.split('\n').filter(Boolean) })
            at += e.len
          }
        }),
        dep.getLines(SEQ, d0, d1, { lineCallback: l => depLines.push(l) }),
      ])
      return { tiles, dep: depLines }
    },
  }
}

function sCand(name, dir, prefix, rows = 'o') {
  let entries
  return {
    name,
    rows,
    strictDeps: true,
    async open() {
      const text = new TextDecoder().decode(zlib.gunzipSync(new Uint8Array(await (await fetch(BASE + `${dir}/${prefix}.walks.idx.gz`)).arrayBuffer())))
      const all = text.trim().split('\n').map(l => l.split('\t'))
      const h = all.find(c => c[3] === 'header')
      await fetch(BASE + `${dir}/${prefix}.walks.gz`, { headers: { range: `bytes=${h[5]}-${+h[5] + +h[6] - 1}` } })
      entries = all
        .filter(c => c[0] === SEQ && (c[3] === 'tile' || c[3] === 'departures'))
        .map(c => ({ kind: c[3], lo: +c[1], hi: +c[2], cs: +c[4], off: +c[5], len: +c[6] }))
        .sort((a, b) => a.off - b.off)
    },
    async window(D) {
      const hit = entries.filter(e => e.lo < D.end && e.hi > D.start)
      const ranges = []
      for (const e of hit) {
        const last = ranges.at(-1)
        if (last && last.off + last.len === e.off) {
          last.len += e.len
          last.items.push(e)
        } else ranges.push({ off: e.off, len: e.len, items: [e] })
      }
      const tiles = []
      const dep = new Set()
      const split = { tile: 0, departures: 0 }
      for (const e of hit) split[e.kind] += e.len
      await Promise.all(
        ranges.map(async r => {
          const res = await fetch(BASE + `${dir}/${prefix}.walks.gz`, { headers: { range: `bytes=${r.off}-${r.off + r.len - 1}` } })
          const buf = new Uint8Array(await res.arrayBuffer())
          let at = 0
          for (const e of r.items) {
            const lines = new TextDecoder().decode(await unzip(buf.subarray(at, at + e.len))).split('\n').filter(Boolean)
            if (e.kind === 'tile') tiles.push({ cs: e.cs, lines })
            else for (const l of lines) if (+l.split('\t')[1] < D.end && +l.split('\t')[2] > D.start) dep.add(l)
            at += e.len
          }
        }),
      )
      let attach
      if (ATTACH) {
        const read = new Set(hit.filter(e => e.kind === 'tile'))
        const tileOf = b => entries.find(e => e.kind === 'tile' && e.lo <= b && e.hi > b)
        const bases = attachBases([...dep], b => {
          const e = tileOf(b)
          return !e || read.has(e) ? true : e
        })
        const a0 = log.length
        await Promise.all(
          bases.map(b => {
            const e = tileOf(b)
            return fetch(BASE + `${dir}/${prefix}.walks.gz`, { headers: { range: `bytes=${e.off}-${e.off + e.len - 1}` } })
          }),
        )
        attach = { fetches: bases.length, bytes: log.slice(a0).reduce((x, r) => x + r.bytes, 0) }
      }
      return { tiles, dep: [...dep], split, attach }
    },
  }
}

function s7Cand(name, dir, prefix) {
  let entries
  const file = BASE + `${dir}/${prefix}.walks.gz`
  return {
    name,
    rows: 's7',
    strictDeps: true,
    async open() {
      const directory = (await (await fetch(file + '.idx')).text()).trim().split('\n').map(l => l.split('\t'))
      const [walks, ...rest] = directory
      if (walks[0] !== '#walks' || !walks.includes('format:i:7')) throw new Error('not a format 7 directory')
      const bytes = +walks.find(t => t.startsWith('bytes:i:')).slice(8)
      const range = c => ({ headers: { range: `bytes=${c[1]}-${+c[1] + +c[2] - 1}` } })
      const seqLine = rest.find(c => c[0] === SEQ)
      const [head, section] = await Promise.all([
        fetch(file, range(rest.find(c => c[0] === '#header'))),
        +seqLine[2] === 0 ? '' : fetch(file, range(seqLine)).then(async r => new TextDecoder().decode(await unzip(new Uint8Array(await r.arrayBuffer())))),
      ])
      const total = +/\/(\d+)$/.exec(head.headers.get('content-range'))[1]
      const headText = new TextDecoder().decode(await unzip(new Uint8Array(await head.arrayBuffer())))
      if (total !== bytes || headText.split('\n')[0] !== walks.filter(t => !t.startsWith('bytes:i:')).join('\t')) throw new Error('directory does not match the data file')
      entries = section
        .split('\n')
        .filter(l => l.startsWith('#entry\t'))
        .map(l => l.split('\t').slice(1))
        .filter(c => (c[3] === 'tile' || c[3] === 'departures') && +c[6] > 0)
        .map(c => ({ kind: c[3], lo: +c[1], hi: +c[2], cs: +c[4], off: +c[5], len: +c[6] }))
        .sort((a, b) => a.off - b.off)
    },
    async window(D) {
      const hit = entries.filter(e => e.lo < D.end && e.hi > D.start)
      const ranges = []
      for (const e of hit) {
        const last = ranges.at(-1)
        if (last && last.off + last.len === e.off) {
          last.len += e.len
          last.items.push(e)
        } else ranges.push({ off: e.off, len: e.len, items: [e] })
      }
      const tiles = []
      const dep = new Set()
      const split = { tile: 0, departures: 0 }
      for (const e of hit) split[e.kind] += e.len
      await Promise.all(
        ranges.map(async r => {
          const res = await fetch(file, { headers: { range: `bytes=${r.off}-${r.off + r.len - 1}` } })
          const buf = new Uint8Array(await res.arrayBuffer())
          let at = 0
          for (const e of r.items) {
            const lines = new TextDecoder().decode(await unzip(buf.subarray(at, at + e.len))).split('\n').filter(l => l && !l.startsWith('#'))
            if (e.kind === 'tile') tiles.push({ cs: e.cs, lines })
            else for (const l of lines) if (+l.split('\t')[1] < D.end && +l.split('\t')[2] > D.start) dep.add(l)
            at += e.len
          }
        }),
      )
      let attach
      if (ATTACH) {
        const read = new Set(hit.filter(e => e.kind === 'tile'))
        const tileOf = b => entries.find(e => e.kind === 'tile' && e.lo <= b && e.hi > b)
        const bases = attachBases([...dep], b => {
          const e = tileOf(b)
          return !e || read.has(e) ? true : e
        })
        const a0 = log.length
        await Promise.all(bases.map(b => { const e = tileOf(b); return fetch(file, { headers: { range: `bytes=${e.off}-${e.off + e.len - 1}` } }) }))
        attach = { fetches: bases.length, bytes: log.slice(a0).reduce((x, r) => x + r.bytes, 0) }
      }
      return { tiles, dep: [...dep], split, attach }
    },
  }
}

// arbB's T64b: rows at chunk spans under its exact CSI; departure rows filed at
// their pyramid block, the record's own extent in two trailing columns, read
// over the drawn stretch and kept when that extent touches it
function t64bCand(name, dir) {
  let t
  return {
    name,
    rows: 'f6',
    strictDeps: true,
    async open() {
      t = new PatchedTabix({ url: BASE + `${dir}/t64b.bed.gz`, csiUrl: BASE + `${dir}/t64b.exact.csi` })
      await t.getHeader()
    },
    async window(D) {
      t.clearChunkCache()
      const [w0, w1] = narrowQuery(D, C)
      const walk = []
      const dep = []
      await Promise.all([
        t.getLines(SEQ, w0, w1, { lineCallback: l => walk.push(l) }),
        t.getLines(`${SEQ}~departure`, D.start, D.end, {
          lineCallback: l => {
            const c = l.split('\t')
            if (c.length < 16 || (+c[14] < D.end && +c[15] > D.start)) dep.push([c[0], c[14] ?? c[1], c[15] ?? c[2], ...c.slice(3, 14)].join('\t'))
          },
        }),
      ])
      let attach
      if (ATTACH) {
        const read = new Set(walk.map(l => +l.split('\t', 2)[1]))
        const bases = attachBases(dep, b => (read.has(floorTo(b, C)) ? true : floorTo(b, C)))
        const a0 = log.length
        await Promise.all(bases.map(b => t.getLines(SEQ, Math.max(0, b - REACH), b + 1, { lineCallback: () => {} })))
        attach = { fetches: bases.length, bytes: log.slice(a0).reduce((x, r) => x + r.bytes, 0) }
      }
      return { walk, dep, attach }
    },
  }
}

function nativeCand(name, file, cell = 16384) {
  let t
  return {
    name,
    rows: 'native',
    async open() {
      t = new PatchedTabix({ url: BASE + file, tbiUrl: BASE + file + '.tbi' })
      await t.getHeader()
    },
    async window(D) {
      t.clearChunkCache()
      const walk = []
      await t.getLines(SEQ, floorTo(D.start, cell), Math.ceil(D.end / cell) * cell, { lineCallback: l => walk.push(l) })
      return { walk, dep: [] }
    },
  }
}

const o = `out/${FILES}`
const c16 = `out/${FILES}c16`
const ALL = {
  a0: () => tabixCand('a0', ORIG, ORIG + '.tbi', { patched: false, query: a0Query, shipped: true }),
  f6p: () => tabixCand('f6p', `${o}/f6p.bed.gz`, `${o}/f6p.bed.gz.tbi`, { query: narrowQuery }),
  t: () => tabixCand('t', `${o}/t.bed.gz`, `${o}/t.bed.gz.csi`, { csi: true, query: narrowQuery }),
  tn: () => tabixCand('tn', `${o}/tn.bed.gz`, `${o}/tn.bed.gz.csi`, { csi: true, query: narrowQuery, strict: true }),
  t16: () => tabixCand('t16', `${c16}/t.bed.gz`, `${c16}/t.bed.gz.tbi`, { chunk: 16384, query: narrowQuery }),
  o: () => tableCand('o', o, 'o', 'o'),
  ou: () => tableCand('ou', o, 'o', 'o', 'depu'),
  t64b: () => tabixCand('t64b', `arbB/${FILES}/t64d19.bed.gz`, `arbB/${FILES}/t64d19.bed.gz.csi`, { csi: true, query: narrowQuery, plainReach: true }),
  tl: () => tabixCand('tl', `${o}/tl.bed.gz`, `${o}/tl.bed.gz.csi`, { csi: true, query: narrowQuery, strict: true, levels: [0, 1, 2, 3] }),
  tlb: () => tabixCand('tlb', `${o}/tlb.bed.gz`, `${o}/tlb.bed.gz.csi`, { csi: true, query: narrowQuery, strict: true, levels: [0, 1, 2, 3] }),
  s7: () => s7Cand('s7', o, 's7'),
  s7t: () => s7Cand('s7t', o, 's7t'),
  t64bx: () => t64bCand('t64bx', `arbB/${FILES}`),
  s512: () => sCand('s512', o, 's512'),
  onochain: () => tableCand('onochain', o, 'onochain', 'x'),
  oabs: () => tableCand('oabs', o, 'oabs', 'x'),
  sabs: () => tableCand('sabs', o, 'sabs', 'sabs'),
  srel: () => tableCand('srel', o, 'srel', 'srel'),
  s: () => sCand('s', o, 's'),
  s2: () => sCand('s2', o, 's2', 'onc'),
  n: () => nativeCand('n', `native/${FILES}.native.bed.gz`),
}
const cands = (candArg ?? Object.keys(ALL).join(',')).split(',').map(k => ALL[k]())
const checkEvery = +(checkArg ?? 0)

// ---- windows: seeded, 300 per size
function mulberry32(a) {
  return () => {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}
const SIZES = (process.env.SIZES ?? '1000,10000,100000,1000000').split(',').map(Number)
const PER = +(process.env.PER ?? 300)
const windows = []
if (process.env.WINDOWS) for (const l of fs.readFileSync(process.env.WINDOWS, 'utf8').trim().split('\n')) windows.push(JSON.parse(l))
else
for (const size of SIZES) {
  const rnd = mulberry32(ds.seed * 1000 + size)
  for (let i = 0; i < PER; i++) {
    const s = Math.floor(ds.range[0] + rnd() * (ds.range[1] - ds.range[0] - size))
    windows.push({ size, i, start: s, end: s + size })
  }
}

// ---- the check: each piece's steps over D, and the records over the
// departure extent, from the fetched rows against format 6's decode
const orig = new StockTabix({ path: path.join(ROOT, ORIG) })
const keyOf = r => `${r.name}|${r.fragStart}|${r.piece}`

function clipF6(decoded, D, out) {
  const len = id => decoded.chunk.lengths.get(id)
  for (const r of decoded.rows) {
    const s = r.steps
    if (r.abridged) {
      const a = Math.min(s.refStarts[0], s.refStarts[1])
      const b = Math.max(s.refStarts[0], s.refStarts[1]) + (len(s.ids[s.refStarts[1] >= s.refStarts[0] ? 1 : 0]) ?? 0)
      if (a < D.end && b > D.start) out.set(keyOf(r), `A:${a}`)
      continue
    }
    clipSteps(keyOf(r), s, i => len(s.ids[i]), D, out)
  }
}
function clipSteps(key, s, lengthAt, D, out) {
  let first = -1
  let last = -1
  for (let i = 0; i < s.ids.length; i++) {
    const r = s.refStarts[i]
    if (Number.isFinite(r) && r < D.end && r + lengthAt(i) > D.start) {
      if (first < 0) first = i
      last = i
    }
  }
  if (first < 0) return
  const toks = []
  for (let i = first; i <= last; i++) toks.push(`${s.rev[i] ? '<' : '>'}${s.ids[i]}@${Number.isFinite(s.refStarts[i]) ? s.refStarts[i] : '.'}`)
  const prev = out.get(key)
  if (prev && prev !== toks.join('')) throw new Error(`piece ${key} decodes twice differently`)
  out.set(key, toks.join(''))
}

function groupF6(lines) {
  const by = new Map()
  for (const l of lines) {
    const c = l.split('\t')
    const k = c[1]
    if (!by.has(k)) by.set(k, [])
    by.get(k).push(c)
  }
  return [...by.values()]
}

function depKeys(lines, [d0, d1]) {
  const keys = new Set()
  for (const l of lines) {
    const c = l.split('\t')
    if (+c[1] < d1 && +c[2] > d0) keys.add(c.slice(3).join('\t'))
  }
  return keys
}

async function truth(D) {
  let from = floorTo(D.start, C) - 2 * C
  for (const p of longOver(D.start, D.end)) from = Math.min(from, floorTo(p.start, C) - C)
  const lines = []
  await orig.getLines(SEQ, Math.max(0, from), D.end, { lineCallback: l => lines.push(l) })
  const pieces = new Map()
  for (const rows of groupF6(lines)) clipF6(decodeChunk(rows, undefined), D, pieces)
  const de = depExtent(D)
  const dl = []
  await orig.getLines(`${SEQ}~departure`, de[0], de[1], { lineCallback: l => dl.push(l) })
  return { pieces, deps: depKeys(dl, de), strict: depKeys(dl, [D.start, D.end]) }
}

function sDecode(mode, cs, lines, D, out) {
  const ref = new Ref()
  const refLines = lines.filter(l => l.startsWith('R\t')).map(l => l.split('\t'))
  refLines.sort((a, b) => +a[2] - +b[2])
  for (const c of refLines) {
    const { ids, rev } = decodeIds(c[7], mode === 'abs' ? 'abs' : 'rel')
    ref.add(ids, rev, c[8].split(',').map(Number), +c[2])
    const s = { ids, rev, refStarts: [], against: [] }
    let at = +c[2]
    const lens = c[8].split(',').map(Number)
    for (const L of lens) {
      s.refStarts.push(at)
      at += L
    }
    clipSteps(`${c[4]}|${c[5]}|${c[6]}`, s, i => lens[i], D, out)
  }
  const nodeLen = new Map()
  for (const l of lines) {
    if (!l.startsWith('N\t')) continue
    const c = l.split('\t')
    let id = 0
    const ids = mode === 'abs' ? c[4].split(',').map(Number) : c[4].split(',').map(t => (id += +t))
    const lens = c[5].split(',').map(Number)
    ids.forEach((x, k) => nodeLen.set(x, lens[k]))
  }
  for (const l of lines) {
    const c = l.split('\t')
    if (c[0] === 'A') {
      if (+c[2] < D.end && +c[3] > D.start) out.set(`${c[4]}|${c[5]}|${c[7]}`, `A:${c[2]}`)
    } else if (c[0] === 'W') {
      const s = decodeWalk(c[8], ref, mode === 'abs' ? 'abs' : 'rel', cs)
      const lenAt = i => (Number.isFinite(s.refStarts[i]) ? ref.lengths[ref.index(s.refStarts[i], s.ids[i])] : nodeLen.get(s.ids[i]))
      clipSteps(`${c[4]}|${c[5]}|${c[7]}`, s, lenAt, D, out)
    }
  }
}

function candPieces(cand, got, D) {
  const pieces = new Map()
  if (got.walk) for (const rows of groupF6(got.walk)) clipF6(decodeChunk(rows, undefined), D, pieces)
  if (got.tiles && (cand.rows === 'o' || cand.rows === 'onc'))
    for (const t of got.tiles) {
      const rows = t.lines.map(l => [SEQ, String(t.cs), String(t.cs + 1), ...l.split('\t')])
      clipF6(decodeChunk(cand.rows === 'onc' ? rechain(rows) : rows, undefined), D, pieces)
    }
  if (got.tiles && cand.rows === 's7')
    for (const t of got.tiles) clipF6(decodeChunk(t.lines.map(l => { const c = l.split('\t'); return [c[0], String(t.cs), String(t.cs + 1), ...c.slice(3)] }), undefined), D, pieces)
  if (got.tiles && cand.rows.startsWith('s') && cand.rows !== 's7')
    for (const t of got.tiles) sDecode(cand.rows === 'sabs' ? 'abs' : 'rel', t.cs, t.lines, D, pieces)
  return pieces
}

// route rows whose tokens start from 0 on each row, chained again across
// rows as format 6 decodes them
function rechain(rows) {
  const prev = { id: 0 }
  return rows.map(c => {
    if (c[3] !== 'route') return c
    const own = { id: 0 }
    const hs = [4, 5, 6].map(k =>
      c[k] === '.'
        ? []
        : c[k].split(',').map(t => {
            const d = +t
            const r = d & 1
            own.id += (d - r) / 2
            return own.id * 2 + r
          }),
    )
    return [
      ...c.slice(0, 4),
      ...hs.map(h =>
        h.length
          ? h
              .map(x => {
                const r = x & 1
                const id = (x - r) / 2
                const t = 2 * (id - prev.id) + r
                prev.id = id
                return t
              })
              .join(',')
          : '.',
      ),
    ]
  })
}

function compare(a, b) {
  let missing = 0
  let differ = 0
  for (const [k, v] of a) {
    if (!b.has(k)) missing++
    else if (b.get(k) !== v) {
      differ++
      if (process.env.DEBUG && differ === 1) console.error('DIFF', k, '\n truth', v.slice(0, 600), '\n cand ', b.get(k).slice(0, 600))
    }
  }
  let extra = 0
  for (const k of b.keys()) if (!a.has(k)) extra++
  return { missing, differ, extra }
}

// ---- run
const outFile = fs.createWriteStream(outPath)
for (const cand of cands) {
  log.length = 0
  timeline.length = 0
  await cand.open()
  const open = { bytes: log.reduce((s, r) => s + r.bytes, 0), requests: log.length }
  outFile.write(JSON.stringify({ cand: cand.name, open }) + '\n')
  for (const w of windows) {
    const D = { start: Math.max(0, w.start - CONTEXT), end: w.end + CONTEXT }
    log.length = 0
    timeline.length = 0
    const got = await cand.window(D)
    const rec = {
      cand: cand.name,
      size: w.size,
      i: w.i,
      start: w.start,
      requests: log.length,
      bytes: log.reduce((s, r) => s + r.bytes, 0),
      trips: depth(timeline),
      tiles: got.tiles?.length,
      files: Object.fromEntries(
        [...new Set(log.map(r => r.file))].map(f => [f.replace(/.*\//, ''), log.filter(r => r.file === f).reduce((a, r) => a + r.bytes, 0)]),
      ),
      split: got.split,
      attach: got.attach,
    }
    if (checkEvery && w.i % checkEvery === 0 && cand.rows !== 'x' && cand.rows !== 'native' && (w.size < 1_000_000 || w.i % (checkEvery * 5) === 0)) {
      const tr = await truth(D)
      const mine = candPieces(cand, got, D)
      rec.check = { pieces: tr.pieces.size, ...compare(tr.pieces, mine) }
      const de = cand.strictDeps ? [0, Infinity] : depExtent(D)
      const dk = depKeys(got.dep, de)
      const need = cand.strictDeps ? tr.strict : tr.deps
      let dm = 0
      for (const k of need) if (!dk.has(k)) dm++
      rec.check.deps = need.size
      rec.check.depMissing = dm
      rec.check.depExtra = [...dk].filter(k => !tr.deps.has(k)).length
      if (process.env.DEBUG && rec.check.depExtra) console.error('EXTRA', [...dk].filter(k => !tr.deps.has(k)).slice(0, 2))
    }
    outFile.write(JSON.stringify(rec) + '\n')
  }
  console.error(cand.name, 'done')
}
outFile.end()
server.close()
