use crate::gfa::Graph;

pub struct Node {
    pub sequence: Vec<u8>,
    pub start: u64,
    pub end: u64,
    pub rank: i64,
    // assemblies whose paths visit the node, as an SM:Z: tag; None for rGFA
    pub carriers: Option<Vec<u8>>,
}

pub struct Placed {
    pub nodes: Vec<Option<Node>>,
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
                sequence: graph.sequences[p.sequence as usize].clone(),
                start: p.start,
                end: p.start + length.unwrap_or(0),
                rank: p.rank,
                carriers: None,
            })
        })
        .collect();
    Placed {
        nodes,
        summary: "rGFA: coordinates from SN/SO/SR tags".into(),
        notes: Vec::new(),
    }
}

fn sample(name: &[u8]) -> &[u8] {
    name.split(|&b| b == b'#').next().unwrap_or(name)
}

// PanSN names an assembly with its first two fields: HG002#1#chr1 -> HG002.1
fn assembly(name: &[u8]) -> Vec<u8> {
    let fields: Vec<&[u8]> = name.split(|&b| b == b'#').collect();
    if fields.len() >= 3 {
        [fields[0], fields[1]].join(&b'.')
    } else {
        fields[0].to_vec()
    }
}

fn text(bytes: &[u8]) -> String {
    String::from_utf8_lossy(bytes).into_owned()
}

pub fn from_paths(graph: &Graph, reference: Option<&str>) -> Result<Placed, String> {
    if let Some(overlap) = &graph.overlap {
        return Err(format!(
            "{overlap}. Coordinates come from summing node lengths along a path, \
             which is only right when consecutive nodes abut. Blunt the graph \
             first (e.g. `vg mod -X` or `odgi build`), or use an rGFA."
        ));
    }
    let paths = &graph.paths;
    if paths.is_empty() {
        return Err("no P or W lines, and the S lines carry no rGFA tags: \
                    nothing gives this graph coordinates"
            .into());
    }
    let reference_path = match reference {
        None => 0,
        Some(wanted) => {
            let wanted = wanted.as_bytes();
            let prefix = [wanted, b"#"].concat();
            paths
                .iter()
                .position(|p| {
                    sample(&p.name) == wanted || p.name == wanted || p.name.starts_with(&prefix)
                })
                .ok_or_else(|| {
                    let names: Vec<String> = paths.iter().map(|p| text(&p.name)).collect();
                    format!(
                        "--reference {} matches no path; have: {}",
                        text(wanted),
                        names.join(", ")
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

    let mut assembly_ids: Vec<u32> = Vec::with_capacity(paths.len());
    let mut assembly_names: Vec<&Vec<u8>> = Vec::new();
    for name in &assemblies {
        let id = match assembly_names.iter().position(|n| *n == name) {
            Some(id) => id,
            None => {
                assembly_names.push(name);
                assembly_names.len() - 1
            }
        };
        assembly_ids.push(id as u32);
    }

    // Reference paths walk first, so they claim their nodes at rank 0 before
    // any other path reaches them.
    let order = (0..paths.len())
        .filter(|&i| is_reference[i])
        .chain((0..paths.len()).filter(|&i| !is_reference[i]));
    let mut first_visit: Vec<Option<(usize, u64, i64)>> = vec![None; graph.node_ids.len()];
    let mut carriers: Vec<Vec<u32>> = vec![Vec::new(); graph.node_ids.len()];
    for i in order {
        let path = &paths[i];
        let rank = if is_reference[i] { 0 } else { 1 };
        let mut offset = path.start;
        for &node in &path.steps {
            let node = node as usize;
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
            }
            if !carriers[node].contains(&assembly_ids[i]) {
                carriers[node].push(assembly_ids[i]);
            }
            offset += length;
        }
    }

    let nodes = first_visit
        .iter()
        .enumerate()
        .map(|(node, visit)| {
            visit.map(|(path, start, rank)| {
                let names: Vec<&[u8]> = carriers[node]
                    .iter()
                    .map(|&id| assembly_names[id as usize].as_slice())
                    .collect();
                Node {
                    sequence: paths[path].name.clone(),
                    start,
                    end: start + graph.lengths[node].unwrap_or(0),
                    rank,
                    carriers: Some([b"SM:Z:".as_slice(), &names.join(&b',')].concat()),
                }
            })
        })
        .collect();
    Ok(Placed {
        nodes,
        summary: format!(
            "plain GFA: coordinates from paths, reference {} ({} of {} paths)",
            text(&reference_assembly),
            reference_paths,
            paths.len()
        ),
        notes,
    })
}
