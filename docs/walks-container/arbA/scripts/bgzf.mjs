import fs from 'node:fs'
import zlib from 'node:zlib'

const MAX = 0xff00
const EOF = Buffer.from('1f8b08040000000000ff0600424302001b0003000000000000000000', 'hex')

// A BGZF writer whose caller can end a block early, so a run of rows starts
// on a block boundary. `offset` is the compressed offset of the next block.
export class BgzfWriter {
  constructor(path) {
    this.fd = fs.openSync(path, 'w')
    this.parts = []
    this.size = 0
    this.offset = 0
  }
  write(text) {
    let buf = Buffer.from(text)
    while (buf.length > 0) {
      const room = MAX - this.size
      const take = buf.subarray(0, room)
      this.parts.push(take)
      this.size += take.length
      buf = buf.subarray(take.length)
      if (this.size === MAX) this.flush()
    }
  }
  flush() {
    if (this.size === 0) return
    const data = Buffer.concat(this.parts)
    this.parts = []
    this.size = 0
    const deflated = zlib.deflateRawSync(data, { level: 6 })
    const header = Buffer.from('1f8b08040000000000ff060042430200', 'hex')
    const block = Buffer.alloc(18 + deflated.length + 8)
    header.copy(block, 0)
    block.writeUInt16LE(block.length - 1, 16)
    deflated.copy(block, 18)
    block.writeUInt32LE(zlib.crc32(data), 18 + deflated.length)
    block.writeUInt32LE(data.length, 22 + deflated.length)
    fs.writeSync(this.fd, block)
    this.offset += block.length
  }
  close() {
    this.flush()
    fs.writeSync(this.fd, EOF)
    fs.closeSync(this.fd)
  }
}
