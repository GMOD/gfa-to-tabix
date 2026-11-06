// Tile extent widths: how far each tile's true extent reaches past its nominal
// 64 kb, and which tiles a given window selects. usage: node extents.mjs <dir>
import fs from 'node:fs'
import zlib from 'node:zlib'

const [dir] = process.argv.slice(2)
const file = `${dir}/s7.walks.gz`
const fd = fs.openSync(file, 'r')
const directory = fs.readFileSync(`${file}.idx`, 'utf8').trim().split('\n').slice(2).map(l => l.split('\t'))
const tiles = []
for (const [, off, len] of directory) {
  const buf = Buffer.alloc(+len)
  fs.readSync(fd, buf, 0, +len, +off)
  for (const l of zlib.gunzipSync(buf).toString().trim().split('\n').slice(1)) {
    const c = l.split('\t')
    if (c[4] === 'tile') tiles.push({ seq: c[1], lo: +c[2], hi: +c[3], cs: +c[5], len: +c[7] })
  }
}
const widths = tiles.map(t => t.hi - t.lo).sort((a, b) => a - b)
const q = p => widths[Math.min(widths.length - 1, Math.floor(p * widths.length))]
const over = k => tiles.filter(t => t.hi - t.lo > k * 65536).length
const reach = tiles.map(t => Math.max(t.cs - t.lo, t.hi - (t.cs + 65536))).sort((a, b) => a - b)
console.log(JSON.stringify({ tiles: tiles.length, widthMedian: q(0.5), p99: q(0.99), max: widths.at(-1), over2x: over(2), over4x: over(4), over16x: over(16), reachPastNominalP99: reach[Math.floor(0.99 * reach.length)], reachPastNominalMax: reach.at(-1) }))
for (const t of [...tiles].sort((a, b) => b.hi - b.lo - (a.hi - a.lo)).slice(0, 5)) console.log(JSON.stringify(t), 'width', t.hi - t.lo)
const at = tiles.filter(t => t.seq === 'CHM13#0#chr14' && t.lo < 13621284 + 1000 && t.hi > 13620284 - 1000)
if (at.length) console.log('CHM13 chr14 13,620,284 window selects', at.length, 'tiles', JSON.stringify(at.map(t => [t.cs, t.lo, t.hi, t.len])))
