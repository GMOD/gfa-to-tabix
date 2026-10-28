// The --walks mode: every path of a base-level GFA cut into pieces filed under
// fixed chunks of each reference's coordinate, written as one Tabix-indexed
// BED file per reference in walk format 5 (`routes.rs` writes a chunk's rows). A
// row's interval is the first base of its chunk: a full-chunk interval would
// share a Tabix bin with the next chunk, and a query would pull both. Header
// lines give the format, the chunk size and the longest node, then the
// reference and the haplotypes.

use std::collections::{BTreeSet, HashMap, HashSet};
use std::fs::{self, File};
use std::io::{BufReader, BufWriter, Read, Write};
use std::path::PathBuf;
use std::sync::Mutex;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::mpsc::{Receiver, sync_channel};
use std::thread;
use std::time::Instant;

use crate::bed;
use crate::gfa::{blunt_error, is_blunt, parse_u64, split_path_name, text};
use crate::intern::{FastMap, Interner};
use crate::routes::{self, Piece, PieceRef};
use crate::sorter::Sorter;

pub struct Options {
    pub refs: Vec<String>,
    pub chunk: u64,
    pub sequences: bool,
    pub stay: u64,
    pub budget: routes::Budget,
}

const NONE: u32 = u32::MAX;
// The most chunks a path's jump over the reference files `skip` rows in; a
// farther jump is a paralog's
const SKIP_CHUNKS: u64 = 32;
// The first byte of a `skip` row in the sort, after a chunk's pieces, which
// start 0 (the reference's) or 1
const SKIP_ROW: u8 = 2;
// Set on a placement taken from a path off the reference: rank 1.
const OFF_REFERENCE: u32 = 1 << 31;

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

fn node_id(bytes: &[u8]) -> Result<u32, String> {
    match parse_u64(bytes, "node id") {
        Ok(id) if id < u64::from(OFF_REFERENCE) => Ok(id as u32),
        _ => Err(format!(
            "--walks needs integer node ids below 2^31, as vg and Minigraph-Cactus write; {} is not one",
            text(bytes)
        )),
    }
}

// A P or W line: the PanSN sample, the name its rows carry, where the path
// starts and (on a W line) ends on that sequence, and its steps as handles,
// 2 * id + reverse.
struct PathLine<'a> {
    sample: &'a [u8],
    name: Vec<u8>,
    start: u64,
    end: Option<u64>,
    steps: &'a [u8],
    walk: bool,
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
                end: Some(parse_u64(cols[4], "W line end")?),
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
                return Err(blunt_error(&format!(
                    "path {} has a non-blunt overlap ({})",
                    text(cols[0]),
                    text(bad)
                )));
            }
            let (name, start) = split_path_name(cols[0]);
            Ok(Some(PathLine {
                sample: name.split(|&b| b == b'#').next().unwrap_or(name),
                name: name.to_vec(),
                start,
                end: None,
                steps: cols[1],
                walk: false,
            }))
        }
        _ => Ok(None),
    }
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

struct Graph {
    // NONE: no S line
    lengths: Vec<u32>,
    // with --sequences: where each node's sequence starts in `bases`
    sequence_at: Vec<u64>,
    bases: Vec<u8>,
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
// OFF_REFERENCE set for rank 1) and its offset there. `path_ends` holds where
// each of the sample's own paths ends, which bounds its chunks even past its
// last first-visited node. `visits` lists every pass of the sample's paths
// over a node they pass more than once, by node, name and offset;
// `visits_of` gives each such node's stretch of it.
struct Reference {
    sample: Vec<u8>,
    walks: u64,
    placement: Vec<u32>,
    offset: Vec<u64>,
    reverse: Bits,
    revisited: Bits,
    visits: Vec<Visit>,
    visits_of: FastMap<u32, (u32, u32)>,
    path_ends: HashMap<u32, u64>,
    pieces: u64,
    skips: u64,
    unplaced: u64,
    haplotypes: BTreeSet<Vec<u8>>,
}

impl Reference {
    fn on_reference(&self, id: usize) -> bool {
        self.placement[id] & OFF_REFERENCE == 0
    }

    // maxnode: the longest node on the reference paths, in bp
    fn longest(&self, lengths: &[u32]) -> u32 {
        (0..lengths.len())
            .filter(|&id| self.on_reference(id))
            .map(|id| lengths[id])
            .max()
            .unwrap_or(0)
    }

    // Every pass of the reference's paths over a node longer than `chunk`, as
    // (name id, start, end), for the `#long` header lines
    fn long_passes(&self, lengths: &[u32], chunk: u64) -> Vec<(u32, u64, u64)> {
        let mut passes = Vec::new();
        for id in
            (0..lengths.len()).filter(|&id| self.on_reference(id) && u64::from(lengths[id]) > chunk)
        {
            let length = u64::from(lengths[id]);
            if self.revisited.get(id) {
                let (from, to) = self.visits_of[&(id as u32)];
                for v in &self.visits[from as usize..to as usize] {
                    passes.push((v.name, v.offset, v.offset + length));
                }
            } else {
                passes.push((
                    self.placement[id],
                    self.offset[id],
                    self.offset[id] + length,
                ));
            }
        }
        passes
    }

    fn first_visit(&self, id: usize) -> Visit {
        Visit {
            name: self.placement[id],
            offset: self.offset[id],
            reverse: self.reverse.get(id),
        }
    }

    // The pass over `id` on sequence `name` whose offset lies nearest
    // `expected`, the earlier on a tie; the first visit when that sequence
    // has none.
    fn visit_near(&self, id: usize, name: u32, expected: i64) -> Visit {
        if !self.revisited.get(id) {
            return self.first_visit(id);
        }
        let (from, to) = self.visits_of[&(id as u32)];
        let visits = &self.visits[from as usize..to as usize];
        let lo = visits.partition_point(|v| v.name < name);
        let hi = visits.partition_point(|v| v.name <= name);
        let on = &visits[lo..hi];
        if on.is_empty() {
            return self.first_visit(id);
        }
        let k = on.partition_point(|v| (v.offset as i64) < expected);
        match (k.checked_sub(1).map(|j| on[j]), on.get(k)) {
            (Some(a), Some(b)) if b.offset as i64 - expected < expected - a.offset as i64 => *b,
            (Some(a), _) => a,
            (None, Some(b)) => *b,
            (None, None) => unreachable!(),
        }
    }
}

#[derive(Clone, Copy)]
struct Visit {
    name: u32,
    offset: u64,
    reverse: bool,
}

struct Bits(Vec<u64>);

impl Bits {
    fn with_len(n: usize) -> Bits {
        Bits(vec![0; n.div_ceil(64)])
    }

    fn get(&self, i: usize) -> bool {
        self.0[i / 64] >> (i % 64) & 1 == 1
    }

    fn set(&mut self, i: usize) {
        self.0[i / 64] |= 1 << (i % 64);
    }
}

struct RefWalk {
    reference: usize,
    name: u32,
    start: u64,
    handles: Vec<u32>,
}

// Reads (and decompresses) the input on a separate thread, so parsing never
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
    fn offer(&mut self, names: &Interner, id: usize, name: u32, offset: u64) {
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
                let after = names[name as usize] < names[held as usize];
                self.sorts_after[held as usize] = (self.paths, after);
                after
            }
        };
        if better {
            self.name[id] = name;
            self.offset[id] = offset;
        }
    }

    // Returns where the path ends.
    fn visit(
        &mut self,
        names: &Interner,
        name: u32,
        start: u64,
        ids: &[u32],
        lengths: &[u32],
    ) -> u64 {
        if self.name.len() < lengths.len() {
            self.name.resize(lengths.len(), NONE);
            self.offset.resize(lengths.len(), 0);
        }
        if self.sorts_after.len() < names.len() {
            self.sorts_after.resize(names.len(), (0, false));
        }
        self.paths += 1;
        let mut offset = start;
        for &id in ids {
            let id = id as usize;
            self.offer(names, id, name, offset);
            offset += u64::from(lengths[id]);
        }
        offset
    }
}

// A W or P line with steps: its name id and the stretch of its contig it covers.
struct Record {
    name: u32,
    start: u64,
    end: u64,
}

// Refuses a W line whose end column disagrees with its steps.
fn record(path: &PathLine, name: u32, end: u64) -> Result<Record, String> {
    if let Some(stated) = path.end
        && stated != end
    {
        return Err(format!(
            "path {} ends at {stated}, but its steps from {} end at {end}",
            text(&path.name),
            path.start
        ));
    }
    Ok(Record {
        name,
        start: path.start,
        end,
    })
}

// Pass 1: node lengths (and sequences), every reference sample's paths,
// which give each node they visit a reference coordinate, every path's claim
// on the nodes off the references, and the record of every path with steps,
// in file order.
fn first_pass(
    gfa: &str,
    options: &Options,
    names: &mut Interner,
) -> Result<(Graph, Vec<Reference>, Vec<Record>), String> {
    let mut lengths: Vec<u32> = Vec::new();
    let mut sequence_at: Vec<u64> = Vec::new();
    let mut bases = Vec::new();
    let mut ref_walks: Vec<RefWalk> = Vec::new();
    let mut walks = vec![0u64; options.refs.len()];
    let mut handles = Vec::new();
    let mut ids = Vec::new();
    let mut samples = Interner::default();
    let mut stable = Stable::default();
    let mut records: Vec<Record> = Vec::new();
    // paths that reach a node before its S line, by line number and record,
    // visited once lengths are known
    let mut deferred: Vec<(u64, usize)> = Vec::new();
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
                    return Err(blunt_error(&format!(
                        "link {}->{} has a non-blunt overlap ({})",
                        text(cols[0]),
                        text(cols[2]),
                        text(cols[4])
                    )));
                }
            }
            Some(b'W' | b'P') if line.get(1) == Some(&b'\t') => {
                let Some(path) = path_line(line)? else {
                    return Ok(());
                };
                samples.id(path.sample);
                parse_steps(&path, &mut handles)?;
                let name = names.id(&path.name);
                ids.clear();
                ids.extend(handles.iter().map(|h| h >> 1));
                if ids
                    .iter()
                    .all(|&id| lengths.get(id as usize).is_some_and(|&l| l != NONE))
                {
                    let end = stable.visit(names, name, path.start, &ids, &lengths);
                    let record = record(&path, name, end)?;
                    if !ids.is_empty() {
                        records.push(record);
                    }
                } else {
                    deferred.push((number, records.len()));
                    records.push(Record {
                        name,
                        start: path.start,
                        end: path.start,
                    });
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
                        handles: handles.clone(),
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
            let Some(&&(_, at)) = next.peek().filter(|(n, _)| *n == number) else {
                return Ok(());
            };
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
            let end = stable.visit(names, name, path.start, &ids, &lengths);
            records[at] = record(&path, name, end)?;
            Ok(())
        })?;
    }
    for (reference, count) in walks.iter().enumerate() {
        if *count == 0 {
            let shown: Vec<String> = samples.iter().take(20).map(|s| text(s)).collect();
            let more = match samples.len().saturating_sub(20) {
                0 => String::new(),
                n => format!(" and {n} more"),
            };
            return Err(format!(
                "--refs {} matches no path's sample; have: {}{more}",
                options.refs[reference],
                shown.join(", ")
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
            reverse: Bits::with_len(nodes),
            revisited: Bits::with_len(nodes),
            visits: Vec::new(),
            visits_of: FastMap::default(),
            path_ends: HashMap::new(),
            pieces: 0,
            skips: 0,
            unplaced: 0,
            haplotypes: BTreeSet::new(),
        })
        .collect();
    let mut on_reference: Vec<Stable> = options.refs.iter().map(|_| Stable::default()).collect();
    for walk in &ref_walks {
        ids.clear();
        ids.extend(walk.handles.iter().map(|h| h >> 1));
        if let Some(id) = ids
            .iter()
            .find(|&&id| lengths.get(id as usize).is_none_or(|&l| l == NONE))
        {
            return Err(format!(
                "path {} visits segment {id}, which has no S line",
                text(&names[walk.name as usize])
            ));
        }
        on_reference[walk.reference].visit(names, walk.name, walk.start, &ids, &lengths);
        let length: u64 = ids.iter().map(|&id| u64::from(lengths[id as usize])).sum();
        let end = references[walk.reference]
            .path_ends
            .entry(walk.name)
            .or_default();
        *end = (*end).max(walk.start + length);
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
    for (r, reference) in references.iter_mut().enumerate() {
        index_visits(
            reference,
            ref_walks.iter().filter(|w| w.reference == r),
            &lengths,
        );
    }
    Ok((
        Graph {
            lengths,
            sequence_at,
            bases,
        },
        references,
        records,
    ))
}

// Notes each first visit's strand, and every pass over the nodes the
// sample's paths pass more than once.
fn index_visits<'a>(
    reference: &mut Reference,
    walks: impl Iterator<Item = &'a RefWalk> + Clone,
    lengths: &[u32],
) {
    let mut passes = vec![0u8; reference.placement.len()];
    for walk in walks.clone() {
        for &h in &walk.handles {
            let n = &mut passes[(h >> 1) as usize];
            *n = n.saturating_add(1);
        }
    }
    let mut visits = Vec::new();
    for walk in walks {
        let mut offset = walk.start;
        for &h in &walk.handles {
            let id = (h >> 1) as usize;
            let visit = Visit {
                name: walk.name,
                offset,
                reverse: h & 1 == 1,
            };
            if visit.reverse
                && visit.name == reference.placement[id]
                && visit.offset == reference.offset[id]
            {
                reference.reverse.set(id);
            }
            if passes[id] > 1 {
                reference.revisited.set(id);
                visits.push((id as u32, visit));
            }
            offset += u64::from(lengths[id]);
        }
    }
    visits.sort_unstable_by_key(|&(id, v)| (id, v.name, v.offset));
    for (k, &(id, _)) in visits.iter().enumerate() {
        let k = k as u32;
        reference.visits_of.entry(id).or_insert((k, k)).1 = k + 1;
    }
    reference.visits = visits.into_iter().map(|(_, v)| v).collect();
}

// The chunks every reference sequence is cut into, numbered in the order the
// files are sorted: by sequence name in byte order, then by start.
struct Chunks {
    size: u64,
    // by name id: the number of a reference sequence's first chunk, and the
    // reference it belongs to
    first: Vec<u32>,
    owner: Vec<u32>,
    // by chunk number: (name id, start)
    starts: Vec<(u32, u64)>,
}

impl Chunks {
    // `ends` maps a reference sequence's name id to (its reference, its end).
    fn new(size: u64, ends: &HashMap<u32, (u32, u64)>, names: &Interner) -> Result<Chunks, String> {
        let mut sequences: Vec<(&[u8], u32, u32, u64)> = ends
            .iter()
            .map(|(&name, &(owner, end))| (names[name as usize].as_slice(), name, owner, end))
            .collect();
        sequences.sort_unstable();
        let mut first = vec![NONE; names.len()];
        let mut owner = vec![NONE; names.len()];
        let mut starts = Vec::new();
        let count: u64 = sequences.iter().map(|&(_, _, _, end)| end / size + 1).sum();
        if count >= u64::from(NONE) {
            return Err("more than 2^32 chunks; use a larger --chunk".into());
        }
        for (_, name, reference, end) in sequences {
            first[name as usize] = starts.len() as u32;
            owner[name as usize] = reference;
            for c in 0..=end / size {
                starts.push((name, c * size));
            }
        }
        Ok(Chunks {
            size,
            first,
            owner,
            starts,
        })
    }

    fn of(&self, name: u32, offset: u64) -> u32 {
        self.first[name as usize] + (offset / self.size) as u32
    }

    // Whether a reader of a window over `chunk`, which reads the chunk before
    // it too, reads `home`.
    fn reaches(&self, chunk: u32, home: u32) -> bool {
        home <= chunk
            && chunk - home <= 1
            && self.starts[chunk as usize].0 == self.starts[home as usize].0
    }
}

// Under one reference: the chunks a record's first and last pieces are filed
// under, NONE for a record with no rows there, and its number of pieces.
#[derive(Clone, Copy)]
struct Placed {
    first: u32,
    last: u32,
    pieces: u32,
}

const UNPLACED: Placed = Placed {
    first: NONE,
    last: NONE,
    pieces: 0,
};

// The records before and after one on its contig, NONE at either end.
#[derive(Clone, Copy)]
struct Link {
    previous: u32,
    next: u32,
}

struct Builder {
    graph: Graph,
    names: Interner,
    chunks: Chunks,
    stay: u64,
    references: Vec<Reference>,
    rows: Sorter,
    // by record, then reference
    placed: Vec<Placed>,
    paths: u64,
    steps: u64,
    handles: Vec<u32>,
    before: Vec<u64>,
    chunk_of: Vec<u32>,
    // by step of a path off the reference: the reference pass a step on a
    // reference node takes, as (name id, offset); NONE for any other step
    pass: Vec<(u32, u64)>,
    pieces: Vec<(usize, usize)>,
}

// A path's PanSN haplotype, `sample#haplotype`: its name up to the second `#`.
fn haplotype(name: &[u8]) -> &[u8] {
    match name.iter().enumerate().filter(|&(_, &b)| b == b'#').nth(1) {
        Some((at, _)) => &name[..at],
        None => name,
    }
}

impl Builder {
    fn path(&mut self, path: &PathLine) -> Result<(), String> {
        let mut handles = std::mem::take(&mut self.handles);
        parse_steps(path, &mut handles)?;
        let result = self.cut_path(path, &handles);
        self.handles = handles;
        result
    }

    fn cut_path(&mut self, path: &PathLine, handles: &[u32]) -> Result<(), String> {
        self.before.clear();
        let mut offset = 0u64;
        for &h in handles {
            self.before.push(offset);
            offset += self.graph.length(path, h)?;
        }
        if handles.is_empty() {
            return Ok(());
        }
        let record = self.paths as u32;
        self.paths += 1;
        self.steps += handles.len() as u64;
        for r in 0..self.references.len() {
            let own = (self.references[r].sample == path.sample).then(|| {
                (
                    self.names
                        .get(&path.name)
                        .expect("the first pass named every path"),
                    path.start,
                )
            });
            if !self.assign_chunks(r, handles, own) {
                self.references[r].unplaced += 1;
                self.placed.push(UNPLACED);
                continue;
            }
            if own.is_none() {
                let haplotypes = &mut self.references[r].haplotypes;
                let name = haplotype(&path.name);
                if !haplotypes.contains(name) {
                    haplotypes.insert(name.to_vec());
                }
            }
            self.cut_pieces();
            self.references[r].pieces += self.pieces.len() as u64;
            self.placed.push(Placed {
                first: self.chunk_of[0],
                last: self.chunk_of[handles.len() - 1],
                pieces: self.pieces.len() as u32,
            });
            let pieces = std::mem::take(&mut self.pieces);
            let mut result = self.write_pieces(r, path, handles, record, &pieces);
            if own.is_none() && result.is_ok() {
                result = self.write_skips(r, path, handles, &pieces);
            }
            self.pieces = pieces;
            result?;
        }
        Ok(())
    }

    // Gives every step the chunk its piece is filed under: a reference step
    // its node's, any other step the last reference step's before it (the
    // first reference step's for those that lead). On one of the reference's
    // own paths, `own` (its name id and start), a step takes the chunk that
    // holds its offset. On any other path, a step on a node the reference
    // passes more than once takes the pass `visits_along` picks. False when
    // the path visits no node of the reference.
    fn assign_chunks(&mut self, r: usize, handles: &[u32], own: Option<(u32, u64)>) -> bool {
        let reference = &self.references[r];
        self.chunk_of.clear();
        self.chunk_of.resize(handles.len(), NONE);
        match own {
            Some((name, start)) => {
                for (i, &h) in handles.iter().enumerate() {
                    if reference.on_reference((h >> 1) as usize) {
                        self.chunk_of[i] = self.chunks.of(name, start + self.before[i]);
                    }
                }
            }
            None => {
                let chunks = &self.chunks;
                let chunk_of = &mut self.chunk_of;
                let pass = &mut self.pass;
                pass.clear();
                pass.resize(handles.len(), (NONE, 0));
                visits_along(
                    reference,
                    handles,
                    &self.before,
                    &self.graph.lengths,
                    |i, v| {
                        chunk_of[i] = chunks.of(v.name, v.offset);
                        pass[i] = (v.name, v.offset);
                    },
                );
            }
        }
        let Some(first) = self.chunk_of.iter().copied().find(|&c| c != NONE) else {
            return false;
        };
        let mut current = first;
        for chunk in self.chunk_of.iter_mut() {
            if *chunk == NONE {
                *chunk = current;
            } else {
                current = *chunk;
            }
        }
        if own.is_none() && self.stay > 0 {
            stay_home(
                &mut self.chunk_of,
                handles,
                reference,
                &self.graph.lengths,
                self.stay,
                |chunk, home| self.chunks.reaches(chunk, home),
            );
        }
        true
    }

    // A piece runs while the chunk stays the same.
    fn cut_pieces(&mut self) {
        self.pieces.clear();
        let n = self.chunk_of.len();
        let mut from = 0;
        for i in 1..=n {
            if i == n || self.chunk_of[i] != self.chunk_of[i - 1] {
                self.pieces.push((from, i));
                from = i;
            }
        }
    }

    fn write_pieces(
        &mut self,
        r: usize,
        path: &PathLine,
        handles: &[u32],
        record: u32,
        pieces: &[(usize, usize)],
    ) -> Result<(), String> {
        let reference = self.references[r].sample == path.sample;
        let mut tags = Vec::new();
        for (k, &(a, b)) in pieces.iter().enumerate() {
            let chunk = self.chunk_of[a];
            tags.clear();
            let previous = k.checked_sub(1).and_then(|j| pieces.get(j));
            for (tag, at) in [(b"pv", previous), (b"nx", pieces.get(k + 1))] {
                if let Some(&(c, _)) = at {
                    let there = self.chunk_of[c];
                    push_chunk_tag(&mut tags, tag, &self.chunks, &self.names, chunk, there);
                }
            }
            let before = &self.before;
            self.rows.push(chunk, |out| {
                Piece::write(
                    out,
                    &PieceRef {
                        reference,
                        name: &path.name,
                        frag: path.start,
                        offset: path.start + before[a],
                        piece: k as u32,
                        record,
                        tags: &tags,
                        handles: &handles[a..b],
                    },
                )
            })?;
        }
        Ok(())
    }

    // Writes a `skip` row into each chunk a path jumps over between two of its
    // pieces on one reference sequence, when the jump spans at most
    // SKIP_CHUNKS chunks: `skip path fragStart piece from to refStart refEnd`,
    // where `piece` numbers the piece before the jump, `from` and `to` are the
    // chunks the two pieces are filed under, and refStart-refEnd is the
    // reference between the passes either side of the jump. A chunk gets one
    // skip row per path, from its first jump over the chunk, and none where
    // the path has a piece: in a collapsed repeat a path hops over the same
    // chunks again and again.
    fn write_skips(
        &mut self,
        r: usize,
        path: &PathLine,
        handles: &[u32],
        pieces: &[(usize, usize)],
    ) -> Result<(), String> {
        let lengths = &self.graph.lengths;
        let pass = &self.pass;
        let mut covered: HashSet<u32> = pieces.iter().map(|&(a, _)| self.chunk_of[a]).collect();
        let span = |i: usize| {
            let (name, start) = pass[i];
            (
                name,
                start,
                start + u64::from(lengths[(handles[i] >> 1) as usize]),
            )
        };
        let mut line = Vec::new();
        for (k, pair) in pieces.windows(2).enumerate() {
            let ((a, b), (_, c)) = (pair[0], pair[1]);
            let (Some(i), Some(j)) = (
                (a..b).rev().find(|&i| pass[i].0 != NONE),
                (b..c).find(|&j| pass[j].0 != NONE),
            ) else {
                continue;
            };
            let ((name, i_start, i_end), (other, j_start, j_end)) = (span(i), span(j));
            let (gap_start, gap_end) = match () {
                _ if name != other => continue,
                _ if i_end < j_start => (i_end, j_start),
                _ if j_end < i_start => (j_end, i_start),
                _ => continue,
            };
            let (first, last) = (
                self.chunks.of(name, gap_start),
                self.chunks.of(name, gap_end - 1),
            );
            let (from, to) = (self.chunk_of[a], self.chunk_of[b]);
            let starts = &self.chunks.starts;
            if u64::from(last - first) >= SKIP_CHUNKS
                || starts[from as usize].0 != name
                || starts[to as usize].0 != name
            {
                continue;
            }
            line.clear();
            line.extend_from_slice(b"skip\t");
            line.extend_from_slice(&path.name);
            for n in [
                path.start,
                k as u64,
                starts[from as usize].1,
                starts[to as usize].1,
                gap_start,
                gap_end,
            ] {
                line.push(b'\t');
                push_u64(&mut line, n);
            }
            line.push(b'\n');
            for chunk in first..=last {
                if !covered.insert(chunk) {
                    continue;
                }
                self.rows.push(chunk, |out| {
                    out.push(SKIP_ROW);
                    out.extend_from_slice(&line);
                })?;
                self.references[r].skips += 1;
            }
        }
        Ok(())
    }
}

// Files a run of steps away from the current piece's chunk under that chunk
// when the path comes back to it, the run spends at most `stay` bp on
// reference nodes, one of those nodes is one the reference passes more than
// once, and a reader of the chunk of each node it passes once also reads the
// piece's, as `reaches` says. A step on a node the reference passes more than
// once has no one true chunk, so it needs no reader. Any other run moves the
// piece on to the run's first chunk.
fn stay_home(
    chunk_of: &mut [u32],
    handles: &[u32],
    reference: &Reference,
    lengths: &[u32],
    stay: u64,
    reaches: impl Fn(u32, u32) -> bool,
) {
    let n = chunk_of.len();
    let mut home = chunk_of[0];
    let mut i = 1;
    while i < n {
        if chunk_of[i] == home {
            i += 1;
            continue;
        }
        let mut content = 0u64;
        let mut revisits = false;
        let mut seen = true;
        let mut j = i;
        while j < n && chunk_of[j] != home && content <= stay {
            let id = (handles[j] >> 1) as usize;
            if reference.on_reference(id) {
                content += u64::from(lengths[id]);
                let revisited = reference.revisited.get(id);
                revisits |= revisited;
                seen &= revisited || reaches(chunk_of[j], home);
            }
            j += 1;
        }
        if j < n && chunk_of[j] == home && content <= stay && revisits && seen {
            chunk_of[i..j].fill(home);
            i = j;
        } else {
            home = chunk_of[i];
            i += 1;
        }
    }
}

// Calls `place` with the reference pass each reference step of a path takes.
// A node the reference passes once has one. For a node it passes more than
// once, the path's last placed step predicts an offset, as far along the
// reference as the path has gone since, in the direction their strands agree
// on, and the pass nearest it wins. Placing starts at the path's first step
// on a node the reference passes once and runs outward both ways, so a path
// that follows the reference through a collapsed tandem repeat takes each
// copy in turn.
fn visits_along(
    reference: &Reference,
    handles: &[u32],
    before: &[u64],
    lengths: &[u32],
    mut place: impl FnMut(usize, Visit),
) {
    let id = |i: usize| (handles[i] >> 1) as usize;
    let on = |i: usize| reference.on_reference(id(i));
    let Some(anchor) = (0..handles.len())
        .find(|&i| on(i) && !reference.revisited.get(id(i)))
        .or_else(|| (0..handles.len()).find(|&i| on(i)))
    else {
        return;
    };
    let start = reference.first_visit(id(anchor));
    place(anchor, start);
    let mut from = |order: &mut dyn Iterator<Item = usize>| {
        let (mut i, mut at) = (anchor, start);
        for j in order.filter(|&j| on(j)) {
            let gone = before[j] as i64 - before[i] as i64;
            let expected = if (handles[i] & 1 == 1) == at.reverse {
                at.offset as i64 + gone
            } else {
                at.offset as i64 + i64::from(lengths[id(i)]) - gone - i64::from(lengths[id(j)])
            };
            at = reference.visit_near(id(j), at.name, expected);
            i = j;
            place(j, at);
        }
    };
    from(&mut (anchor + 1..handles.len()));
    from(&mut (0..anchor).rev());
}

// A tag giving the start of the chunk `there`, with its reference sequence's
// name when that differs from the sequence of the chunk `here`.
fn push_chunk_tag(
    out: &mut Vec<u8>,
    tag: &[u8],
    chunks: &Chunks,
    names: &Interner,
    here: u32,
    there: u32,
) {
    let (name, start) = chunks.starts[there as usize];
    out.push(b'\t');
    out.extend_from_slice(tag);
    if name == chunks.starts[here as usize].0 {
        out.extend_from_slice(b":i:");
    } else {
        out.extend_from_slice(b":Z:");
        out.extend_from_slice(&names[name as usize]);
        out.push(b':');
    }
    push_u64(out, start);
}

// Chains the records of each contig in start order, refusing two that start
// at the same place or overlap.
fn link_records(records: &[Record], names: &Interner) -> Result<Vec<Link>, String> {
    let mut order: Vec<u32> = (0..records.len() as u32).collect();
    order.sort_unstable_by_key(|&i| (records[i as usize].name, records[i as usize].start));
    let mut links = vec![
        Link {
            previous: NONE,
            next: NONE,
        };
        records.len()
    ];
    for pair in order.windows(2) {
        let (a, b) = (&records[pair[0] as usize], &records[pair[1] as usize]);
        if a.name != b.name {
            continue;
        }
        let name = text(&names[a.name as usize]);
        if a.start == b.start {
            return Err(format!("path {name} has two lines starting at {}", a.start));
        }
        if b.start < a.end {
            return Err(format!(
                "path {name}: the line covering {}-{} overlaps the one covering {}-{}",
                a.start, a.end, b.start, b.end
            ));
        }
        links[pair[0] as usize].next = pair[1];
        links[pair[1] as usize].previous = pair[0];
    }
    Ok(links)
}

struct TempDir(PathBuf);

impl Drop for TempDir {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

const SORT_BUDGET: usize = 512 << 20;

// The detail records of a sequence's chunks, held on disk until its main rows
// are written, since Tabix needs each sequence's rows together. Chunk `cs` of
// sequence `seq` files its records as `seq~cs`, record k at k × DETAIL_SPACING.
struct Details {
    file: BufWriter<File>,
    path: PathBuf,
    sequence: Option<Vec<u8>>,
    any: bool,
}

impl Details {
    fn create(dir: &std::path::Path, n: usize) -> Result<Details, String> {
        let path = dir.join(format!("details{n}"));
        let file = File::create(&path).map_err(|e| format!("{}: {e}", path.display()))?;
        Ok(Details {
            file: BufWriter::new(file),
            path,
            sequence: None,
            any: false,
        })
    }

    fn add(&mut self, start: u64, records: &routes::Details) -> Result<(), String> {
        let path = &self.path;
        let io = |e: std::io::Error| format!("{}: {e}", path.display());
        for (k, record) in records.iter().enumerate() {
            for row in record {
                self.file.write_all(&start.to_le_bytes()).map_err(io)?;
                self.file.write_all(&(k as u64).to_le_bytes()).map_err(io)?;
                self.file
                    .write_all(&(row.len() as u64).to_le_bytes())
                    .map_err(io)?;
                self.file.write_all(row).map_err(io)?;
                self.any = true;
            }
        }
        Ok(())
    }

    // Writes the held records under the current sequence and empties the file
    fn flush(&mut self, writer: &mut bed::Writer) -> Result<u64, String> {
        let Some(sequence) = self.sequence.as_deref() else {
            return Ok(0);
        };
        if !self.any {
            return Ok(0);
        }
        let path = &self.path;
        let io = |e: std::io::Error| format!("{}: {e}", path.display());
        self.file.flush().map_err(io)?;
        let mut reader = BufReader::new(File::open(path).map_err(io)?);
        let (mut word, mut row, mut line, mut name) =
            ([0u8; 8], Vec::new(), Vec::new(), Vec::new());
        let mut rows = 0;
        let mut read_u64 = |reader: &mut BufReader<File>| -> Result<Option<u64>, String> {
            match reader.read_exact(&mut word) {
                Ok(()) => Ok(Some(u64::from_le_bytes(word))),
                Err(e) if e.kind() == std::io::ErrorKind::UnexpectedEof => Ok(None),
                Err(e) => Err(io(e)),
            }
        };
        while let Some(start) = read_u64(&mut reader)? {
            let k = read_u64(&mut reader)?.ok_or("a detail record ends early")?;
            let len = read_u64(&mut reader)?.ok_or("a detail record ends early")?;
            row.resize(len as usize, 0);
            reader.read_exact(&mut row).map_err(io)?;
            name.clear();
            name.extend_from_slice(sequence);
            name.push(b'~');
            push_u64(&mut name, start);
            let at = k * routes::DETAIL_SPACING;
            line.clear();
            line.extend_from_slice(&name);
            line.push(b'\t');
            push_u64(&mut line, at);
            line.push(b'\t');
            push_u64(&mut line, at + 1);
            line.push(b'\t');
            line.extend_from_slice(&row);
            writer.push(&name, at, at + 1, &line)?;
            rows += 1;
        }
        let file = File::create(path).map_err(io)?;
        self.file = BufWriter::new(file);
        self.any = false;
        Ok(rows)
    }
}

// One reference's walk file as the rows reach it
struct Output {
    writer: bed::Writer,
    path: String,
    rows: u64,
    counts: routes::Counts,
    details: Details,
}

pub fn run(gfa: &str, prefix: &str, options: &Options) -> Result<(), String> {
    if gfa == "-" {
        return Err("--walks reads the GFA twice, so it needs a file, not stdin".into());
    }
    let clock = Instant::now();
    let elapsed = || format!("[{:6.1} s]", clock.elapsed().as_secs_f64());
    let mut names = Interner::default();
    let (graph, references, records) = first_pass(gfa, options, &mut names)?;
    let links = link_records(&records, &names)?;
    let mut ends: HashMap<u32, (u32, u64)> = HashMap::new();
    for (r, reference) in references.iter().enumerate() {
        let mut extend = |name: u32, end: u64| {
            let held = ends.entry(name).or_insert((r as u32, 0));
            held.1 = held.1.max(end);
        };
        let mut on = 0;
        for (id, &placement) in reference.placement.iter().enumerate() {
            if reference.on_reference(id) {
                on += 1;
                extend(
                    placement,
                    reference.offset[id] + u64::from(graph.lengths[id]),
                );
            }
        }
        for (&name, &end) in &reference.path_ends {
            extend(name, end);
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
        graph,
        names,
        chunks,
        references,
        rows: Sorter::new(&temp.0, "rows", SORT_BUDGET),
        placed: Vec::new(),
        paths: 0,
        steps: 0,
        handles: Vec::new(),
        before: Vec::new(),
        chunk_of: Vec::new(),
        pass: Vec::new(),
        pieces: Vec::new(),
        stay: options.stay,
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
            "{}: {} pieces, {} skip rows, {} paths visit no {} node and are left out",
            text(&reference.sample),
            reference.pieces,
            reference.skips,
            reference.unplaced,
            text(&reference.sample)
        );
    }

    let Builder {
        graph,
        names,
        chunks,
        references,
        rows,
        placed,
        ..
    } = builder;
    let threads = thread::available_parallelism().map_or(4, |n| n.get());
    let mut writers = Vec::with_capacity(references.len());
    for reference in &references {
        let path = format!("{prefix}.{}.walks.bed.gz", text(&reference.sample));
        let mut writer = bed::Writer::create(&path)?;
        let longest = reference.longest(&graph.lengths);
        let mut header = format!(
            "#walks\tformat:i:5\tchunk:i:{}\tmaxnode:i:{longest}\tstay:i:{}\tabridge:i:{}\tabridgebytes:i:{}\tskip:i:{SKIP_CHUNKS}\n#reference\t{}\n",
            chunks.size,
            options.stay,
            options.budget.cost,
            options.budget.bytes,
            text(&reference.sample)
        )
        .into_bytes();
        let mut long: Vec<(&[u8], u64, u64)> = reference
            .long_passes(&graph.lengths, chunks.size)
            .into_iter()
            .map(|(name, start, end)| (names[name as usize].as_slice(), start, end))
            .collect();
        long.sort_unstable();
        long.dedup();
        for (name, start, end) in long {
            header.extend_from_slice(b"#long\t");
            header.extend_from_slice(name);
            header.extend_from_slice(format!("\t{start}\t{end}\n").as_bytes());
        }
        for name in &reference.haplotypes {
            header.extend_from_slice(b"#haplotype\t");
            header.extend_from_slice(name);
            header.push(b'\n');
        }
        writer.header(&header)?;
        let details = Details::create(&temp.0, writers.len())?;
        writers.push(Output {
            writer,
            path,
            rows: 0,
            counts: routes::Counts::default(),
            details,
        });
    }
    let sequence_of = |id: usize| graph.sequence(id);
    let sequence = options.sequences.then_some(&sequence_of);
    // Chunks encode in parallel, a batch at a time, and are written in order.
    type Encoded = Result<(Vec<u8>, Vec<usize>, routes::Counts, routes::Details), String>;
    let refs = references.len();
    // the gap to the record before or after a piece's on its contig, and the
    // chunk that record's nearest piece is filed under
    let record_tags = |piece: &mut Piece, chunk: u32| {
        let r = chunks.owner[chunks.starts[chunk as usize].0 as usize] as usize;
        let record = piece.record as usize;
        let link = links[record];
        let here = &records[record];
        if piece.piece == 0 && link.previous != NONE {
            let previous = link.previous as usize;
            piece.tags.extend_from_slice(b"\tpg:i:");
            push_u64(&mut piece.tags, here.start - records[previous].end);
            let last = placed[previous * refs + r].last;
            if last != NONE {
                push_chunk_tag(&mut piece.tags, b"pr", &chunks, &names, chunk, last);
            }
        }
        if piece.piece + 1 == placed[record * refs + r].pieces && link.next != NONE {
            let next = link.next as usize;
            piece.tags.extend_from_slice(b"\tng:i:");
            push_u64(&mut piece.tags, records[next].start - here.end);
            let first = placed[next * refs + r].first;
            if first != NONE {
                push_chunk_tag(&mut piece.tags, b"nr", &chunks, &names, chunk, first);
            }
        }
    };
    let encode = |chunk: u32, raw: &[Vec<u8>]| -> Encoded {
        let (skips, raw): (Vec<&Vec<u8>>, Vec<&Vec<u8>>) =
            raw.iter().partition(|r| r[0] == SKIP_ROW);
        let mut pieces: Vec<Piece> = raw.iter().map(|r| Piece::read(r)).collect();
        for piece in &mut pieces {
            record_tags(piece, chunk);
        }
        let (mut lines, mut ends) = (Vec::new(), Vec::new());
        let mut counts = routes::Counts::default();
        let mut details = routes::Details::new();
        routes::write_chunk(
            &pieces,
            &graph.lengths,
            sequence,
            options.budget,
            &mut counts,
            &mut |rest| {
                lines.extend_from_slice(rest);
                ends.push(lines.len());
                Ok(())
            },
            &mut details,
        )?;
        for skip in skips {
            lines.extend_from_slice(&skip[1..]);
            ends.push(lines.len());
        }
        Ok((lines, ends, counts, details))
    };
    let mut line = Vec::new();
    let mut write_batch = |batch: &mut Vec<(u32, Vec<Vec<u8>>)>| -> Result<(), String> {
        let next = AtomicUsize::new(0);
        let encoded: Vec<Mutex<Option<Encoded>>> = batch.iter().map(|_| Mutex::new(None)).collect();
        thread::scope(|scope| {
            for _ in 0..threads.min(batch.len()) {
                scope.spawn(|| {
                    loop {
                        let k = next.fetch_add(1, Ordering::Relaxed);
                        let Some((chunk, raw)) = batch.get(k) else {
                            break;
                        };
                        *encoded[k].lock().unwrap() = Some(encode(*chunk, raw));
                    }
                });
            }
        });
        for ((chunk, _), slot) in batch.iter().zip(encoded) {
            let (name, start) = chunks.starts[*chunk as usize];
            let name_text = &names[name as usize];
            let (lines, ends, chunk_counts, chunk_details) = slot
                .into_inner()
                .unwrap()
                .expect("every chunk of the batch is encoded")
                .map_err(|e| format!("{}:{start}: {e}", text(name_text)))?;
            let out = &mut writers[chunks.owner[name as usize] as usize];
            if out.details.sequence.as_deref() != Some(name_text.as_slice()) {
                out.rows += out.details.flush(&mut out.writer)?;
                out.details.sequence = Some(name_text.clone());
            }
            out.details.add(start, &chunk_details)?;
            out.counts += chunk_counts;
            let mut from = 0;
            for end in ends {
                line.clear();
                line.extend_from_slice(name_text);
                line.push(b'\t');
                push_u64(&mut line, start);
                line.push(b'\t');
                push_u64(&mut line, start + 1);
                line.push(b'\t');
                line.extend_from_slice(&lines[from..end]);
                out.writer.push(name_text, start, start + 1, &line)?;
                out.rows += 1;
                from = end;
            }
        }
        batch.clear();
        Ok(())
    };
    let batch_size = 4 * threads;
    let mut batch: Vec<(u32, Vec<Vec<u8>>)> = Vec::new();
    rows.merge(|chunk, rest| {
        if batch.last().is_none_or(|(c, _)| *c != chunk) {
            if batch.len() == batch_size {
                write_batch(&mut batch)?;
            }
            batch.push((chunk, Vec::new()));
        }
        batch
            .last_mut()
            .expect("a chunk is open")
            .1
            .push(rest.to_vec());
        Ok(())
    })?;
    write_batch(&mut batch)?;
    drop(write_batch);
    for mut out in writers {
        let rows = out.rows + out.details.flush(&mut out.writer)?;
        let index = out.writer.finish()?;
        let (path, counts) = (out.path, out.counts);
        eprintln!(
            "{} {rows} rows -> {path} (+ .{index}): {} routes, {} walk rows, {} with step counts; {} paths abridged to {} detail walk rows",
            elapsed(),
            counts.routes,
            counts.walks,
            counts.counted,
            counts.abridged,
            counts.detail_walks
        );
    }
    Ok(())
}
