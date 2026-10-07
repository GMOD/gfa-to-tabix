use std::collections::HashMap;

use crate::gfa::Graph;
use crate::place::Node;

// (sequence, start, end): an interval a row is filed under
pub type Span = (u32, u64, u64);

pub struct Spans {
    pub sequences: Vec<Vec<u8>>,
    pub nodes: Vec<Vec<Span>>,
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
    Spans {
        sequences,
        nodes: own
            .into_iter()
            .map(|span| span.into_iter().collect())
            .collect(),
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
    let mut anchors: HashMap<u32, Vec<Span>> = HashMap::new();
    for link in &graph.links {
        for (allele_end, reference_end) in [(link.source, link.target), (link.target, link.source)]
        {
            if allele(allele_end) && reference(reference_end) {
                let component = find(&mut parent, allele_end);
                let span = own[reference_end as usize].expect("reference node is placed");
                widen(anchors.entry(component).or_default(), span);
            }
        }
    }
    for spans in anchors.values_mut() {
        spans.sort_unstable();
    }
    let nodes = (0..nodes.len() as u32)
        .map(|n| match own[n as usize] {
            None => Vec::new(),
            Some(span) if reference(n) => vec![span],
            Some(span) => anchors
                .get(&find(&mut parent, n))
                .cloned()
                .unwrap_or_else(|| vec![span]),
        })
        .collect();
    Spans { sequences, nodes }
}
