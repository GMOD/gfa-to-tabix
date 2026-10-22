// The walk-format rows for one chunk of a reference. The reference's pieces in
// the chunk become `ref` rows, and concatenated in offset order they are the
// chunk's reference path R. Every other piece becomes a `walk` row that lists
// the routes it takes off R: a route is an entry handle on R, the steps off R
// and an exit handle on R, and each distinct route becomes one `route` row,
// stored the way round whose handles sort first. Between routes a walk
// follows R, so those steps are implied. The encoder decodes every walk row it
// writes and compares the steps, and writes explicit step counts for a walk
// that the default rule would decode wrongly.

use crate::intern::FastMap;

const NONE: u32 = u32::MAX;

pub struct Piece {
    pub reference: bool,
    pub name: Vec<u8>,
    pub frag: u64,
    pub offset: u64,
    pub piece: u32,
    pub record: u32,
    pub tags: Vec<u8>,
    pub handles: Vec<u32>,
}

// A piece as the streaming pass holds it, borrowed from its path
pub struct PieceRef<'a> {
    pub reference: bool,
    pub name: &'a [u8],
    pub frag: u64,
    pub offset: u64,
    pub piece: u32,
    pub record: u32,
    pub tags: &'a [u8],
    pub handles: &'a [u32],
}

fn push_varint(out: &mut Vec<u8>, mut n: u64) {
    while n >= 0x80 {
        out.push(n as u8 | 0x80);
        n >>= 7;
    }
    out.push(n as u8);
}

fn read_varint(bytes: &[u8], at: &mut usize) -> u64 {
    let mut n = 0u64;
    let mut shift = 0;
    loop {
        let b = bytes[*at];
        *at += 1;
        n |= u64::from(b & 0x7f) << shift;
        if b < 0x80 {
            return n;
        }
        shift += 7;
    }
}

fn zigzag(n: i64) -> u64 {
    ((n << 1) ^ (n >> 63)) as u64
}

fn unzigzag(n: u64) -> i64 {
    (n >> 1) as i64 ^ -((n & 1) as i64)
}

impl Piece {
    // The sort key's text: reference pieces sort first in a chunk, then by
    // name, fragStart and offset, which are big-endian so bytes sort as
    // numbers. The record index never decides the order, since no two pieces
    // share a name, fragStart, offset and piece. Handles follow as zigzag
    // varint deltas.
    pub fn write(out: &mut Vec<u8>, piece: &PieceRef) {
        let PieceRef {
            reference,
            name,
            frag,
            offset,
            piece,
            record,
            tags,
            handles,
        } = *piece;
        out.push(u8::from(!reference));
        out.extend_from_slice(name);
        out.push(0);
        out.extend_from_slice(&frag.to_be_bytes());
        out.extend_from_slice(&offset.to_be_bytes());
        out.extend_from_slice(&piece.to_be_bytes());
        out.extend_from_slice(&record.to_be_bytes());
        out.extend_from_slice(&(tags.len() as u32).to_be_bytes());
        out.extend_from_slice(tags);
        let mut previous = 0i64;
        for &h in handles {
            push_varint(out, zigzag(i64::from(h) - previous));
            previous = i64::from(h);
        }
    }

    pub fn read(bytes: &[u8]) -> Piece {
        let reference = bytes[0] == 0;
        let end = 1 + bytes[1..].iter().position(|&b| b == 0).expect("name ends");
        let name = bytes[1..end].to_vec();
        let mut at = end + 1;
        let mut take = |n: usize| {
            let field = &bytes[at..at + n];
            at += n;
            field
        };
        let frag = u64::from_be_bytes(take(8).try_into().unwrap());
        let offset = u64::from_be_bytes(take(8).try_into().unwrap());
        let piece = u32::from_be_bytes(take(4).try_into().unwrap());
        let record = u32::from_be_bytes(take(4).try_into().unwrap());
        let tags_len = u32::from_be_bytes(take(4).try_into().unwrap()) as usize;
        let tags = take(tags_len).to_vec();
        let mut handles = Vec::new();
        let mut previous = 0i64;
        while at < bytes.len() {
            previous += unzigzag(read_varint(bytes, &mut at));
            handles.push(previous as u32);
        }
        Piece {
            reference,
            name,
            frag,
            offset,
            piece,
            record,
            tags,
            handles,
        }
    }
}

type IdMap<V> = FastMap<u32, V>;

// The chunk's reference path R, with each node's occurrences in it chained
// from the first.
struct Path {
    handles: Vec<u32>,
    first: IdMap<u32>,
    next: Vec<u32>,
}

impl Path {
    fn new(handles: Vec<u32>) -> Path {
        let mut first = IdMap::default();
        let mut last: IdMap<u32> = IdMap::default();
        let mut next = vec![NONE; handles.len()];
        for (i, &h) in handles.iter().enumerate() {
            let i = i as u32;
            match last.insert(h >> 1, i) {
                Some(previous) => next[previous as usize] = i,
                None => {
                    first.insert(h >> 1, i);
                }
            }
        }
        Path {
            handles,
            first,
            next,
        }
    }

    fn holds(&self, handle: u32) -> bool {
        self.first.contains_key(&(handle >> 1))
    }

    // The occurrence of a node nearest index `i`, the later one on a tie.
    fn nearest(&self, handle: u32, i: usize) -> Option<usize> {
        let mut at = *self.first.get(&(handle >> 1))?;
        let mut best = at as usize;
        while at != NONE {
            let j = at as usize;
            if j.abs_diff(i) <= best.abs_diff(i) {
                best = j;
            }
            at = self.next[j];
        }
        Some(best)
    }

    fn first(&self, handle: u32) -> Option<usize> {
        self.first.get(&(handle >> 1)).map(|&i| i as usize)
    }

    // The handle one step from `i` in the direction `handle` reads R there.
    fn step(&self, i: usize, handle: u32) -> Option<(usize, u32)> {
        if self.handles[i] == handle {
            let j = i + 1;
            (j < self.handles.len()).then(|| (j, self.handles[j]))
        } else {
            let j = i.checked_sub(1)?;
            Some((j, self.handles[j] ^ 1))
        }
    }
}

#[derive(Clone, PartialEq, Eq, Hash)]
struct Route {
    // NONE where the walk starts or ends off R
    entry: u32,
    interior: Vec<u32>,
    exit: u32,
}

impl Route {
    fn flipped(&self) -> Route {
        Route {
            entry: if self.exit == NONE {
                NONE
            } else {
                self.exit ^ 1
            },
            interior: self.interior.iter().rev().map(|h| h ^ 1).collect(),
            exit: if self.entry == NONE {
                NONE
            } else {
                self.entry ^ 1
            },
        }
    }

    fn sort_key(&self) -> (i64, &[u32], i64) {
        let end = |h: u32| if h == NONE { -1 } else { i64::from(h) };
        (end(self.entry), &self.interior, end(self.exit))
    }
}

struct Choice {
    route: usize,
    flip: bool,
    implied: u32,
}

struct Walk {
    start: u32,
    end: u32,
    tail: u32,
    choices: Vec<Choice>,
    counted: bool,
}

#[derive(Default)]
struct Routes {
    index: FastMap<Route, usize>,
    list: Vec<Route>,
    uses: Vec<u64>,
}

impl Routes {
    fn intern(&mut self, route: Route) -> (usize, bool) {
        let flipped = route.flipped();
        let (key, flip) = if flipped.sort_key() < route.sort_key() {
            (flipped, true)
        } else {
            (route, false)
        };
        let next = self.list.len();
        let id = *self.index.entry(key.clone()).or_insert(next);
        if id == next {
            self.list.push(key);
            self.uses.push(0);
        }
        self.uses[id] += 1;
        (id, flip)
    }
}

fn encode(path: &Path, handles: &[u32], routes: &mut Routes) -> Option<Walk> {
    let mut at: Option<usize> = None;
    let mut current = 0;
    let mut start = 0;
    let mut pending: Vec<u32> = Vec::new();
    let mut implied = 0;
    let mut choices = Vec::new();
    let mut take = |routes: &mut Routes, route: Route, implied: u32| {
        let (route, flip) = routes.intern(route);
        choices.push(Choice {
            route,
            flip,
            implied,
        });
    };
    for &h in handles {
        if !path.holds(h) {
            pending.push(h);
            continue;
        }
        let Some(i) = at else {
            start = h;
            at = path.first(h);
            if !pending.is_empty() {
                let interior = std::mem::take(&mut pending);
                take(
                    routes,
                    Route {
                        entry: NONE,
                        interior,
                        exit: h,
                    },
                    0,
                );
            }
            current = h;
            continue;
        };
        let next = path.step(i, current);
        if pending.is_empty() && next.is_some_and(|(_, n)| n == h) {
            at = next.map(|(j, _)| j);
            implied += 1;
        } else {
            let interior = std::mem::take(&mut pending);
            take(
                routes,
                Route {
                    entry: current,
                    interior,
                    exit: h,
                },
                implied,
            );
            implied = 0;
            at = path.nearest(h, i);
        }
        current = h;
    }
    at?;
    if !pending.is_empty() {
        take(
            routes,
            Route {
                entry: current,
                interior: pending,
                exit: NONE,
            },
            implied,
        );
        implied = 0;
    }
    Some(Walk {
        start,
        end: current,
        tail: implied,
        choices,
        counted: false,
    })
}

// The steps a walk row stands for. With `counted`, each stretch along R takes
// its stated step count; otherwise it runs until it reaches the next route's
// entry, or the row's last reference handle.
fn decode(path: &Path, walk: &Walk, routes: &[Route], counted: bool) -> Option<Vec<u32>> {
    let mut steps = Vec::new();
    let mut choices = walk.choices.iter().peekable();
    let oriented = |c: &Choice| {
        if c.flip {
            routes[c.route].flipped()
        } else {
            routes[c.route].clone()
        }
    };
    if let Some(c) = choices.peek() {
        let route = oriented(c);
        if route.entry == NONE {
            steps.extend_from_slice(&route.interior);
            choices.next();
        }
    }
    let mut h = walk.start;
    let mut i = path.first(h)?;
    steps.push(h);
    let follow = |steps: &mut Vec<u32>, h: &mut u32, i: &mut usize, target: u32, count: u32| {
        let mut taken = 0;
        while if counted { taken < count } else { *h != target } {
            let (j, next) = path.step(*i, *h)?;
            *i = j;
            *h = next;
            steps.push(next);
            taken += 1;
        }
        Some(())
    };
    for c in choices {
        let route = oriented(c);
        if route.entry == NONE {
            return None;
        }
        follow(&mut steps, &mut h, &mut i, route.entry, c.implied)?;
        if h != route.entry {
            return None;
        }
        steps.extend_from_slice(&route.interior);
        if route.exit == NONE {
            return Some(steps);
        }
        h = route.exit;
        i = path.nearest(h, i)?;
        steps.push(h);
    }
    follow(&mut steps, &mut h, &mut i, walk.end, walk.tail)?;
    (h == walk.end).then_some(steps)
}

fn push_i64(out: &mut Vec<u8>, n: i64) {
    out.extend_from_slice(n.to_string().as_bytes());
}

fn push_list(out: &mut Vec<u8>, items: impl Iterator<Item = i64>) {
    let mut any = false;
    for item in items {
        if any {
            out.push(b',');
        }
        push_i64(out, item);
        any = true;
    }
    if !any {
        out.push(b'.');
    }
}

// Each handle after the first as twice the id change plus the reverse bit.
fn delta_steps(handles: &[u32], previous: &mut i64) -> impl Iterator<Item = i64> {
    let mut previous_id = *previous;
    let deltas: Vec<i64> = handles
        .iter()
        .map(|&h| {
            let id = i64::from(h >> 1);
            let d = 2 * (id - previous_id) + i64::from(h & 1);
            previous_id = id;
            d
        })
        .collect();
    *previous = previous_id;
    deltas.into_iter()
}

#[derive(Default)]
pub struct Counts {
    pub routes: u64,
    pub walks: u64,
    pub counted: u64,
    pub abridged: u64,
    pub detail_walks: u64,
}

impl std::ops::AddAssign for Counts {
    fn add_assign(&mut self, other: Counts) {
        self.routes += other.routes;
        self.walks += other.walks;
        self.counted += other.counted;
        self.abridged += other.abridged;
        self.detail_walks += other.detail_walks;
    }
}

// A chunk's most a reader decodes: `cost` in interior steps, counting a step
// along R as a quarter of one, and `bytes` compressed. Zero leaves it unbounded.
#[derive(Clone, Copy, Default)]
pub struct Budget {
    pub cost: u64,
    pub bytes: u64,
}

// A step along R costs a viewer about a quarter of one off it: it decodes faster,
// but the cut still keeps and draws it
const STEPS_PER_INTERIOR: u64 = 4;

// bgzip compresses a stream in blocks of this many bytes
const BGZF_BLOCK: usize = 65280;

// One record per Tabix leaf bin, so a query for one detail record reads no other
pub const DETAIL_SPACING: u64 = 16384;

// The rows a chunk files under its detail sequence, one record per abridged
// path, each row without the anchor columns and with its newline
pub type Details = Vec<Vec<Vec<u8>>>;

struct Encoded<'p> {
    routes: Routes,
    walks: Vec<(&'p Piece, Walk)>,
}

fn encode_all<'p>(
    path: &Path,
    pieces: &[&'p Piece],
    counts: &mut Counts,
) -> Result<Encoded<'p>, String> {
    let mut routes = Routes::default();
    let mut walks = Vec::new();
    for &piece in pieces {
        let Some(mut walk) = encode(path, &piece.handles, &mut routes) else {
            return Err(format!(
                "{}: a piece with no step on the reference path in its chunk",
                String::from_utf8_lossy(&piece.name)
            ));
        };
        if decode(path, &walk, &routes.list, false).as_deref() != Some(&piece.handles[..]) {
            walk.counted = true;
            if decode(path, &walk, &routes.list, true).as_deref() != Some(&piece.handles[..]) {
                return Err(format!(
                    "{}: the walk row does not decode to its steps",
                    String::from_utf8_lossy(&piece.name)
                ));
            }
            counts.counted += 1;
        }
        walks.push((piece, walk));
    }
    Ok(Encoded { routes, walks })
}

fn compressed_len(text: &[u8]) -> u64 {
    use flate2::Compression;
    use flate2::write::DeflateEncoder;
    use std::io::Write;
    text.chunks(BGZF_BLOCK)
        .map(|block| {
            let mut encoder = DeflateEncoder::new(Vec::new(), Compression::new(6));
            encoder.write_all(block).expect("writes to memory");
            encoder.finish().expect("writes to memory").len() as u64
        })
        .sum()
}

fn piece_cost(enc: &Encoded, piece: &Piece, walk: &Walk) -> u64 {
    piece.handles.len() as u64
        + walk
            .choices
            .iter()
            .map(|c| STEPS_PER_INTERIOR * enc.routes.list[c.route].interior.len() as u64)
            .sum::<u64>()
}

// A path's pieces in the chunk, which abridging moves together
struct Group {
    pieces: Vec<usize>,
    cost: u64,
    raw: u64,
    routes: Vec<usize>,
}

// The paths whose pieces leave the chunk, costliest first, until the rest fit
// the budget. `raw` is the length of the chunk's rows, and `ratio` how far
// they compress.
fn abridged_groups(enc: &Encoded, budget: Budget, raw: u64, ratio: f64) -> Vec<Group> {
    let mut by_path: FastMap<(&[u8], u64), usize> = FastMap::default();
    let mut groups: Vec<Group> = Vec::new();
    for (k, (piece, walk)) in enc.walks.iter().enumerate() {
        let g = *by_path
            .entry((&piece.name[..], piece.frag))
            .or_insert_with(|| {
                groups.push(Group {
                    pieces: Vec::new(),
                    cost: 0,
                    raw: 0,
                    routes: Vec::new(),
                });
                groups.len() - 1
            });
        let group = &mut groups[g];
        group.pieces.push(k);
        group.cost += piece_cost(enc, piece, walk);
        group.raw += 40 + 4 * walk.choices.len() as u64;
        group.routes.extend(walk.choices.iter().map(|c| c.route));
    }
    let mut users = vec![0u32; enc.routes.list.len()];
    for group in &mut groups {
        group.routes.sort_unstable();
        group.routes.dedup();
        for &r in &group.routes {
            users[r] += 1;
        }
    }
    let route_raw = |r: usize| 8 + 6 * enc.routes.list[r].interior.len() as u64;
    let over_cost = |cost: u64| budget.cost > 0 && cost > budget.cost * STEPS_PER_INTERIOR;
    let over_bytes = |raw: u64| budget.bytes > 0 && raw as f64 * ratio > budget.bytes as f64;
    let mut cost: u64 = groups.iter().map(|g| g.cost).sum();
    let mut raw = raw;
    groups.sort_by_key(|g| std::cmp::Reverse(g.cost));
    let mut moved = Vec::new();
    for group in groups {
        if !over_cost(cost) && !over_bytes(raw) {
            break;
        }
        cost -= group.cost;
        raw = raw.saturating_sub(group.raw);
        for &r in &group.routes {
            users[r] -= 1;
            if users[r] == 0 {
                raw = raw.saturating_sub(route_raw(r));
            }
        }
        moved.push(group);
    }
    moved
}

// Writes the chunk's rows through `emit`, each without the anchor columns and
// with its newline. `sequence` gives a node's bases with --sequences. A chunk
// over `budget` moves its costliest paths' rows to `details`, and leaves an
// `abridged` row for each.
pub fn write_chunk<'g, S: Fn(usize) -> Option<&'g [u8]>>(
    pieces: &[Piece],
    lengths: &[u32],
    sequence: Option<&S>,
    budget: Budget,
    counts: &mut Counts,
    emit: &mut dyn FnMut(&[u8]) -> Result<(), String>,
    details: &mut Details,
) -> Result<(), String> {
    let mut references: Vec<&Piece> = pieces.iter().filter(|p| p.reference).collect();
    references.sort_by_key(|p| p.offset);
    let path = Path::new(
        references
            .iter()
            .flat_map(|p| p.handles.iter().copied())
            .collect(),
    );
    let others: Vec<&Piece> = pieces.iter().filter(|p| !p.reference).collect();
    let mut scratch = Counts::default();
    let enc = encode_all(&path, &others, &mut scratch)?;
    let mut text = Vec::new();
    emit_rows(
        &path,
        &references,
        &enc,
        lengths,
        sequence,
        &mut scratch,
        &mut |row| {
            text.extend_from_slice(row);
            Ok(())
        },
    )?;
    let total: u64 = enc.walks.iter().map(|(p, w)| piece_cost(&enc, p, w)).sum();
    let over_cost = budget.cost > 0 && total > budget.cost * STEPS_PER_INTERIOR;
    let raw = text.len() as u64;
    let over_bytes = budget.bytes > 0 && raw > budget.bytes;
    if !over_cost && !over_bytes {
        *counts += scratch;
        for row in text.split_inclusive(|&b| b == b'\n') {
            emit(row)?;
        }
        return Ok(());
    }
    let ratio = if over_bytes {
        compressed_len(&text) as f64 / raw as f64
    } else {
        1.0
    };
    drop(text);
    let moved = abridged_groups(&enc, budget, raw, ratio);
    let mut gone = vec![false; enc.walks.len()];
    for group in &moved {
        for &k in &group.pieces {
            gone[k] = true;
        }
    }
    let kept: Vec<&Piece> = enc
        .walks
        .iter()
        .zip(&gone)
        .filter(|(_, gone)| !**gone)
        .map(|((piece, _), _)| *piece)
        .collect();
    let kept = encode_all(&path, &kept, counts)?;
    emit_rows(&path, &references, &kept, lengths, sequence, counts, emit)?;
    let mut detail_counts = Counts::default();
    for (k, group) in moved.iter().enumerate() {
        let mut members: Vec<(&Piece, &Walk)> = group
            .pieces
            .iter()
            .map(|&i| (enc.walks[i].0, &enc.walks[i].1))
            .collect();
        members.sort_by_key(|(piece, _)| piece.offset);
        emit(&summary_row(&members, lengths, k))?;
        let pieces: Vec<&Piece> = members.iter().map(|(piece, _)| *piece).collect();
        let alone = encode_all(&path, &pieces, &mut detail_counts)?;
        let mut record = Vec::new();
        emit_rows(
            &path,
            &[],
            &alone,
            lengths,
            sequence,
            &mut detail_counts,
            &mut |row| {
                record.push(row.to_vec());
                Ok(())
            },
        )?;
        details.push(record);
        counts.abridged += 1;
    }
    counts.detail_walks += detail_counts.walks;
    Ok(())
}

// The `abridged` row standing for a path's pieces `members`, in offset order,
// whose rows are detail record `k`
fn summary_row(members: &[(&Piece, &Walk)], lengths: &[u32], k: usize) -> Vec<u8> {
    let (first, first_walk) = members[0];
    let (last, last_walk) = members[members.len() - 1];
    let steps: u64 = members.iter().map(|(p, _)| p.handles.len() as u64).sum();
    let bp: u64 = members
        .iter()
        .flat_map(|(p, _)| p.handles.iter())
        .map(|&h| u64::from(lengths[(h >> 1) as usize]))
        .sum();
    let mut line = b"abridged\t".to_vec();
    line.extend_from_slice(&first.name);
    for n in [first.frag, first.offset] {
        line.push(b'\t');
        line.extend_from_slice(n.to_string().as_bytes());
    }
    line.push(b'\t');
    let mut previous = 0i64;
    push_list(
        &mut line,
        members.iter().map(|(p, _)| {
            let piece = i64::from(p.piece);
            let d = piece - previous;
            previous = piece;
            d
        }),
    );
    for n in [
        steps,
        bp,
        u64::from(first_walk.start),
        u64::from(last_walk.end),
        k as u64,
    ] {
        line.push(b'\t');
        line.extend_from_slice(n.to_string().as_bytes());
    }
    let mut tags = |piece: &Piece, keep: [&[u8]; 3]| {
        for tag in piece.tags.split(|&b| b == b'\t') {
            if keep.iter().any(|k| tag.starts_with(k)) {
                line.push(b'\t');
                line.extend_from_slice(tag);
            }
        }
    };
    tags(first, [b"pv:", b"pg:", b"pr:"]);
    tags(last, [b"nx:", b"ng:", b"nr:"]);
    line.push(b'\n');
    line
}

// The rows of encoded pieces: `references`' ref rows, then the nodes, route
// and walk rows
fn emit_rows<'g, S: Fn(usize) -> Option<&'g [u8]>>(
    path: &Path,
    references: &[&Piece],
    enc: &Encoded,
    lengths: &[u32],
    sequence: Option<&S>,
    counts: &mut Counts,
    emit: &mut dyn FnMut(&[u8]) -> Result<(), String>,
) -> Result<(), String> {
    let routes = &enc.routes;
    let walks = &enc.walks;
    let anchor = |route: &Route| {
        [route.entry, route.exit]
            .iter()
            .filter(|&&h| h != NONE)
            .filter_map(|&h| path.first(h))
            .min()
            .unwrap_or(usize::MAX)
    };
    let mut order: Vec<usize> = (0..routes.list.len()).collect();
    order.sort_by(|&a, &b| {
        let (a, b) = (&routes.list[a], &routes.list[b]);
        anchor(a)
            .cmp(&anchor(b))
            .then_with(|| a.sort_key().cmp(&b.sort_key()))
    });
    let mut id = vec![0usize; order.len()];
    for (rank, &route) in order.iter().enumerate() {
        id[route] = rank;
    }
    counts.routes += order.len() as u64;
    counts.walks += walks.len() as u64;

    let mut line = Vec::new();
    let with_bases = |line: &mut Vec<u8>, handles: &[u32]| {
        if let Some(sequence) = sequence {
            line.extend_from_slice(b"\tSQ:Z:");
            for &h in handles {
                line.extend_from_slice(sequence((h >> 1) as usize).unwrap_or_default());
            }
        }
    };
    let piece_columns = |line: &mut Vec<u8>, kind: &[u8], p: &Piece| {
        line.extend_from_slice(kind);
        line.push(b'\t');
        line.extend_from_slice(&p.name);
        for n in [p.frag, p.offset, u64::from(p.piece), p.handles.len() as u64] {
            line.push(b'\t');
            line.extend_from_slice(n.to_string().as_bytes());
        }
        line.push(b'\t');
    };
    for p in references {
        line.clear();
        piece_columns(&mut line, b"ref", p);
        push_list(&mut line, delta_steps(&p.handles, &mut 0));
        line.push(b'\t');
        push_list(
            &mut line,
            p.handles
                .iter()
                .map(|&h| i64::from(lengths[(h >> 1) as usize])),
        );
        line.extend_from_slice(&p.tags);
        with_bases(&mut line, &p.handles);
        line.push(b'\n');
        emit(&line)?;
    }
    let mut interior: Vec<u32> = routes
        .list
        .iter()
        .flat_map(|route| route.interior.iter().map(|h| h & !1))
        .collect();
    interior.sort_unstable();
    interior.dedup();
    if !interior.is_empty() {
        line.clear();
        line.extend_from_slice(b"nodes\t");
        let mut previous = 0i64;
        push_list(
            &mut line,
            interior.iter().map(|&h| {
                let id = i64::from(h >> 1);
                let d = id - previous;
                previous = id;
                d
            }),
        );
        line.push(b'\t');
        push_list(
            &mut line,
            interior
                .iter()
                .map(|&h| i64::from(lengths[(h >> 1) as usize])),
        );
        with_bases(&mut line, &interior);
        line.push(b'\n');
        emit(&line)?;
    }
    let mut previous = 0i64;
    for &r in &order {
        let route = &routes.list[r];
        line.clear();
        line.extend_from_slice(b"route");
        for part in [&[route.entry][..], &route.interior[..], &[route.exit][..]] {
            line.push(b'\t');
            if part.first() == Some(&NONE) {
                line.push(b'.');
            } else {
                push_list(&mut line, delta_steps(part, &mut previous));
            }
        }
        line.push(b'\n');
        emit(&line)?;
    }
    for (p, walk) in walks {
        line.clear();
        piece_columns(&mut line, b"walk", p);
        push_i64(&mut line, i64::from(walk.start));
        line.push(b'\t');
        push_i64(&mut line, i64::from(walk.end) - i64::from(walk.start));
        if walk.counted {
            line.push(b':');
            push_i64(&mut line, i64::from(walk.tail));
        }
        line.push(b'\t');
        if walk.choices.is_empty() {
            line.push(b'.');
        }
        let mut previous = 0i64;
        for (k, c) in walk.choices.iter().enumerate() {
            if k > 0 {
                line.push(b',');
            }
            let r = id[c.route] as i64;
            push_i64(&mut line, 2 * (r - previous) + i64::from(c.flip));
            previous = r;
            if walk.counted {
                line.push(b':');
                push_i64(&mut line, i64::from(c.implied));
            }
        }
        line.extend_from_slice(&p.tags);
        line.push(b'\n');
        emit(&line)?;
    }
    Ok(())
}
