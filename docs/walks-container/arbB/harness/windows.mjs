// Seeded random windows, N per size, uniform over [LO, HI) of one sequence.
//
// usage: node windows.mjs OUT.jsonl SEQ LO HI N SEED
import fs from 'node:fs'

const [out, seq, loArg, hiArg, nArg, seedArg] = process.argv.slice(2)
const lo = +loArg
const hi = +hiArg
const n = +(nArg ?? 300)
const seed = +(seedArg ?? 1)
const sizes = [1_000, 10_000, 100_000, 1_000_000]

function rng(s0) {
  let s = s0 >>> 0
  return () => {
    s = (s + 0x6d2b79f5) >>> 0
    let t = s
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const lines = []
for (const size of sizes) {
  const r = rng(seed * 1000 + size)
  for (let i = 0; i < n; i++) {
    const start = lo + Math.floor(r() * (hi - lo - size))
    lines.push(JSON.stringify({ seq, size, start, end: start + size }))
  }
}
fs.writeFileSync(out, lines.join('\n') + '\n')
