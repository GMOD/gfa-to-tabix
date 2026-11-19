#!/usr/bin/env node
// The consumer-side check of claim C1: @jbrowse/graph-walks 7, the real
// reader of walk format 8, rebuilds from the walk files the tool writes every path exactly
// as the GFA states it. Each fixture is built under the option sets of
// check-walks.sh; each reference sample's file is opened with WalkReader,
// and every reference sequence S, a sequence the file lists, is cut whole,
// [0, |S|), with context 0,
// every haplotype kept, every budget lifted, every attach fetch allowed,
// node bases asked for, once with every abridged walk expanded from its
// detail unit and once with none. The check demands:
//
// - Every fragment of the expanded cut is a run of whole steps of one GFA
//   line: its hapStart and hapEnd fall on step boundaries of the line named
//   by `name` and `fragStart` (0 bp segments dropped first, as the writer
//   drops them on read), and its ids and strands are the line's handles
//   there, step for step.
// - Every step a fragment places on the reference (refStarts not NaN) sits
//   at an offset where S's own lines pass that node, with `against` the
//   step's strand relation to that pass. In a file whose header says
//   revisited:i:0 every reference node has one pass, so this is the exact
//   offset the GFA gives it; such a file also may not place a step on a
//   reference node off the reference.
// - Coverage: every step of every GFA line that lies on a node of the
//   reference comes back exactly once per (line, step) over the expanded
//   cuts of all S. The writer files a step on a reference node under the
//   pass it took, in that sequence's tile (C13), so S's whole cut returns
//   every piece of S's tiles and the step is in exactly one sequence's
//   fragments. Steps on no reference node are checked wherever a fragment
//   holds them but are not demanded: a cut returns a walk from its first
//   step on S to its last, so own steps before, after or between two
//   sequences' pieces come back only as a departure record's own steps
//   (C132), which this check does not count.
// - Departures: for a revisited:i:0 file the cut's departures, records and
//   computed alike, equal as a multiset those recomputed from the GFA for
//   every line of no reference sequence: between each two consecutive
//   steps on S that are not adjacent there, holes removed (C77, C79 to
//   C81), each end with its node's pass count. For a file passing nodes
//   more than once only the departures between two once-passed ends with no
//   reference node between them are demanded, since any other end is a
//   placement choice. A record's own steps are not compared.
// - Every sequence the file lists is a path of the header's reference
//   sample with a line in the GFA, and in a file this script builds every
//   path of that sample is listed; a file given with --file, or a broken
//   one, can take one haplotype of the sample for its reference, the
//   sample's other paths then being lines like any other.
// - The header's holes on S are the stretches no line of S covers, and its
//   haplotypes are those of the lines with a step on the reference, once
//   each in byte order (C51, C52); every reference node of S the cut places
//   lies at a pass of S, its earliest, with its length and pass count, and
//   in a revisited:i:0 file every reference node of S is placed; the bases
//   the cut holds for a node are its S line's.
// - The unexpanded cut, which builds each abridged piece from its blocks
//   row with each run off R one placeholder step of known bp, equals the
//   expanded one: each fragment as its name, offsets and trims, each step
//   on the reference as its place, strand and node and each run of steps
//   off it as its bp, counted as often as it comes; its departures as the
//   expanded cut's; and no placeholder on the reference or beside another
//   step off it (C164).
//
// Before the builds, the broken files BROKEN names in
// docs/departures/scripts/broken/ must each fail the check, by a mismatch
// or by graph-walks refusing the file. Exits 1 naming each failure; prints
// one line per file otherwise.
//
// Usage: scripts/graph-walks-rebuild.mjs <graph-walks checkout> <gfa-to-tabix binary> ["fixture.gfa refs opts..." ...]
//        scripts/graph-walks-rebuild.mjs <graph-walks checkout> --file <walks.gz> <gfa>
// Needs a Node that strips types (22.18 or later): it imports the
// checkout's src/index.ts directly.
import { spawnSync } from 'node:child_process'
import { mkdtempSync, readFileSync, rmSync } from 'node:fs'
import { open, readFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const REPO = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const DATA = join(REPO, 'tests/data')
const BROKEN_DIR = join(REPO, 'docs/departures/scripts/broken')
const P_NAMES = join(REPO, 'docs/walks-container/dialect/p-names.tsv')
const OPTION_SETS = [
  '--tile 10',
  '--tile 7 --stay 0',
  '--tile 10 --abridge-bytes 1',
  '--tile 1000 --abridge-steps 1',
]
const FIXTURES = [
  'walks-two-refs.gfa GRCh38,Q',
  'walks-two-refs-p.gfa GRCh38,Q',
  'walks-repeat.gfa R',
  'walks-loop.gfa R',
  'walks-records.gfa R',
  'walks-contig-ends.gfa R',
  'walks-skip.gfa R,Q',
  'walks-sequences.gfa R',
  'walks-long-jump.gfa R',
].flatMap(fixture => OPTION_SETS.map(opts => `${fixture} ${opts}`))
const EXTRA_BUILDS = [
  'walks-abridge-bytes.gfa R --tile 100 --abridge-bytes 600',
  'walks-sequences.gfa R --tile 10 --sequences',
]
const BROKEN = [
  'abridged-detail',
  'abridged-hapoffset',
  'abridged-span',
  'abridged-thirteen-columns',
  'blocks-ends-swapped',
  'blocks-first',
  'blocks-foreign-row',
  'blocks-last',
  'blocks-leading-later',
  'blocks-leading-off',
  'blocks-merged',
  'blocks-moved',
  'blocks-own',
  'blocks-row-dropped',
  'blocks-row-misfiled',
  'blocks-run-zero',
  'blocks-runs-adjacent',
  'blocks-strand',
  'blocks-ten-columns',
  'blocks-trailing-dropped',
  'blocks-trailing-dropped-mid',
  'blocks-trailing-off',
  'blocks-trailing-over-record',
  'blocks-unit-dropped',
  'blocks-unit-empty',
  'dir-tag-header-line',
  'dir-tag-seq-line',
  'format-7',
  'hap-dup',
  'hap-missing',
  'hapstart-wrong-G',
  'hdr-len-idx-only',
  'header-len-100',
  'header-len-right-ctl',
  'hole-bogus',
  'hole-inside',
  'hole-trailing',
  'interior-flipped',
  'last-piece-dropped',
  'missing-overstated',
  'missing-understated',
  'missing-understated-G',
  'node-two-lengths',
  'nodes-bases',
  'nodes-bases-abridged',
  'on-reference-as-interior',
  'on-reference-as-interior-abridged',
  'ownbp-overstated-G',
  'passes-once-as-twice',
  'passes-understated',
  'piece-split-at-jump',
  'piece-walk-and-abridged',
  'point',
  'record-bogus-path',
  'record-dropped',
  'record-leavepasses',
  'record-within-piece',
  'ref-lengths',
  'ref-strand-flipped',
  'reference-wrong',
  'revisited-as-interior',
  'revisited-zero',
  'row-new-kind-in-blocks',
  'row-new-kind-in-departures',
  'row-new-kind-in-detail',
  'row-new-kind-in-tile',
  'sqbad',
  'table-named',
  'tag-entry',
  'tag-malformed',
  'tag-row-walk-underscore',
  'tag-unit-table',
  'tag-unit-tile',
  'walks-differ-ctl',
  'walks-differ-len100',
]
const MOST_FAILURES = 20

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

  async close() {
    await (await this.handle).close()
  }
}

const COLON = /^(.*):([0-9]{1,19})-([0-9]{1,19})$/s
const BRACKET = /^(.*)\[([0-9]{1,19})(?:-([0-9]{1,19}))?\]$/s
const FOURTH = /^([^#]*#[^#]*#[^#]*)#([0-9]{1,19})$/s

// A P line's path and where the line starts on it, from its name and its
// steps' bp, by the three steps of walks-format.md's Path names: from the
// right, a `:a-b` the steps span, a `[s]` or `[s-e]`, a fourth `#` field of
// digits, the starts summed. `refused` says why the tool refuses the line.
function readPathName(written, bp) {
  const colon = COLON.exec(written)
  const cut =
    colon !== null && bp > 0 && Number(colon[3]) - Number(colon[2]) === bp
  const uncut = cut ? colon[1] : written
  const bracket = BRACKET.exec(uncut)
  const whole = bracket === null ? uncut : bracket[1]
  const fourth = FOURTH.exec(whole)
  const name = fourth === null ? whole : fourth[1]
  const fragStart =
    (cut ? Number(colon[2]) : 0) +
    (bracket === null ? 0 : Number(bracket[2])) +
    (fourth === null ? 0 : Number(fourth[2]))
  return bracket !== null &&
    !cut &&
    bracket[3] !== undefined &&
    Number(bracket[3]) - Number(bracket[2]) !== bp
    ? { refused: 'end' }
    : name === ''
      ? { refused: 'empty' }
      : { name, fragStart }
}

const sampleOf = name => name.split('#')[0]
// What `#haplotype` lists a path under: sample#haplotype where its name has
// three fields or more, its sample where it has fewer
const haplotypeOf = name => {
  const fields = name.split('#')
  return fields.length > 2 ? `${fields[0]}#${fields[1]}` : fields[0]
}

// readPathName and haplotypeOf against the table every reader of P line
// names shares
function checkPathNames() {
  const failures = []
  for (const row of readFileSync(P_NAMES, 'utf8').split('\n').slice(1)) {
    if (row !== '') {
      const [written, bp, path, start, under] = row.split('\t')
      const read = readPathName(written, Number(bp))
      const got =
        read.refused === undefined
          ? [read.name, String(read.fragStart), haplotypeOf(read.name)]
          : ['refused', read.refused, '.']
      if (got.join('\t') !== [path, start, under].join('\t')) {
        failures.push(
          `reads P line name ${written} of ${bp} bp as ${got.join(' ')}, p-names.tsv says ${path} ${start} ${under}`,
        )
      }
    }
  }
  return failures
}

function parseGfa(text) {
  const lengths = new Map()
  const bases = new Map()
  const lines = []
  for (const raw of text.split('\n')) {
    const cols = raw.replace(/\r$/, '').split('\t')
    if (cols[0] === 'S') {
      const ln = cols.slice(3).find(tag => tag.startsWith('LN:i:'))
      const id = Number(cols[1])
      lengths.set(id, cols[2] === '*' ? Number(ln?.slice(5)) : cols[2].length)
      if (cols[2] !== '*') {
        bases.set(id, cols[2])
      }
    } else if (cols[0] === 'W') {
      lines.push({
        name: `${cols[1]}#${cols[2]}#${cols[3]}`,
        fragStart: Number(cols[4]),
        steps: [...cols[6].matchAll(/([<>])(\d+)/g)].map(m => ({
          id: Number(m[2]),
          rev: m[1] === '<',
        })),
      })
    } else if (cols[0] === 'P') {
      lines.push({
        written: cols[1],
        steps: cols[2].split(',').map(step => ({
          id: Number(step.slice(0, -1)),
          rev: step.endsWith('-'),
        })),
      })
    }
  }
  const kept = []
  for (const line of lines) {
    const steps = line.steps.filter(step => lengths.get(step.id) > 0)
    if (steps.length > 0) {
      const prefix = [0]
      for (const step of steps) {
        prefix.push(prefix.at(-1) + lengths.get(step.id))
      }
      const read =
        line.written === undefined
          ? line
          : readPathName(line.written, prefix.at(-1))
      if (read.refused !== undefined) {
        throw new Error(
          `P line ${line.written}: the tool refuses its name (${read.refused})`,
        )
      }
      kept.push({
        name: read.name,
        fragStart: read.fragStart,
        steps,
        prefix,
        end: read.fragStart + prefix.at(-1),
      })
    }
  }
  return { lengths, bases, lines: kept }
}

function referenceOf(gfa, listed) {
  const names = new Set(listed)
  const sequences = new Map()
  for (const line of gfa.lines.filter(l => names.has(l.name))) {
    sequences.set(line.name, [...(sequences.get(line.name) ?? []), line])
  }
  const passes = new Map()
  const holes = new Map()
  const lengths = new Map()
  for (const [seq, lines] of sequences) {
    lines.sort((a, b) => a.fragStart - b.fragStart)
    const gaps = []
    let covered = 0
    for (const line of lines) {
      if (line.fragStart > covered) {
        gaps.push({ start: covered, end: line.fragStart })
      }
      covered = line.end
      line.steps.forEach((step, k) => {
        passes.set(step.id, [
          ...(passes.get(step.id) ?? []),
          { seq, offset: line.fragStart + line.prefix[k], rev: step.rev },
        ])
      })
    }
    holes.set(seq, gaps)
    lengths.set(seq, covered)
  }
  const passesOf = id => passes.get(id) ?? []
  const haplotypes = [
    ...new Set(
      gfa.lines
        .filter(
          l =>
            !names.has(l.name) &&
            l.steps.some(step => passesOf(step.id).length > 0),
        )
        .map(l => haplotypeOf(l.name)),
    ),
  ].sort()
  return { names, sequences, passesOf, holes, lengths, haplotypes }
}

const squeezer = holes => bp => {
  let out = bp
  for (const { start, end } of holes) {
    if (end <= bp) {
      out -= end - start
    }
  }
  return out
}

const strand = reversed => (reversed ? '-' : '+')

const departureKey = d =>
  `${d.name} own ${d.hapStart}+${d.ownBp} (${d.missingBp} missing) leaves ${d.leavePos}${strand(d.leaveReversed)} (${d.leavePasses} passes) rejoins ${d.rejoinPos}${strand(d.rejoinReversed)} (${d.rejoinPasses} passes)`

// The departures from S the GFA states, as departureKey strings, for every
// contig that is no reference sequence; with `exact`, between every two
// consecutive steps on S, else only between once-passed ends with no
// reference node between
function departuresOf(gfa, ref, seq, exact) {
  const squeeze = squeezer(ref.holes.get(seq))
  const contigs = new Map()
  for (const line of gfa.lines.filter(l => !ref.names.has(l.name))) {
    contigs.set(line.name, [...(contigs.get(line.name) ?? []), line])
  }
  const out = []
  for (const [name, lines] of contigs) {
    lines.sort((a, b) => a.fragStart - b.fragStart)
    const steps = []
    lines.forEach((line, l) => {
      line.steps.forEach((step, k) => {
        steps.push({
          ...step,
          line: l,
          at: line.fragStart + line.prefix[k],
          end: line.fragStart + line.prefix[k + 1],
        })
      })
    })
    const onSeq = step => ref.passesOf(step.id).some(p => p.seq === seq)
    let previous = -1
    steps.forEach((step, i) => {
      if (onSeq(step)) {
        if (previous >= 0) {
          const a = steps[previous]
          const between = steps.slice(previous + 1, i)
          const certain =
            exact ||
            (ref.passesOf(a.id).length === 1 &&
              ref.passesOf(step.id).length === 1 &&
              between.every(s => ref.passesOf(s.id).length === 0))
          if (certain) {
            const pa = ref.passesOf(a.id).find(p => p.seq === seq)
            const pb = ref.passesOf(step.id).find(p => p.seq === seq)
            const leaveReversed = a.rev !== pa.rev
            const rejoinReversed = step.rev !== pb.rev
            const leavePos = leaveReversed
              ? pa.offset
              : pa.offset + gfa.lengths.get(a.id)
            const rejoinPos = rejoinReversed
              ? pb.offset + gfa.lengths.get(step.id)
              : pb.offset
            const ownBp = step.at - a.end
            let missingBp = 0
            for (let l = a.line + 1; l <= step.line; l++) {
              missingBp += lines[l].fragStart - lines[l - 1].end
            }
            const adjacent =
              ownBp === 0 &&
              leaveReversed === rejoinReversed &&
              squeeze(leavePos) === squeeze(rejoinPos)
            if (!adjacent) {
              out.push(
                departureKey({
                  name,
                  hapStart: a.end,
                  ownBp,
                  missingBp,
                  leavePos,
                  leaveReversed,
                  leavePasses: ref.passesOf(a.id).length,
                  rejoinPos,
                  rejoinReversed,
                  rejoinPasses: ref.passesOf(step.id).length,
                }),
              )
            }
          }
        }
        previous = i
      }
    })
  }
  return out
}

const counted = keys => {
  const counts = new Map()
  for (const key of keys) {
    counts.set(key, (counts.get(key) ?? 0) + 1)
  }
  return counts
}

// A fragment with each run of steps off the reference as its bp, every step
// on it as its place, strand and node
function collapsed(graph, f) {
  const items = []
  let off = -1
  for (let i = 0; i <= f.ids.length; i++) {
    if (i < f.ids.length && Number.isNaN(f.refStarts[i])) {
      const node = graph.nodes.get(f.ids[i])
      off = Math.max(off, 0) + (node ? node.end - node.start : 0)
    } else {
      if (off >= 0) {
        items.push(`off ${off}`)
      }
      off = -1
      if (i < f.ids.length) {
        items.push(
          `${f.refStarts[i]}${f.against[i] === 1 ? '-' : '+'}${f.rev[i] === 1 ? '<' : '>'}${f.ids[i]}`,
        )
      }
    }
  }
  return `fragment ${f.name} at ${f.fragStart}, ${f.hapStart}-${f.hapEnd}, trimmed ${f.trimmedBefore} and ${f.trimmedAfter}: ${items.join(' ')}`
}

// A placeholder on the reference, or beside another step off it
function misplaced(f, isPlaceholder) {
  const offR = k => k >= 0 && k < f.ids.length && Number.isNaN(f.refStarts[k])
  return f.ids.some(
    (id, i) => isPlaceholder(id) && (offR(i - 1) || offR(i + 1) || !offR(i)),
  )
}

const handle = step => `${step.rev ? '<' : '>'}${step.id}`
const earliest = offsets => offsets.reduce((a, b) => Math.min(a, b))
const holeText = h => `${h.start}-${h.end}`

const CUT_OPTIONS = {
  context: 0,
  stepBudget: Infinity,
  byteBudget: Infinity,
  departureByteBudget: Infinity,
  attachBp: Infinity,
  attachFetches: Infinity,
  nodeLimit: Infinity,
  links: false,
  sequences: true,
}

async function checkFile(
  { WalkReader, isPlaceholder },
  walksPath,
  gfaPath,
  wholeSample = false,
) {
  const failures = []
  const fail = text => {
    failures.push(text)
  }
  const gfa = parseGfa(await readFile(gfaPath, 'utf8'))
  const files = {
    data: new LocalFile(walksPath),
    directory: new LocalFile(`${walksPath}.idx`),
  }
  const reader = WalkReader.fromFilehandles(files)
  const counts = {
    sequences: 0,
    fragments: 0,
    steps: 0,
    departures: 0,
    placeholders: 0,
  }
  const differ = (what, unexpanded, expanded) => {
    for (const key of new Set([...unexpanded.keys(), ...expanded.keys()])) {
      const [m, n] = [unexpanded.get(key) ?? 0, expanded.get(key) ?? 0]
      if (m !== n) {
        fail(
          `${what} ${key} came back ${m} times, the expanded cut's ${n} times`,
        )
      }
    }
  }
  try {
    const header = await reader.header()
    const sample = header.references[0]
    const listed = await reader.referenceSequences()
    const ref = referenceOf(gfa, listed)
    const exact = header.revisited === 0
    if (ref.sequences.size === 0) {
      fail('the GFA has no line of a sequence the file lists')
    }
    if (header.haplotypes.join(' ') !== ref.haplotypes.join(' ')) {
      fail(
        `the header lists haplotypes ${header.haplotypes.join(' ')}, the GFA's lines with a step on the file's reference sequences are of ${ref.haplotypes.join(' ')}`,
      )
    }
    for (const seq of listed) {
      if (sampleOf(seq) !== sample) {
        fail(`the file lists ${seq}, which is not of its reference ${sample}`)
      }
      if (!ref.sequences.has(seq)) {
        fail(`the file lists ${seq}, which the GFA has no line of`)
      }
    }
    if (wholeSample) {
      for (const { name } of gfa.lines) {
        if (sampleOf(name) === sample && !ref.names.has(name)) {
          fail(
            `the file lists no sequence ${name}, which ${sample} has lines on`,
          )
        }
      }
    }
    const linesByKey = new Map(
      gfa.lines.map(line => [`${line.name}\t${line.fragStart}`, line]),
    )
    const seen = new Map(gfa.lines.map(line => [line, []]))
    // the line a fragment's name and fragStart name, and the steps of it
    // its hapStart and hapEnd bound
    const locate = f => {
      const line = linesByKey.get(`${f.name}\t${f.fragStart}`)
      const first = line?.prefix.indexOf(f.hapStart - f.fragStart) ?? -1
      const last = (line?.prefix.indexOf(f.hapEnd - f.fragStart) ?? 0) - 1
      return !line
        ? { problem: 'a line the GFA lacks' }
        : first < 0 || last < first
          ? { problem: 'not a run of whole steps of the line' }
          : { line, first, last }
    }
    // step `k` of `line` as fragment `f` holds it at `i`, against the GFA
    const checkStep = (seq, where, f, i, line, k) => {
      const step = line.steps[k]
      const got = { id: f.ids[i], rev: f.rev[i] === 1 }
      const start = f.refStarts[i]
      const against = f.against[i] === 1
      const passes = ref.passesOf(step.id)
      const pass = passes.find(p => p.seq === seq && p.offset === start)
      if (got.id !== step.id || got.rev !== step.rev) {
        fail(`${where}: step ${k} is ${handle(got)}, the GFA's ${handle(step)}`)
      } else if (Number.isNaN(start)) {
        if (exact && passes.length > 0) {
          fail(
            `${where}: step ${k} ${handle(step)} came back off the reference, which passes it at ${passes[0].seq}:${passes[0].offset}`,
          )
        }
      } else if (!pass) {
        fail(
          `${where}: step ${k} ${handle(step)} placed at ${seq}:${start}, where the reference has no pass of it`,
        )
      } else if (against !== (step.rev !== pass.rev)) {
        fail(
          `${where}: step ${k} ${handle(step)} at ${seq}:${start} is ${against ? 'against' : 'along'} the reference, whose pass is ${handle({ id: step.id, rev: pass.rev })}`,
        )
      }
    }
    for (const seq of listed.filter(s => ref.sequences.has(s))) {
      counts.sequences++
      const region = { start: 0, end: ref.lengths.get(seq) }
      const stated = header.holes.filter(h => h.refName === seq)
      const expectedHoles = ref.holes.get(seq)
      if (
        stated.map(holeText).join(' ') !== expectedHoles.map(holeText).join(' ')
      ) {
        fail(
          `${seq}: the header states holes ${stated.map(holeText).join(' ') || 'none'}, the GFA's lines leave ${expectedHoles.map(holeText).join(' ') || 'none'}`,
        )
      }
      const { graph, fragments, departures } = await reader.cut(seq, region, {
        ...CUT_OPTIONS,
        expand: () => true,
      })
      counts.fragments += fragments.length
      counts.departures += departures.length
      for (const f of fragments) {
        const where = `${seq}: ${f.name} at ${f.fragStart}, ${f.hapStart}-${f.hapEnd}`
        const { line, first, last, problem } = locate(f)
        if (problem) {
          fail(`${where}: ${problem}`)
        } else if (f.abridged) {
          fail(`${where}: came back abridged though every walk was expanded`)
        } else if (last - first + 1 !== f.ids.length) {
          fail(
            `${where}: ${f.ids.length} steps where the line has ${last - first + 1}`,
          )
        } else {
          counts.steps += f.ids.length
          for (let k = first; k <= last; k++) {
            seen.get(line).push({ k, seq })
            checkStep(seq, where, f, k - first, line, k)
          }
        }
      }
      const placed = new Set()
      for (const [id, node] of graph.nodes) {
        if (node.rank === 0 && node.refName === seq) {
          placed.add(id)
          const offsets = ref
            .passesOf(id)
            .filter(p => p.seq === seq)
            .map(p => p.offset)
          const where = `${seq}: node ${id} placed at ${node.start}-${node.end} with ${node.passes} passes`
          if (offsets.length === 0) {
            fail(`${where}, which the reference's lines never pass`)
          } else if (node.start !== earliest(offsets)) {
            fail(`${where}, its earliest pass at ${earliest(offsets)}`)
          } else if (node.end - node.start !== gfa.lengths.get(id)) {
            fail(`${where}, its length ${gfa.lengths.get(id)}`)
          } else if (node.passes !== ref.passesOf(id).length) {
            fail(
              `${where}, which the reference passes ${ref.passesOf(id).length} times`,
            )
          }
        }
      }
      for (const line of ref.sequences.get(seq)) {
        for (const step of line.steps) {
          if (exact && !placed.has(step.id)) {
            fail(
              `${seq}: node ${step.id} of the reference's line at ${line.fragStart} is not placed on it`,
            )
          }
        }
      }
      for (const [id, bases] of graph.sequences) {
        if (gfa.bases.has(id) && gfa.bases.get(id) !== bases) {
          fail(
            `${seq}: node ${id}'s bases are ${bases}, the GFA's ${gfa.bases.get(id)}`,
          )
        }
      }
      const expected = counted(departuresOf(gfa, ref, seq, exact))
      const got = counted(departures.map(departureKey))
      for (const [key, n] of expected) {
        const m = got.get(key) ?? 0
        if (m !== n) {
          fail(
            `${seq}: departure ${key} came back ${m} times, the GFA states it${n > 1 ? ` ${n} times` : ''}`,
          )
        }
      }
      if (exact) {
        for (const [key, m] of got) {
          if (!expected.has(key)) {
            fail(
              `${seq}: departure ${key} came back ${m} times, the GFA has none`,
            )
          }
        }
      }
      const plain = await reader.cut(seq, region, CUT_OPTIONS)
      for (const f of plain.fragments) {
        const placeholders = f.ids.filter(isPlaceholder).length
        counts.placeholders += placeholders
        if (placeholders > 0 && misplaced(f, isPlaceholder)) {
          fail(
            `${seq}: ${f.name} at ${f.fragStart}, unexpanded ${f.hapStart}-${f.hapEnd}: a placeholder on the reference or beside another step off it`,
          )
        }
      }
      differ(
        `${seq}: unexpanded`,
        counted(plain.fragments.map(f => collapsed(plain.graph, f))),
        counted(fragments.map(f => collapsed(graph, f))),
      )
      differ(
        `${seq}: unexpanded departure`,
        counted(plain.departures.map(departureKey)),
        got,
      )
    }
    for (const line of gfa.lines) {
      line.steps.forEach((step, k) => {
        const passes = ref.passesOf(step.id)
        const times = seen.get(line).filter(s => s.k === k)
        if (passes.length > 0 && times.length !== 1) {
          const places = times.map(t => t.seq).join(', ')
          fail(
            `${line.name} at ${line.fragStart}: step ${k} ${handle(step)}, on ${passes[0].seq}:${passes[0].offset}, came back ${times.length === 0 ? 'in no fragment' : `${times.length} times (${places})`}`,
          )
        }
      })
    }
  } catch (error) {
    fail(`graph-walks refuses the file: ${error.message}`)
  } finally {
    await Promise.all([files.data.close(), files.directory.close()])
  }
  return {
    failures,
    summary: `${counts.sequences} sequences, ${counts.fragments} fragments, ${counts.steps} steps, ${counts.departures} departures rebuilt; unexpanded, ${counts.placeholders} placeholders`,
  }
}

function report(label, { failures, summary }) {
  if (failures.length === 0) {
    console.log(`${label}: ${summary}`)
  } else {
    for (const text of failures.slice(0, MOST_FAILURES)) {
      console.log(`${label}: ${text}`)
    }
    if (failures.length > MOST_FAILURES) {
      console.log(`${label}: ${failures.length - MOST_FAILURES} more failures`)
    }
  }
  return failures.length === 0
}

async function checkBroken(graphWalks) {
  const cases = new Map(
    (await readFile(join(BROKEN_DIR, 'cases.tsv'), 'utf8'))
      .split('\n')
      .filter(line => line !== '')
      .map(line => line.split('\t'))
      .map(([name, gfa, , what]) => [name, { gfa, what }]),
  )
  let ok = true
  for (const name of BROKEN) {
    const { gfa, what } = cases.get(name)
    const gfaPath = gfa.startsWith('broken/')
      ? join(BROKEN_DIR, '..', gfa)
      : join(DATA, gfa)
    const result = await checkFile(
      graphWalks,
      join(BROKEN_DIR, `${name}.walks.gz`),
      gfaPath,
    )
    if (result.failures.length === 0) {
      console.log(`passes broken/${name} (${what})`)
      ok = false
    } else {
      console.log(`broken/${name} fails: ${result.failures[0]}`)
    }
  }
  return ok
}

async function checkBuilds(graphWalks, binary, builds) {
  const dir = mkdtempSync(join(tmpdir(), 'graph-walks-rebuild-'))
  let ok = true
  try {
    for (const build of builds) {
      const [gfa, refs, ...opts] = build.split(/\s+/)
      const gfaPath = gfa.includes('/') ? resolve(gfa) : join(DATA, gfa)
      const label = `${gfa} ${opts.join(' ')}`
      const run = spawnSync(
        binary,
        [gfaPath, '--walks', '--refs', refs, ...opts, '-o', join(dir, 'o')],
        { encoding: 'utf8' },
      )
      if (run.status !== 0) {
        console.log(`${label}: BUILD ${run.stderr.trim().split('\n').at(-1)}`)
        ok = false
      } else {
        for (const ref of refs.split(',')) {
          const result = await checkFile(
            graphWalks,
            join(dir, `o.${ref}.walks.gz`),
            gfaPath,
            true,
          )
          ok = report(`${label} ${ref}`, result) && ok
        }
      }
    }
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
  return ok
}

const misread = checkPathNames()
if (misread.length > 0) {
  console.error(misread.join('\n'))
  process.exit(1)
}
const [checkout, binary, ...rest] = process.argv.slice(2)
if (checkout === undefined || binary === undefined) {
  console.error(
    'Usage: graph-walks-rebuild.mjs <graph-walks checkout> <gfa-to-tabix binary> ["fixture.gfa refs opts..." ...]\n       graph-walks-rebuild.mjs <graph-walks checkout> --file <walks.gz> <gfa>',
  )
  process.exit(2)
}
const graphWalks = await import(
  pathToFileURL(join(resolve(checkout), 'src/index.ts')).href
)
const results =
  binary === '--file'
    ? [report(rest[0], await checkFile(graphWalks, rest[0], rest[1]))]
    : [
        await checkBroken(graphWalks),
        await checkBuilds(
          graphWalks,
          resolve(binary),
          rest.length > 0 ? rest : [...FIXTURES, ...EXTRA_BUILDS],
        ),
      ]
process.exit(results.every(ok => ok) ? 0 : 1)
