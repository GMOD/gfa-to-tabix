// One window, shipped read against a candidate (cutcheck's sources), with
// the differing departures and kept nodes printed.
// usage: node cutdebug.mjs DATADIR CAND SEQ START END
import fs from 'node:fs'
import { execFileSync } from 'node:child_process'

const [dataDir, cand, seq, start, end] = process.argv.slice(2)
const tmp = `/tmp/claude-1001/-home-cdiesh-src-gfa-to-tabix/95217c34-cd76-4f06-8705-ae30877df61b/scratchpad/format-review/arbB/results/cutdebug-${cand}.jsonl`
fs.writeFileSync(`${tmp}.win`, JSON.stringify({ seq, size: +end - +start, start: +start, end: +end }) + '\n')
process.env.CUTDEBUG = '1'
execFileSync('node', [new URL('./cutcheck.mjs', import.meta.url).pathname, dataDir, `${tmp}.win`, cand, tmp, '1'], {
  stdio: 'inherit',
  env: { ...process.env, CUTDEBUG: '1' },
})
