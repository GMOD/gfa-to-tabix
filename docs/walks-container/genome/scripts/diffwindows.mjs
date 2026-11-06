// The windows of a cut-check result that were not identical.
// usage: node diffwindows.mjs <genome> <cut result.jsonl> <windows.jsonl> > out.jsonl
import fs from 'node:fs'

const [genome, resultPath, windowsPath] = process.argv.slice(2)
const keyOf = w => `${w.seq}|${w.set}|${w.size}|${w.i}`
const bad = new Set(
  fs
    .readFileSync(resultPath, 'utf8')
    .trim()
    .split('\n')
    .map(l => JSON.parse(l))
    .filter(r => !r.identical)
    .map(keyOf),
)
for (const l of fs.readFileSync(windowsPath, 'utf8').trim().split('\n')) {
  const w = JSON.parse(l)
  if (w.genome === genome && bad.has(keyOf(w))) console.log(l)
}
