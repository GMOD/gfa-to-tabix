// The S7 file's structure: directory and per-sequence table sizes, units by
// kind, the largest units, the departure pyramid's duplication, the largest
// offset. usage: node structure.mjs <dir> > structure.json
import fs from 'node:fs'
import zlib from 'node:zlib'

const [dir] = process.argv.slice(2)
const file = `${dir}/s7.walks.gz`
const fd = fs.openSync(file, 'r')
const read = (off, len) => {
  const buf = Buffer.alloc(len)
  fs.readSync(fd, buf, 0, len, off)
  return buf
}
const directoryText = fs.readFileSync(`${file}.idx`)
const directory = directoryText.toString().trim().split('\n').slice(1).map(l => l.split('\t'))
const header = directory.find(c => c[0] === '#header')
const sections = directory.filter(c => c[0] !== '#header').map(c => ({ seq: c[0], off: +c[1], len: +c[2] }))

const kinds = {}
const largest = {}
const perSeq = {}
let maxEnd = 0
let depLines = 0
let detailCollisions = 0
const records = new Set()
const unitsBySize = []
for (const s of sections) {
  const lines = zlib.gunzipSync(read(s.off, s.len)).toString().trim().split('\n').slice(1)
  const units = lines.map(l => l.split('\t').slice(1)).map(c => ({ seq: c[0], lo: +c[1], hi: +c[2], kind: c[3], name: c[4], off: +c[5], len: +c[6] }))
  const byKind = {}
  for (const l of lines) (byKind[l.split('\t')[4]] ??= []).push(l)
  const gz = ls => (ls?.length ? zlib.gzipSync(ls.join('\n') + '\n', { level: 6 }).length : 0)
  const noDetail = lines.filter(l => l.split('\t')[4] !== 'detail')
  perSeq[s.seq] = {
    tableBytes: s.len,
    tableTextBytes: lines.join('\n').length,
    units: units.length,
    entries: Object.fromEntries(Object.entries(byKind).map(([k, ls]) => [k, { n: ls.length, textBytes: ls.join('\n').length + 1, gzipAlone: gz(ls) }])),
    gzipWithoutDetail: gz(noDetail),
  }
  const names = new Map()
  for (const u of units.filter(u => u.kind === 'detail')) names.set(u.name, (names.get(u.name) ?? 0) + 1)
  detailCollisions += [...names.values()].filter(n => n > 1).reduce((a, n) => a + n, 0)
  for (const u of units) {
    const k = (kinds[u.kind] ??= { n: 0, bytes: 0, zero: 0 })
    k.n++
    k.bytes += u.len
    if (u.len === 0) k.zero++
    maxEnd = Math.max(maxEnd, u.off + u.len)
    unitsBySize.push(u)
    if (u.kind === 'departures') {
      for (const l of zlib.gunzipSync(read(u.off, u.len)).toString().split('\n')) {
        if (l && !l.startsWith('#')) {
          depLines++
          records.add(l)
        }
      }
    }
  }
}
unitsBySize.sort((a, b) => b.len - a.len)
for (const kind of Object.keys(kinds)) largest[kind] = unitsBySize.filter(u => u.kind === kind).slice(0, 3)
const bigText = unitsBySize.slice(0, 3).map(u => ({ ...u, textBytes: zlib.gunzipSync(read(u.off, u.len)).length }))
console.log(
  JSON.stringify(
    {
      fileBytes: fs.statSync(file).size,
      directoryBytes: directoryText.length,
      directoryLines: directory.length + 1,
      headerBytes: +header[2],
      sections: sections.length,
      tablesTotalBytes: sections.reduce((s, x) => s + x.len, 0),
      maxUnitEnd: maxEnd,
      over4GB: maxEnd > 2 ** 32,
      kinds,
      departureLines: depLines,
      departureRecords: records.size,
      duplication: depLines / records.size,
      detailUnitsSharingAName: detailCollisions,
      largest,
      largestUnitsText: bigText,
      perSeq,
    },
    null,
    1,
  ),
)
