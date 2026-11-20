#!/usr/bin/env node
// What @jbrowse/graph-walks' cut returns over each window it is given, in the
// form window-oracle.py states what it must return: one JSON line per window
// read from stdin, {seq, start, end, context, expand, attachBp}, each cut
// with every walk kept and every budget lifted. A fragment is its
// name, fragStart, hapStart, hapEnd, trimmedBefore, trimmedAfter and steps,
// a departure its record's columns, fromSteps and own steps; a step on the
// reference is `refStart±` then `>id` or `<id`, a step off it `>id` or
// `<id`, and a placeholder `~bp`.
//
// With digest 1, each list of steps is the first 16 hex digits of its text's
// SHA-1.
//
// Usage: window-cuts.mjs <graph-walks checkout> <walks.gz> [digest] < windows.jsonl
import { createHash } from 'node:crypto'
import { open, readFile } from 'node:fs/promises'
import { createInterface } from 'node:readline'
import { join, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

class LocalFile {
  constructor(path) {
    this.source = path
    this.handle = open(path, 'r')
  }

  async read(length, position = 0) {
    const buffer = new Uint8Array(length)
    const { bytesRead } = await (
      await this.handle
    ).read(buffer, 0, length, position)
    return buffer.subarray(0, bytesRead)
  }

  readFile(options) {
    return readFile(this.source, options)
  }

  async stat() {
    return (await this.handle).stat()
  }
}

const [checkout, walksPath, digest = '0'] = process.argv.slice(2)
const { WalkReader, isPlaceholder } = await import(
  pathToFileURL(join(resolve(checkout), 'src/index.ts')).href
)
const reader = WalkReader.fromFilehandles({
  data: new LocalFile(walksPath),
  directory: new LocalFile(`${walksPath}.idx`),
})

const shown = text =>
  digest === '1'
    ? createHash('sha1').update(text).digest('hex').slice(0, 16)
    : text

const stepsText = (graph, ids, rev, refStarts, against) =>
  shown(
    Array.from(ids, (id, i) => {
      const handle = `${rev[i] === 1 ? '<' : '>'}${id}`
      const node = graph.nodes.get(id)
      return isPlaceholder(id)
        ? `~${node.end - node.start}`
        : refStarts === undefined || Number.isNaN(refStarts[i])
          ? handle
          : `${refStarts[i]}${against[i] === 1 ? '-' : '+'}${handle}`
    }).join(' '),
  )

const lines = createInterface({ input: process.stdin, crlfDelay: Infinity })
for await (const line of lines) {
  if (line.trim() !== '') {
    const { seq, start, end, context, expand, attachBp } = JSON.parse(line)
    const out = { seq, start, end, context, expand }
    try {
      const { graph, fragments, departures } = await reader.cut(
        seq,
        { start, end },
        {
          context,
          expand: () => expand,
          stepBudget: Infinity,
          byteBudget: Infinity,
          departureByteBudget: Infinity,
          attachBp,
          nodeLimit: Infinity,
          links: 'none',
        },
      )
      out.fragments = fragments.map(f => [
        f.name,
        f.fragStart,
        f.hapStart,
        f.hapEnd,
        f.trimmedBefore,
        f.trimmedAfter,
        stepsText(graph, f.ids, f.rev, f.refStarts, f.against),
      ])
      out.departures = departures.map(d => [
        d.name,
        d.hapStart,
        d.ownBp,
        d.missingBp,
        d.leavePos,
        d.leaveReversed,
        d.leavePasses,
        d.rejoinPos,
        d.rejoinReversed,
        d.rejoinPasses,
        d.fromSteps,
        d.steps ? stepsText(graph, d.steps.ids, d.steps.rev) : null,
      ])
    } catch (error) {
      out.error = String(error?.message ?? error)
    }
    process.stdout.write(`${JSON.stringify(out)}\n`)
  }
}
