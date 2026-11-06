// S7 over HTTP ranges with arbA's reader (measure.mjs s7Cand, copied), on the
// same windows as f6.mjs, and on every `CHECK`th window arbA's piece and
// departure check against the shipped format 6 rows (measure.mjs truth,
// copied). usage: node s7win.mjs <windows.jsonl> <out.jsonl> [set,...]
import fs from 'node:fs'
import { unzip } from './h/node_modules/@gmod/bgzf-filehandle/esm/index.js'
import { TabixIndexedFile as StockTabix } from './h/node_modules/@gmod/tabix/esm/index.js'
import { decodeChunk } from './gw/src/walkChunk.ts'
import { rangeServer } from './rangeServer.mjs'

const [windowsPath, outPath, setsArg] = process.argv.slice(2)
const CHECK = +(process.env.CHECK ?? 4)
const CONTEXT = 1000
const C = 65536
const MAXNODE = 1024
const ATTACH_BP = 65_536
const ATTACH_FETCHES = 8
const ORIG = {
  grch38: `${process.env.HOME}/work/genome3/hprc-v2.1-mc-grch38.GRCh38.walks.bed.gz`,
  chm13: `${process.env.HOME}/work/genome3/hprc-v2.1-mc-chm13.CHM13.walks.bed.gz`,
}
const sets = setsArg ? new Set(setsArg.split(',')) : undefined
const windows = fs
  .readFileSync(windowsPath, 'utf8')
  .trim()
  .split('\n')
  .map(l => JSON.parse(l))
  .filter(w => !sets || sets.has(w.set))
const srv = await rangeServer(`${process.env.HOME}/work`)
const fetchR = srv.timedFetch

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

function s7Cand(genome, SEQ) {
  let entries
  const file = srv.base + `s7-genome/out/${genome}/s7.walks.gz`
  return {
    async open() {
      const directory = (await (await fetchR(file + '.idx')).text()).trim().split('\n').map(l => l.split('\t'))
      const [walks, ...rest] = directory
      if (walks[0] !== '#walks' || !walks.includes('format:i:7')) throw new Error('not a format 7 directory')
      const bytes = +walks.find(t => t.startsWith('bytes:i:')).slice(8)
      const range = c => ({ headers: { range: `bytes=${c[1]}-${+c[1] + +c[2] - 1}` } })
      const seqLine = rest.find(c => c[0] === SEQ)
      const [head, section] = await Promise.all([
        fetchR(file, range(rest.find(c => c[0] === '#header'))),
        +seqLine[2] === 0 ? '' : fetchR(file, range(seqLine)).then(async r => new TextDecoder().decode(await unzip(new Uint8Array(await r.arrayBuffer())))),
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
      return { directory: rest.length, sectionBytes: +seqLine[2], headerBytes: +rest.find(c => c[0] === '#header')[2] }
    },
    async window(D, attach) {
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
          const res = await fetchR(file, { headers: { range: `bytes=${r.off}-${r.off + r.len - 1}` } })
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
      let fetches = 0
      if (attach) {
        const read = new Set(hit.filter(e => e.kind === 'tile'))
        const tileOf = b => entries.find(e => e.kind === 'tile' && e.lo <= b && e.hi > b)
        const bases = attachBases([...dep], b => {
          const e = tileOf(b)
          return !e || read.has(e) ? true : e
        })
        fetches = bases.length
        await Promise.all(bases.map(b => { const e = tileOf(b); return fetchR(file, { headers: { range: `bytes=${e.off}-${e.off + e.len - 1}` } }) }))
      }
      return { tiles, dep: [...dep], split, fetches, units: hit.length, largest: Math.max(0, ...hit.map(e => e.len)) }
    },
  }
}

const floorTo = (x, u) => Math.max(0, Math.floor(x / u) * u)
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
    if (!by.has(c[1])) by.set(c[1], [])
    by.get(c[1]).push(c)
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
const shipped = Object.fromEntries(Object.entries(ORIG).map(([g, p]) => [g, new StockTabix({ path: p })]))
async function truth(genome, SEQ, D) {
  const orig = shipped[genome]
  const from = floorTo(D.start, C) - 2 * C
  const lines = []
  await orig.getLines(SEQ, Math.max(0, from), D.end, { lineCallback: l => lines.push(l) })
  const pieces = new Map()
  for (const rows of groupF6(lines)) clipF6(decodeChunk(rows, undefined), D, pieces)
  const de = [Math.max(0, D.start - MAXNODE), D.end + MAXNODE]
  const dl = []
  await orig.getLines(`${SEQ}~departure`, de[0], de[1], { lineCallback: l => dl.push(l) })
  return { pieces, deps: depKeys(dl, de), strict: depKeys(dl, [D.start, D.end]) }
}
function s7Pieces(got, D) {
  const pieces = new Map()
  for (const t of got.tiles) clipF6(decodeChunk(t.lines.map(l => { const c = l.split('\t'); return [c[0], String(t.cs), String(t.cs + 1), ...c.slice(3)] }), undefined), D, pieces)
  return pieces
}
function compare(a, b) {
  let missing = 0
  let differ = 0
  for (const [k, v] of a) {
    if (!b.has(k)) missing++
    else if (b.get(k) !== v) differ++
  }
  let extra = 0
  for (const k of b.keys()) if (!a.has(k)) extra++
  return { missing, differ, extra }
}

const out = fs.createWriteStream(outPath)
const cands = new Map()
for (const w of windows) {
  const D = { start: Math.max(0, w.start - CONTEXT), end: w.end + CONTEXT }
  const rec = { ...w }
  if (w.set === 'first') {
    const cand = s7Cand(w.genome, w.seq)
    const m0 = srv.mark()
    rec.sizes = await cand.open()
    rec.open = srv.since(m0)
    const m1 = srv.mark()
    const got = await cand.window(D, true)
    rec.window = srv.since(m1)
    rec.total = srv.since(m0)
    rec.units = got.units
  } else {
    const key = `${w.genome}|${w.seq}`
    if (!cands.has(key)) {
      const cand = s7Cand(w.genome, w.seq)
      await cand.open()
      cands.set(key, cand)
    }
    const cand = cands.get(key)
    const m0 = srv.mark()
    const got = await cand.window(D, false)
    rec.read = srv.since(m0)
    rec.split = got.split
    rec.units = got.units
    rec.largest = got.largest
    const m1 = srv.mark()
    const withAttach = await cand.window(D, true)
    rec.withAttach = srv.since(m1)
    rec.attachFetches = withAttach.fetches
    if (w.i % CHECK === 0) {
      const tr = await truth(w.genome, w.seq, D)
      const mine = s7Pieces(got, D)
      const dk = depKeys(got.dep, [0, Infinity])
      rec.check = { pieces: tr.pieces.size, ...compare(tr.pieces, mine), deps: tr.strict.size }
      rec.check.depMissing = [...tr.strict].filter(k => !dk.has(k)).length
      rec.check.depExtra = [...dk].filter(k => !tr.deps.has(k)).length
    }
  }
  out.write(JSON.stringify(rec) + '\n')
}
out.end()
srv.close()
