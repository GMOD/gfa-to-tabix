// serve.mjs PORT PREFIX=DIR...: a static server answering range requests with CORS, as S3 does, each url prefix
// mapped to a directory; PREFIX may be empty for the root
import { createReadStream, statSync } from 'node:fs'
import { createServer } from 'node:http'
import { extname, join, normalize } from 'node:path'

const [port, ...mounts] = process.argv.slice(2)
const roots = mounts
  .map(m => m.split('='))
  .map(([prefix, dir]) => ({ prefix: `/${prefix}`.replace(/\/?$/, '/'), dir }))
  .sort((a, b) => b.prefix.length - a.prefix.length)
const TYPES = {
  '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css',
  '.json': 'application/json', '.wasm': 'application/wasm', '.svg': 'image/svg+xml', '.png': 'image/png',
  '.ico': 'image/x-icon', '.map': 'application/json',
}

createServer((req, res) => {
  const path = decodeURIComponent(new URL(req.url, 'http://x').pathname)
  const root = roots.find(r => path.startsWith(r.prefix))
  let file = root && join(root.dir, normalize(path.slice(root.prefix.length)))
  let stat
  try {
    stat = file && statSync(file)
    if (stat?.isDirectory()) {
      file = join(file, 'index.html')
      stat = statSync(file)
    }
  } catch {
    stat = undefined
  }
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Access-Control-Allow-Headers', 'Range')
  res.setHeader('Access-Control-Expose-Headers', 'Content-Length, Content-Range, Accept-Ranges')
  res.setHeader('Accept-Ranges', 'bytes')
  res.setHeader('Cache-Control', 'no-store')
  if (req.method === 'OPTIONS') {
    res.writeHead(204).end()
  } else if (!stat) {
    res.writeHead(404).end('not found')
  } else {
    res.setHeader('Content-Type', TYPES[extname(file)] ?? 'application/octet-stream')
    const range = /^bytes=(\d*)-(\d*)$/.exec(req.headers.range ?? '')
    if (range) {
      const start = range[1] === '' ? Math.max(0, stat.size - Number(range[2])) : Number(range[1])
      const end = range[1] !== '' && range[2] !== '' ? Math.min(Number(range[2]), stat.size - 1) : stat.size - 1
      res.writeHead(206, { 'Content-Range': `bytes ${start}-${end}/${stat.size}`, 'Content-Length': end - start + 1 })
      req.method === 'HEAD' ? res.end() : createReadStream(file, { start, end }).pipe(res)
    } else {
      res.writeHead(200, { 'Content-Length': stat.size })
      req.method === 'HEAD' ? res.end() : createReadStream(file).pipe(res)
    }
  }
}).listen(Number(port), '127.0.0.1', () => console.log(`serving on ${port}`))
