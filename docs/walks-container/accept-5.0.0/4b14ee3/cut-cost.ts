// node cut-cost.ts <graph-walks repo> <walks.gz> <sequence> <start> <end> <unloaded|loaded> [repeats]
// One cut of every haplotype over one window, budgets lifted, timed after the
// reader has read its header and the sequence's table; repeated, the first
// read of the data being the cold one. Prints each time, the bytes and
// requests each cut read, what it holds, and the process's peak RSS.
const [repo, walks, refName, from, to, mode, repeats = '3'] = process.argv.slice(2)
const { LocalFile } = await import(`${repo}/node_modules/generic-filehandle2/esm/index.js`)
const { WalkReader } = await import(`${repo}/src/index.ts`)
let bytes = 0
let requests = 0
const reader = WalkReader.open(walks!, (p: string) => {
  const file = new LocalFile(p)
  const read = file.read.bind(file)
  file.read = (length: number, position?: number, opts?: object) => {
    bytes += length
    requests++
    return read(length, position, opts)
  }
  return file
})
await reader.header()
await reader.units(refName!)
const lifted = { stepBudget: Infinity, byteBudget: Infinity, departureByteBudget: Infinity }
const region = { start: Number(from), end: Number(to) }
for (let k = 0; k < Number(repeats); k++) {
  bytes = 0
  requests = 0
  const t = performance.now()
  const cut = await reader.cut(refName!, region, {
    ...lifted,
    ...(mode === 'loaded' ? { expand: () => true } : {}),
  })
  const ms = Math.round(performance.now() - t)
  const unloaded = cut.fragments.filter((f: { abridged?: unknown }) => f.abridged !== undefined).length
  console.log(
    `${repo!.split('/').at(-1)} ${mode} ${refName}:${from}-${to} cut ${k + 1}: ${ms} ms, ${bytes} bytes in ${requests} reads; ${cut.fragments.length} fragments (${unloaded} with unloaded pieces), ${cut.departures.length} departures, ${cut.gaps?.length ?? 0} gaps, ${cut.kept.size} nodes kept`,
  )
}
console.log(`${repo!.split('/').at(-1)} ${mode} peak rss ${Math.round(process.resourceUsage().maxRSS / 1024)} MB`)
