// The --walks mode: every path of a base-level GFA cut into pieces filed under
// fixed chunks of each reference's coordinate, written as one Tabix-indexed
// BED file per reference in format 2 (`routes.rs` writes a chunk's rows). A
// row's interval is the first base of its chunk: a full-chunk interval would
// share a Tabix bin with the next chunk, and a query would pull both. Header
// lines give the format, the chunk size and the longest node, then the
// reference and the haplotypes.

use std::collections::{BTreeSet, HashMap};
use std::fs;
use std::io::Read;
use std::path::PathBuf;
use std::sync::Mutex;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::mpsc::{Receiver, sync_channel};
use std::thread;
use std::time::Instant;

use crate::bed;
use crate::gfa::{blunt_error, is_blunt, parse_u64, split_path_name, text};
use crate::intern::Interner;
use crate::routes::{self, Piece, PieceRef};
use crate::sorter::Sorter;

pub struct Options {
    pub refs: Vec<String>,
    pub chunk: u64,
    pub sequences: bool,
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
// starts on that sequence, and its steps as handles, 2 * id + reverse.
struct PathLine<'a> {
    sample: &'a [u8],
    name: Vec<u8>,
    start: u64,
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
// last first-visited node.
struct Reference {
    sample: Vec<u8>,
    walks: u64,
    placement: Vec<u32>,
    offset: Vec<u64>,
    path_ends: HashMap<u32, u64>,
    pieces: u64,
    unplaced: u64,
    haplotypes: BTreeSet<Vec<u8>>,
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

    fn visit(&mut self, names: &Interner, name: u32, start: u64, ids: &[u32], lengths: &[u32]) {
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
    }
}

// Pass 1: node lengths (and sequences), every reference sample's paths,
// which give each node they visit a reference coordinate, and every path's
// claim on the nodes off the references.
fn first_pass(
    gfa: &str,
    options: &Options,
    names: &mut Interner,
) -> Result<(Graph, Vec<Reference>), String> {
    let mut lengths: Vec<u32> = Vec::new();
    let mut sequence_at: Vec<u64> = Vec::new();
    let mut bases = Vec::new();
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
            path_ends: HashMap::new(),
            pieces: 0,
            unplaced: 0,
            haplotypes: BTreeSet::new(),
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
                text(&names[walk.name as usize])
            ));
        }
        on_reference[walk.reference].visit(names, walk.name, walk.start, &walk.ids, &lengths);
        let length: u64 = walk
            .ids
            .iter()
            .map(|&id| u64::from(lengths[id as usize]))
            .sum();
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
    Ok((
        Graph {
            lengths,
            sequence_at,
            bases,
        },
        references,
    ))
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
}

struct Builder {
    graph: Graph,
    names: Interner,
    chunks: Chunks,
    references: Vec<Reference>,
    rows: Sorter,
    paths: u64,
    steps: u64,
    handles: Vec<u32>,
    before: Vec<u64>,
    chunk_of: Vec<u32>,
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
        if handles.is_empty() {
            return Ok(());
        }
        self.paths += 1;
        self.steps += handles.len() as u64;
        self.before.clear();
        let mut offset = 0u64;
        for &h in handles {
            self.before.push(offset);
            offset += self.graph.length(path, h)?;
        }
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
            let result = self.write_pieces(r, path, handles, &pieces);
            self.pieces = pieces;
            result?;
        }
        Ok(())
    }

    // Gives every step the chunk its piece is filed under: a reference step
    // its node's, any other step the last reference step's before it (the
    // first reference step's for those that lead). On one of the reference's
    // own paths, `own` (its name id and start), a step takes the chunk that
    // holds its offset, so a later visit to a node is filed where the path is, not
    // at the node's first visit. False when the path visits no node of the
    // reference.
    fn assign_chunks(&mut self, r: usize, handles: &[u32], own: Option<(u32, u64)>) -> bool {
        let reference = &self.references[r];
        self.chunk_of.clear();
        let mut current = NONE;
        for (i, &h) in handles.iter().enumerate() {
            let id = (h >> 1) as usize;
            if reference.on_reference(id) {
                current = match own {
                    Some((name, start)) => self.chunks.of(name, start + self.before[i]),
                    None => self
                        .chunks
                        .of(reference.placement[id], reference.offset[id]),
                };
            }
            self.chunk_of.push(current);
        }
        let Some(first) = self.chunk_of.iter().copied().find(|&c| c != NONE) else {
            return false;
        };
        for chunk in self.chunk_of.iter_mut().take_while(|c| **c == NONE) {
            *chunk = first;
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
        let mut tags = Vec::new();
        for (k, &(a, b)) in pieces.iter().enumerate() {
            let chunk = self.chunk_of[a];
            let (chunks, names, chunk_of) = (&self.chunks, &self.names, &self.chunk_of);
            // where the piece before or after this one is filed: its chunk's
            // start, with the reference sequence's name when it differs
            let neighbour = |out: &mut Vec<u8>, tag: &[u8], at: Option<&(usize, usize)>| {
                if let Some(&(c, _)) = at {
                    let (name, start) = chunks.starts[chunk_of[c] as usize];
                    out.push(b'\t');
                    out.extend_from_slice(tag);
                    if name == chunks.starts[chunk as usize].0 {
                        out.extend_from_slice(b":i:");
                    } else {
                        out.extend_from_slice(b":Z:");
                        out.extend_from_slice(&names[name as usize]);
                        out.push(b':');
                    }
                    push_u64(out, start);
                }
            };
            tags.clear();
            neighbour(
                &mut tags,
                b"pv",
                k.checked_sub(1).and_then(|j| pieces.get(j)),
            );
            neighbour(&mut tags, b"nx", pieces.get(k + 1));
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
                        tags: &tags,
                        handles: &handles[a..b],
                    },
                )
            })?;
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
    let mut names = Interner::default();
    let (graph, references) = first_pass(gfa, options, &mut names)?;
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
        paths: 0,
        steps: 0,
        handles: Vec::new(),
        before: Vec::new(),
        chunk_of: Vec::new(),
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
            "{}: {} pieces, {} paths visit no {} node and are left out",
            text(&reference.sample),
            reference.pieces,
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
        ..
    } = builder;
    let longest = graph
        .lengths
        .iter()
        .filter(|&&l| l != NONE)
        .max()
        .copied()
        .unwrap_or(0);
    let threads = thread::available_parallelism().map_or(4, |n| n.get());
    let mut writers = Vec::with_capacity(references.len());
    for reference in &references {
        let path = format!("{prefix}.{}.walks.bed.gz", text(&reference.sample));
        let mut writer = bed::Writer::create_parallel(&path, threads)?;
        let mut header = format!(
            "#walks\tformat:i:2\tchunk:i:{}\tmaxnode:i:{longest}\n#reference\t{}\n",
            chunks.size,
            text(&reference.sample)
        )
        .into_bytes();
        for name in &reference.haplotypes {
            header.extend_from_slice(b"#haplotype\t");
            header.extend_from_slice(name);
            header.push(b'\n');
        }
        writer.header(&header)?;
        writers.push((writer, path, 0u64, routes::Counts::default()));
    }
    let sequence_of = |id: usize| graph.sequence(id);
    let sequence = options.sequences.then_some(&sequence_of);
    // Chunks encode in parallel, a batch at a time, and are written in order.
    type Encoded = Result<(Vec<u8>, Vec<usize>, routes::Counts), String>;
    let encode = |raw: &[Vec<u8>]| -> Encoded {
        let pieces: Vec<Piece> = raw.iter().map(|r| Piece::read(r)).collect();
        let (mut lines, mut ends) = (Vec::new(), Vec::new());
        let mut counts = routes::Counts::default();
        routes::write_chunk(
            &pieces,
            &graph.lengths,
            sequence,
            &mut counts,
            &mut |rest| {
                lines.extend_from_slice(rest);
                ends.push(lines.len());
                Ok(())
            },
        )?;
        Ok((lines, ends, counts))
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
                        let Some((_, raw)) = batch.get(k) else {
                            break;
                        };
                        *encoded[k].lock().unwrap() = Some(encode(raw));
                    }
                });
            }
        });
        for ((chunk, _), slot) in batch.iter().zip(encoded) {
            let (name, start) = chunks.starts[*chunk as usize];
            let name_text = &names[name as usize];
            let (lines, ends, chunk_counts) = slot
                .into_inner()
                .unwrap()
                .expect("every chunk of the batch is encoded")
                .map_err(|e| format!("{}:{start}: {e}", text(name_text)))?;
            let (writer, _, rows, counts) = &mut writers[chunks.owner[name as usize] as usize];
            counts.routes += chunk_counts.routes;
            counts.walks += chunk_counts.walks;
            counts.counted += chunk_counts.counted;
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
                writer.push(name_text, start, start + 1, &line)?;
                *rows += 1;
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
    for (writer, path, rows, counts) in writers {
        writer.finish()?;
        eprintln!(
            "{} {rows} rows -> {path} (+ .tbi): {} routes, {} walk rows, {} with step counts",
            elapsed(),
            counts.routes,
            counts.walks,
            counts.counted
        );
    }
    Ok(())
}
