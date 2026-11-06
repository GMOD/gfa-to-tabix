// Seeded windows over each measured sequence's row extent, plus the CHM13
// trouble spots. usage: node windows.mjs <res dir> > windows.jsonl
import fs from 'node:fs'

const [res] = process.argv.slice(2)
const PER = 200
const FIRST = 20
const SIZES = [1000, 100_000]

const extentOf = (genome, seq) => {
  let lo = Infinity
  let hi = -Infinity
  for (const l of fs.readFileSync(`${res}/inv.${genome}.chunks`, 'utf8').split('\n')) {
    const [s, cs] = l.split('\t')
    if (s === seq) {
      lo = Math.min(lo, +cs)
      hi = Math.max(hi, +cs + 65536)
    }
  }
  return [lo, hi]
}

const SETS = [
  ...['chr1', 'chr6', 'chr22'].map(c => ({ genome: 'grch38', seq: `GRCh38#0#${c}`, set: 'all' })),
  ...['chr9', 'chr14', 'chr22'].map(c => ({ genome: 'chm13', seq: `CHM13#0#${c}`, set: 'all' })),
  { genome: 'chm13', seq: 'CHM13#0#chr9', set: '38-80Mb', range: [38_000_000, 80_000_000] },
  { genome: 'chm13', seq: 'CHM13#0#chr14', set: '13-14Mb', range: [13_000_000, 14_000_000] },
]
const FIRST_VIEW = ['chr1', 'chr6', 'chr9', 'chr14', 'chr22', 'chrX'].flatMap(c => [
  { genome: 'grch38', seq: `GRCh38#0#${c}`, set: 'first' },
  { genome: 'chm13', seq: `CHM13#0#${c}`, set: 'first' },
])

function mulberry32(a) {
  return () => {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}
const seedOf = text => [...text].reduce((h, ch) => (Math.imul(h, 31) + ch.charCodeAt(0)) | 0, 7)

const emit = (s, size, n) => {
  const [lo, hi] = s.range ?? extentOf(s.genome, s.seq)
  const rnd = mulberry32(seedOf(`${s.genome}|${s.seq}|${s.set}|${size}`))
  for (let i = 0; i < n; i++) {
    const start = Math.floor(lo + rnd() * (hi - lo - size))
    console.log(JSON.stringify({ genome: s.genome, seq: s.seq, set: s.set, size, i, start, end: start + size }))
  }
}
for (const s of FIRST_VIEW) emit(s, 1000, FIRST)
for (const s of SETS) for (const size of SIZES) emit(s, size, PER)
