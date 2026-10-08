// The --walks mode: every path of a base-level GFA cut into pieces filed under
// fixed chunks of each reference's coordinate, with the nodes and links those
// pieces touch, as three Tabix-indexed BED files. A row's interval is the
// first base of its chunk: a full-chunk interval would share a Tabix bin with
// the next chunk, and a query would pull both. A header line gives the chunk
// size.

use std::collections::HashMap;
use std::fs;
use std::io::Read;
use std::path::PathBuf;
use std::sync::mpsc::{Receiver, sync_channel};
use std::thread;
use std::time::Instant;

use crate::bed;
use crate::gfa::is_blunt;
use crate::sorter::Sorter;

pub struct Options {
    pub refs: Vec<String>,
    pub chunk: u64,
    pub cap: usize,
    pub settle: u64,
    pub sequences: bool,
}

const NONE: u32 = u32::MAX;
// Set on a placement taken from a path off the reference: rank 1.
const OFF_REFERENCE: u32 = 1 << 31;

fn text(bytes: &[u8]) -> String {
    String::from_utf8_lossy(bytes).into_owned()
}

fn push_u64(out: &mut Vec<u8>, mut n: u64) {
    let mut digits = [0u8; 20];
    let mut at = digits.len();
    loop {
        at -= 1;
        digits[at] = b'0' + (n % 10) as u8;
        n /= 10;
        if n == 0 {
            break;
        }
    }
    out.extend_from_slice(&digits[at..]);
}

fn push_i64(out: &mut Vec<u8>, n: i64) {
    if n < 0 {
        out.push(b'-');
    }
    push_u64(out, n.unsigned_abs());
}

fn parse_u64(bytes: &[u8], what: &str) -> Result<u64, String> {
    if bytes.is_empty() || bytes.len() > 19 || !bytes.iter().all(u8::is_ascii_digit) {
        return Err(format!(
            "{what}: {} is not a non-negative integer",
            text(bytes)
        ));
    }
    Ok(bytes.iter().fold(0, |n, &b| n * 10 + u64::from(b - b'0')))
}

fn node_id(bytes: &[u8]) -> Result<u32, String> {
    match parse_u64(bytes, "node id") {
        Ok(id) if id < u64::from(OFF_REFERENCE) => Ok(id as u32),
        _ => Err(format!(
            "--walks needs integer node ids below 2^31, as vg and Minigraph-Cactus write; {} is not one",
            text(bytes)
        )),
    }
}

#[derive(Default)]
struct Names {
    index: HashMap<Vec<u8>, u32>,
    names: Vec<Vec<u8>>,
}

impl Names {
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

// A P or W line: the PanSN sample, the name its rows carry, where the path
// starts on that sequence, and its steps as handles, 2 * id + reverse.
struct PathLine<'a> {
    sample: &'a [u8],
    name: Vec<u8>,
    start: u64,
    steps: &'a [u8],
    walk: bool,
}

// `vg convert -W` names a path piece `sample#hap#contig[start]` or, for a
// haplotype, `sample#hap#contig#start`; `odgi extract` writes `name:start-end`.
fn split_p_name(name: &[u8]) -> (&[u8], u64) {
    let number = |s: &[u8]| parse_u64(s, "").ok();
    if let Some(inner) = name.strip_suffix(b"]")
        && let Some(open) = inner.iter().rposition(|&b| b == b'[')
        && let Some(start) = inner[open + 1..]
            .split(|&b| b == b'-')
            .next()
            .and_then(number)
    {
        return (&name[..open], start);
    }
    if name.iter().filter(|&&b| b == b'#').count() == 3
        && let Some(hash) = name.iter().rposition(|&b| b == b'#')
        && let Some(start) = number(&name[hash + 1..])
    {
        return (&name[..hash], start);
    }
    if let Some(colon) = name.iter().rposition(|&b| b == b':')
        && let [start, end] = name[colon + 1..].split(|&b| b == b'-').collect::<Vec<_>>()[..]
        && number(end).is_some()
        && let Some(start) = number(start)
    {
        return (&name[..colon], start);
    }
    (name, 0)
}

fn path_line(line: &[u8]) -> Result<Option<PathLine<'_>>, String> {
    let mut cols = line.split(|&b| b == b'\t');
    match cols.next() {
        Some(b"W") => {
            let cols: Vec<&[u8]> = cols.take(6).collect();
            if cols.len() < 6 {
                return Err("W line with too few fields".into());
            }
            Ok(Some(PathLine {
                sample: cols[0],
                name: [cols[0], cols[1], cols[2]].join(&b'#'),
                start: parse_u64(cols[3], "W line start")?,
                steps: cols[5],
                walk: true,
            }))
        }
        Some(b"P") => {
            let cols: Vec<&[u8]> = cols.take(3).collect();
            if cols.len() < 2 {
                return Err("P line with too few fields".into());
            }
            if let Some(bad) = cols
                .get(2)
                .and_then(|o| o.split(|&b| b == b',').find(|o| !is_blunt(o)))
            {
                return Err(blunt_error(format!(
                    "path {} has a non-blunt overlap ({})",
                    text(cols[0]),
                    text(bad)
                )));
            }
            let (name, start) = split_p_name(cols[0]);
            Ok(Some(PathLine {
                sample: name.split(|&b| b == b'#').next().unwrap_or(name),
                name: name.to_vec(),
                start,
                steps: cols[1],
                walk: false,
            }))
        }
        _ => Ok(None),
    }
}

fn blunt_error(what: String) -> String {
    format!(
        "{what}. Coordinates come from summing node lengths along a path, \
         which is only right when consecutive nodes abut. Blunt the graph \
         first (e.g. `vg mod -X` or `odgi build`)."
    )
}

fn parse_steps(path: &PathLine, handles: &mut Vec<u32>) -> Result<(), String> {
    handles.clear();
    let steps = path.steps;
    let bad = |step: &[u8]| {
        format!(
            "path {}: step {} is not an integer node id with an orientation",
            text(&path.name),
            text(step)
        )
    };
    if path.walk {
        let mut at = 0;
        while at < steps.len() {
            let reverse = match steps[at] {
                b'>' => 0,
                b'<' => 1,
                _ => return Err(bad(&steps[at..steps.len().min(at + 20)])),
            };
            let end = steps[at + 1..]
                .iter()
                .position(|&b| b == b'>' || b == b'<')
                .map_or(steps.len(), |p| at + 1 + p);
            handles.push(2 * node_id(&steps[at + 1..end])? + reverse);
            at = end;
        }
    } else {
        for step in steps.split(|&b| b == b',') {
            let reverse = match step.last() {
                Some(b'+') => 0,
                Some(b'-') => 1,
                _ if step.is_empty() => continue,
                _ => return Err(bad(step)),
            };
            handles.push(2 * node_id(&step[..step.len() - 1])? + reverse);
        }
    }
    Ok(())
}

// A link's two handles, written the way round that puts the smaller first:
// a->b and b'->a' (each handle flipped) are the same link.
fn canonical(a: u32, b: u32) -> (u32, u32) {
    if a > (b ^ 1) { (b ^ 1, a ^ 1) } else { (a, b) }
}

// The graph's links by source handle, so each has an index.
#[derive(Default)]
struct Links {
    first: Vec<u32>,
    targets: Vec<u32>,
}

impl Links {
    fn build(mut packed: Vec<u64>, nodes: usize) -> Result<Links, String> {
        packed.sort_unstable();
        packed.dedup();
        let handles = 2 * nodes;
        let mut first = vec![0u32; handles + 1];
        let mut targets = Vec::with_capacity(packed.len());
        for &link in &packed {
            let (source, target) = ((link >> 32) as usize, link as u32);
            if source < handles && (target as usize) < handles {
                first[source + 1] += 1;
                targets.push(target);
            }
        }
        if targets.len() >= u32::MAX as usize {
            return Err("more than 2^32 links".into());
        }
        for h in 0..handles {
            first[h + 1] += first[h];
        }
        Ok(Links { first, targets })
    }

    fn find(&self, source: u32, target: u32) -> Option<usize> {
        let source = source as usize;
        if source + 1 >= self.first.len() {
            return None;
        }
        let (from, to) = (self.first[source] as usize, self.first[source + 1] as usize);
        self.targets[from..to]
            .iter()
            .position(|&t| t == target)
            .map(|i| from + i)
    }
}

struct Graph {
    // NONE: no S line
    lengths: Vec<u32>,
    // with --sequences: where each node's sequence starts in `bases`
    sequence_at: Vec<u64>,
    bases: Vec<u8>,
    links: Links,
}

impl Graph {
    fn length(&self, path: &PathLine, handle: u32) -> Result<u64, String> {
        let id = (handle >> 1) as usize;
        match self.lengths.get(id) {
            Some(&length) if length != NONE => Ok(u64::from(length)),
            _ => Err(format!(
                "path {} visits segment {id}, which has no S line",
                text(&path.name)
            )),
        }
    }

    fn sequence(&self, id: usize) -> Option<&[u8]> {
        let at = *self.sequence_at.get(id)?;
        (at != u64::MAX).then(|| &self.bases[at as usize..at as usize + self.lengths[id] as usize])
    }
}

// Per reference sample, per node: where the node is placed (a name id, with
// OFF_REFERENCE set for rank 1), its offset there, and the last chunk a row
// for it was filed under; per link, the last chunk likewise.
struct Reference {
    sample: Vec<u8>,
    walks: u64,
    placement: Vec<u32>,
    offset: Vec<u64>,
    node_chunk: Vec<u32>,
    link_chunk: Vec<u32>,
    pieces: u64,
    settled_steps: u64,
    unplaced: u64,
}

impl Reference {
    fn on_reference(&self, id: usize) -> bool {
        self.placement[id] & OFF_REFERENCE == 0
    }
}

struct RefWalk {
    reference: usize,
    name: u32,
    start: u64,
    ids: Vec<u32>,
}

// Reads (and decompresses) the input on its own thread, so parsing never
// waits on inflate.
struct Prefetched {
    chunks: Receiver<Result<Vec<u8>, String>>,
    chunk: Vec<u8>,
    at: usize,
}

impl Prefetched {
    fn open(path: &str) -> Prefetched {
        let (sender, chunks) = sync_channel(4);
        let path = path.to_string();
        thread::spawn(move || {
            let mut input = match crate::open_input(&path) {
                Ok(input) => input,
                Err(e) => return drop(sender.send(Err(e))),
            };
            loop {
                let mut chunk = Vec::with_capacity(4 << 20);
                let read = (&mut input)
                    .take(4 << 20)
                    .read_to_end(&mut chunk)
                    .map_err(|e| format!("{path}: {e}"));
                let done = matches!(read, Ok(0) | Err(_));
                if sender.send(read.map(|_| chunk)).is_err() || done {
                    return;
                }
            }
        });
        Prefetched {
            chunks,
            chunk: Vec::new(),
            at: 0,
        }
    }

    // Appends through the next newline, which it drops; false at the end.
    fn line(&mut self, line: &mut Vec<u8>) -> Result<bool, String> {
        line.clear();
        loop {
            if self.at == self.chunk.len() {
                match self.chunks.recv() {
                    Ok(Ok(chunk)) if !chunk.is_empty() => {
                        self.chunk = chunk;
                        self.at = 0;
                    }
                    Ok(Err(e)) => return Err(e),
                    _ => return Ok(!line.is_empty()),
                }
            }
            let rest = &self.chunk[self.at..];
            match rest.iter().position(|&b| b == b'\n') {
                Some(end) => {
                    line.extend_from_slice(&rest[..end]);
                    self.at += end + 1;
                    return Ok(true);
                }
                None => {
                    line.extend_from_slice(rest);
                    self.at = self.chunk.len();
                }
            }
        }
    }
}

fn read_lines(
    path: &str,
    mut each: impl FnMut(u64, &[u8]) -> Result<(), String>,
) -> Result<(), String> {
    let mut input = Prefetched::open(path);
    let mut line = Vec::new();
    let mut number = 0u64;
    while input.line(&mut line)? {
        number += 1;
        if line.last() == Some(&b'\r') {
            line.pop();
        }
        each(number, &line).map_err(|e| format!("{path}: line {number}: {e}"))?;
    }
    Ok(())
}

// Per node, the visiting path whose name sorts first in byte order and where
// that path first reaches the node, so a node's coordinate does not depend on
// the order of the paths in the file.
#[derive(Default)]
struct Stable {
    name: Vec<u32>,
    offset: Vec<u64>,
    // by name id: (the path being visited, whether its name sorts before this one)
    sorts_after: Vec<(u64, bool)>,
    paths: u64,
}

impl Stable {
    fn offer(&mut self, names: &Names, id: usize, name: u32, offset: u64) {
        let held = self.name[id];
        let better = if held == NONE {
            true
        } else if held == name {
            offset < self.offset[id]
        } else {
            let (path, after) = self.sorts_after[held as usize];
            if path == self.paths {
                after
            } else {
                let after = names.names[name as usize] < names.names[held as usize];
                self.sorts_after[held as usize] = (self.paths, after);
                after
            }
        };
        if better {
            self.name[id] = name;
            self.offset[id] = offset;
        }
    }

    fn visit(&mut self, names: &Names, name: u32, start: u64, ids: &[u32], lengths: &[u32]) {
        if self.name.len() < lengths.len() {
            self.name.resize(lengths.len(), NONE);
            self.offset.resize(lengths.len(), 0);
        }
        if self.sorts_after.len() < names.names.len() {
            self.sorts_after.resize(names.names.len(), (0, false));
        }
        self.paths += 1;
        let mut offset = start;
        for &id in ids {
            let id = id as usize;
            self.offer(names, id, name, offset);
            offset += u64::from(lengths[id]);
        }
    }
}

// Pass 1: node lengths (and sequences), links, every reference sample's paths,
// which give each node they visit a reference coordinate, and every path's
// claim on the nodes off the references.
fn first_pass(
    gfa: &str,
    options: &Options,
    names: &mut Names,
) -> Result<(Graph, Vec<Reference>), String> {
    let mut lengths: Vec<u32> = Vec::new();
    let mut sequence_at: Vec<u64> = Vec::new();
    let mut bases = Vec::new();
    let mut packed = Vec::new();
    let mut ref_walks: Vec<RefWalk> = Vec::new();
    let mut walks = vec![0u64; options.refs.len()];
    let mut handles = Vec::new();
    let mut ids = Vec::new();
    let mut samples: Vec<Vec<u8>> = Vec::new();
    let mut stable = Stable::default();
    // paths that reach a node before its S line, visited once lengths are known
    let mut deferred: Vec<u64> = Vec::new();
    read_lines(gfa, |number, line| {
        match line.first() {
            Some(b'S') if line.get(1) == Some(&b'\t') => {
                let mut cols = line.split(|&b| b == b'\t').skip(1);
                let (Some(id), Some(sequence)) = (cols.next(), cols.next()) else {
                    return Err("S line with too few fields".into());
                };
                let id = node_id(id)? as usize;
                let length = if sequence == b"*" {
                    cols.find_map(|tag| tag.strip_prefix(b"LN:i:"))
                        .map(|ln| parse_u64(ln, "LN tag"))
                        .transpose()?
                        .ok_or_else(|| {
                            format!(
                                "segment {id} has no sequence and no LN:i: tag, so every \
                                 node after it on a path would be misplaced"
                            )
                        })?
                } else {
                    sequence.len() as u64
                };
                if length >= u64::from(NONE) {
                    return Err(format!("segment {id} is longer than 2^32 bp"));
                }
                if id >= lengths.len() {
                    lengths.resize(id + 1, NONE);
                }
                lengths[id] = length as u32;
                if options.sequences {
                    if id >= sequence_at.len() {
                        sequence_at.resize(id + 1, u64::MAX);
                    }
                    if sequence != b"*" {
                        sequence_at[id] = bases.len() as u64;
                        bases.extend_from_slice(sequence);
                    }
                }
            }
            Some(b'L') if line.get(1) == Some(&b'\t') => {
                let cols: Vec<&[u8]> = line.split(|&b| b == b'\t').skip(1).take(5).collect();
                if cols.len() < 4 {
                    return Err("L line with too few fields".into());
                }
                if cols.len() > 4 && !is_blunt(cols[4]) {
                    return Err(blunt_error(format!(
                        "link {}->{} has a non-blunt overlap ({})",
                        text(cols[0]),
                        text(cols[2]),
                        text(cols[4])
                    )));
                }
                let handle = |id: &[u8], strand: &[u8]| -> Result<u32, String> {
                    Ok(2 * node_id(id)? + u32::from(strand == b"-"))
                };
                let (source, target) =
                    canonical(handle(cols[0], cols[1])?, handle(cols[2], cols[3])?);
                packed.push(u64::from(source) << 32 | u64::from(target));
            }
            Some(b'W' | b'P') if line.get(1) == Some(&b'\t') => {
                let Some(path) = path_line(line)? else {
                    return Ok(());
                };
                if !samples.iter().any(|s| s == path.sample) {
                    samples.push(path.sample.to_vec());
                }
                parse_steps(&path, &mut handles)?;
                let name = names.id(&path.name);
                ids.clear();
                ids.extend(handles.iter().map(|h| h >> 1));
                if ids
                    .iter()
                    .all(|&id| lengths.get(id as usize).is_some_and(|&l| l != NONE))
                {
                    stable.visit(names, name, path.start, &ids, &lengths);
                } else {
                    deferred.push(number);
                }
                if let Some(reference) = options
                    .refs
                    .iter()
                    .position(|r| r.as_bytes() == path.sample)
                {
                    walks[reference] += 1;
                    ref_walks.push(RefWalk {
                        reference,
                        name,
                        start: path.start,
                        ids: ids.clone(),
                    });
                }
            }
            _ => {}
        }
        Ok(())
    })?;
    if lengths.is_empty() {
        return Err(format!("{gfa}: no S lines"));
    }
    if !deferred.is_empty() {
        let mut next = deferred.iter().peekable();
        read_lines(gfa, |number, line| {
            if next.peek() != Some(&&number) {
                return Ok(());
            }
            next.next();
            let Some(path) = path_line(line)? else {
                return Ok(());
            };
            parse_steps(&path, &mut handles)?;
            let name = names.id(&path.name);
            ids.clear();
            for &h in &handles {
                let id = h >> 1;
                if lengths.get(id as usize).is_none_or(|&l| l == NONE) {
                    return Err(format!(
                        "path {} visits segment {id}, which has no S line",
                        text(&path.name)
                    ));
                }
                ids.push(id);
            }
            stable.visit(names, name, path.start, &ids, &lengths);
            Ok(())
        })?;
    }
    for (reference, count) in walks.iter().enumerate() {
        if *count == 0 {
            let samples: Vec<String> = samples.iter().map(|s| text(s)).collect();
            return Err(format!(
                "--refs {} matches no path's sample; have: {}",
                options.refs[reference],
                samples.join(", ")
            ));
        }
    }

    let nodes = lengths.len();
    let mut references: Vec<Reference> = options
        .refs
        .iter()
        .zip(&walks)
        .map(|(sample, &walks)| Reference {
            sample: sample.as_bytes().to_vec(),
            walks,
            placement: vec![NONE; nodes],
            offset: vec![0; nodes],
            node_chunk: vec![NONE; nodes],
            link_chunk: Vec::new(),
            pieces: 0,
            settled_steps: 0,
            unplaced: 0,
        })
        .collect();
    let mut on_reference: Vec<Stable> = options.refs.iter().map(|_| Stable::default()).collect();
    for walk in &ref_walks {
        if let Some(id) = walk
            .ids
            .iter()
            .find(|&&id| lengths.get(id as usize).is_none_or(|&l| l == NONE))
        {
            return Err(format!(
                "path {} visits segment {id}, which has no S line",
                text(&names.names[walk.name as usize])
            ));
        }
        on_reference[walk.reference].visit(names, walk.name, walk.start, &walk.ids, &lengths);
    }
    for (reference, best) in references.iter_mut().zip(&on_reference) {
        for (id, &name) in best.name.iter().enumerate() {
            if name != NONE {
                reference.placement[id] = name;
                reference.offset[id] = best.offset[id];
            }
        }
        for (id, &name) in stable.name.iter().enumerate() {
            if name != NONE && reference.placement[id] == NONE {
                reference.placement[id] = name | OFF_REFERENCE;
                reference.offset[id] = stable.offset[id];
            }
        }
    }
    drop(on_reference);
    drop(stable);
    let links = Links::build(packed, nodes)?;
    for reference in &mut references {
        reference.link_chunk = vec![NONE; links.targets.len()];
    }
    Ok((
        Graph {
            lengths,
            sequence_at,
            bases,
            links,
        },
        references,
    ))
}

// The chunks every reference sequence is cut into, numbered in the order the
// files are sorted: by sequence name in byte order, then by start.
struct Chunks {
    size: u64,
    // by name id: the number of a reference sequence's first chunk
    first: Vec<u32>,
    // by chunk number: (name id, start)
    starts: Vec<(u32, u64)>,
}

impl Chunks {
    fn new(size: u64, ends: &HashMap<u32, u64>, names: &Names) -> Result<Chunks, String> {
        let mut sequences: Vec<(&[u8], u32, u64)> = ends
            .iter()
            .map(|(&name, &end)| (names.names[name as usize].as_slice(), name, end))
            .collect();
        sequences.sort_unstable();
        let mut first = vec![NONE; names.names.len()];
        let mut starts = Vec::new();
        let count: u64 = sequences.iter().map(|&(_, _, end)| end / size + 1).sum();
        if count >= u64::from(NONE) {
            return Err("more than 2^32 chunks; use a larger --chunk".into());
        }
        for (_, name, end) in sequences {
            first[name as usize] = starts.len() as u32;
            for c in 0..=end / size {
                starts.push((name, c * size));
            }
        }
        Ok(Chunks {
            size,
            first,
            starts,
        })
    }

    fn of(&self, name: u32, offset: u64) -> u32 {
        self.first[name as usize] + (offset / self.size) as u32
    }
}

struct Run {
    key: u32,
    bp: u64,
    steps: u64,
    settled: u32,
}

struct Builder<'a> {
    options: &'a Options,
    graph: Graph,
    names: Names,
    chunks: Chunks,
    references: Vec<Reference>,
    walks: Sorter,
    nodes: Sorter,
    links: Sorter,
    paths: u64,
    steps: u64,
    handles: Vec<u32>,
    before: Vec<u64>,
    deltas: Vec<u8>,
    delta_end: Vec<u32>,
    chunk_of: Vec<u32>,
    runs: Vec<Run>,
    pieces: Vec<(usize, usize)>,
}

fn node_row(out: &mut Vec<u8>, id: usize, reference: &Reference, graph: &Graph, names: &Names) {
    let placement = reference.placement[id];
    let length = u64::from(graph.lengths[id]);
    let start = reference.offset[id];
    push_u64(out, id as u64);
    out.extend_from_slice(if placement & OFF_REFERENCE == 0 {
        b"\t0\t"
    } else {
        b"\t1\t"
    });
    out.extend_from_slice(&names.names[(placement & !OFF_REFERENCE) as usize]);
    out.push(b'\t');
    push_u64(out, start);
    out.push(b'\t');
    push_u64(out, start + length);
    out.extend_from_slice(b"\tLN:i:");
    push_u64(out, length);
    if let Some(sequence) = graph.sequence(id) {
        out.extend_from_slice(b"\tSQ:Z:");
        out.extend_from_slice(sequence);
    }
}

fn placed_end(out: &mut Vec<u8>, id: usize, reference: &Reference, graph: &Graph, names: &Names) {
    let placement = reference.placement[id];
    let start = reference.offset[id];
    out.extend_from_slice(&names.names[(placement & !OFF_REFERENCE) as usize]);
    out.push(b'\t');
    push_u64(out, start);
    out.push(b'\t');
    push_u64(out, start + u64::from(graph.lengths[id]));
    out.extend_from_slice(if placement & OFF_REFERENCE == 0 {
        b"\t0"
    } else {
        b"\t1"
    });
}

fn link_row(
    out: &mut Vec<u8>,
    (source, target): (u32, u32),
    reference: &Reference,
    graph: &Graph,
    names: &Names,
) {
    let strand = |h: u32| if h & 1 == 1 { b'-' } else { b'+' };
    push_u64(out, u64::from(source >> 1));
    out.push(strand(source));
    out.push(b'\t');
    push_u64(out, u64::from(target >> 1));
    out.push(strand(target));
    out.push(b'\t');
    placed_end(out, (source >> 1) as usize, reference, graph, names);
    out.push(b'\t');
    placed_end(out, (target >> 1) as usize, reference, graph, names);
}

impl Builder<'_> {
    fn emit_node(&mut self, r: usize, chunk: u32, id: usize) -> Result<(), String> {
        let reference = &mut self.references[r];
        if reference.node_chunk[id] == chunk {
            return Ok(());
        }
        reference.node_chunk[id] = chunk;
        let (reference, graph, names) = (&self.references[r], &self.graph, &self.names);
        self.nodes
            .push(chunk, |out| node_row(out, id, reference, graph, names))
    }

    fn emit_link(&mut self, r: usize, chunk: u32, a: u32, b: u32) -> Result<(), String> {
        let link = canonical(a, b);
        if let Some(index) = self.graph.links.find(link.0, link.1) {
            let held = &mut self.references[r].link_chunk[index];
            if *held == chunk {
                return Ok(());
            }
            *held = chunk;
        }
        let (reference, graph, names) = (&self.references[r], &self.graph, &self.names);
        self.links
            .push(chunk, |out| link_row(out, link, reference, graph, names))
    }

    fn path(&mut self, path: &PathLine) -> Result<(), String> {
        let mut handles = std::mem::take(&mut self.handles);
        parse_steps(path, &mut handles)?;
        let result = self.cut_path(path, &handles);
        self.handles = handles;
        result
    }

    fn cut_path(&mut self, path: &PathLine, handles: &[u32]) -> Result<(), String> {
        if handles.is_empty() {
            return Ok(());
        }
        self.paths += 1;
        self.steps += handles.len() as u64;
        self.before.clear();
        self.deltas.clear();
        self.delta_end.clear();
        let mut offset = 0u64;
        let mut previous = 0i64;
        for &h in handles {
            self.before.push(offset);
            offset += self.graph.length(path, h)?;
            let id = i64::from(h >> 1);
            if !self.delta_end.is_empty() {
                self.deltas.push(b',');
            }
            push_i64(&mut self.deltas, 2 * (id - previous) + i64::from(h & 1));
            self.delta_end.push(self.deltas.len() as u32);
            previous = id;
        }
        for r in 0..self.references.len() {
            if !self.assign_chunks(r, handles) {
                self.references[r].unplaced += 1;
                continue;
            }
            self.cut_pieces();
            self.references[r].pieces += self.pieces.len() as u64;
            let pieces = std::mem::take(&mut self.pieces);
            let result = self.write_pieces(r, path, handles, &pieces);
            self.pieces = pieces;
            result?;
        }
        Ok(())
    }

    // Gives every step the chunk its piece is filed under: a reference step
    // its own, any other step the last reference step's before it (the first
    // reference step's for those that lead). A run of reference steps in one
    // chunk spanning fewer than --settle bp (a collapsed repeat copy, a short
    // inversion) stays with the chunk the path was in. False when the path
    // visits no node of the reference.
    fn assign_chunks(&mut self, r: usize, handles: &[u32]) -> bool {
        let reference = &self.references[r];
        self.chunk_of.clear();
        self.runs.clear();
        for &h in handles {
            let id = (h >> 1) as usize;
            if !reference.on_reference(id) {
                self.chunk_of.push(NONE);
                continue;
            }
            let key = self
                .chunks
                .of(reference.placement[id], reference.offset[id]);
            self.chunk_of.push(key);
            let bp = u64::from(self.graph.lengths[id]);
            match self.runs.last_mut() {
                Some(run) if run.key == key => {
                    run.bp += bp;
                    run.steps += 1;
                }
                _ => self.runs.push(Run {
                    key,
                    bp,
                    steps: 1,
                    settled: key,
                }),
            }
        }
        if self.runs.is_empty() {
            return false;
        }
        let settle = self.options.settle;
        let mut current = match self.runs.iter().find(|run| run.bp >= settle) {
            Some(run) => run.key,
            None => {
                let mut longest = &self.runs[0];
                for run in &self.runs {
                    if run.bp > longest.bp {
                        longest = run;
                    }
                }
                longest.key
            }
        };
        let mut moved = 0;
        for run in &mut self.runs {
            if run.bp >= settle {
                current = run.key;
            } else if run.key != current {
                run.settled = current;
                moved += run.steps;
            }
        }
        self.references[r].settled_steps += moved;
        let mut run = 0;
        let mut key = self.runs[0].key;
        let mut current = self.runs[0].settled;
        for chunk in &mut self.chunk_of {
            if *chunk != NONE {
                if *chunk != key {
                    run += 1;
                    key = *chunk;
                }
                current = self.runs[run].settled;
            }
            *chunk = current;
        }
        true
    }

    // A piece runs while the chunk stays the same, up to --cap steps.
    fn cut_pieces(&mut self) {
        self.pieces.clear();
        let cap = self.options.cap;
        let n = self.chunk_of.len();
        let mut from = 0;
        for i in 1..=n {
            if i == n || self.chunk_of[i] != self.chunk_of[i - 1] {
                let mut start = from;
                while i - start > cap {
                    self.pieces.push((start, start + cap));
                    start += cap;
                }
                self.pieces.push((start, i));
                from = i;
            }
        }
    }

    fn write_pieces(
        &mut self,
        r: usize,
        path: &PathLine,
        handles: &[u32],
        pieces: &[(usize, usize)],
    ) -> Result<(), String> {
        let mut previous_chunk = NONE;
        for (k, &(a, b)) in pieces.iter().enumerate() {
            let chunk = self.chunk_of[a];
            let (before, deltas, delta_end) = (&self.before, &self.deltas, &self.delta_end);
            self.walks.push(chunk, |out| {
                out.extend_from_slice(&path.name);
                out.push(b'\t');
                push_u64(out, path.start);
                out.push(b'\t');
                push_u64(out, path.start + before[a]);
                out.push(b'\t');
                push_u64(out, k as u64);
                out.push(b'\t');
                push_u64(out, (b - a) as u64);
                out.push(b'\t');
                push_u64(out, u64::from(handles[a]));
                if b > a + 1 {
                    out.extend_from_slice(
                        &deltas[delta_end[a] as usize..delta_end[b - 1] as usize],
                    );
                }
            })?;
            for &h in &handles[a..b] {
                self.emit_node(r, chunk, (h >> 1) as usize)?;
            }
            for i in a..b - 1 {
                self.emit_link(r, chunk, handles[i], handles[i + 1])?;
            }
            if a > 0 {
                self.emit_link(r, chunk, handles[a - 1], handles[a])?;
                self.emit_link(r, previous_chunk, handles[a - 1], handles[a])?;
            }
            previous_chunk = chunk;
        }
        Ok(())
    }
}

struct TempDir(PathBuf);

impl Drop for TempDir {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

const SORT_BUDGET: usize = 512 << 20;

pub fn run(gfa: &str, prefix: &str, options: &Options) -> Result<(), String> {
    if gfa == "-" {
        return Err("--walks reads the GFA twice, so it needs a file, not stdin".into());
    }
    let clock = Instant::now();
    let elapsed = || format!("[{:6.1} s]", clock.elapsed().as_secs_f64());
    let mut names = Names::default();
    let (graph, references) = first_pass(gfa, options, &mut names)?;
    let mut ends: HashMap<u32, u64> = HashMap::new();
    for reference in &references {
        let mut on = 0;
        for (id, &placement) in reference.placement.iter().enumerate() {
            if reference.on_reference(id) {
                on += 1;
                let end = reference.offset[id] + u64::from(graph.lengths[id]);
                let held = ends.entry(placement).or_default();
                *held = (*held).max(end);
            }
        }
        eprintln!(
            "{} reference {}: {} paths, {on} nodes",
            elapsed(),
            text(&reference.sample),
            reference.walks
        );
    }
    let chunks = Chunks::new(options.chunk, &ends, &names)?;

    let temp = TempDir(PathBuf::from(format!(
        "{prefix}.walks-tmp-{}",
        std::process::id()
    )));
    fs::create_dir_all(&temp.0).map_err(|e| format!("{}: {e}", temp.0.display()))?;
    let mut builder = Builder {
        options,
        graph,
        names,
        chunks,
        references,
        walks: Sorter::new(&temp.0, "walks", false, SORT_BUDGET),
        nodes: Sorter::new(&temp.0, "nodes", true, SORT_BUDGET / 2),
        links: Sorter::new(&temp.0, "links", true, SORT_BUDGET / 2),
        paths: 0,
        steps: 0,
        handles: Vec::new(),
        before: Vec::new(),
        deltas: Vec::new(),
        delta_end: Vec::new(),
        chunk_of: Vec::new(),
        runs: Vec::new(),
        pieces: Vec::new(),
    };
    read_lines(gfa, |_, line| match line.first() {
        Some(b'W' | b'P') if line.get(1) == Some(&b'\t') => match path_line(line)? {
            Some(path) => builder.path(&path),
            None => Ok(()),
        },
        _ => Ok(()),
    })?;
    eprintln!(
        "{} {} paths, {} steps",
        elapsed(),
        builder.paths,
        builder.steps
    );
    for reference in &builder.references {
        eprintln!(
            "{}: {} pieces, {} steps held in their chunk by --settle, {} paths visit no {} node and are left out",
            text(&reference.sample),
            reference.pieces,
            reference.settled_steps,
            reference.unplaced,
            text(&reference.sample)
        );
    }

    let Builder {
        names,
        chunks,
        walks,
        nodes,
        links,
        ..
    } = builder;
    let (names, chunks) = (&names, &chunks);
    let threads = thread::available_parallelism().map_or(4, |n| n.get());
    let write = |kind: &str, sorter: Sorter| -> Result<(String, u64), String> {
        let path = format!("{prefix}.{kind}.bed.gz");
        let mut writer = bed::Writer::create_parallel(&path, threads)?;
        writer.header(format!("#{kind}\tchunk:i:{}\n", chunks.size).as_bytes())?;
        let mut line = Vec::new();
        let rows = sorter.merge(|chunk, rest| {
            let (name, start) = chunks.starts[chunk as usize];
            let name = &names.names[name as usize];
            let end = start + 1;
            line.clear();
            line.extend_from_slice(name);
            line.push(b'\t');
            push_u64(&mut line, start);
            line.push(b'\t');
            push_u64(&mut line, end);
            line.push(b'\t');
            line.extend_from_slice(rest);
            line.push(b'\n');
            writer.push(name, start, end, &line)
        })?;
        writer.finish()?;
        Ok((path, rows))
    };
    let written: Vec<Result<(String, u64), String>> = thread::scope(|scope| {
        let handles = [("walks", walks), ("nodes", nodes), ("links", links)]
            .map(|(kind, sorter)| scope.spawn(move || write(kind, sorter)));
        handles
            .into_iter()
            .map(|h| h.join().unwrap_or_else(|_| Err("writing panicked".into())))
            .collect()
    });
    let mut summary = Vec::new();
    for result in written {
        let (path, rows) = result?;
        summary.push(format!("{rows} rows -> {path}"));
    }
    eprintln!("{} {} (+ .tbi)", elapsed(), summary.join(", "));
    Ok(())
}
