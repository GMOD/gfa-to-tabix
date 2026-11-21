// measure.mjs READER URL TIMEOUT_S: one run of one reader on one window. Launches headless Chrome, opens URL, waits
// until the reader has laid the graph out and drawn it, then zooms and pans once. Prints one JSON object.
//   READER bjs: BandageJS built with the nc:* performance marks (cut, graph, layout, geometry, draw)
//   READER plugin: a GraphGenomeView in jbrowse-web, timed from the graph-stats element's data-* attributes
// Times are ms since navigation start on the page's clock. Memory is the main thread's JS heap from CDP and the peak
// resident size (VmHWM) of the renderer process, which holds the page, its workers and their wasm.
import { readFileSync, readdirSync } from 'node:fs'
import { createRequire } from 'node:module'

const [reader, url, timeoutS] = process.argv.slice(2)
const puppeteer = createRequire(`${process.env.PUPPETEER_DIR}/`)('puppeteer')
const timeout = Number(timeoutS) * 1000
const WIDTH = 1400
const HEIGHT = 1000

function procTree(root) {
  const parents = new Map()
  for (const pid of readdirSync('/proc').filter(p => /^\d+$/.test(p))) {
    try {
      const stat = readFileSync(`/proc/${pid}/stat`, 'utf8')
      parents.set(Number(pid), Number(stat.slice(stat.lastIndexOf(')') + 2).split(' ')[1]))
    } catch {}
  }
  const tree = new Set([root])
  let grew = true
  while (grew) {
    grew = false
    for (const [pid, ppid] of parents) {
      if (tree.has(ppid) && !tree.has(pid)) {
        tree.add(pid)
        grew = true
      }
    }
  }
  return [...tree]
}

function peakMb(root, type) {
  const peaks = procTree(root).flatMap(pid => {
    try {
      const cmd = readFileSync(`/proc/${pid}/cmdline`, 'utf8')
      const hwm = /VmHWM:\s+(\d+) kB/.exec(readFileSync(`/proc/${pid}/status`, 'utf8'))
      return cmd.includes(`--type=${type}`) && hwm ? [Number(hwm[1]) / 1024] : []
    } catch {
      return []
    }
  })
  return peaks.length ? Math.round(Math.max(...peaks)) : undefined
}

// Both readers' clones mark nc:cut-start/-end around the cut, nc:layout-start/-end around the layout (the end's detail
// carries the engine's own ms), nc:geometry-end after the geometry is built and nc:draw after each paint of the canvas;
// a paint is timed two frames after its nc:draw mark
function markTimings() {
  const at = name => performance.getEntriesByName(name).at(-1)?.startTime
  const layoutEnd = performance.getEntriesByName('nc:layout-end').at(-1)
  const after = name => performance.getEntriesByName(name).find(m => m.startTime >= layoutEnd.startTime)?.startTime
  const drawn = after('nc:draw')
  return {
    cut_start: at('nc:cut-start'),
    cut_end: at('nc:cut-end'),
    graph_at: at('nc:graph'),
    layout_start: at('nc:layout-start'),
    layout_end: layoutEnd.startTime,
    drawn_mode: layoutEnd.detail?.mode,
    layout_engine_ms: layoutEnd.detail?.ms,
    geometry_end: after('nc:geometry-end'),
    draw_end: drawn,
    painted: window.__paints.find(([mark]) => mark >= drawn)?.[1],
    marks: performance
      .getEntriesByType('mark')
      .filter(m => m.name !== 'nc:draw' || m.startTime >= layoutEnd.startTime)
      .slice(0, 40)
      .map(m => [m.name.replace('nc:', ''), Math.round(m.startTime)]),
  }
}
function drawnAfterLayout() {
  const end = performance.getEntriesByName('nc:layout-end').at(-1)
  return !!end && window.__paints.some(([mark]) => mark >= end.startTime)
}

const READERS = {
  bjs: {
    ready: () => {
      const toast = document.getElementById('toast')
      const error = toast && !toast.hidden && /fail|error|too large|cannot|refus/i.test(toast.textContent) ? toast.textContent : undefined
      return error ? { error } : window.__drawnAfterLayout() ? { ok: true } : false
    },
    timings: () => {
      const stats = document.getElementById('stats')
      const n = re => Number((re.exec(stats.textContent)?.[1] ?? '').replace(/,/g, ''))
      return {
        ...window.__markTimings(),
        nodes: n(/([\d,]+) nodes/),
        links: n(/([\d,]+) edges/),
        drawn_label: stats.textContent.split(' · ').at(-1),
      }
    },
    canvas: '#pane',
  },
  plugin: {
    ready: () => {
      const retry = document.querySelector('[data-testid="graph-genome-retry"]')
      const shown = /Graph too large to draw[^\n]*|RuntimeError[^\n]*|Layout failed[^\n]*/.exec(document.body.innerText)
      const error = retry ? retry.closest('div')?.parentElement?.innerText : shown?.[0]
      const ok =
        window.__drawnAfterLayout() &&
        document.querySelector('[data-testid="app-ready-marker"]')?.getAttribute('data-app-phase') === 'ready'
      return error ? { error } : ok ? { ok: true } : false
    },
    timings: () => {
      const s = document.querySelector('[data-testid="graph-stats"]')
      const a = name => (s.getAttribute(name) === '' ? undefined : Number(s.getAttribute(name)))
      return {
        ...window.__markTimings(),
        nodes: a('data-node-count'),
        links: a('data-edge-count'),
        fetch_ms: a('data-fetch-ms'),
        geometry_ms: a('data-geometry-ms'),
        geometry_strokes: a('data-geometry-strokes'),
      }
    },
    canvas: '[data-testid="graph-genome-canvas"]',
  },
}
const r = READERS[reader]

const browser = await puppeteer.launch({
  executablePath: process.env.CHROME,
  headless: true,
  protocolTimeout: timeout + 120_000,
  args: ['--no-sandbox', '--enable-unsafe-swiftshader', '--enable-precise-memory-info', `--window-size=${WIDTH},${HEIGHT}`],
})
const chromePid = browser.process().pid
const out = { reader, url, status: 'ok', chrome: await browser.version() }
const page = await browser.newPage()
let crashed = false
const crash = new Promise((_, reject) => {
  page.on('error', e => {
    crashed = true
    reject(new Error(`page crashed: ${e}`))
  })
})
crash.catch(() => {})
const guard = p => Promise.race([p, crash])
page.on('pageerror', e => {
  out.pageerrors = [...(out.pageerrors ?? []), String(e).slice(0, 300)]
})
await page.setViewport({ width: WIDTH, height: HEIGHT })
await page.evaluateOnNewDocument(
  (timings, drawn) => {
    window.__markTimings = new Function(`return (${timings})()`)
    window.__drawnAfterLayout = new Function(`return (${drawn})()`)
  },
  markTimings.toString(),
  drawnAfterLayout.toString(),
)
await page.evaluateOnNewDocument(() => {
  localStorage.setItem('bandagejs-hint-dismissed', 'true')
  window.__paints = []
  new PerformanceObserver(list => {
    for (const e of list.getEntries()) {
      if (e.name === 'nc:draw') {
        requestAnimationFrame(() => requestAnimationFrame(() => window.__paints.push([e.startTime, performance.now()])))
      }
    }
  }).observe({ type: 'mark' })
  window.__longtasks = []
  new PerformanceObserver(list => {
    for (const e of list.getEntries()) {
      window.__longtasks.push([e.startTime, e.duration])
    }
  }).observe({ type: 'longtask', buffered: true })
})
const cdp = await page.createCDPSession()
await cdp.send('Performance.enable')

const sleep = ms => new Promise(res => setTimeout(res, ms))
const nextFrame = () => page.evaluate(() => new Promise(res => requestAnimationFrame(() => requestAnimationFrame(() => res(performance.now())))))

// the longest main-thread task in [from, to), and when the last one starting after `from` ended
const longtasks = (from, to = Infinity) =>
  page.evaluate(
    (f, t) => {
      const tasks = window.__longtasks.filter(([s]) => s >= f && s < t)
      return { max: Math.max(0, ...tasks.map(([, d]) => d)), lastEnd: Math.max(0, ...tasks.map(([s, d]) => s + d)) }
    },
    from,
    to,
  )

async function interact(kind) {
  const box = await (await page.$(r.canvas)).boundingBox()
  // over the drawing but off the nodes of a force layout, which lies along the middle: a pointer over a node
  // hovers it, and the zoom should time the redraw alone
  const cx = box.x + box.width * 0.4
  const cy = box.y + 12
  await page.mouse.move(cx, cy)
  await sleep(300)
  if (kind === 'pan') {
    await page.mouse.down()
    await page.mouse.move(cx + 100, cy + 10, { steps: 3 })
  }
  const paints = await page.evaluate(() => window.__paints.length)
  const t = await page.evaluate(() => performance.now())
  if (kind === 'zoom') {
    await page.mouse.wheel({ deltaY: -300 })
  } else {
    await page.mouse.move(cx + 160, cy + 20)
    await page.mouse.up()
  }
  const frame = await nextFrame()
  let settled = frame
  const deadline = Date.now() + 120_000
  for (;;) {
    const { lastEnd } = await longtasks(t)
    const now = await page.evaluate(() => performance.now())
    settled = Math.max(frame, lastEnd)
    if (now - settled > 1000 || Date.now() > deadline) {
      break
    }
    await sleep(250)
  }
  const repaint = await page.evaluate((n, from) => window.__paints.slice(n).find(([mark]) => mark >= from)?.[1], paints, t)
  return {
    [`${kind}_frame_ms`]: Math.round(frame - t),
    [`${kind}_repaint_ms`]: repaint === undefined ? undefined : Math.round(repaint - t),
    [`${kind}_settle_ms`]: Math.round(settled - t),
  }
}

let phase = 'load'
const began = Date.now()
try {
  await guard(page.goto(url, { waitUntil: 'domcontentloaded', timeout: 120_000 }))
  const handle = await guard(page.waitForFunction(r.ready, { timeout, polling: 500 }))
  const state = await handle.jsonValue()
  if (state.error) {
    out.status = 'error'
    out.error = state.error.slice(0, 400)
  } else {
    Object.assign(out, await guard(page.evaluate(r.timings)))
    const lt = await guard(longtasks(0, out.painted ?? Infinity))
    out.main_block_max_ms = Math.round(lt.max)
    const { metrics } = await guard(cdp.send('Performance.getMetrics'))
    const metric = name => Math.round(metrics.find(m => m.name === name).value / 1e6)
    out.js_heap_mb = metric('JSHeapUsedSize')
    // read before the zoom and pan, which can crash the renderer and leave a fresh one to read
    out.renderer_paint_peak_mb = peakMb(chromePid, 'renderer')
    phase = 'zoom'
    Object.assign(out, await guard(interact('zoom')))
    phase = 'pan'
    Object.assign(out, await guard(interact('pan')))
    phase = 'done'
    out.interaction = 'ok'
  }
} catch (e) {
  const outcome = crashed ? 'crash' : /Waiting failed|timeout/i.test(String(e)) ? 'timeout' : 'fail'
  // a reader that drew and then failed on a zoom or pan keeps its draw's numbers; the interaction says what failed
  out.status = phase === 'load' ? outcome : 'ok'
  out.interaction = `${outcome} during ${phase}`
  out.error = String(e).slice(0, 400)
  out.screen = crashed ? undefined : await Promise.race([
    page.evaluate(() => document.body.innerText.replace(/\s+/g, ' ').slice(0, 600)).catch(() => undefined),
    sleep(20_000),
  ])
}
out.wall_ms = Date.now() - began
out.renderer_peak_mb = peakMb(chromePid, 'renderer')
out.gpu_peak_mb = peakMb(chromePid, 'gpu-process')
console.log(JSON.stringify(out))
await browser.close().catch(() => {})
process.exit(0)
