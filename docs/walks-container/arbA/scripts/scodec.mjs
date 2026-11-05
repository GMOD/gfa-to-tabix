// S rows: a walk piece as a GAF-style path of reference intervals and
// off-reference nodes. `abs`: absolute coordinates and node ids. `rel`:
// intervals relative to the tile start, node ids as deltas within the line.

export class Ref {
  constructor() {
    this.ids = []
    this.rev = []
    this.starts = []
    this.lengths = []
    this.at = new Map()
  }
  add(ids, rev, lengths, start) {
    for (let k = 0; k < ids.length; k++) {
      const i = this.ids.length
      this.ids.push(ids[k])
      this.rev.push(rev[k])
      this.starts.push(start)
      this.lengths.push(lengths[k])
      const list = this.at.get(start)
      if (list) list.push(i)
      else this.at.set(start, [i])
      start += lengths[k]
    }
  }
  index(start, id) {
    const list = this.at.get(start)
    if (!list) throw new Error(`no R node at ${start}`)
    for (const i of list) if (this.ids[i] === id) return i
    throw new Error(`no R node ${id} at ${start}`)
  }
  firstAt(start) {
    const list = this.at.get(start)
    if (!list) throw new Error(`no R node starts at ${start}`)
    return list[0]
  }
}

const sign = r => (r ? '<' : '>')

// steps: {ids, rev, refStarts, against}
export function encodeWalk(steps, ref, mode, cs) {
  const n = steps.ids.length
  const out = []
  let prevId = 0
  let k = 0
  let lo = Infinity
  let hi = -Infinity
  while (k < n) {
    const r = steps.refStarts[k]
    if (Number.isFinite(r)) {
      const back = steps.against[k] === 1
      const i0 = ref.index(r, steps.ids[k])
      let i = i0
      let j = k + 1
      while (j < n && Number.isFinite(steps.refStarts[j]) && (steps.against[j] === 1) === back) {
        const next = back ? i - 1 : i + 1
        if (next < 0 || next >= ref.ids.length || ref.ids[next] !== steps.ids[j] || ref.starts[next] !== steps.refStarts[j]) break
        i = next
        j++
      }
      const a = Math.min(ref.starts[i0], ref.starts[i])
      const lastI = Math.max(i0, i)
      const firstI = Math.min(i0, i)
      const b = ref.starts[lastI] + ref.lengths[lastI]
      // a block's bp interval names its R positions only when no 0 bp node
      // sits at its ends
      if (ref.lengths[firstI] === 0 || ref.lengths[lastI] === 0) throw new Error('0 bp node at a block end')
      if (ref.firstAt(ref.starts[firstI]) !== firstI) throw new Error('ambiguous block start')
      lo = Math.min(lo, a)
      hi = Math.max(hi, b)
      const off = mode === 'abs' ? 0 : cs
      out.push(`${back ? '<' : '>'}${a - off}-${b - off}`)
      k = j
    } else {
      const id = steps.ids[k]
      if (mode === 'abs') out.push(`${sign(steps.rev[k])}${id}`)
      else {
        const d = id - prevId
        out.push(`${sign(steps.rev[k])}${d >= 0 ? '+' : ''}${d}`)
        prevId = id
      }
      k++
    }
  }
  return { walk: out.join(''), lo, hi }
}

const TOKEN = /([<>])([+-]?\d+)(?:-(\d+))?/g

export function decodeWalk(walk, ref, mode, cs) {
  const ids = []
  const rev = []
  const refStarts = []
  const against = []
  let prevId = 0
  const off = mode === 'abs' ? 0 : cs
  for (const m of walk.matchAll(TOKEN)) {
    const back = m[1] === '<'
    if (m[3] !== undefined) {
      const a = +m[2] + off
      const b = +m[3] + off
      let i = ref.firstAt(a)
      const run = []
      for (;;) {
        run.push(i)
        if (ref.starts[i] + ref.lengths[i] === b) break
        i++
        if (i >= ref.ids.length || ref.starts[i] >= b) throw new Error(`interval ${a}-${b} does not end on a node`)
      }
      if (back) run.reverse()
      for (const p of run) {
        ids.push(ref.ids[p])
        rev.push(back ? 1 - ref.rev[p] : ref.rev[p])
        refStarts.push(ref.starts[p])
        against.push(back ? 1 : 0)
      }
    } else {
      let id = +m[2]
      if (mode !== 'abs') {
        id += prevId
        prevId = id
      }
      ids.push(id)
      rev.push(back ? 1 : 0)
      refStarts.push(NaN)
      against.push(0)
    }
  }
  return { ids, rev, refStarts, against }
}

export function encodeIds(ids, rev, mode) {
  if (mode === 'abs') return ids.map((id, k) => `${sign(rev[k])}${id}`).join('')
  let prev = 0
  return ids
    .map((id, k) => {
      const d = 2 * (id - prev) + rev[k]
      prev = id
      return d
    })
    .join(',')
}

export function decodeIds(field, mode) {
  const ids = []
  const rev = []
  if (mode === 'abs') {
    for (const m of field.matchAll(/([<>])(\d+)/g)) {
      ids.push(+m[2])
      rev.push(m[1] === '<' ? 1 : 0)
    }
  } else {
    let prev = 0
    for (const t of field.split(',')) {
      const d = +t
      const r = d & 1
      prev += (d - r) / 2
      ids.push(prev)
      rev.push(r)
    }
  }
  return { ids, rev }
}
