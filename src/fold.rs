// A graph with every variant under a size folded into the reference, as rGFA:
// the coarse tier a graph track draws once zoomed out past the fine index.
// Ports bandage-core's foldVariants (src/foldVariants.ts), which the plugin
// runs on each cut it draws, so a tier and a fine cut fold alike.
//
// An allele is a run of segments contiguous on one stable sequence at one rank.
// One is big when its own length, or the reference between the backbone it
// hangs from, reaches `below`. The fold keeps the backbone, every big allele,
// and from each big allele's two ends the shortest way back to the backbone.
// Kept segments keep their ids, and a run of one allele's segments that no kept
// link branches off merges into its first, so folding the result again at a
// larger size folds the original at that size.

use std::cmp::Reverse;
use std::collections::{BinaryHeap, HashMap, HashSet};

use crate::gfa::Graph;
use crate::place::Placed;

#[derive(Clone, Copy, PartialEq)]
enum Side {
    Start,
    End,
}

impl Side {
    fn flip(self) -> Side {
        match self {
            Side::Start => Side::End,
            Side::End => Side::Start,
        }
    }
}

struct Node<'a> {
    name: &'a [u8],
    sequence: &'a [u8],
    start: i64,
    length: i64,
    rank: i64,
}

impl Node<'_> {
    fn backbone(&self) -> bool {
        self.rank == 0
    }
}

struct Edge {
    from: usize,
    from_side: Side,
    from_strand: u8,
    to: usize,
    to_side: Side,
    to_strand: u8,
}

// both ends of a link, on each segment's own forward strand: `L a + b +` leaves
// a's end and enters b's start
fn edge(from: usize, from_strand: u8, to: usize, to_strand: u8) -> Edge {
    Edge {
        from,
        from_side: if from_strand == b'-' {
            Side::Start
        } else {
            Side::End
        },
        from_strand,
        to,
        to_side: if to_strand == b'-' {
            Side::End
        } else {
            Side::Start
        },
        to_strand,
    }
}

fn one_sequence(a: &Node, b: &Node) -> bool {
    a.sequence == b.sequence && a.rank == b.rank
}

// whether a link reads one stable sequence straight on: opposite ends of two
// segments that abut there, either way round
fn continues(a: &Node, a_side: Side, b: &Node, b_side: Side) -> bool {
    one_sequence(a, b)
        && a_side != b_side
        && (a.start + a.length == b.start || b.start + b.length == a.start)
}

// reference bp a link jumps between two segments of one stable sequence at one
// rank, which is a deletion there; 0 for any other link
fn skipped(a: &Node, a_side: Side, b: &Node, b_side: Side) -> i64 {
    if !one_sequence(a, b) || continues(a, a_side, b, b_side) {
        return 0;
    }
    (b.start - (a.start + a.length)).max(a.start - (b.start + b.length))
}

fn alleles(nodes: &[Node], edges: &[Edge]) -> Vec<usize> {
    let mut parent: Vec<usize> = (0..nodes.len()).collect();
    fn find(parent: &mut [usize], mut i: usize) -> usize {
        while parent[i] != i {
            parent[i] = parent[parent[i]];
            i = parent[i];
        }
        i
    }
    for e in edges {
        if continues(&nodes[e.from], e.from_side, &nodes[e.to], e.to_side) {
            let (a, b) = (find(&mut parent, e.from), find(&mut parent, e.to));
            parent[a] = b;
        }
    }
    (0..nodes.len()).map(|i| find(&mut parent, i)).collect()
}

// An allele's own length, or the reference between the backbone it hangs from
// where that is longer: a 93 bp segment standing in for 7 kb of reference is a
// 7 kb deletion. The backbone is never folded.
fn content(group: &[usize], nodes: &[Node], links: &[Vec<(usize, Side)>], allele: &[usize]) -> i64 {
    if nodes[group[0]].backbone() {
        return i64::MAX;
    }
    let mut length = 0;
    let mut sequence: Option<&[u8]> = None;
    let (mut lo, mut hi) = (i64::MAX, i64::MIN);
    let mut one = true;
    for &i in group {
        length += nodes[i].length;
        for &(other, _) in &links[i] {
            let node = &nodes[other];
            if allele[other] != allele[i] && node.backbone() {
                let held = *sequence.get_or_insert(node.sequence);
                one &= node.sequence == held;
                lo = lo.min(node.start + node.length);
                hi = hi.max(node.start);
            }
        }
    }
    if one && hi > lo {
        length.max(hi - lo)
    } else {
        length
    }
}

// Where an allele meets the rest of the graph: each side of its first and last
// segment, in its stable sequence's order, that no link to the allele's own
// segments uses
fn ends(
    group: &[usize],
    nodes: &[Node],
    links: &[Vec<(usize, Side)>],
    allele: &[usize],
) -> Vec<(usize, Side)> {
    let start = |i: usize| nodes[i].start;
    let end = |i: usize| nodes[i].start + nodes[i].length;
    let (mut first, mut last) = (group[0], group[0]);
    for &i in group {
        if start(i) < start(first) {
            first = i;
        }
        if end(i) > end(last) {
            last = i;
        }
    }
    let mut out = Vec::new();
    let mut seen = vec![first];
    if last != first {
        seen.push(last);
    }
    for i in seen {
        for side in [Side::Start, Side::End] {
            if !links[i]
                .iter()
                .any(|&(other, s)| s == side && allele[other] == allele[i])
            {
                out.push((i, side));
            }
        }
    }
    out
}

// The neighbour off one end of an allele nearest the backbone, ties to the
// lower id so the choice does not depend on the order nodes arrived in
fn nearest_outside(
    i: usize,
    side: Side,
    links: &[Vec<(usize, Side)>],
    allele: &[usize],
    dist: &[u64],
    nodes: &[Node],
) -> Option<usize> {
    let mut best: Option<usize> = None;
    for &(j, s) in &links[i] {
        if s == side
            && allele[j] != allele[i]
            && dist[j] != u64::MAX
            && best.is_none_or(|b| {
                dist[j] < dist[b] || (dist[j] == dist[b] && nodes[j].name < nodes[b].name)
            })
        {
            best = Some(j);
        }
    }
    best
}

// Shortest bp from every node back to the backbone, and the neighbour that way
// lies through, ties to the lower id
fn distances(nodes: &[Node], links: &[Vec<(usize, Side)>]) -> (Vec<u64>, Vec<Option<usize>>) {
    let mut dist = vec![u64::MAX; nodes.len()];
    let mut pred: Vec<Option<usize>> = vec![None; nodes.len()];
    let mut heap: BinaryHeap<Reverse<(u64, &[u8], usize)>> = BinaryHeap::new();
    for (i, node) in nodes.iter().enumerate() {
        if node.backbone() {
            dist[i] = 0;
            heap.push(Reverse((0, node.name, i)));
        }
    }
    while let Some(Reverse((d0, _, i))) = heap.pop() {
        if d0 > dist[i] {
            continue;
        }
        for &(other, _) in &links[i] {
            if nodes[other].backbone() {
                continue;
            }
            let d = d0 + nodes[other].length as u64;
            if d < dist[other] {
                dist[other] = d;
                pred[other] = Some(i);
                heap.push(Reverse((d, nodes[other].name, other)));
            } else if d == dist[other] && pred[other].is_some_and(|p| nodes[i].name < nodes[p].name)
            {
                pred[other] = Some(i);
            }
        }
    }
    (dist, pred)
}

#[derive(Clone)]
struct Merged {
    length: i64,
}

type OutNode = (usize, Option<Merged>);
type OutEdge<'a> = (&'a [u8], u8, &'a [u8], u8);

fn rgfa(nodes: &[Node], out_nodes: &[OutNode], out_edges: &[OutEdge]) -> Vec<u8> {
    let mut text = b"H\tVN:Z:1.0\n".to_vec();
    for (i, merged) in out_nodes {
        let node = &nodes[*i];
        let length = merged.as_ref().map_or(node.length, |m| m.length);
        text.extend_from_slice(b"S\t");
        text.extend_from_slice(node.name);
        text.extend_from_slice(format!("\t*\tLN:i:{length}\tSN:Z:").as_bytes());
        text.extend_from_slice(node.sequence);
        text.extend_from_slice(format!("\tSO:i:{}\tSR:i:{}\n", node.start, node.rank).as_bytes());
    }
    for (from, from_strand, to, to_strand) in out_edges {
        text.extend_from_slice(b"L\t");
        text.extend_from_slice(from);
        text.push(b'\t');
        text.push(*from_strand);
        text.push(b'\t');
        text.extend_from_slice(to);
        text.push(b'\t');
        text.push(*to_strand);
        text.extend_from_slice(b"\t0M\n");
    }
    text
}

// The folded graph as rGFA text, every segment `*` with its length and place in
// the tags, which `gfa-to-tabix` files it by.
pub fn fold(graph: &Graph, placed: &Placed, below: i64) -> Vec<u8> {
    let mut compact: Vec<Option<usize>> = vec![None; graph.node_ids.len()];
    let mut nodes: Vec<Node> = Vec::new();
    for (i, node) in placed.nodes.iter().enumerate() {
        if let Some(node) = node {
            compact[i] = Some(nodes.len());
            nodes.push(Node {
                name: &graph.node_ids[i],
                sequence: &node.sequence,
                start: node.start as i64,
                length: (node.end - node.start) as i64,
                rank: node.rank,
            });
        }
    }
    let edges: Vec<Edge> = graph
        .links
        .iter()
        .filter_map(|l| {
            let (a, b) = (compact[l.source as usize]?, compact[l.target as usize]?);
            Some(edge(
                a,
                l.source_strand.first().copied().unwrap_or(b'+'),
                b,
                l.target_strand.first().copied().unwrap_or(b'+'),
            ))
        })
        .collect();
    let pass = |kept: &[bool]| -> (Vec<OutNode>, Vec<OutEdge>) {
        (
            (0..nodes.len())
                .filter(|&i| kept[i])
                .map(|i| (i, None))
                .collect(),
            edges
                .iter()
                .filter(|e| kept[e.from] && kept[e.to])
                .map(|e| {
                    (
                        nodes[e.from].name,
                        e.from_strand,
                        nodes[e.to].name,
                        e.to_strand,
                    )
                })
                .collect(),
        )
    };
    if below <= 0 || !nodes.iter().any(Node::backbone) {
        let (n, e) = pass(&vec![true; nodes.len()]);
        return rgfa(&nodes, &n, &e);
    }

    let mut links: Vec<Vec<(usize, Side)>> = vec![Vec::new(); nodes.len()];
    for e in &edges {
        links[e.from].push((e.to, e.from_side));
        links[e.to].push((e.from, e.to_side));
    }
    let allele = alleles(&nodes, &edges);
    let mut order: Vec<usize> = Vec::new();
    let mut members: HashMap<usize, Vec<usize>> = HashMap::new();
    for (i, &root) in allele.iter().enumerate() {
        members
            .entry(root)
            .or_insert_with(|| {
                order.push(root);
                Vec::new()
            })
            .push(i);
    }

    let mut kept = vec![false; nodes.len()];
    let mut big: Vec<&Vec<usize>> = Vec::new();
    for root in &order {
        let group = &members[root];
        if content(group, &nodes, &links, &allele) >= below {
            for &i in group {
                kept[i] = true;
            }
            if !nodes[group[0]].backbone() {
                big.push(group);
            }
        }
    }

    let (dist, pred) = distances(&nodes, &links);
    for group in big {
        for (i, side) in ends(group, &nodes, &links, &allele) {
            let mut next = nearest_outside(i, side, &links, &allele, &dist, &nodes);
            while let Some(n) = next {
                if kept[n] {
                    break;
                }
                kept[n] = true;
                next = if nodes[n].backbone() { None } else { pred[n] };
            }
        }
    }

    let kept_edges: Vec<&Edge> = edges
        .iter()
        .filter(|e| {
            let skip = skipped(&nodes[e.from], e.from_side, &nodes[e.to], e.to_side);
            kept[e.from] && kept[e.to] && !(skip > 0 && skip < below)
        })
        .collect();
    merge_runs(&nodes, &kept_edges, &kept, &allele)
}

fn merge_runs(nodes: &[Node], edges: &[&Edge], kept: &[bool], allele: &[usize]) -> Vec<u8> {
    let key = |i: usize, side: Side| (i, side == Side::End);
    let mut degree: HashMap<(usize, bool), usize> = HashMap::new();
    for e in edges {
        *degree.entry(key(e.from, e.from_side)).or_default() += 1;
        *degree.entry(key(e.to, e.to_side)).or_default() += 1;
    }
    // the next segment along the sequence, and the side each joins it by
    struct Step {
        j: usize,
        out: Side,
        into: Side,
    }
    let mut next: HashMap<usize, Step> = HashMap::new();
    let mut has_prev: HashSet<usize> = HashSet::new();
    let mut internal: HashSet<usize> = HashSet::new();
    for (k, e) in edges.iter().enumerate() {
        let (a, b) = ((e.from, e.from_side), (e.to, e.to_side));
        if a.0 != b.0
            && allele[a.0] == allele[b.0]
            && continues(&nodes[a.0], a.1, &nodes[b.0], b.1)
            && degree[&key(a.0, a.1)] == 1
            && degree[&key(b.0, b.1)] == 1
        {
            let (left, right) = if nodes[a.0].start < nodes[b.0].start {
                (a, b)
            } else {
                (b, a)
            };
            next.insert(
                left.0,
                Step {
                    j: right.0,
                    out: left.1,
                    into: right.1,
                },
            );
            has_prev.insert(right.0);
            internal.insert(k);
        }
    }
    // a run member's outer side, as the merged segment's start or end
    let mut head_of: Vec<usize> = (0..nodes.len()).collect();
    let mut outer: HashMap<(usize, bool), Side> = HashMap::new();
    let mut merged: HashMap<usize, Merged> = HashMap::new();
    for i in 0..nodes.len() {
        if !kept[i] || has_prev.contains(&i) || !next.contains_key(&i) {
            continue;
        }
        let mut run = vec![i];
        let mut into = next[&i].out.flip();
        outer.insert(key(i, into), Side::Start);
        let mut step = next.get(&i);
        while let Some(s) = step {
            run.push(s.j);
            into = s.into;
            step = next.get(&s.j);
        }
        outer.insert(
            key(*run.last().expect("run has a head"), into.flip()),
            Side::End,
        );
        for &j in &run {
            head_of[j] = i;
        }
        merged.insert(
            i,
            Merged {
                length: run.iter().map(|&j| nodes[j].length).sum(),
            },
        );
    }
    let endpoint = |i: usize, side: Side| -> (usize, Option<Side>) {
        let side = if head_of[i] == i && !merged.contains_key(&i) {
            Some(side)
        } else {
            outer.get(&key(i, side)).copied()
        };
        (head_of[i], side)
    };

    let out_nodes: Vec<OutNode> = (0..nodes.len())
        .filter(|&i| kept[i] && head_of[i] == i)
        .map(|i| (i, merged.get(&i).cloned()))
        .collect();
    let out_edges: Vec<OutEdge> = edges
        .iter()
        .enumerate()
        .filter(|(k, _)| !internal.contains(k))
        .map(|(_, e)| {
            if !merged.contains_key(&head_of[e.from]) && !merged.contains_key(&head_of[e.to]) {
                return (
                    nodes[e.from].name,
                    e.from_strand,
                    nodes[e.to].name,
                    e.to_strand,
                );
            }
            let (from, from_side) = endpoint(e.from, e.from_side);
            let (to, to_side) = endpoint(e.to, e.to_side);
            (
                nodes[from].name,
                if from_side == Some(Side::End) {
                    b'+'
                } else {
                    b'-'
                },
                nodes[to].name,
                if to_side == Some(Side::Start) {
                    b'+'
                } else {
                    b'-'
                },
            )
        })
        .collect();
    rgfa(nodes, &out_nodes, &out_edges)
}
