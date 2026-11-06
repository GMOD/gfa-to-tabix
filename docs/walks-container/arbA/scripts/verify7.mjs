// Release checks for an S7 walks file: the header, units, tables and EOF
// partition the file; each unit starts a gzip member and its `#unit` line; the
// tables list every unit in file order; each tile's lines lie in its extent;
// each departure line is in a block of its record's cover.
// usage: node verify7.mjs <file.walks.gz> [tile]
import fs from 'node:fs'
import zlib from 'node:zlib'

const [file, tileArg] = process.argv.slice(2)
const C = +(tileArg ?? 65536)
const SIZES = [C * 512, C * 64, C * 8, C]
const data = fs.readFileSync(file)
const dir = fs.readFileSync(file + '.idx', 'utf8').trim().split('\n').map(l => l.split('\t'))
const fail = msg => {
  throw new Error(msg)
}
const walks = dir[0]
if (walks[0] !== '#walks' || !walks.includes('format:i:7')) fail('directory line 1 is not a format 7 #walks line')
if (+walks.find(t => t.startsWith('bytes:i:')).slice(8) !== data.length) fail('bytes:i: is not the file length')

// gzip members in file order
const members = []
for (let at = 0; at < data.length; ) {
  if (data[at] !== 0x1f || data[at + 1] !== 0x8b) fail(`no gzip member at ${at}`)
  const size = data.readUInt16LE(at + 16) + 1
  members.push({ at, size })
  at += size
}
const eof = members.pop()
if (eof.size !== 28 || zlib.gunzipSync(data.subarray(eof.at, eof.at + 28)).length !== 0) fail('no EOF block')
const textOf = (a, b) => zlib.gunzipSync(data.subarray(a, b)).toString()

// units by scanning: each starts on a member whose text begins `#unit`
const header = dir.find(c => c[0] === '#header')
if (+header[1] !== 0) fail('header does not start the file')
const headerText = textOf(0, +header[2])
if (headerText.split('\n')[0] !== walks.filter(t => !t.startsWith('bytes:i:')).join('\t')) fail('directory and header disagree')
const scanned = []
for (const m of members) {
  if (m.at < +header[2]) continue
  const first = zlib.gunzipSync(data.subarray(m.at, m.at + m.size)).toString()
  if (first.startsWith('#unit\t')) scanned.push({ at: m.at, end: m.at + m.size })
  else if (scanned.length) scanned.at(-1).end = m.at + m.size
  else fail(`a member at ${m.at} belongs to no unit`)
}
if (scanned[0].at !== +header[2] || scanned.at(-1).end !== eof.at) fail('units do not partition the file')
for (let k = 1; k < scanned.length; k++) if (scanned[k].at !== scanned[k - 1].end) fail('a gap between units')

function cover(lo, hi) {
  const out = []
  let at = Math.floor(lo / C) * C
  const end = Math.floor((hi - 1) / C) * C + C
  while (at < end) {
    const size = SIZES.find(s => at % s === 0 && at + s <= end) ?? C
    out.push(`${at}:${size}`)
    at += size
  }
  return out
}

const stats = { units: 0, tables: 0, lines: 0, departureLines: 0 }
const listed = new Map()
for (const c of dir.slice(1).filter(c => c[0] !== '#header')) {
  const t = textOf(+c[1], +c[1] + +c[2]).split('\n').filter(Boolean)
  const [, seq, , , kind] = t[0].split('\t')
  if (kind !== 'table' || seq !== c[0]) fail(`directory entry ${c[0]} is not its table`)
  stats.tables++
  let prev = -1
  for (const l of t.slice(1)) {
    const e = l.split('\t')
    if (e[0] !== '#entry' || e[1] !== seq) fail(`bad table line ${l}`)
    if (+e[6] <= prev) fail('table not in file order')
    prev = +e[6]
    listed.set(+e[6], e)
  }
}
for (const u of scanned) {
  const lines = textOf(u.at, u.end).split('\n').filter(Boolean)
  const [, seq, lo, hi, kind, name] = lines[0].split('\t')
  if (kind === 'table') continue
  stats.units++
  const e = listed.get(u.at)
  if (!e || +e[7] !== u.end - u.at || e.slice(1, 6).join('\t') !== [seq, lo, hi, kind, name].join('\t')) fail(`unit at ${u.at} is not listed as it is`)
  let a = Infinity
  let b = -Infinity
  for (const l of lines.slice(1)) {
    const c = l.split('\t')
    stats.lines++
    if (c[0] !== seq) fail(`a line of another sequence in unit ${u.at}`)
    if (kind === 'departures') {
      stats.departureLines++
      if (!cover(+c[1], +c[2]).includes(`${lo}:${hi - lo}`)) fail(`departure line outside its cover: ${l.slice(0, 80)}`)
    } else {
      if (+c[1] < +lo || +c[2] > +hi) fail(`a line outside its unit's extent: ${l.slice(0, 80)}`)
      if (c[3] === 'walk' || c[3] === 'abridged' || c[3] === 'ref') {
        a = Math.min(a, +c[1])
        b = Math.max(b, +c[2])
      }
    }
  }
  if (kind !== 'departures' && (a !== +lo || b !== +hi)) fail(`unit ${u.at}'s extent is not its lines' union`)
}
if (stats.units !== listed.size) fail('a listed unit was not found')
console.log(JSON.stringify({ file, ok: true, ...stats }))
