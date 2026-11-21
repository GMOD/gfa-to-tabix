// urls.mjs READER SPEC LAYOUT BASE: the address a reader opens for one window and layout. SPEC is chr:start:width with a
// 0-based start; LAYOUT is fmmm, stress, ordered, walkrows or tubemap. BASE is the local server's root
const [reader, spec, layout, base] = process.argv.slice(2)
const [refName, s, w] = spec.split(':')
const start = Number(s)
const end = start + Number(w)
const HAPLOTYPES = ['HG002#1', 'HG00733#1', 'NA19240#1', 'HG00097#1']
const WALKS = `${base}/data/hprc-v2.1-mc-grch38-f8.GRCh38`
const mode = layout === 'fmmm' || layout === 'stress' ? 'force' : layout
const engine = layout === 'stress' ? 'stress' : 'fmmm'
if (reader === 'bjs') {
  const q = new URLSearchParams({
    walks: `${WALKS}.walks.gz`,
    loc: `${refName}:${start + 1}-${end}`,
    haps: HAPLOTYPES.join(','),
    layout: mode,
    engine,
    genes: '0',
    maxNodes: '1000000000',
  })
  console.log(`${base}/bjs/?${q}`)
} else {
  const session = {
    views: [
      {
        type: 'GraphGenomeView',
        loadedTrackId: 'hprc_v2_1_walks',
        loadedRegion: { refName, assemblyName: 'hg38', start, end },
        subgraphHaplotypes: HAPLOTYPES,
        layoutMode: mode,
        layoutEngine: engine,
        maxGraphNodes: 1e9,
        maxRegionBp: 1e9,
      },
    ],
  }
  console.log(`${base}/?config=config.json&session=spec-${encodeURIComponent(JSON.stringify(session))}`)
}
