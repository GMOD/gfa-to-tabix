use std::collections::HashMap;

use crate::gfa::Graph;
use crate::place::Node;

// (sequence, start, end): an interval a row is filed under
pub type Span = (u32, u64, u64);

pub struct Spans {
    pub sequences: Vec<Vec<u8>>,
    // where each node's own row is filed
    pub nodes: Vec<Vec<Span>>,
    // what each node contributes to the interval its links are filed under
    pub links: Vec<Vec<Span>>,
}

struct Sequences {
    index: HashMap<Vec<u8>, u32>,
    names: Vec<Vec<u8>>,
}

impl Sequences {
    fn id(&mut self, name: &[u8]) -> u32 {
        if let Some(&id) = self.index.get(name) {
            return id;
        }
        let id = self.names.len() as u32;
        self.index.insert(name.to_vec(), id);
        self.names.push(name.to_vec());
        id
    }
}

fn own_spans(nodes: &[Option<Node>]) -> (Vec<Option<Span>>, Vec<Vec<u8>>) {
    let mut sequences = Sequences {
        index: HashMap::new(),
        names: Vec::new(),
    };
    let own = nodes
        .iter()
        .map(|node| {
            node.as_ref()
                .map(|n| (sequences.id(&n.sequence), n.start, n.end))
        })
        .collect();
    (own, sequences.names)
}

// Every node under its own coordinate.
pub fn by_contig(nodes: &[Option<Node>]) -> Spans {
    let (own, sequences) = own_spans(nodes);
    let nodes: Vec<Vec<Span>> = own
        .into_iter()
        .map(|span| span.into_iter().collect())
        .collect();
    Spans {
        sequences,
        links: nodes.clone(),
        nodes,
    }
}

fn find(parent: &mut [u32], mut node: u32) -> u32 {
    while parent[node as usize] != node {
        parent[node as usize] = parent[parent[node as usize] as usize];
        node = parent[node as usize];
    }
    node
}

fn widen(spans: &mut Vec<Span>, span: Span) {
    match spans.iter_mut().find(|s| s.0 == span.0) {
        Some(held) => {
            held.1 = held.1.min(span.1);
            held.2 = held.2.max(span.2);
        }
        None => spans.push(span),
    }
}

// A reference node (rank 0) under its own coordinate. Every other node under
// the reference interval its bubble hangs from: the nodes joined to it without
// passing through the reference form one component, and the component's
// interval on a reference sequence runs from the first to the last reference
// node it links to there. A component that touches no reference node keeps its
// own coordinates.
//
// A link is filed under the interval covering what both of its nodes reach. A
// node in a component reaches the component's interval. A reference node
// reaches its own coordinate, the components hanging from it and the reference
// nodes it links to. A region query on the link file then returns every link
// with a node under the region, and every link between the nodes those lead
// to, along with others the reader drops: it keeps a link when one of its
// nodes came back from the node file, or when both are far ends of links it
// kept.
pub fn anchored(graph: &Graph, nodes: &[Option<Node>]) -> Spans {
    let (own, sequences) = own_spans(nodes);
    let reference = |n: u32| {
        nodes[n as usize]
            .as_ref()
            .is_some_and(|node| node.rank == 0)
    };
    let allele = |n: u32| {
        nodes[n as usize]
            .as_ref()
            .is_some_and(|node| node.rank != 0)
    };

    let mut parent: Vec<u32> = (0..nodes.len() as u32).collect();
    for link in &graph.links {
        if allele(link.source) && allele(link.target) {
            let (a, b) = (
                find(&mut parent, link.source),
                find(&mut parent, link.target),
            );
            if a != b {
                parent[a as usize] = b;
            }
        }
    }
    let attachments: Vec<(u32, u32)> = graph
        .links
        .iter()
        .flat_map(|link| [(link.source, link.target), (link.target, link.source)])
        .filter(|&(allele_end, reference_end)| allele(allele_end) && reference(reference_end))
        .map(|(allele_end, reference_end)| (find(&mut parent, allele_end), reference_end))
        .collect();
    let mut anchors: HashMap<u32, Vec<Span>> = HashMap::new();
    for &(component, reference_end) in &attachments {
        let span = own[reference_end as usize].expect("reference node is placed");
        widen(anchors.entry(component).or_default(), span);
    }
    for spans in anchors.values_mut() {
        spans.sort_unstable();
    }
    let filed: Vec<Vec<Span>> = (0..nodes.len() as u32)
        .map(|n| match own[n as usize] {
            None => Vec::new(),
            Some(span) if reference(n) => vec![span],
            Some(span) => anchors
                .get(&find(&mut parent, n))
                .cloned()
                .unwrap_or_else(|| vec![span]),
        })
        .collect();
    let mut links = filed.clone();
    for &(component, reference_end) in &attachments {
        for &span in &anchors[&component] {
            widen(&mut links[reference_end as usize], span);
        }
    }
    for link in &graph.links {
        if reference(link.source) && reference(link.target) {
            for (node, neighbour) in [(link.source, link.target), (link.target, link.source)] {
                let span = own[neighbour as usize].expect("reference node is placed");
                widen(&mut links[node as usize], span);
            }
        }
    }
    Spans {
        sequences,
        nodes: filed,
        links,
    }
}
