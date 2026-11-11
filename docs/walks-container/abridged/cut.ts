import { WalkReader } from '/home/cdiesh/src/graph-walks/src/index.ts'
const [which, refName, prefix, ...wins] = process.argv.slice(2)
const url = which === 'chm13'
  ? 'https://jbrowse.org/demos/hprc/hprc-v2.1-mc-chm13.CHM13.walks.gz'
  : 'https://jbrowse.org/demos/hprc/hprc-v2.1-mc-grch38.GRCh38.walks.gz'
const reader = WalkReader.open(url)
const keep = (n: string) => n.startsWith(prefix!)
const modes: [string, any][] = [
  ['plain', {}],
  ['expand', { expand: keep }],
  ['contained', { contained: true }],
  ['contained+expand', { contained: true, expand: keep }],
]
const want = (process.env.MODES ?? "plain,expand").split(",")
for (const w of wins) {
  const [s, e, c] = w.split('-').map(Number)
  for (const [label, o] of modes.filter(m => want.includes(m[0]))) {
    try {
      const r = await reader.cut(refName!, { start: s!, end: e! }, { keep, context: c ?? 0, stepBudget: Infinity, byteBudget: Infinity, ...o })
      const len = (id: number) => { const n = r.graph.nodes.get(id); return n ? n.end - n.start : 0 }
      console.log(`## ${w} ${label}: fragments ${r.fragments.length} departures ${r.departures.length} kept ${r.kept.size}`)
      for (const f of r.fragments) {
        let lo = Infinity, hi = -Infinity, on = 0, inWin = 0
        for (let i = 0; i < f.ids.length; i++) { const x = f.refStarts[i]!; if (!Number.isNaN(x)) { on++; lo = Math.min(lo, x); hi = Math.max(hi, x + len(f.ids[i]!)); if (x < e! + (c ?? 0) && x + len(f.ids[i]!) > s! - (c ?? 0)) inWin++ } }
        console.log(`  F ${f.name} hap ${f.hapStart}-${f.hapEnd} (${f.hapEnd - f.hapStart}bp) steps ${f.ids.length} onR ${on} inWin ${inWin} R ${lo}-${hi} ${f.abridged ? `ABRIDGED steps=${f.abridged.steps} bp=${f.abridged.bp} against=${[...f.against]}` : ''} trim ${f.trimmedBefore}/${f.trimmedAfter}`)
      }
      console.log(`  Dsummary computed ${r.departures.filter(d => d.fromSteps).length} record ${r.departures.filter(d => !d.fromSteps).length}`)
      for (const d of process.env.DEPS ? r.departures : []) {
        console.log(`  D ${d.name} hap ${d.hapStart} own ${d.ownBp} miss ${d.missingBp} leave ${d.leavePos}${d.leaveReversed ? '-' : '+'} rejoin ${d.rejoinPos}${d.rejoinReversed ? '-' : '+'} ${d.fromSteps ? 'computed' : 'record'} steps ${d.steps ? d.steps.ids.length : 'none'}`)
      }
      const gaps = r.gaps ?? []
      for (const g of process.env.DEPS ? gaps : []) console.log(`  G ${g.name} ${g.start}-${g.end} ${g.segments.map((x: any) => `${x.kind}:${x.bp}${x.abridged ? '(abr)' : ''}`).join(',')}`)
    } catch (err: any) { console.log(`## ${w} ${label}: ERROR ${err.message.slice(0, 200)}`) }
  }
}
