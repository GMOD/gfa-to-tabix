// node chunkmap.mjs OUT.jsonl WALKS.walks.bed.gz MAP.json
// For each index-only node of class 2, 3 or 3? in OUT.jsonl, the chunks of
// the walk file whose ref or nodes rows hold it: the chunk's own rows
// (`main`, by chunk start on its sequence) and its detail records (`detail`,
// by the chunk they belong to, from `seq~cs`). A chunk's ref and nodes rows
// list every node its routes and walks step on.
import { spawn } from 'node:child_process'
import fs from 'node:fs'
import readline from 'node:readline'

const [outPath, walks, mapPath] = process.argv.slice(2)
const wanted = new Set()
for await (const line of readline.createInterface({ input: fs.createReadStream(outPath), crlfDelay: Infinity })) {
  if (!line) continue
  const rec = JSON.parse(line)
  for (const n of rec.indexOnly ?? []) {
    if (n.cls === 2 || n.cls === 3 || n.cls === '3?') wanted.add(+n.id)
  }
}
console.error(`${wanted.size} nodes to place`)
const found = new Map()
const note = (id, key) => {
  let set = found.get(id)
  if (!set) found.set(id, (set = new Set()))
  set.add(key)
}
const unzip = spawn('bgzip', ['-@', '4', '-dc', walks], {
  stdio: ['ignore', 'pipe', 'inherit'],
})
const lines = readline.createInterface({ input: unzip.stdout, crlfDelay: Infinity })
let n = 0
for await (const line of lines) {
  if (++n % 5e6 === 0) console.error(`${n / 1e6}M lines`)
  if (line.charCodeAt(0) === 35) continue
  const t1 = line.indexOf('\t')
  const t2 = line.indexOf('\t', t1 + 1)
  const t3 = line.indexOf('\t', t2 + 1)
  const t4 = line.indexOf('\t', t3 + 1)
  const kind = line.slice(t3 + 1, t4)
  if (kind !== 'ref' && kind !== 'nodes') continue
  const seq = line.slice(0, t1)
  const tilde = seq.indexOf('~')
  const key =
    tilde < 0
      ? `${seq}\t${line.slice(t1 + 1, t2)}\tmain`
      : `${seq.slice(0, tilde)}\t${seq.slice(tilde + 1)}\tdetail`
  const cols = line.split('\t')
  let id = 0
  if (kind === 'ref') {
    for (const t of cols[9].split(',')) {
      const d = +t
      const r = d & 1
      id += (d - r) / 2
      if (wanted.has(id)) note(id, key)
    }
  } else {
    for (const t of cols[4].split(',')) {
      id += +t
      if (wanted.has(id)) note(id, key)
    }
  }
}
const out = {}
for (const [id, keys] of found) {
  out[id] = [...keys].map(k => {
    const [seq, cs, where] = k.split('\t')
    return { seq, cs: +cs, where }
  })
}
fs.writeFileSync(mapPath, JSON.stringify(out))
console.error(`${found.size} of ${wanted.size} placed`)
