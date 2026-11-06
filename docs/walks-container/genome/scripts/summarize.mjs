// Tables from the f6 (and later s7) result files.
// usage: node summarize.mjs <res dir>
import fs from 'node:fs'

const [res] = process.argv.slice(2)
const load = f => (fs.existsSync(f) ? fs.readFileSync(f, 'utf8').trim().split('\n').filter(Boolean).map(l => JSON.parse(l)) : [])
const kb = b => (b / 1024).toFixed(b < 10240 ? 1 : 0)
const q = (xs, p) => {
  const s = [...xs].sort((a, b) => a - b)
  return s[Math.min(s.length - 1, Math.floor(p * s.length))]
}
const mpp = xs => [0.5, 0.9, 0.99].map(p => kb(q(xs, p))).join(' / ')
const short = seq => seq.split('#').at(-1)
const groupBy = (xs, key) => xs.reduce((m, x) => m.set(key(x), [...(m.get(key(x)) ?? []), x]), new Map())

const f6 = [...load(`${res}/f6.grch38.jsonl`), ...load(`${res}/f6.chm13.jsonl`)]

console.log('## Format 6 first view (header + whole .tbi + one 1 kb window), 20 seeded windows per sequence\n')
console.log('| genome | seq | open: requests, KB (tbi + header) | window KB median / max | window requests median / max | total KB median / max | round trips max |')
console.log('|---|---|---|---|---|---|---|')
for (const [k, rs] of groupBy(f6.filter(r => r.set === 'first'), r => `${r.genome}|${r.seq}`)) {
  const [genome, seq] = k.split('|')
  const o = rs[0].open
  const tbi = Object.entries(o.byFile).find(([f]) => f.endsWith('.tbi'))[1]
  const win = rs.map(r => r.window.bytes)
  const reqs = rs.map(r => r.window.requests)
  const tot = rs.map(r => r.total.bytes)
  console.log(`| ${genome} | ${short(seq)} | ${o.requests}, ${kb(o.bytes)} (${kb(tbi)} + ${kb(o.bytes - tbi)}) | ${kb(q(win, 0.5))} / ${kb(Math.max(...win))} | ${q(reqs, 0.5)} / ${Math.max(...reqs)} | ${kb(q(tot, 0.5))} / ${kb(Math.max(...tot))} | ${Math.max(...rs.map(r => r.total.trips))} |`)
}

console.log('\n## Format 6 windows: KB median / p90 / p99, requests median / max, round trips max\n')
console.log('| genome | seq | set | size | n | read KB | read + attach KB | requests | trips |')
console.log('|---|---|---|---|---|---|---|---|---|')
for (const [k, rs] of groupBy(f6.filter(r => r.set !== 'first'), r => `${r.genome}|${r.seq}|${r.set}|${r.size}`)) {
  const [genome, seq, set, size] = k.split('|')
  const reqs = rs.map(r => r.withAttach.requests)
  console.log(`| ${genome} | ${short(seq)} | ${set} | ${+size / 1000} kb | ${rs.length} | ${mpp(rs.map(r => r.read.bytes))} | ${mpp(rs.map(r => r.withAttach.bytes))} | ${q(reqs, 0.5)} / ${Math.max(...reqs)} | ${Math.max(...rs.map(r => r.withAttach.trips))} |`)
}

const s7 = [...load(`${res}/s7.grch38.jsonl`), ...load(`${res}/s7.chm13.jsonl`)]
if (s7.length) {
  const f6By = new Map(f6.map(r => [`${r.genome}|${r.seq}|${r.set}|${r.size}|${r.i}`, r]))
  const keyOf = r => `${r.genome}|${r.seq}|${r.set}|${r.size}|${r.i}`

  console.log('\n## First view, S7 against format 6: open + one 1 kb window with attach fetches, 20 seeded windows per sequence\n')
  console.log('| genome | seq | S7 open KB (directory + header + table) | S7 open requests, trips | S7 window KB median / max | S7 total KB median / max | S7 trips max | format 6 total KB median / max | format 6 trips max | S7 / format 6 total, median |')
  console.log('|---|---|---|---|---|---|---|---|---|---|')
  for (const [k, rs] of groupBy(s7.filter(r => r.set === 'first'), r => `${r.genome}|${r.seq}`)) {
    const [genome, seq] = k.split('|')
    const o = rs[0].open
    const dirBytes = Object.entries(o.byFile).find(([f]) => f.endsWith('.idx'))[1]
    const f6s = rs.map(r => f6By.get(keyOf(r)))
    const tot = rs.map(r => r.total.bytes)
    const ftot = f6s.map(r => r.total.bytes)
    const win = rs.map(r => r.window.bytes)
    console.log(`| ${genome} | ${short(seq)} | ${kb(o.bytes)} (${kb(dirBytes)} + ${kb(rs[0].sizes.headerBytes)} + ${kb(rs[0].sizes.sectionBytes)}) | ${o.requests}, ${o.trips} | ${kb(q(win, 0.5))} / ${kb(Math.max(...win))} | ${kb(q(tot, 0.5))} / ${kb(Math.max(...tot))} | ${Math.max(...rs.map(r => r.total.trips))} | ${kb(q(ftot, 0.5))} / ${kb(Math.max(...ftot))} | ${Math.max(...f6s.map(r => r.total.trips))} | ${(q(tot, 0.5) / q(ftot, 0.5)).toFixed(2)} |`)
  }

  console.log('\n## Windows, S7 against format 6: KB median / p90 / p99 (read; read + attach), requests median / max, round trips max\n')
  console.log('| genome | seq | set | size | n | S7 read | format 6 read | S7 + attach | format 6 + attach | S7 req | format 6 req | S7 trips | format 6 trips |')
  console.log('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
  for (const [k, rs] of groupBy(s7.filter(r => r.set !== 'first'), r => `${r.genome}|${r.seq}|${r.set}|${r.size}`)) {
    const [genome, seq, set, size] = k.split('|')
    const fs6 = rs.map(r => f6By.get(keyOf(r)))
    const req = xs => `${q(xs, 0.5)} / ${Math.max(...xs)}`
    console.log(
      `| ${genome} | ${short(seq)} | ${set} | ${+size / 1000} kb | ${rs.length} | ${mpp(rs.map(r => r.read.bytes))} | ${mpp(fs6.map(r => r.read.bytes))} | ${mpp(rs.map(r => r.withAttach.bytes))} | ${mpp(fs6.map(r => r.withAttach.bytes))} | ${req(rs.map(r => r.withAttach.requests))} | ${req(fs6.map(r => r.withAttach.requests))} | ${Math.max(...rs.map(r => Math.max(r.read.trips, r.withAttach.trips)))} | ${Math.max(...fs6.map(r => r.withAttach.trips))} |`,
    )
  }

  console.log('\n## Piece and departure check (arbA\'s, every 4th window)\n')
  console.log('| genome | set | windows | pieces | missing | differ | extra | departures | missing | outside truth |')
  console.log('|---|---|---|---|---|---|---|---|---|---|')
  for (const [k, rs] of groupBy(s7.filter(r => r.check), r => `${r.genome}|${r.set}`)) {
    const [genome, set] = k.split('|')
    const sum = f => rs.reduce((s, r) => s + r.check[f], 0)
    console.log(`| ${genome} | ${set} | ${rs.length} | ${sum('pieces')} | ${sum('missing')} | ${sum('differ')} | ${sum('extra')} | ${sum('deps')} | ${sum('depMissing')} | ${sum('depExtra')} |`)
  }
}
