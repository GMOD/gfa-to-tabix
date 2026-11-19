#!/usr/bin/env node
// Says whether @jbrowse/graph-walks reads a walk file without refusing it:
// it opens the file, reads the header and cuts every reference sequence
// whole, once with every abridged piece expanded and once with none, with
// every budget lifted. Prints `reads` and what it read, or `refuses` and
// the error. It does not say the cut is right: graph-walks-rebuild.mjs
// does that, against the GFA.
// Usage: reader-probe.mjs <graph-walks checkout> <walks.gz>
import { open, readFile } from 'node:fs/promises'
import { pathToFileURL } from 'node:url'

const [checkout, path] = process.argv.slice(2)
const { WalkReader } = await import(pathToFileURL(`${checkout}/src/index.ts`).href)

class LocalFile {
  constructor(source) {
    this.source = source
    this.handle = open(source, 'r')
  }
  async read(length, position = 0) {
    const buffer = new Uint8Array(length)
    const { bytesRead } = await (await this.handle).read(buffer, 0, length, position)
    return buffer.subarray(0, bytesRead)
  }
  readFile(options) {
    return readFile(this.source, options)
  }
  async stat() {
    return (await this.handle).stat()
  }
}

const unbounded = {
  context: 0,
  stepBudget: Infinity,
  byteBudget: Infinity,
  departureByteBudget: Infinity,
  attachBp: Infinity,
  attachFetches: Infinity,
  nodeLimit: Infinity,
  links: false,
}
const read = []
try {
  const reader = WalkReader.fromFilehandles({
    data: new LocalFile(path),
    directory: new LocalFile(`${path}.idx`),
  })
  const header = await reader.header()
  read.push(`tile ${header.tile}, ${header.haplotypes.length} haplotypes`)
  for (const seq of await reader.referenceSequences()) {
    const region = { start: 0, end: await reader.sequenceLength(seq) }
    const expanded = await reader.cut(seq, region, { ...unbounded, expand: () => true })
    const plain = await reader.cut(seq, region, unbounded)
    read.push(`${JSON.stringify(seq)}: ${expanded.fragments.length} and ${plain.fragments.length} fragments, ${expanded.departures.length} departures`)
  }
  console.log(`reads\t${read.join('; ')}`)
} catch (error) {
  console.log(`refuses\t${error.name}: ${String(error.message).slice(0, 200)}`)
}
