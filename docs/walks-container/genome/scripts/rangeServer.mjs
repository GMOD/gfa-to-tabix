import fs from 'node:fs'
import http from 'node:http'
import path from 'node:path'

export async function rangeServer(root) {
  const log = []
  const server = http.createServer((req, res) => {
    const file = path.join(root, decodeURIComponent(req.url.slice(1)))
    const size = fs.existsSync(file) ? fs.statSync(file).size : -1
    if (size < 0) {
      res.writeHead(404)
      res.end()
    } else {
      const m = /bytes=(\d+)-(\d*)/.exec(req.headers.range ?? '')
      const start = m ? +m[1] : 0
      const end = m && m[2] !== '' ? Math.min(+m[2], size - 1) : size - 1
      const buf = Buffer.alloc(Math.max(0, end - start + 1))
      const fd = fs.openSync(file, 'r')
      fs.readSync(fd, buf, 0, buf.length, start)
      fs.closeSync(fd)
      log.push({ file: req.url, start, end, bytes: buf.length })
      res.writeHead(m ? 206 : 200, {
        'content-length': buf.length,
        'content-range': `bytes ${start}-${end}/${size}`,
        'accept-ranges': 'bytes',
      })
      res.end(buf)
    }
  })
  server.keepAliveTimeout = 3_600_000
  await new Promise(r => server.listen(0, '127.0.0.1', r))
  const timeline = []
  const timedFetch = async (url, opts) => {
    const t0 = performance.now()
    const r = await fetch(url, opts)
    const buf = await r.arrayBuffer()
    timeline.push({ t0, t1: performance.now() })
    return new Response(buf, { status: r.status, headers: r.headers })
  }
  const mark = () => ({ log: log.length, timeline: timeline.length })
  const since = from => {
    const reqs = log.slice(from.log)
    const byFile = {}
    for (const r of reqs) byFile[r.file] = (byFile[r.file] ?? 0) + r.bytes
    return {
      requests: reqs.length,
      bytes: reqs.reduce((s, r) => s + r.bytes, 0),
      trips: roundTrips(timeline.slice(from.timeline)),
      byFile,
    }
  }
  return { base: `http://127.0.0.1:${server.address().port}/`, timedFetch, mark, since, close: () => server.close() }
}

export function roundTrips(tl) {
  const s = [...tl].sort((a, b) => a.t0 - b.t0)
  const d = s.map(() => 1)
  for (let j = 0; j < s.length; j++) for (let i = 0; i < j; i++) if (s[i].t1 <= s[j].t0) d[j] = Math.max(d[j], d[i] + 1)
  return Math.max(0, ...d)
}
