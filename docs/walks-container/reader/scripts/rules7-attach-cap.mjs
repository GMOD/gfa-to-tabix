// Cuts windows with graph-walks at $GW and prints, per window, each kept
// walk fragments steps far from D and fromSteps departures far from D.
//   node h2.mjs <file> <refName> <windows.json> <attachFetches> [keepName]
import { readFileSync } from "node:fs"
const GW = process.env.GW
const { LocalFile } = await import(`${GW}/node_modules/generic-filehandle2/esm/index.js`)
const { WalkReader } = await import(`${GW}/src/index.ts`)
const [file, refName, windowsPath, fetches, keepName] = process.argv.slice(2)
const windows = JSON.parse(readFileSync(windowsPath, "utf8"))
const reader = WalkReader.fromFilehandles({ data: new LocalFile(file), directory: new LocalFile(`${file}.idx`) })
const TILE = 65536
for (const [start, end, context] of windows) {
  const lo = start - context - TILE, hi = end + context + TILE
  const ds = start - context, de = end + context
  try {
    const { fragments, departures } = await reader.cut(refName, { start, end }, {
      context, stepBudget: Infinity, byteBudget: Infinity, departureByteBudget: Infinity,
      attachFetches: Number(fetches), nodeLimit: Infinity, links: false,
      keep: keepName ? n => n === keepName || n === refName : undefined,
    })
    const far = {}
    for (const f of fragments) {
      let n = 0
      for (const x of f.refStarts) if (!Number.isNaN(x) && (x >= hi || x < lo)) n++
      if (n) far[f.name] = (far[f.name] ?? 0) + n
    }
    let fsFar = 0
    for (const d of departures) {
      const a = Math.min(d.leavePos, d.rejoinPos), b = Math.max(d.leavePos, d.rejoinPos)
      if (d.fromSteps && (b < lo || a > hi)) fsFar++
    }
    const sig = fragments.map(f => `${f.name}:${f.hapStart}-${f.hapEnd}:${f.ids.length}`).sort().join(";")
    console.log(JSON.stringify({ start, end, fragments: fragments.length, departures: departures.length, farWalks: Object.keys(far).length, farSteps: Object.values(far).reduce((s, n) => s + n, 0), fsFar, far: Object.fromEntries(Object.entries(far).slice(0, 3)), sig: sig.length > 0 ? hash(sig) : 0 }))
  } catch (e) { console.log(JSON.stringify({ start, end, error: String(e.message ?? e) })) }
}
function hash(s) { let h = 0; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0; return h }
