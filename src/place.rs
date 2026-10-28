use std::collections::{HashMap, HashSet};
use std::sync::Arc;

use crate::gfa::{Graph, blunt_error, split_path_name, text};
use crate::intern::Interner;

pub struct Node {
    // an index into `Placed::sequences`
    pub sequence: u32,
    pub start: u64,
    pub end: u64,
    pub rank: i64,
    // assemblies whose paths visit the node, as a tag shared by every node
    // with the same ones: SM:Z: names them, SB:H: sets their bits in
    // `Placed::samples`. None for rGFA
    pub carriers: Option<Arc<[u8]>>,
}

#[derive(Clone, Copy, PartialEq)]
pub enum CarrierTag {
    Names,
    Bits,
}

pub struct Placed {
    pub sequences: Vec<Vec<u8>>,
    pub nodes: Vec<Option<Node>>,
    // segments the path that placed them reads reversed, which `flip` turns
    // to read forward there
    pub flipped: Vec<bool>,
    pub from_tags: bool,
    // the assemblies in byte order, which SB:H: numbers from 0; empty for rGFA
    pub samples: Vec<Vec<u8>>,
    pub summary: String,
    pub notes: Vec<String>,
}

pub fn from_tags(graph: &Graph) -> Placed {
    let nodes = graph
        .tagged
        .iter()
        .zip(&graph.lengths)
        .map(|(tagged, length)| {
            tagged.as_ref().map(|p| Node {
                sequence: p.sequence,
                start: p.start,
                end: p.start + length.unwrap_or(0),
                rank: p.rank,
                carriers: None,
            })
        })
        .collect();
    Placed {
        sequences: graph.sequences.to_vec(),
        nodes,
        flipped: vec![false; graph.node_ids.len()],
        from_tags: true,
        samples: Vec::new(),
        summary: "rGFA: coordinates from SN/SO/SR tags".into(),
        notes: Vec::new(),
    }
}

fn sample(name: &[u8]) -> &[u8] {
    name.split(|&b| b == b'#').next().unwrap_or(name)
}

// PanSN identifies an assembly by its first two fields: HG002#1#chr1 -> HG002.1
fn assembly(name: &[u8]) -> Vec<u8> {
    let fields: Vec<&[u8]> = name.split(|&b| b == b'#').collect();
    if fields.len() >= 3 {
        [fields[0], fields[1]].join(&b'.')
    } else {
        fields[0].to_vec()
    }
}

// The hex digit i / 4 holds the assembly numbered i as bit i % 4, digits
// counted from the left, and trailing zero digits are dropped.
fn carrier_bits(ids: &[u32], bit_of: &[u32]) -> Vec<u8> {
    let mut nibbles = vec![
        0u8;
        ids.iter()
            .map(|&id| bit_of[id as usize] / 4 + 1)
            .max()
            .unwrap_or(0) as usize
    ];
    for &id in ids {
        let bit = bit_of[id as usize];
        nibbles[(bit / 4) as usize] |= 1 << (bit % 4);
    }
    nibbles
        .iter()
        .map(|&n| b"0123456789abcdef"[n as usize])
        .collect()
}

pub fn from_paths(
    graph: &Graph,
    reference: Option<&str>,
    carrier_tag: CarrierTag,
) -> Result<Placed, String> {
    if let Some(overlap) = &graph.overlap {
        return Err(format!("{} Or use an rGFA.", blunt_error(overlap)));
    }
    let paths = &graph.paths;
    if paths.is_empty() && graph.has_tags() {
        return Err("--reference needs P or W lines, and this graph has none; \
                    without --reference, its rGFA tags give the coordinates"
            .into());
    }
    if paths.is_empty() {
        return Err("no P or W lines, and the S lines carry no rGFA tags: \
                    nothing gives this graph coordinates"
            .into());
    }
    let reference_path = match reference {
        None => 0,
        Some(given) => {
            let (wanted, _) = split_path_name(given.as_bytes());
            let prefix = [wanted, b"#"].concat();
            paths
                .iter()
                .position(|p| p.name == wanted || p.name.starts_with(&prefix))
                .ok_or_else(|| {
                    let mut names: Vec<&[u8]> = paths.iter().map(|p| p.name.as_slice()).collect();
                    names.dedup();
                    let shown: Vec<String> = names.iter().take(20).map(|n| text(n)).collect();
                    let more = match names.len().saturating_sub(20) {
                        0 => String::new(),
                        n => format!(" and {n} more"),
                    };
                    format!(
                        "--reference {given} matches no path; have: {}{more}",
                        shown.join(", ")
                    )
                })?
        }
    };
    let assemblies: Vec<Vec<u8>> = paths.iter().map(|p| assembly(&p.name)).collect();
    let reference_assembly = assemblies[reference_path].clone();
    let is_reference: Vec<bool> = assemblies
        .iter()
        .map(|a| *a == reference_assembly)
        .collect();
    let reference_paths = is_reference.iter().filter(|&&r| r).count();

    let mut notes = Vec::new();
    if !reference.unwrap_or("").contains('#') {
        let reference_sample = sample(&paths[reference_path].name);
        let mut others: Vec<&Vec<u8>> = paths
            .iter()
            .zip(&assemblies)
            .filter(|(p, a)| sample(&p.name) == reference_sample && **a != reference_assembly)
            .map(|(_, a)| a)
            .collect();
        others.sort();
        others.dedup();
        if !others.is_empty() {
            let others: Vec<String> = others.iter().map(|a| text(a)).collect();
            notes.push(format!(
                "note: reference assembly {}; {} of the same sample stay rank 1. \
                 Name one of them to anchor on it instead.",
                text(&reference_assembly),
                others.join(", ")
            ));
        }
    }

    let mut assembly_names = Interner::default();
    let assembly_ids: Vec<u32> = assemblies.iter().map(|a| assembly_names.id(a)).collect();

    // Reference paths walk first, so they claim their nodes at rank 0 before
    // any other path reaches them. Within each group paths walk in name and
    // start order, as the walk files place nodes, so the rows don't depend on
    // the order of the lines, which `vg convert` changes from run to run.
    let mut order: Vec<usize> = (0..paths.len()).collect();
    order.sort_by(|&a, &b| {
        (!is_reference[a], &paths[a].name, paths[a].start).cmp(&(
            !is_reference[b],
            &paths[b].name,
            paths[b].start,
        ))
    });
    let mut first_visit: Vec<Option<(usize, u64, i64)>> = vec![None; graph.node_ids.len()];
    let mut flipped = vec![false; graph.node_ids.len()];
    let mut carriers: Vec<Vec<u32>> = vec![Vec::new(); graph.node_ids.len()];
    for i in order {
        let path = &paths[i];
        let rank = if is_reference[i] { 0 } else { 1 };
        let mut offset = path.start;
        for &step in &path.steps {
            let node = step.node() as usize;
            let Some(length) = graph.lengths[node] else {
                return Err(if graph.declared[node] {
                    format!(
                        "segment {} has no sequence and no LN:i: tag, so every \
                         node after it on a path would be misplaced",
                        text(&graph.node_ids[node])
                    )
                } else {
                    format!(
                        "path {} visits segment {}, which has no S line",
                        text(&path.name),
                        text(&graph.node_ids[node])
                    )
                });
            };
            if first_visit[node].is_none() {
                first_visit[node] = Some((i, offset, rank));
                flipped[node] = step.reversed();
            }
            if carriers[node].last() != Some(&assembly_ids[i]) {
                carriers[node].push(assembly_ids[i]);
            }
            offset += length;
        }
    }

    let mut samples: Vec<Vec<u8>> = (0..assembly_names.len())
        .map(|id| assembly_names[id].clone())
        .collect();
    samples.sort();
    let bit_of: Vec<u32> = (0..assembly_names.len())
        .map(|id| {
            samples
                .binary_search(&assembly_names[id])
                .expect("a listed assembly") as u32
        })
        .collect();
    let mut sequences = Interner::default();
    let sequence_of: Vec<u32> = paths.iter().map(|p| sequences.id(&p.name)).collect();
    let mut seen = HashSet::new();
    for ids in &mut carriers {
        seen.clear();
        ids.retain(|&id| seen.insert(id));
    }
    let mut tags: HashMap<Vec<u32>, Arc<[u8]>> = HashMap::new();
    let nodes = first_visit
        .iter()
        .zip(carriers)
        .enumerate()
        .map(|(node, (visit, carriers))| {
            visit.map(|(path, start, rank)| {
                let tag = tags
                    .entry(carriers)
                    .or_insert_with_key(|ids| match carrier_tag {
                        CarrierTag::Names => {
                            let names: Vec<&[u8]> = ids
                                .iter()
                                .map(|&id| assembly_names[id as usize].as_slice())
                                .collect();
                            [b"SM:Z:".as_slice(), &names.join(&b',')].concat().into()
                        }
                        CarrierTag::Bits => [b"SB:H:".as_slice(), &carrier_bits(ids, &bit_of)]
                            .concat()
                            .into(),
                    });
                Node {
                    sequence: sequence_of[path],
                    start,
                    end: start + graph.lengths[node].unwrap_or(0),
                    rank,
                    carriers: Some(tag.clone()),
                }
            })
        })
        .collect();
    Ok(Placed {
        sequences: sequences.into_names(),
        nodes,
        flipped,
        from_tags: false,
        samples,
        summary: format!(
            "plain GFA: coordinates from paths, reference {} ({} of {} paths)",
            text(&reference_assembly),
            reference_paths,
            paths.len()
        ),
        notes,
    })
}

// Turns every flipped segment to read forward where it is placed: each link
// end and path step on it takes the other strand. A self-link turns at both
// ends.
pub fn flip(graph: &mut Graph, flipped: &[bool]) {
    if !flipped.contains(&true) {
        return;
    }
    for link in &mut graph.links {
        link.source_reversed ^= flipped[link.source as usize];
        link.target_reversed ^= flipped[link.target as usize];
    }
    for path in &mut graph.paths {
        for step in &mut path.steps {
            if flipped[step.node() as usize] {
                *step = step.complement();
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::gfa::strand;

    // a is read forward by ref and reversed by alt; b reversed by ref; x, off
    // the reference, reversed by alt, the path that places it
    const GFA: &str = "S\ta\t*\tLN:i:4\nS\tb\t*\tLN:i:2\nS\tx\t*\tLN:i:3\n\
                       L\ta\t+\tb\t-\t0M\nL\tb\t-\tb\t-\t0M\nL\tx\t-\ta\t-\t0M\n\
                       P\talt\tx-,a-\t*\nP\tref\ta+,b-\t*\n";

    #[test]
    fn the_path_that_places_a_segment_says_whether_it_is_flipped() {
        let graph = Graph::read(GFA.as_bytes()).unwrap();
        let placed = from_paths(&graph, Some("ref"), CarrierTag::Names).unwrap();
        assert_eq!(placed.flipped, [false, true, true]);
    }

    #[test]
    fn a_flip_turns_every_link_end_and_step_on_a_flipped_segment() {
        let mut graph = Graph::read(GFA.as_bytes()).unwrap();
        let placed = from_paths(&graph, Some("ref"), CarrierTag::Names).unwrap();
        flip(&mut graph, &placed.flipped);
        let links: Vec<String> = graph
            .links
            .iter()
            .map(|l| {
                text(
                    &[
                        graph.node_ids[l.source as usize].as_slice(),
                        &[strand(l.source_reversed)],
                        &graph.node_ids[l.target as usize],
                        &[strand(l.target_reversed)],
                    ]
                    .concat(),
                )
            })
            .collect();
        assert_eq!(links, ["a+b+", "b+b+", "x+a-"]);
        let steps: Vec<Vec<bool>> = graph
            .paths
            .iter()
            .map(|p| p.steps.iter().map(|s| s.reversed()).collect())
            .collect();
        assert_eq!(steps, [vec![false, true], vec![false, false]]);
    }

    #[test]
    fn an_rgfa_flips_nothing() {
        let graph = Graph::read("S\ta\t*\tLN:i:4\tSN:Z:chr\tSO:i:0\tSR:i:0\n".as_bytes()).unwrap();
        assert_eq!(from_tags(&graph).flipped, [false]);
    }

    #[test]
    fn an_assembly_lists_once_however_many_of_its_paths_visit() {
        let graph = Graph::read(
            "S\ta\t*\tLN:i:4\nP\tA#1#c1\ta+,a+\t*\nP\tB#1#c\ta+\t*\nP\tA#1#c2\ta+\t*\n".as_bytes(),
        )
        .unwrap();
        let placed = from_paths(&graph, None, CarrierTag::Names).unwrap();
        let carriers = placed.nodes[0].as_ref().unwrap().carriers.as_deref();
        assert_eq!(carriers, Some(b"SM:Z:A.1,B.1".as_slice()));
    }
}
