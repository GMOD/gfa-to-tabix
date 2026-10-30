// node lostcheck.mjs NAME WALKS REFSEQ
// For each hap8 window of out/NAME.jsonl with class 3 'skip' or 'none' nodes:
// per selected carrier haplotype, whether the walk file already holds what a
// reader would need to draw those nodes, and how the haplotype crosses the
// window. Reads the chunks the cut read, plus the chunks the haplotype's skip
// rows there name, decoding only that haplotype with graph-walks' decodeChunk.
//
// Per haplotype and window:
//   lost       class 3 skip/none nodes it carries (selected carrier)
//   inRead     of those, on its steps in the chunks the cut read
//   inSkipFrom of the rest, on its steps in the chunks its skip rows name
//   rOnWin     its steps on reference nodes on the window +-1 kb
//   rInChunks  its steps on any read chunk's reference
//   stretches  lost nodes on its steps by the off-reference stretch holding
//              them: spans the window (leaves before, rejoins after), lies
//              before or after it, inside it, or open (no reference step on
//              one side within the read)
//   cross      the run's crossings of the window between reference steps either
//              side: own:N through N steps off the reference, or jump
//   zeroR      its pieces in the window's chunks with no step on their R
//   skipRow    it has a skip row in the window's chunks
import fs from 'node:fs'

const GW = process.env.GRAPH_WALKS ?? new URL('../../../../graph-walks', import.meta.url).pathname
const { joinPieces } = await import(`${GW}/esm/index.js`)
const { decodeChunk } = await import(`${GW}/esm/walkChunk.js`)
const { TabixIndexedFile } = await import(`${GW}/node_modules/@gmod/tabix/esm/index.js`)

const [name, walks, ref] = process.argv.slice(2)
const CONTEXT = 1000
const file = new TabixIndexedFile({ path: walks })
const cache = new Map()
async function chunkRows(cs) {
  if (!cache.has(cs)) {
    const held = []
    await file.getLines(ref, cs, cs + 1, {
      lineCallback: l => {
        const c = l.split('\t')
        if (+c[1] === cs) held.push(c)
      },
    })
    cache.set(cs, held)
    if (cache.size > 64) cache.delete(cache.keys().next().value)
  }
  return cache.get(cs)
}

const out = []
for (const line of fs.readFileSync(`out/${name}.jsonl`, 'utf8').split('\n')) {
  if (!line) continue
  const r = JSON.parse(line)
  if (r.mode !== 'hap8' || !r.indexOnly) continue
  const lostBy = new Map()
  for (const n of r.indexOnly) {
    if (n.sub !== 'skip' && n.sub !== 'none') continue
    for (const c of n.carriersSelected) {
      const h = c.replace('.', '#')
      if (!lostBy.has(h)) lostBy.set(h, new Set())
      lostBy.get(h).add(+n.id)
    }
  }
  if (lostBy.size === 0) continue
  const { chunk, chunksRead } = r.walk
  const winChunks = new Set()
  for (let c = Math.floor(r.start / chunk) * chunk; c < r.end; c += chunk) winChunks.add(c)
  for (const [hap, lost] of lostBy) {
    const keep = n => n.startsWith(`${hap}#`)
    const rows = []
    const refPos = new Map()
    let zeroR = 0
    const skipFrom = new Set()
    let skipRow = false
    for (const cs of chunksRead) {
      const held = await chunkRows(cs)
      const d = decodeChunk(held, keep)
      for (const [id, node] of d.nodes) {
        if (node.rank === 0) {
          if (!refPos.has(id)) refPos.set(id, [])
          refPos.get(id).push(node.start)
        }
      }
      for (const row of d.rows) {
        if (!keep(row.name)) continue
        rows.push(row)
        if (winChunks.has(cs) && !row.abridged && row.n === (row.interior ?? 0)) zeroR++
      }
      for (const c of held) {
        if (c[3] === 'skip' && keep(c[4]) && winChunks.has(cs)) {
          skipRow = true
          skipFrom.add(+c[7])
          skipFrom.add(+c[8])
        }
      }
    }
    const steps = new Set()
    let rOnWin = 0
    let rInChunks = 0
    let bracket = false
    const stretches = {}
    const cross = []
    for (const run of joinPieces(rows)) {
      let prev = run.prev?.start ?? r.start
      const pos = []
      for (const id of run.ids) {
        steps.add(id)
        const at = refPos.get(id)
        if (at) {
          const p = at.reduce((b, x) => (Math.abs(x - prev) < Math.abs(b - prev) ? x : b))
          prev = p
          pos.push(p)
          rInChunks++
          if (p >= r.start - CONTEXT && p < r.end + CONTEXT) rOnWin++
        } else pos.push(undefined)
      }
      // each off-reference stretch holding lost nodes, by the reference steps
      // either side of it: where it leaves and rejoins, undefined past the run
      let lastR
      let count = 0
      const close = p => {
        if (count > 0) {
          const [a, b] = [lastR, p]
          const kind =
            a === undefined || b === undefined
              ? 'open'
              : Math.min(a, b) < r.start && Math.max(a, b) >= r.end
                ? 'spans'
                : Math.max(a, b) < r.start
                  ? 'before'
                  : Math.min(a, b) >= r.end
                    ? 'after'
                    : 'inside'
          stretches[kind] = (stretches[kind] ?? 0) + count
          if (kind === 'spans') bracket = true
        }
        count = 0
      }
      for (let i = 0; i < run.ids.length; i++) {
        const p = pos[i]
        if (p !== undefined) {
          close(p)
          lastR = p
        } else if (lost.has(run.ids[i])) count++
      }
      close(undefined)
      // how the run crosses the window: between two reference steps either
      // side of it, through steps off the reference (own copy) or none (jump)
      let li
      for (let i = 0; i < run.ids.length; i++) {
        const p = pos[i]
        if (p === undefined) continue
        if (li !== undefined) {
          const a = pos[li]
          if (Math.min(a, p) < r.start && Math.max(a, p) >= r.end) {
            const between = i - li - 1
            cross.push(between > 0 ? `own:${between}` : 'jump')
          }
        }
        li = i
      }
    }
    const inRead = [...lost].filter(id => steps.has(id)).length
    let inSkipFrom = 0
    const rest = [...lost].filter(id => !steps.has(id))
    if (rest.length) {
      const more = new Set()
      for (const cs of skipFrom) {
        if (chunksRead.includes(cs)) continue
        const d = decodeChunk(await chunkRows(cs), keep)
        for (const row of d.rows) if (keep(row.name)) for (const id of row.steps.ids) more.add(id)
      }
      inSkipFrom = rest.filter(id => more.has(id)).length
    }
    const rec = { stratum: r.stratum, start: r.start, hap, lost: lost.size, inRead, inSkipFrom, rOnWin, rInChunks, bracket, stretches, cross, zeroR, skipRow }
    out.push(rec)
    console.log(JSON.stringify(rec))
  }
}
fs.writeFileSync(`out/${name}.lostcheck.json`, JSON.stringify(out))
