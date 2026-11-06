// The --walks mode: every path of a base-level GFA cut into pieces filed under
// fixed tiles of each reference's coordinate, written as one walk file per
// reference in walk format 7 (ADR 0010): `routes.rs` writes a tile's rows,
// `departures.rs` the departure records, and `units.rs` the units, tables and
// directory. Every line starts with its sequence and the stretch of it the
// line is about. The header unit gives the format, the tile size and the
// options, then the reference, the haplotypes and the holes.

use std::collections::{BTreeSet, HashMap};
use std::fs::{self, File};
use std::io::{BufReader, BufWriter, Read, Write};
use std::path::PathBuf;
use std::sync::Mutex;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::mpsc::{Receiver, sync_channel};
use std::thread;
use std::time::Instant;

use crate::departures::{self, Departure, End, Holes, Own};
use crate::gfa::{blunt_error, is_blunt, parse_u64, split_path_name, text};
use crate::intern::{FastMap, Interner};
use crate::routes::{self, PieceRef, Span, Stretch};
use crate::sorter::{Merged, Sorter};
use crate::units::UnitFile;

pub struct Options {
    pub refs: Vec<String>,
    pub tile: u64,
    pub sequences: bool,
    pub stay: u64,
    pub budget: routes::Budget,
}

const NONE: u32 = u32::MAX;
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

// Refuses a name a walk file's line would read as a header or `#unit` line
fn named(path: PathLine) -> Result<Option<PathLine>, String> {
    if path.name.first() == Some(&b'#') {
        Err(format!(
            "path {} starts with #, which marks a walk file's header and unit lines",
            text(&path.name)
        ))
    } else {
        Ok(Some(path))
    }
}

fn path_line(line: &[u8]) -> Result<Option<PathLine<'_>>, String> {
    let mut cols = line.split(|&b| b == b'\t');
    match cols.next() {
        Some(b"W") => {
            let cols: Vec<&[u8]> = cols.take(6).collect();
            if cols.len() < 6 {
                return Err("W line with too few fields".into());
            }
            named(PathLine {
                sample: cols[0],
                name: [cols[0], cols[1], cols[2]].join(&b'#'),
                start: parse_u64(cols[3], "W line start")?,
                end: Some(parse_u64(cols[4], "W line end")?),
                steps: cols[5],
                walk: true,
            })
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
            named(PathLine {
                sample: name.split(|&b| b == b'#').next().unwrap_or(name),
                name: name.to_vec(),
                start,
                end: None,
                steps: cols[1],
                walk: false,
            })
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
// `visits_of` gives each such node's stretch of it. `holes` gives each of the
// sample's sequences the stretches its lines leave out.
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
    holes: HashMap<u32, Holes>,
    pieces: u64,
    unplaced: u64,
    departures: u64,
    departure_rows: u64,
    haplotypes: BTreeSet<Vec<u8>>,
}

impl Reference {
    fn on_reference(&self, id: usize) -> bool {
        self.placement[id] & OFF_REFERENCE == 0
    }

    // How many times the reference's paths pass node `id`
    fn passes(&self, id: usize) -> u32 {
        match self.visits_of.get(&(id as u32)) {
            Some(&(from, to)) => to - from,
            None => 1,
        }
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

impl Visit {
    // No pass: a step that is route interior
    const INTERIOR: Visit = Visit {
        name: NONE,
        offset: 0,
        reverse: false,
    };
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

// A W or P line with steps: its name id and the stretch of its contig it
// covers.
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
                    if sequence == b"*" {
                        return Err(format!(
                            "segment {id} has no bases, so --sequences can't write them"
                        ));
                    }
                    if id >= sequence_at.len() {
                        sequence_at.resize(id + 1, u64::MAX);
                    }
                    sequence_at[id] = bases.len() as u64;
                    bases.extend_from_slice(sequence);
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
            holes: HashMap::new(),
            pieces: 0,
            unplaced: 0,
            departures: 0,
            departure_rows: 0,
            haplotypes: BTreeSet::new(),
        })
        .collect();
    let mut on_reference: Vec<Stable> = options.refs.iter().map(|_| Stable::default()).collect();
    // by reference, then sequence: the stretches its lines cover
    let mut covers: Vec<HashMap<u32, Vec<(u64, u64)>>> =
        options.refs.iter().map(|_| HashMap::new()).collect();
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
        covers[walk.reference]
            .entry(walk.name)
            .or_default()
            .push((walk.start, walk.start + length));
        let end = references[walk.reference]
            .path_ends
            .entry(walk.name)
            .or_default();
        *end = (*end).max(walk.start + length);
    }
    for (reference, covers) in references.iter_mut().zip(covers) {
        reference.holes = covers
            .into_iter()
            .map(|(name, cover)| (name, Holes::between(cover)))
            .collect();
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
    // by name id: the number of a reference sequence's first chunk, the
    // reference it belongs to, and where it ends
    first: Vec<u32>,
    owner: Vec<u32>,
    end: Vec<u64>,
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
        let mut ends = vec![0; names.len()];
        let mut starts = Vec::new();
        let count: u64 = sequences.iter().map(|&(_, _, _, end)| end / size + 1).sum();
        if count >= u64::from(NONE) {
            return Err("more than 2^32 tiles; use a larger --tile".into());
        }
        for (_, name, reference, end) in sequences {
            first[name as usize] = starts.len() as u32;
            owner[name as usize] = reference;
            ends[name as usize] = end;
            for c in 0..=end / size {
                starts.push((name, c * size));
            }
        }
        Ok(Chunks {
            size,
            first,
            owner,
            end: ends,
            starts,
        })
    }

    fn of(&self, name: u32, offset: u64) -> u32 {
        self.first[name as usize] + (offset / self.size) as u32
    }
}

// A record's first and last steps on one reference sequence S, as a rejoin
// and a leave, and its own sequence for S before the first and after the
// last, which the departures across the contig's records and at its ends
// take up
#[derive(Clone, Copy)]
struct RecordEnds {
    first: End,
    last: End,
    lead: Own,
    tail: Own,
}

// The record after one on its contig, NONE for the last.
#[derive(Clone, Copy)]
struct Link {
    next: u32,
}

struct Builder {
    graph: Graph,
    names: Interner,
    chunks: Chunks,
    stay: u64,
    references: Vec<Reference>,
    rows: Sorter,
    // departure rows, keyed by the first chunk of their sequence
    departures: Sorter,
    // by reference, then (record, sequence name id)
    ends: Vec<FastMap<(u32, u32), RecordEnds>>,
    paths: u64,
    steps: u64,
    handles: Vec<u32>,
    // by step, and one past the last: where it starts on the path
    before: Vec<u64>,
    chunk_of: Vec<u32>,
    // by step of a path off the reference: the reference pass a step on a
    // reference node takes; name NONE for route interior
    pass: Vec<Visit>,
    positions: Vec<u64>,
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
        self.before.push(offset);
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
            let pieces = std::mem::take(&mut self.pieces);
            let mut result = self.write_pieces(r, path, handles, &pieces);
            if own.is_none() && result.is_ok() {
                result = self.record_departures(r, path, handles, record, &pieces);
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
    // passes more than once takes the pass `visits_along` picks, and `pass`
    // keeps every step's. False when the path visits no node of the
    // reference.
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
                pass.resize(handles.len(), Visit::INTERIOR);
                visits_along(
                    &Along {
                        reference,
                        handles,
                        before: &self.before,
                        lengths: &self.graph.lengths,
                    },
                    |i, v| {
                        chunk_of[i] = chunks.of(v.name, v.offset);
                        pass[i] = v;
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
                &mut self.pass,
                &Along {
                    reference,
                    handles,
                    before: &self.before,
                    lengths: &self.graph.lengths,
                },
                &self.chunks,
                self.stay,
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
        pieces: &[(usize, usize)],
    ) -> Result<(), String> {
        let reference = self.references[r].sample == path.sample;
        self.positions.clear();
        if !reference {
            self.positions.extend(self.pass.iter().map(|v| {
                if v.name == NONE {
                    routes::OFF
                } else {
                    v.offset
                }
            }));
        }
        for (k, &(a, b)) in pieces.iter().enumerate() {
            let chunk = self.chunk_of[a];
            let before = &self.before;
            let positions = if reference {
                &[][..]
            } else {
                &self.positions[a..b]
            };
            self.rows.push(chunk, |out| {
                PieceRef {
                    reference,
                    name: &path.name,
                    frag: path.start,
                    offset: path.start + before[a],
                    piece: k as u32,
                    handles: &handles[a..b],
                    positions,
                }
                .write(out)
            })?;
        }
        Ok(())
    }

    // Files a departure for each pair of consecutive steps of a path on one
    // reference sequence that are not adjacent there and lie in different
    // pieces; a reader computes one inside a piece from its walk row. Keeps
    // each sequence's first and last steps in `ends` for the departures
    // across the contig's records.
    fn record_departures(
        &mut self,
        r: usize,
        path: &PathLine,
        handles: &[u32],
        record: u32,
        pieces: &[(usize, usize)],
    ) -> Result<(), String> {
        let n = handles.len();
        let lengths = &self.graph.lengths;
        let length = |i: usize| u64::from(lengths[(handles[i] >> 1) as usize]);
        let (pass, before) = (&self.pass, &self.before);
        let reference = &self.references[r];
        let end = |i: usize, leave: bool| {
            let passes = reference.passes((handles[i] >> 1) as usize);
            step_end(&self.chunks, handles[i], pass[i], length(i), passes, leave)
        };
        let piece_of = |i: usize| pieces.partition_point(|&(_, b)| b <= i);
        let own = |from: usize, to: usize| Own {
            bp: before[to] - before[from],
            missing: 0,
        };
        // by sequence: its first and last steps so far
        let mut on: Vec<(u32, usize, usize)> = Vec::new();
        let mut filed = (0, 0);
        for j in (0..n).filter(|&j| pass[j].name != NONE) {
            let s = pass[j].name;
            match on.iter_mut().find(|(name, _, _)| *name == s) {
                Some((_, _, last)) => {
                    let i = *last;
                    let (leave, rejoin) = (end(i, true), end(j, false));
                    let between = own(i + 1, j);
                    if piece_of(i) != piece_of(j)
                        && !reference.holes[&s].adjacent(between.bp, &leave, &rejoin)
                    {
                        let departure = Departure {
                            path: &path.name,
                            hap_start: path.start + before[i + 1],
                            own: between,
                            leave,
                            rejoin,
                        };
                        filed.0 += 1;
                        filed.1 += departure.file(
                            self.chunks.first[s as usize],
                            self.chunks.size,
                            &mut self.departures,
                        )?;
                    }
                    *last = j;
                }
                None => on.push((s, j, j)),
            }
        }
        let ends = &mut self.ends[r];
        for (s, first, last) in on {
            ends.insert(
                (record, s),
                RecordEnds {
                    first: end(first, false),
                    last: end(last, true),
                    lead: own(0, first),
                    tail: own(last + 1, n),
                },
            );
        }
        let reference = &mut self.references[r];
        reference.departures += filed.0;
        reference.departure_rows += filed.1;
        Ok(())
    }

    // Files the departures across each contig's records, from a record's last
    // step on a reference sequence to the next record's first step there.
    fn record_contig_departures(
        &mut self,
        records: &[Record],
        links: &[Link],
    ) -> Result<(), String> {
        for r in 0..self.references.len() {
            let ends = std::mem::take(&mut self.ends[r]);
            let mut filed = (0, 0);
            for (&(k, s), here) in &ends {
                let record = &records[k as usize];
                let (next, between) =
                    contig_after(records, links, k, |j| ends.contains_key(&(j, s)));
                if next != NONE {
                    let there = &ends[&(next, s)];
                    let own = here.tail + between + there.lead;
                    if !self.references[r].holes[&s].adjacent(own.bp, &here.last, &there.first) {
                        let departure = Departure {
                            path: &self.names[record.name as usize],
                            hap_start: record.end - here.tail.bp,
                            own,
                            leave: here.last,
                            rejoin: there.first,
                        };
                        filed.0 += 1;
                        filed.1 += departure.file(
                            self.chunks.first[s as usize],
                            self.chunks.size,
                            &mut self.departures,
                        )?;
                    }
                }
            }
            let reference = &mut self.references[r];
            reference.departures += filed.0;
            reference.departure_rows += filed.1;
        }
        Ok(())
    }
}

// One end of a departure: the step `handle`, of `length` bp, on the pass
// `at` of the reference's `passes` over its node, as the leave or the rejoin
fn step_end(chunks: &Chunks, handle: u32, at: Visit, length: u64, passes: u32, leave: bool) -> End {
    let against = (handle & 1 == 1) != at.reverse;
    let on_start = against == leave;
    let bp = if on_start {
        at.offset
    } else {
        at.offset + length
    };
    let base = if length == 0 || on_start { bp } else { bp - 1 };
    End {
        bp,
        against,
        base: base.min(chunks.end[at.name as usize].saturating_sub(1)),
        node: (at.offset, at.offset + length),
        passes,
    }
}

// The nearest record after record `k` on its contig with a step on S, NONE
// for none, and the contig's own sequence for S between the two: the records
// between, which have no step on S, and the gaps between the records, which
// no line covers. `on_s` says whether a record has a step on S.
fn contig_after(
    records: &[Record],
    links: &[Link],
    k: u32,
    on_s: impl Fn(u32) -> bool,
) -> (u32, Own) {
    let gap = |from: u32, to: u32| records[to as usize].start - records[from as usize].end;
    let mut own = Own::default();
    let mut edge = k;
    let mut at = links[k as usize].next;
    while at != NONE && !on_s(at) {
        let (record, missing) = (&records[at as usize], gap(edge, at));
        own = own
            + Own {
                bp: missing + record.end - record.start,
                missing,
            };
        edge = at;
        at = links[at as usize].next;
    }
    if at != NONE {
        let missing = gap(edge, at);
        own = own
            + Own {
                bp: missing,
                missing,
            };
    }
    (at, own)
}

// A path's steps against a reference, for placing them on its passes
struct Along<'a> {
    reference: &'a Reference,
    handles: &'a [u32],
    before: &'a [u64],
    lengths: &'a [u32],
}

impl Along<'_> {
    fn id(&self, i: usize) -> usize {
        (self.handles[i] >> 1) as usize
    }

    fn on(&self, i: usize) -> bool {
        self.reference.on_reference(self.id(i))
    }

    fn length(&self, i: usize) -> i64 {
        i64::from(self.lengths[self.id(i)])
    }

    // The offset step `j` takes from step `i` on the pass `at`: as far along
    // the reference as the path has gone between them, in the direction their
    // strands agree on
    fn predict(&self, i: usize, at: Visit, j: usize) -> i64 {
        let gone = self.before[j] as i64 - self.before[i] as i64;
        if (self.handles[i] & 1 == 1) == at.reverse {
            at.offset as i64 + gone
        } else {
            at.offset as i64 + self.length(i) - gone - self.length(j)
        }
    }
}

// Keeps a run of steps away from the current piece's chunk, its home, in
// that chunk when the path comes back to it, the run spends at most `stay`
// bp on reference nodes and holds no node the reference passes once, and
// each of its steps on a node the home chunk's R holds has a pass there
// within `stay` bp of where `visits_along` predicts it from the run's
// previous placed step. Such a step moves to the nearest such pass, and a
// step on a node the home chunk's R lacks becomes route interior. Any other
// run moves the piece on to the run's first chunk.
fn stay_home(chunk_of: &mut [u32], pass: &mut [Visit], along: &Along, chunks: &Chunks, stay: u64) {
    let n = chunk_of.len();
    let mut home = chunk_of[0];
    let mut i = 1;
    let mut moves: Vec<(usize, Visit)> = Vec::new();
    while i < n {
        if chunk_of[i] == home {
            i += 1;
        } else {
            let mut content = 0;
            let mut once = false;
            let mut j = i;
            while j < n && chunk_of[j] != home && content <= stay {
                if along.on(j) {
                    content += along.length(j) as u64;
                    once |= !along.reference.revisited.get(along.id(j));
                }
                j += 1;
            }
            let returns = j < n && chunk_of[j] == home && content <= stay && !once;
            if returns && rehome(&mut moves, pass, along, chunks, home, i..j, stay) {
                for &(k, v) in &moves {
                    pass[k] = v;
                }
                chunk_of[i..j].fill(home);
                i = j;
            } else {
                home = chunk_of[i];
                i += 1;
            }
        }
    }
}

// The pass in chunk `home` each placed step of `run` moves to, INTERIOR for
// one on a node the chunk's R lacks, into `moves`; false where a step's
// nearest pass there lies more than `stay` bp from where the run's previous
// placed step predicts it
fn rehome(
    moves: &mut Vec<(usize, Visit)>,
    pass: &[Visit],
    along: &Along,
    chunks: &Chunks,
    home: u32,
    run: std::ops::Range<usize>,
    stay: u64,
) -> bool {
    moves.clear();
    let (name, start) = chunks.starts[home as usize];
    let reference = along.reference;
    let mut previous = (0..run.start)
        .rev()
        .find(|&k| pass[k].name != NONE)
        .map(|k| (k, pass[k]));
    run.filter(|&k| pass[k].name != NONE).all(|k| {
        let (from, to) = reference.visits_of[&(along.id(k) as u32)];
        let visits = &reference.visits[from as usize..to as usize];
        let lo = visits.partition_point(|v| (v.name, v.offset) < (name, start));
        let hi = visits.partition_point(|v| (v.name, v.offset) < (name, start + chunks.size));
        let here = &visits[lo..hi];
        if here.is_empty() {
            moves.push((k, Visit::INTERIOR));
            true
        } else {
            let nearest = previous.map(|(p, at)| {
                let expected = along.predict(p, at, k);
                let distance = |v: &Visit| (v.offset as i64 - expected).unsigned_abs();
                let nearest = *here
                    .iter()
                    .min_by_key(|v| distance(v))
                    .expect("a pass in the home chunk");
                (nearest, distance(&nearest))
            });
            match nearest {
                Some((nearest, distance)) if distance <= stay => {
                    moves.push((k, nearest));
                    previous = Some((k, nearest));
                    true
                }
                _ => false,
            }
        }
    })
}

// Calls `place` with the reference pass each reference step of a path takes.
// A node the reference passes once has one. For a node it passes more than
// once, the path's last placed step predicts an offset, as far along the
// reference as the path has gone since, in the direction their strands agree
// on, and the pass nearest it wins. Placing starts at the path's first step
// on a node the reference passes once and runs outward both ways, so a path
// that follows the reference through a collapsed tandem repeat takes each
// copy in turn.
fn visits_along(along: &Along, mut place: impl FnMut(usize, Visit)) {
    let (reference, n) = (along.reference, along.handles.len());
    let anchor = (0..n)
        .find(|&i| along.on(i) && !reference.revisited.get(along.id(i)))
        .or_else(|| (0..n).find(|&i| along.on(i)));
    if let Some(anchor) = anchor {
        let start = reference.first_visit(along.id(anchor));
        place(anchor, start);
        let mut from = |order: &mut dyn Iterator<Item = usize>| {
            let (mut i, mut at) = (anchor, start);
            for j in order.filter(|&j| along.on(j)) {
                at = reference.visit_near(along.id(j), at.name, along.predict(i, at, j));
                i = j;
                place(j, at);
            }
        };
        from(&mut (anchor + 1..n));
        from(&mut (0..anchor).rev());
    }
}

// Chains the records of each contig in start order, refusing two that start
// at the same place or overlap.
fn link_records(records: &[Record], names: &Interner) -> Result<Vec<Link>, String> {
    let mut order: Vec<u32> = (0..records.len() as u32).collect();
    order.sort_unstable_by_key(|&i| (records[i as usize].name, records[i as usize].start));
    let mut links = vec![Link { next: NONE }; records.len()];
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
const DEPARTURE_SORT_BUDGET: usize = 128 << 20;

// A tile's or a detail record's lines, each starting with the sequence and
// its piece's span, or for a row of the tile's dictionary the unit's extent:
// the union of its ref rows' stretches and its pieces' spans
struct Unit {
    extent: Span,
    text: Vec<u8>,
    lines: u64,
}

fn unit_of(seq: &[u8], rows: &[(Stretch, &[u8])]) -> Option<Unit> {
    let extent = rows
        .iter()
        .filter_map(|&(stretch, _)| match stretch {
            Stretch::Piece(span) | Stretch::Ref(span) => Some(span),
            Stretch::Dictionary => None,
        })
        .reduce(|(a, b), (c, d)| (a.min(c), b.max(d)))?;
    let mut text = Vec::new();
    for &(stretch, row) in rows {
        let (lo, hi) = match stretch {
            Stretch::Piece(span) => span,
            Stretch::Ref(_) | Stretch::Dictionary => extent,
        };
        text.extend_from_slice(seq);
        text.push(b'\t');
        push_u64(&mut text, lo);
        text.push(b'\t');
        push_u64(&mut text, hi);
        text.push(b'\t');
        text.extend_from_slice(row);
    }
    Some(Unit {
        extent,
        text,
        lines: rows.len() as u64,
    })
}

// The detail records of the sequence being written, held on disk until its
// tiles and departure blocks are written: each as its tile's start, its
// number there, its extent and its lines
struct Details {
    file: BufWriter<File>,
    path: PathBuf,
}

impl Details {
    fn create(dir: &std::path::Path, n: usize) -> Result<Details, String> {
        let path = dir.join(format!("details{n}"));
        let file = File::create(&path).map_err(|e| format!("{}: {e}", path.display()))?;
        Ok(Details {
            file: BufWriter::new(file),
            path,
        })
    }

    fn add(&mut self, start: u64, k: usize, unit: &Unit) -> Result<(), String> {
        let path = &self.path;
        let io = |e: std::io::Error| format!("{}: {e}", path.display());
        let (lo, hi) = unit.extent;
        for n in [start, k as u64, lo, hi, unit.lines, unit.text.len() as u64] {
            self.file.write_all(&n.to_le_bytes()).map_err(io)?;
        }
        self.file.write_all(&unit.text).map_err(io)
    }

    // Writes the held records as `detail` units of `seq`, each named by its
    // tile's start and its number there, and empties the file. Returns how
    // many lines they hold.
    fn flush(&mut self, seq: &[u8], out: &mut UnitFile) -> Result<u64, String> {
        let path = &self.path;
        let io = |e: std::io::Error| format!("{}: {e}", path.display());
        self.file.flush().map_err(io)?;
        let mut reader = BufReader::new(File::open(path).map_err(io)?);
        let (mut word, mut text) = ([0u8; 8], Vec::new());
        let mut lines = 0;
        let mut read_u64 = |reader: &mut BufReader<File>| -> Result<Option<u64>, String> {
            match reader.read_exact(&mut word) {
                Ok(()) => Ok(Some(u64::from_le_bytes(word))),
                Err(e) if e.kind() == std::io::ErrorKind::UnexpectedEof => Ok(None),
                Err(e) => Err(io(e)),
            }
        };
        while let Some(start) = read_u64(&mut reader)? {
            let mut next = || -> Result<u64, String> {
                read_u64(&mut reader)?.ok_or_else(|| "a detail record ends early".into())
            };
            let (k, lo, hi, count, len) = (next()?, next()?, next()?, next()?, next()?);
            text.resize(len as usize, 0);
            reader.read_exact(&mut text).map_err(io)?;
            out.begin(seq, (lo, hi), "detail", &format!("{start}:{k}"))?;
            out.write(&text)?;
            out.end()?;
            lines += count;
        }
        self.file = BufWriter::new(File::create(path).map_err(io)?);
        Ok(lines)
    }
}

// One reference's walk file as the units reach it
struct Output {
    file: UnitFile,
    path: String,
    lines: u64,
    counts: routes::Counts,
    details: Details,
}

// The walk files, written in file order: each reference sequence's tiles
// with its departure blocks between them by start, a tile before the blocks
// that start with it, then its detail records, then its table
struct Outputs<'a> {
    outputs: Vec<Output>,
    departures: Merged,
    chunks: &'a Chunks,
    names: &'a Interner,
    // every reference sequence in file order, and how many are written
    sequences: Vec<u32>,
    done: usize,
}

impl Outputs<'_> {
    // Writes the departure blocks of sequence `name` that start before `until`
    fn departures(&mut self, name: u32, until: u64) -> Result<(), String> {
        let key = self.chunks.first[name as usize];
        let seq = &self.names[name as usize];
        let out = &mut self.outputs[self.chunks.owner[name as usize] as usize];
        let mut open = None;
        let mut line = Vec::new();
        while let Some((k, row)) = self.departures.peek() {
            let filed = departures::unfile(row);
            if k != key || filed.block.0 >= until {
                break;
            }
            if open != Some(filed.block) {
                if open.is_some() {
                    out.file.end()?;
                }
                let (start, size) = filed.block;
                out.file
                    .begin(seq, (start, start + size), "departures", &size.to_string())?;
                open = Some(filed.block);
            }
            line.clear();
            line.extend_from_slice(seq);
            line.push(b'\t');
            push_u64(&mut line, filed.extent.0);
            line.push(b'\t');
            push_u64(&mut line, filed.extent.1);
            line.push(b'\t');
            line.extend_from_slice(filed.body);
            line.push(b'\n');
            out.file.write(&line)?;
            out.lines += 1;
            self.departures.advance()?;
        }
        if open.is_some() {
            out.file.end()?;
        }
        Ok(())
    }

    // Ends every sequence before `name` in file order, or every one left
    fn close_before(&mut self, name: Option<u32>) -> Result<(), String> {
        while let Some(&s) = self.sequences.get(self.done)
            && Some(s) != name
        {
            self.departures(s, u64::MAX)?;
            let seq = &self.names[s as usize];
            let out = &mut self.outputs[self.chunks.owner[s as usize] as usize];
            out.lines += out.details.flush(seq, &mut out.file)?;
            out.file.table(seq)?;
            self.done += 1;
        }
        Ok(())
    }

    fn tile(&mut self, chunk: u32, tile: &Unit, details: &[Unit]) -> Result<(), String> {
        let (name, start) = self.chunks.starts[chunk as usize];
        self.close_before(Some(name))?;
        self.departures(name, start)?;
        let seq = &self.names[name as usize];
        let out = &mut self.outputs[self.chunks.owner[name as usize] as usize];
        out.file
            .begin(seq, tile.extent, "tile", &start.to_string())?;
        out.file.write(&tile.text)?;
        out.file.end()?;
        out.lines += tile.lines;
        for (k, record) in details.iter().enumerate() {
            out.details.add(start, k, record)?;
        }
        Ok(())
    }

    // Returns each file's path, lines, counts and units
    fn finish(mut self) -> Result<Vec<(String, u64, routes::Counts, u64)>, String> {
        self.close_before(None)?;
        if self.departures.peek().is_some() {
            Err("departure lines of no reference sequence are left unwritten".into())
        } else {
            self.outputs
                .into_iter()
                .map(|out| Ok((out.path, out.lines, out.counts, out.file.finish()?)))
                .collect()
        }
    }
}

// The process's peak resident memory in GiB, where /proc says
fn peak_memory() -> Option<f64> {
    let status = fs::read_to_string("/proc/self/status").ok()?;
    let line = status.lines().find(|l| l.starts_with("VmHWM:"))?;
    let kb: f64 = line.split_whitespace().nth(1)?.parse().ok()?;
    Some(kb / (1 << 20) as f64)
}

pub fn run(gfa: &str, prefix: &str, options: &Options) -> Result<(), String> {
    if gfa == "-" {
        return Err("--walks reads the GFA twice, so it needs a file, not stdin".into());
    }
    let clock = Instant::now();
    let elapsed = || {
        format!(
            "[{:6.1} s{}]",
            clock.elapsed().as_secs_f64(),
            peak_memory().map_or(String::new(), |gib| format!(", {gib:.1} GiB peak"))
        )
    };
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
    let chunks = Chunks::new(options.tile, &ends, &names)?;

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
        departures: Sorter::new(&temp.0, "departures", DEPARTURE_SORT_BUDGET),
        ends: options.refs.iter().map(|_| FastMap::default()).collect(),
        paths: 0,
        steps: 0,
        handles: Vec::new(),
        before: Vec::new(),
        chunk_of: Vec::new(),
        pass: Vec::new(),
        positions: Vec::new(),
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
    builder.record_contig_departures(&records, &links)?;
    eprintln!(
        "{} {} paths, {} steps",
        elapsed(),
        builder.paths,
        builder.steps
    );
    for reference in &builder.references {
        eprintln!(
            "{}: {} pieces, {} departure records in {} rows, {} paths visit no {} node and are left out",
            text(&reference.sample),
            reference.pieces,
            reference.departures,
            reference.departure_rows,
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
        departures,
        ..
    } = builder;
    let threads = thread::available_parallelism().map_or(4, |n| n.get());
    let mut outputs = Vec::with_capacity(references.len());
    for reference in &references {
        let path = format!("{prefix}.{}.walks.gz", text(&reference.sample));
        let mut header = format!(
            "#walks\tformat:i:7\ttile:i:{}\trevisited:i:{}\tstay:i:{}\tabridge:i:{}\tabridgebytes:i:{}\n#reference\t{}\n",
            chunks.size,
            reference.visits_of.len(),
            options.stay,
            options.budget.cost,
            options.budget.bytes,
            text(&reference.sample)
        )
        .into_bytes();
        for name in &reference.haplotypes {
            header.extend_from_slice(b"#haplotype\t");
            header.extend_from_slice(name);
            header.push(b'\n');
        }
        let mut holes: Vec<(&[u8], u64, u64)> = reference
            .holes
            .iter()
            .flat_map(|(&name, holes)| {
                let name = names[name as usize].as_slice();
                holes
                    .spans()
                    .iter()
                    .map(move |&(start, end)| (name, start, end))
            })
            .collect();
        holes.sort_unstable();
        for (name, start, end) in holes {
            header.extend_from_slice(b"#hole\t");
            header.extend_from_slice(name);
            header.extend_from_slice(format!("\t{start}\t{end}\n").as_bytes());
        }
        let file = UnitFile::create(&path, &header, threads)?;
        let details = Details::create(&temp.0, outputs.len())?;
        outputs.push(Output {
            file,
            path,
            lines: 0,
            counts: routes::Counts::default(),
            details,
        });
    }
    let mut sequences: Vec<u32> = chunks.starts.iter().map(|&(name, _)| name).collect();
    sequences.dedup();
    let mut outputs = Outputs {
        outputs,
        departures: departures.merged()?,
        chunks: &chunks,
        names: &names,
        sequences,
        done: 0,
    };
    let sequence_of = |id: usize| graph.sequence(id);
    let sequence = options.sequences.then_some(&sequence_of);
    // Tiles encode in parallel, a batch at a time, and are written in order.
    type Encoded = Result<(Unit, Vec<Unit>, routes::Counts), String>;
    let encode = |chunk: u32, raw: &[Vec<u8>]| -> Encoded {
        let (name, _) = chunks.starts[chunk as usize];
        let reference = &references[chunks.owner[name as usize] as usize];
        let seq = &names[name as usize];
        let (mut lines, mut ends) = (Vec::new(), Vec::new());
        let mut counts = routes::Counts::default();
        let mut details = routes::Details::new();
        routes::write_chunk(
            raw,
            routes::Nodes {
                lengths: &graph.lengths,
                passes: &|id| reference.passes(id),
            },
            sequence,
            options.budget,
            &mut counts,
            &mut |stretch, rest| {
                lines.extend_from_slice(rest);
                ends.push((stretch, lines.len()));
                Ok(())
            },
            &mut details,
        )?;
        let mut from = 0;
        let rows: Vec<(Stretch, &[u8])> = ends
            .iter()
            .map(|&(stretch, end)| {
                let row = &lines[from..end];
                from = end;
                (stretch, row)
            })
            .collect();
        let tile = unit_of(seq, &rows).ok_or("a tile with no step on the reference")?;
        let details = details
            .iter()
            .map(|record| {
                let rows: Vec<(Stretch, &[u8])> = record
                    .iter()
                    .map(|(span, row)| (*span, row.as_slice()))
                    .collect();
                unit_of(seq, &rows).ok_or("a detail record with no step on the reference")
            })
            .collect::<Result<_, _>>()?;
        Ok((tile, details, counts))
    };
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
            let (tile, details, counts) = slot
                .into_inner()
                .unwrap()
                .expect("every tile of the batch is encoded")
                .map_err(|e| format!("{}:{start}: {e}", text(&names[name as usize])))?;
            outputs.outputs[chunks.owner[name as usize] as usize].counts += counts;
            outputs.tile(*chunk, &tile, &details)?;
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
            .expect("a tile is open")
            .1
            .push(rest.to_vec());
        Ok(())
    })?;
    write_batch(&mut batch)?;
    drop(write_batch);
    for (path, lines, counts, units) in outputs.finish()? {
        eprintln!(
            "{} {lines} lines in {units} units -> {path} (+ .idx): {} routes, {} walk rows, {} copies named; {} paths abridged to {} detail walk rows",
            elapsed(),
            counts.routes,
            counts.walks,
            counts.copies,
            counts.abridged,
            counts.detail_walks
        );
    }
    Ok(())
}
