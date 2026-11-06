// node scripts/bandage-figure.mjs GFA_TO_TABIX GRAPH_WALKS BANDAGE_CORE
//
// For each figure below: builds the walk file of docs/figures/<name>.gfa with
// GFA_TO_TABIX, cuts the region through graph-walks' WalkReader, and writes
// the cut as docs/figures/<name>-cut.gfa and as bandage-core draws it,
// docs/figures/<name>-bandage.svg, whose metadata keeps the options and the
// region. scripts/figures.py reads them there, builds the walk file again,
// checks the cut against it and puts the drawing in the figure.
// GRAPH_WALKS is a graph-walks checkout with its node_modules installed, whose
// TypeScript source Node imports directly; BANDAGE_CORE a bandage-core
// checkout with dist built.
import { execFileSync } from 'node:child_process'
import { mkdtemp, rm, writeFile } from 'node:fs/promises'
import { createRequire } from 'node:module'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const FIGURES = [
  {
    name: 'walks-simple',
    args: ['--walks', '--refs', 'GRCh38'],
    region: { refName: 'chr1', start: 0, end: 60 },
  },
  {
    name: 'walks-leave',
    args: ['--walks', '--refs', 'GRCh38', '--tile', '30'],
    region: { refName: 'chr1', start: 0, end: 60 },
  },
]

const [binary, graphWalks, bandageCore] = process.argv.slice(2)
if (!bandageCore) {
  console.error(
    'usage: node scripts/bandage-figure.mjs GFA_TO_TABIX GRAPH_WALKS BANDAGE_CORE',
  )
  process.exit(2)
}
const figures = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  '..',
  'docs',
  'figures',
)
const load = file => import(pathToFileURL(path.join(bandageCore, file)).href)
const { LocalFile } = createRequire(path.join(graphWalks, 'package.json'))(
  'generic-filehandle2',
)
const { WalkReader } = await import(
  pathToFileURL(path.join(graphWalks, 'src', 'index.ts')).href
)
const { graphFromTables, graphTablesGFA } = await load('dist/index.js')
const { figureSvg } = await load('dist/figure.js')
const { layoutModeByValue } = await load('dist/layoutModes.js')

const tmp = await mkdtemp(path.join(tmpdir(), 'bandage-figure-'))
try {
  for (const { name, args, region } of FIGURES) {
    const prefix = path.join(tmp, name)
    execFileSync(binary, [path.join(figures, `${name}.gfa`), ...args, '-o', prefix], {
      stdio: 'ignore',
    })
    const reader = WalkReader.fromFilehandles({
      data: new LocalFile(`${prefix}.GRCh38.walks.gz`),
      directory: new LocalFile(`${prefix}.GRCh38.walks.gz.idx`),
    })
    const { tables, refName } = await reader.cutRegion(region)
    const graph = graphFromTables(tables, name)
    const cut = { ...region, refName }
    const svg = figureSvg(graph, layoutModeByValue('ordered').run(graph, cut), {
      region: cut,
      width: 640,
      walks: tables.walks.names.map(walk => ({ walk })),
      facet: 'walk',
      spec: { options: args, region },
    })
    await writeFile(path.join(figures, `${name}-cut.gfa`), `${graphTablesGFA(tables)}\n`)
    await writeFile(path.join(figures, `${name}-bandage.svg`), svg)
  }
} finally {
  await rm(tmp, { recursive: true })
}
