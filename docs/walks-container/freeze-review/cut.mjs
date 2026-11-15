// usage: node cut.mjs <walks.gz> <refName> <start> <end> [context] [expand]
import { LocalFile } from '/home/cdiesh/src/graph-walks/node_modules/generic-filehandle2/esm/index.js'
import { WalkReader } from '/home/cdiesh/src/graph-walks/src/index.ts'
const [file, refName, start, end, context = '0', expand = 'yes'] = process.argv.slice(2)
const reader = WalkReader.open(file, url => new LocalFile(url))
console.log('header', JSON.stringify(await reader.header()))
const cut = await reader.cut(refName, { start: +start, end: +end }, {
  context: +context,
  expand: expand === 'yes' ? () => true : undefined,
  stepBudget: Infinity, byteBudget: Infinity, departureByteBudget: Infinity,
})
const { graph, kept, fragments, departures } = cut
const t = graph.tables(kept, fragments, departures)
console.log('nodes keys', Object.keys(t.nodes)); const names = t.nodes.names ?? t.nodes.name; console.log('nodes', JSON.stringify(names));
console.log('linksNamed', Array.from(t.links.from).map((f,i)=>`${names[f]}${t.links.strands[i]&1?'-':'+'}>${names[t.links.to[i]]}${t.links.strands[i]&2?'-':'+'}`).join(' '))
console.log('tables keys', Object.keys(t), 'links keys', Object.keys(t.links))
console.log('links', JSON.stringify(t.links, (k, v) => ArrayBuffer.isView(v) ? Array.from(v) : v))
for (const f of fragments) {
  console.log('fragment', f.name, f.hapStart, f.hapEnd, 'ids', Array.from(f.ids).join(','), 'trimmedBefore', f.trimmedBefore, 'trimmedAfter', f.trimmedAfter)
}
console.log('departures', JSON.stringify(departures, (k, v) => ArrayBuffer.isView(v) ? Array.from(v) : v))
