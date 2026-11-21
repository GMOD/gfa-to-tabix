// drive.mjs OUT.jsonl BASE TIMEOUT_S [LAYOUT...]: every run of the study. For each layout, each chromosome's windows in
// windows.txt, smallest first, and three runs, it runs measure.mjs for BandageJS and then the plugin, each run in a
// fresh Chrome under nice -n 10 and a 16 GB, no-swap systemd scope, once the 1-minute load is under 4. A run that
// does not draw (timeout, crash, refusal, error) is not repeated, and that reader is not run on that chromosome's
// wider windows in that layout; a row says so. Appends one JSON line per run to OUT.jsonl, skipping runs already there.
import { spawnSync } from 'node:child_process'
import { appendFileSync, existsSync, readFileSync } from 'node:fs'
import { loadavg } from 'node:os'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const [out, base, timeoutS, ...asked] = process.argv.slice(2)
const LAYOUTS = asked.length ? asked : ['fmmm', 'tubemap', 'stress', 'ordered', 'walkrows']
const READERS = ['bjs', 'plugin']
const RUNS = 3
const windows = readFileSync(join(here, 'windows.txt'), 'utf8').trim().split('\n')
const chromosomes = [...new Set(windows.map(w => w.split(':')[0]))]
const done = existsSync(out) ? readFileSync(out, 'utf8').trim().split('\n').filter(Boolean).map(l => JSON.parse(l)) : []
const key = ({ reader, spec, layout, run }) => `${reader} ${spec} ${layout} ${run}`
const have = new Set(done.map(key))
const sleep = ms => new Promise(r => setTimeout(r, ms))

function measure(reader, spec, layout) {
  const url = spawnSync('node', [join(here, 'urls.mjs'), reader, spec, layout, base], { encoding: 'utf8' }).stdout.trim()
  const r = spawnSync(
    'systemd-run',
    ['--user', '--scope', '-q', '-p', 'MemoryMax=16G', '-p', 'MemorySwapMax=0',
      'nice', '-n', '10', 'node', join(here, 'measure.mjs'), reader, url, timeoutS],
    { encoding: 'utf8', timeout: (Number(timeoutS) + 240) * 1000, maxBuffer: 1 << 26 },
  )
  const line = r.stdout.trim().split('\n').at(-1)
  try {
    return JSON.parse(line)
  } catch {
    return { reader, url, status: 'killed', error: `exit ${r.status} ${r.signal ?? ''} ${r.stderr.slice(-300)}` }
  }
}

for (const layout of LAYOUTS) {
  for (const chr of chromosomes) {
    const stopped = new Map()
    for (const spec of windows.filter(w => w.startsWith(`${chr}:`))) {
      for (let run = 1; run <= RUNS; run++) {
        for (const reader of READERS) {
          const id = { reader, spec, layout, run }
          const prior = done.find(d => key(d) === key(id))
          if (prior && prior.status !== 'ok' && prior.status !== 'not run') {
            stopped.set(reader, spec)
          }
          if (have.has(key(id))) {
            continue
          }
          if (stopped.has(reader)) {
            if (stopped.get(reader) !== spec && run === 1) {
              appendFileSync(out, JSON.stringify({ ...id, status: 'not run', error: `drew nothing at ${stopped.get(reader)}` }) + '\n')
            }
            continue
          }
          while (loadavg()[0] >= 4) {
            await sleep(20_000)
          }
          const load1 = loadavg()[0]
          const started = new Date().toISOString()
          const result = { ...id, load1, started, ...measure(reader, spec, layout), load1_end: loadavg()[0] }
          appendFileSync(out, JSON.stringify(result) + '\n')
          console.error(`${started} ${key(id)} ${result.status} painted=${result.painted} nodes=${result.nodes}`)
          if (result.status !== 'ok') {
            stopped.set(reader, spec)
          }
          await sleep(5000)
        }
      }
    }
  }
}
console.error('done')
