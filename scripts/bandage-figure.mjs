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
//
// bandage-core draws one picture of the cut with every walk lifted, each in
// one colour, and its key says each walk's bp against the reference. Its
// figure has no option that names the nodes, so this script writes each
// node's name over it, at the middle of the node as bandage-core's own fit
// places it.
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
const WIDTH = 640
const LABEL = 'font-family="Helvetica, Arial, sans-serif" font-size="12" font-weight="bold" text-anchor="middle" fill="#1f2328"'

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
const { graphFromTables, graphTablesGFA, drawingBounds, fitTransform, axisScaleOf } =
  await load('dist/index.js')
const { figureSvg } = await load('dist/figure.js')
const { layoutModeByValue } = await load('dist/layoutModes.js')

// Each node's name at its middle, above a node on the reference row and
// below one off it, in the drawing's own pixels: the fit figureSvg made for
// its one panel, read back from that panel's frame. The figure is then cut
// to what is drawn, since figureSvg gives a panel 160 px however little it
// holds and centres the drawing in it.
function nodeNames(svg, graph, layout, region) {
  const frame = svg.match(/<svg y="(\d+)" width="\d+" height="(\d+)">/)
  const fit = fitTransform(
    drawingBounds(layout, { region }),
    WIDTH,
    Number(frame[2]),
    layout.pixelRows ?? false,
  )
  const axis = axisScaleOf(fit.scale, layout.pixelRows ?? false)
  const gap = Math.max(0, Math.floor(fit.translateY - 30))
  let bottom = 0
  const names = graph.nodes.map(node => {
    const mid = midpoint(layout.nodePositions[node.id])
    const x = mid.x * axis.scaleX + fit.translateX
    const y = mid.y * axis.scaleY + fit.translateY + Number(frame[1]) - gap
    const below = mid.y > 0
    bottom = Math.max(bottom, y + (below ? 30 : 14))
    return `<text x="${x.toFixed(1)}" y="${(below ? y + 18 : y - 12).toFixed(1)}" ${LABEL}>${node.name}</text>`
  })
  const height = Math.ceil(bottom)
  return svg
    .replace(/^<svg ([^>]*) height="\d+" viewBox="0 0 (\d+) \d+">/, `<svg $1 height="${height}" viewBox="0 0 $2 ${height}">`)
    .replace(frame[0], `<svg y="${frame[1]}" width="${WIDTH}" height="${Number(frame[2]) - gap}" viewBox="0 ${gap} ${WIDTH} ${Number(frame[2]) - gap}">`)
    .replace(/<\/svg>\n?$/, `${names.join('')}</svg>\n`)
}

// the point half way along a polyline
function midpoint(points) {
  const spans = points.slice(1).map((p, i) => Math.hypot(p.x - points[i].x, p.y - points[i].y))
  let left = spans.reduce((a, b) => a + b, 0) / 2
  for (let i = 0; i < spans.length; i++) {
    if (left <= spans[i]) {
      const t = spans[i] > 0 ? left / spans[i] : 0
      return {
        x: points[i].x + (points[i + 1].x - points[i].x) * t,
        y: points[i].y + (points[i + 1].y - points[i].y) * t,
      }
    }
    left -= spans[i]
  }
  return points[0]
}

// Every node lies on a lifted walk, so nothing is faded and the key for what
// a lift fades names nothing
function withoutFadedKey(svg) {
  return svg.replace(/<g transform="translate\([\d.]+ [\d.]+\)" [^>]*><rect[^>]*fill-opacity="0.3"\/><text[^>]*><tspan font-weight="bold"><\/tspan>only in other haplotypes<\/text><\/g>/, '')
}

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
    const graph = { ...graphFromTables(tables, name), referencePath: refName }
    const cut = { ...region, refName }
    const layout = layoutModeByValue('ordered').run(graph, cut)
    const svg = figureSvg(graph, layout, {
      region: cut,
      width: WIDTH,
      walks: tables.walks.names.map(walk => ({ walk })),
      spec: { options: args, region },
    })
    await writeFile(path.join(figures, `${name}-cut.gfa`), `${graphTablesGFA(tables)}\n`)
    await writeFile(path.join(figures, `${name}-bandage.svg`), nodeNames(withoutFadedKey(svg), graph, layout, cut))
  }
} finally {
  await rm(tmp, { recursive: true })
}
