import { WalkReader } from '/home/cdiesh/src/graph-walks/src/index.ts'
import { walkRowRuns, walkRowsOf } from '/home/cdiesh/src/bandage-core/src/layout/walkRowRuns.ts'
import { walkRowReadout } from '/home/cdiesh/src/bandage-core/src/layout/walkRowDraw.ts'
const [which, refName, prefix, ...wins] = process.argv.slice(2)
const url = which === 'chm13'
  ? 'https://jbrowse.org/demos/hprc/hprc-v2.1-mc-chm13.CHM13.walks.gz'
  : 'https://jbrowse.org/demos/hprc/hprc-v2.1-mc-grch38.GRCh38.walks.gz'
const reader = WalkReader.open(url)
const keep = (n: string) => n.startsWith(prefix!) || n === refName
for (const w of wins) {
  const [s, e] = w.split('-').map(Number)
  for (const [label, o] of [['plain', {}], ['expand', { expand: keep }]] as [string, any][]) {
    const r = await reader.cut(refName!, { start: s!, end: e! }, { keep, stepBudget: Infinity, ...o })
    const tables: any = r.graph.tables(r.kept, r.fragments, r.departures)
    const runs = walkRowRuns(tables, { start: s!, end: e! })
    console.log(`## ${w} ${label}: fragments ${r.fragments.filter(f => f.name !== refName).length} departures ${r.departures.length}`)
    if (!runs) { console.log('  no rows'); continue }
    const rows = walkRowsOf(runs)
    console.log(`  REF ${rows.reference.name} bp ${rows.reference.bp}`)
    for (const row of rows.rows) {
      const segs = row.runs.map(x => x.gap ? `[gap ${x.bp} ${x.cause ?? 'outside'}]` : `${x.onReference ? 'R' : 'o'}${x.reversed ? '<' : ''}${x.bp}`)
      const short = segs.length > 14 ? [...segs.slice(0, 6), `…${segs.length - 12} runs…`, ...segs.slice(-6)] : segs
      const onR = row.runs.filter(x => !x.gap && x.onReference).reduce((a, x) => a + x.bp, 0)
      console.log(`  ROW ${row.name} bp ${row.bp} onRefBp ${onR} gapBp ${row.gapBp} complete ${row.complete} stepless ${!!row.stepless} estimated ${!!row.estimated} abridgedSteps ${row.abridgedSteps ?? 0}\n      text: "${walkRowReadout(row, rows.reference)}"\n      runs: ${short.join(' ')}`)
    }
  }
}
