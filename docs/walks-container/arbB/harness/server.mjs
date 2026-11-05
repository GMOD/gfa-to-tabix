// Static file server with HTTP range support that logs every request it
// serves: path, the byte range, the bytes sent, and when it started and
// finished. GET /__reads returns the log since the last call and clears it.
//
// usage: node server.mjs ROOT PORT [DELAY_MS]
import http from 'node:http'
import fs from 'node:fs'
import path from 'node:path'

const [root, portArg, delayArg] = process.argv.slice(2)
const port = +(portArg ?? 8765)
const delay = +(delayArg ?? 5)
let log = []
let seq = 0

http
  .createServer((req, res) => {
    const url = new URL(req.url, 'http://localhost')
    if (url.pathname === '/__reads') {
      const out = log
      log = []
      res.setHeader('content-type', 'application/json')
      res.end(JSON.stringify(out))
      return
    }
    const rel = decodeURIComponent(url.pathname).replace(/^\/+/, '')
    const file = path.join(root, rel)
    let size
    try {
      size = fs.statSync(file).size
    } catch {
      res.writeHead(404)
      res.end()
      return
    }
    const t0 = performance.now()
    const id = seq++
    const range = req.headers.range
    let start = 0
    let end = size - 1
    let status = 200
    if (range) {
      const m = /^bytes=(\d*)-(\d*)$/.exec(range)
      if (!m) {
        res.writeHead(416)
        res.end()
        return
      }
      if (m[1] === '') {
        start = Math.max(0, size - +m[2])
      } else {
        start = +m[1]
        end = m[2] === '' ? size - 1 : Math.min(+m[2], size - 1)
      }
      if (start >= size) {
        res.writeHead(416, { 'content-range': `bytes */${size}` })
        res.end()
        return
      }
      status = 206
    }
    const length = end - start + 1
    const send = () => {
      const headers = {
        'content-type': 'application/octet-stream',
        'content-length': String(length),
        'accept-ranges': 'bytes',
      }
      if (status === 206) {
        headers['content-range'] = `bytes ${start}-${end}/${size}`
      }
      res.writeHead(status, headers)
      if (req.method === 'HEAD') {
        res.end()
      } else {
        const fd = fs.openSync(file, 'r')
        const buf = Buffer.alloc(length)
        fs.readSync(fd, buf, 0, length, start)
        fs.closeSync(fd)
        res.end(buf)
      }
      log.push({
        id,
        file: rel,
        start,
        end: end + 1,
        bytes: req.method === 'HEAD' ? 0 : length,
        status,
        t0,
        t1: performance.now(),
      })
    }
    setTimeout(send, delay)
  })
  .listen(port, '127.0.0.1', () => {
    process.stdout.write(`ready ${port}\n`)
  })
