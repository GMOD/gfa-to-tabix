// node read-scan.ts <walks.gz> [limit]: the bytes an unloaded cut of every
// haplotype, budgets lifted, reads over 1 kb windows at the start, middle
// and end of every abridged tile, against the reader's bytesFor; prints the
// worst 20 and how many pass 4,000,000 bytes
const [walks, limit = '4000000'] = process.argv.slice(2)
const repo = '/home/cdiesh/work/review-gw7/gw-4b14ee3'
const { LocalFile } = await import(`${repo}/node_modules/generic-filehandle2/esm/index.js`)
const { WalkReader } = await import(`${repo}/src/index.ts`)
let bytes = 0
const reader = WalkReader.open(walks!, (p: string) => {
  const file = new LocalFile(p)
  const read = file.read.bind(file)
  if (p === walks) {
    file.read = (length: number, position?: number, opts?: object) => {
      bytes += length
      return read(length, position, opts)
    }
  }
  return file
})
await reader.header()
const lifted = { stepBudget: Infinity, byteBudget: Infinity, departureByteBudget: Infinity }
const rows: [number, number, string][] = []
for (const refName of await reader.referenceSequences()) {
  const units = await reader.units(refName)
  const abridged = new Set(units.filter((u: { kind: string }) => u.kind === 'blocks').map((u: { name: string }) => u.name))
  for (const t of units.filter((u: { kind: string; name: string }) => u.kind === 'tile' && abridged.has(u.name))) {
    const mid = Math.floor((t.start + t.end) / 2)
    for (const start of [t.start, mid - 500, t.end - 1000]) {
      const region = { start, end: start + 1000 }
      bytes = 0
      await reader.cut(refName, region, lifted)
      rows.push([bytes, await reader.bytesFor(refName, region), `${refName}:${start}-${start + 1000}`])
    }
  }
}
rows.sort((a, b) => b[0] - a[0])
console.log(`${walks}: ${rows.length} windows; cut read over ${limit} bytes: ${rows.filter(r => r[0] > Number(limit)).length}; bytesFor over it: ${rows.filter(r => r[1] > Number(limit)).length}`)
for (const [n, f, w] of rows.slice(0, 20)) {
  console.log(`  ${w}  cut read ${n}  bytesFor ${f}`)
}
