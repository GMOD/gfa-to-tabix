// The walk-format rows for one chunk of a reference. The reference's pieces in
// the chunk become `ref` rows, and concatenated in offset order they are the
// chunk's reference path R. Every other piece becomes a `walk` row that lists
// the routes it takes off R: a route is an entry handle on R, the steps off R
// and an exit handle on R, and each distinct route becomes one `route` row,
// stored the way round whose handles sort first. Between routes a walk
// follows R, so those steps are implied. Each step of a walk piece comes with
// the position the placement gave it on R's sequence, or none for route
// interior, and the row names the copy of R it takes wherever the default
// rule would take another: where it starts, where it leaves R for a route
// and where the route's exit lands. The encoder decodes every walk row it
// writes and compares the steps and their copies.

use std::hash::BuildHasherDefault;

use indexmap::IndexSet;

use crate::intern::{FastMap, IdHasher};

const NONE: u32 = u32::MAX;
// A step's position where it is route interior
pub const OFF: u64 = u64::MAX;

// A piece as the cutting pass writes it into the sort, borrowed from its
// path: for a walk piece, each step's position on R's sequence, OFF for route
// interior; none for a reference piece
pub struct PieceRef<'a> {
    pub reference: bool,
    pub name: &'a [u8],
    pub frag: u64,
    pub offset: u64,
    pub piece: u32,
    pub handles: &'a [u32],
    pub positions: &'a [u64],
}

// A piece read back from the sort. A walk piece's `targets` give each step's
// position in R, NONE for route interior; a reference piece has none.
struct Piece<'a> {
    name: &'a [u8],
    frag: u64,
    offset: u64,
    piece: u32,
    handles: Vec<u32>,
    targets: Vec<u32>,
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

impl PieceRef<'_> {
    // The sort key's text: reference pieces sort first in a chunk, then by
    // name, fragStart and offset, which are big-endian so bytes sort as
    // numbers, then by piece, which no two pieces share with all three.
    // Handles follow as zigzag varint deltas, then positions as zigzag varint
    // deltas plus one, 0 for OFF.
    pub fn write(&self, out: &mut Vec<u8>) {
        out.push(u8::from(!self.reference));
        out.extend_from_slice(self.name);
        out.push(0);
        out.extend_from_slice(&self.frag.to_be_bytes());
        out.extend_from_slice(&self.offset.to_be_bytes());
        out.extend_from_slice(&self.piece.to_be_bytes());
        out.extend_from_slice(&(self.handles.len() as u32).to_be_bytes());
        let mut previous = 0i64;
        for &h in self.handles {
            push_varint(out, zigzag(i64::from(h) - previous));
            previous = i64::from(h);
        }
        let mut previous = 0i64;
        for &p in self.positions {
            if p == OFF {
                push_varint(out, 0);
            } else {
                push_varint(out, zigzag(p as i64 - previous) + 1);
                previous = p as i64;
            }
        }
    }
}

fn is_reference(row: &[u8]) -> bool {
    row[0] == 0
}

impl<'a> Piece<'a> {
    // A piece from its row in the sort; a walk piece's positions are placed
    // in `path`, the chunk's R
    fn read(bytes: &'a [u8], path: Option<&Path>) -> Result<Piece<'a>, String> {
        let end = 1 + bytes[1..].iter().position(|&b| b == 0).expect("name ends");
        let name = &bytes[1..end];
        let mut at = end + 1;
        let mut take = |n: usize| {
            let field = &bytes[at..at + n];
            at += n;
            field
        };
        let frag = u64::from_be_bytes(take(8).try_into().unwrap());
        let offset = u64::from_be_bytes(take(8).try_into().unwrap());
        let piece = u32::from_be_bytes(take(4).try_into().unwrap());
        let count = u32::from_be_bytes(take(4).try_into().unwrap()) as usize;
        let mut handles = Vec::with_capacity(count);
        let mut previous = 0i64;
        for _ in 0..count {
            previous += unzigzag(read_varint(bytes, &mut at));
            handles.push(previous as u32);
        }
        let mut targets = Vec::with_capacity(if path.is_some() { count } else { 0 });
        if let Some(path) = path {
            let mut previous = 0i64;
            for &h in &handles {
                let n = read_varint(bytes, &mut at);
                if n == 0 {
                    targets.push(NONE);
                } else {
                    previous += unzigzag(n - 1);
                    let j = path.index_at(h, previous as u64).ok_or_else(|| {
                        format!(
                            "{}: a step on node {} placed at {previous} is not on the chunk's reference path",
                            String::from_utf8_lossy(name),
                            h >> 1
                        )
                    })?;
                    targets.push(j as u32);
                }
            }
        }
        Ok(Piece {
            name,
            frag,
            offset,
            piece,
            handles,
            targets,
        })
    }
}

type IdMap<V> = FastMap<u32, V>;

// The chunk's reference path R with each step's offset on its sequence, and
// each node's occurrences in it chained from the first.
struct Path {
    handles: Vec<u32>,
    offsets: Vec<u64>,
    first: IdMap<u32>,
    next: Vec<u32>,
}

impl Path {
    fn new(handles: Vec<u32>, offsets: Vec<u64>) -> Path {
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
            offsets,
            first,
            next,
        }
    }

    // The position in R of the step on `handle`'s node at `offset`
    fn index_at(&self, handle: u32, offset: u64) -> Option<usize> {
        let from = self.offsets.partition_point(|&o| o < offset);
        (from..self.offsets.len())
            .take_while(|&j| self.offsets[j] == offset)
            .find(|&j| self.handles[j] >> 1 == handle >> 1)
    }

    // A node's positions in R, in order
    fn occurrences(&self, handle: u32) -> impl Iterator<Item = usize> + '_ {
        std::iter::successors(self.first.get(&(handle >> 1)).copied(), |&at| {
            let next = self.next[at as usize];
            (next != NONE).then_some(next)
        })
        .map(|at| at as usize)
    }

    // How many of R's occurrences of the node at `j` come before it
    fn rank(&self, j: usize) -> u32 {
        self.occurrences(self.handles[j])
            .position(|at| at == j)
            .expect("an occurrence of its own node") as u32
    }

    // Occurrence `k` of a node, from 0
    fn copy(&self, handle: u32, k: u32) -> Option<usize> {
        self.occurrences(handle).nth(k as usize)
    }

    // The occurrence of a node nearest index `i`, the later one on a tie.
    fn nearest(&self, handle: u32, i: usize) -> Option<usize> {
        self.occurrences(handle).reduce(|best, j| {
            if j.abs_diff(i) <= best.abs_diff(i) {
                j
            } else {
                best
            }
        })
    }

    fn first(&self, handle: u32) -> Option<usize> {
        self.first.get(&(handle >> 1)).map(|&i| i as usize)
    }

    // The first position from `i`, reading R the way `handle` reads it there,
    // whose handle read that way is `target`: where a decoder stepping along
    // R until it reaches `target` stops
    fn reached(&self, i: usize, handle: u32, target: u32) -> Option<usize> {
        if self.handles[i] == handle {
            (i..self.handles.len()).find(|&j| self.handles[j] == target)
        } else {
            (0..=i).rev().find(|&j| self.handles[j] ^ 1 == target)
        }
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
    // the occurrence of the entry's node the walk leaves R from, where
    // stepping along R until the entry would stop at an earlier one
    entry_copy: Option<u32>,
    // the occurrence the exit lands on, where it is not the one nearest the
    // entry's
    exit_copy: Option<u32>,
}

// `start_at` and `end_at` are the positions in R of the piece's first and
// last steps on R, and `start_copy` names the first's occurrence where it is
// not R's first
struct Walk {
    start: u32,
    start_at: usize,
    start_copy: Option<u32>,
    end: u32,
    end_at: usize,
    choices: Vec<Choice>,
}

// The chunk's distinct routes, numbered in the order they first appear
#[derive(Default)]
struct Routes {
    list: IndexSet<Route, BuildHasherDefault<IdHasher>>,
}

impl Routes {
    fn intern(&mut self, route: Route) -> (usize, bool) {
        let flipped = route.flipped();
        let (key, flip) = if flipped.sort_key() < route.sort_key() {
            (flipped, true)
        } else {
            (route, false)
        };
        (self.list.insert_full(key).0, flip)
    }
}

// `targets` gives each step's position in R, NONE for route interior. The
// walk continues along R only where R's next position is the step's, and
// otherwise takes a route, with an empty interior if need be.
fn encode(path: &Path, handles: &[u32], targets: &[u32], routes: &mut Routes) -> Option<Walk> {
    // the last step on R: its position there and its handle
    let mut on: Option<(usize, u32)> = None;
    // where the walk last landed on R: the start or the last exit
    let mut landing = (0, 0);
    let mut pending: Vec<u32> = Vec::new();
    let mut choices = Vec::new();
    let mut take =
        |routes: &mut Routes, route: Route, entry_copy: Option<u32>, exit_copy: Option<u32>| {
            let (route, flip) = routes.intern(route);
            choices.push(Choice {
                route,
                flip,
                entry_copy,
                exit_copy,
            });
        };
    let entry_copy = |i: usize, current: u32, (at, landed): (usize, u32)| {
        (path.reached(at, landed, current) != Some(i)).then(|| path.rank(i))
    };
    for (&h, &target) in handles.iter().zip(targets) {
        if target == NONE {
            pending.push(h);
        } else {
            let j = target as usize;
            match on {
                None => {
                    landing = (j, h);
                    if !pending.is_empty() {
                        let interior = std::mem::take(&mut pending);
                        take(
                            routes,
                            Route {
                                entry: NONE,
                                interior,
                                exit: h,
                            },
                            None,
                            None,
                        );
                    }
                }
                Some((i, current)) => {
                    if !(pending.is_empty() && path.step(i, current) == Some((j, h))) {
                        let interior = std::mem::take(&mut pending);
                        let exit_copy = (path.nearest(h, i) != Some(j)).then(|| path.rank(j));
                        take(
                            routes,
                            Route {
                                entry: current,
                                interior,
                                exit: h,
                            },
                            entry_copy(i, current, landing),
                            exit_copy,
                        );
                        landing = (j, h);
                    }
                }
            }
            on = Some((j, h));
        }
    }
    let (end_at, end) = on?;
    if !pending.is_empty() {
        take(
            routes,
            Route {
                entry: end,
                interior: pending,
                exit: NONE,
            },
            entry_copy(end_at, end, landing),
            None,
        );
    }
    let first = targets.iter().position(|&t| t != NONE)?;
    let (start, start_at) = (handles[first], targets[first] as usize);
    Some(Walk {
        start,
        start_at,
        start_copy: (path.first(start) != Some(start_at)).then(|| path.rank(start_at)),
        end,
        end_at,
        choices,
    })
}

// The `count` steps a walk row stands for, each with its position in R, NONE
// for route interior. Each stretch along R runs until it reaches the next
// route's entry, or the occurrence its `:k` names, and the last until the
// row has its steps.
fn decode(path: &Path, walk: &Walk, routes: &Routes, count: usize) -> Option<Vec<(u32, u32)>> {
    let mut steps = Vec::new();
    let mut choices = walk.choices.iter().peekable();
    let oriented = |c: &Choice| {
        if c.flip {
            routes.list[c.route].flipped()
        } else {
            routes.list[c.route].clone()
        }
    };
    let interior = |steps: &mut Vec<(u32, u32)>, route: &Route| {
        steps.extend(route.interior.iter().map(|&h| (h, NONE)));
    };
    if let Some(c) = choices.peek() {
        let route = oriented(c);
        if route.entry == NONE {
            interior(&mut steps, &route);
            choices.next();
        }
    }
    let mut h = walk.start;
    let mut i = match walk.start_copy {
        Some(k) => path.copy(h, k)?,
        None => path.first(h)?,
    };
    steps.push((h, i as u32));
    let step = |steps: &mut Vec<(u32, u32)>, h: &mut u32, i: &mut usize| {
        let (j, next) = path.step(*i, *h)?;
        *i = j;
        *h = next;
        steps.push((next, j as u32));
        Some(())
    };
    for c in choices {
        let route = oriented(c);
        if route.entry == NONE {
            return None;
        }
        match c.entry_copy {
            Some(k) => {
                let at = path.copy(route.entry, k)?;
                while i != at {
                    step(&mut steps, &mut h, &mut i)?;
                }
            }
            None => {
                while h != route.entry {
                    step(&mut steps, &mut h, &mut i)?;
                }
            }
        }
        if h != route.entry {
            return None;
        }
        interior(&mut steps, &route);
        if route.exit == NONE {
            return Some(steps);
        }
        h = route.exit;
        i = match c.exit_copy {
            Some(k) => path.copy(h, k)?,
            None => path.nearest(h, i)?,
        };
        steps.push((h, i as u32));
    }
    while steps.len() < count {
        step(&mut steps, &mut h, &mut i)?;
    }
    Some(steps)
}

fn decodes_to(steps: Option<Vec<(u32, u32)>>, handles: &[u32], targets: &[u32]) -> bool {
    steps.is_some_and(|steps| {
        steps
            .iter()
            .copied()
            .eq(handles.iter().copied().zip(targets.iter().copied()))
    })
}

fn push_i64(out: &mut Vec<u8>, n: i64) {
    out.extend_from_slice(n.to_string().as_bytes());
}

// A handle, with `@k` naming its occurrence in R where it is not the default
fn push_copy(out: &mut Vec<u8>, handle: u32, copy: Option<u32>) {
    push_i64(out, i64::from(handle));
    if let Some(k) = copy {
        out.push(b'@');
        push_i64(out, i64::from(k));
    }
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

// Each value as its change from the one before, `previous` before the first.
fn differences<'a>(
    values: impl IntoIterator<Item = i64> + 'a,
    previous: &'a mut i64,
) -> impl Iterator<Item = i64> + 'a {
    values.into_iter().map(move |v| {
        let d = v - *previous;
        *previous = v;
        d
    })
}

// Each handle as twice the id change plus the reverse bit.
fn delta_steps<'a>(handles: &'a [u32], previous: &'a mut i64) -> impl Iterator<Item = i64> + 'a {
    differences(handles.iter().map(|&h| i64::from(h >> 1)), previous)
        .zip(handles)
        .map(|(d, &h)| 2 * d + i64::from(h & 1))
}

// `copies` counts the walk rows' `@k` and `:k`
#[derive(Default)]
pub struct Counts {
    pub routes: u64,
    pub walks: u64,
    pub copies: u64,
    pub abridged: u64,
    pub detail_walks: u64,
}

impl std::ops::AddAssign for Counts {
    fn add_assign(&mut self, other: Counts) {
        self.routes += other.routes;
        self.walks += other.walks;
        self.copies += other.copies;
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

// Each node's length in bp, and how many times the reference's paths pass it
#[derive(Clone, Copy)]
pub struct Nodes<'a> {
    pub lengths: &'a [u32],
    pub passes: &'a dyn Fn(usize) -> u32,
}

// The rows a chunk files under its detail sequence, one record per abridged
// path, each row without the anchor columns and with its newline
pub type Details = Vec<Vec<Vec<u8>>>;

struct Encoded<'p> {
    routes: Routes,
    walks: Vec<(&'p Piece<'p>, Walk)>,
}

// Encodes the walk pieces `members` of `pieces`, in that order
fn encode_all<'p>(
    path: &Path,
    pieces: &'p [Piece<'p>],
    members: impl IntoIterator<Item = usize>,
) -> Result<Encoded<'p>, String> {
    let mut routes = Routes::default();
    let mut walks = Vec::new();
    for piece in members.into_iter().map(|k| &pieces[k]) {
        let name = || String::from_utf8_lossy(piece.name).into_owned();
        let (handles, targets) = (&piece.handles, &piece.targets);
        let walk = encode(path, handles, targets, &mut routes).ok_or_else(|| {
            format!(
                "{}: a piece with no step on the reference path in its chunk",
                name()
            )
        })?;
        if !decodes_to(
            decode(path, &walk, &routes, handles.len()),
            handles,
            targets,
        ) {
            return Err(format!(
                "{}: the walk row does not decode to its steps and their copies",
                name()
            ));
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
        let g = *by_path.entry((piece.name, piece.frag)).or_insert_with(|| {
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

// Writes the rows of a chunk's pieces, `raw` as the sort holds them, through
// `emit`, each without the anchor columns and with its newline. `sequence`
// gives a node's bases with --sequences. A chunk over `budget` moves its
// costliest paths' rows to `details`, and leaves an `abridged` row for each
// of their pieces.
pub fn write_chunk<'g, S: Fn(usize) -> Option<&'g [u8]>>(
    raw: &[Vec<u8>],
    nodes: Nodes,
    sequence: Option<&S>,
    budget: Budget,
    counts: &mut Counts,
    emit: &mut dyn FnMut(&[u8]) -> Result<(), String>,
    details: &mut Details,
) -> Result<(), String> {
    let lengths = nodes.lengths;
    let mut references: Vec<Piece> = raw
        .iter()
        .filter(|row| is_reference(row))
        .map(|row| Piece::read(row, None))
        .collect::<Result<_, _>>()?;
    references.sort_by_key(|p| p.offset);
    let mut offsets = Vec::new();
    for p in &references {
        let mut at = p.offset;
        for &h in &p.handles {
            offsets.push(at);
            at += u64::from(lengths[(h >> 1) as usize]);
        }
    }
    let path = Path::new(
        references
            .iter()
            .flat_map(|p| p.handles.iter().copied())
            .collect(),
        offsets,
    );
    let pieces: Vec<Piece> = raw
        .iter()
        .filter(|row| !is_reference(row))
        .map(|row| Piece::read(row, Some(&path)))
        .collect::<Result<_, _>>()?;
    let mut scratch = Counts::default();
    let enc = encode_all(&path, &pieces, 0..pieces.len())?;
    let mut text = Vec::new();
    emit_rows(
        &path,
        &references,
        &enc,
        nodes,
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
    drop(enc);
    let mut gone = vec![false; pieces.len()];
    for group in &moved {
        for &k in &group.pieces {
            gone[k] = true;
        }
    }
    let kept = encode_all(&path, &pieces, (0..pieces.len()).filter(|&k| !gone[k]))?;
    emit_rows(&path, &references, &kept, nodes, sequence, counts, emit)?;
    drop(kept);
    let mut detail_counts = Counts::default();
    for (k, group) in moved.iter().enumerate() {
        let mut members = group.pieces.clone();
        members.sort_by_key(|&k| pieces[k].offset);
        let alone = encode_all(&path, &pieces, members)?;
        for (piece, walk) in &alone.walks {
            emit(&summary_row(&path, piece, walk, lengths, k))?;
        }
        let mut record = Vec::new();
        emit_rows(
            &path,
            &[],
            &alone,
            nodes,
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

// The `abridged` row standing for one piece of a path whose pieces in the
// chunk are detail record `k`: its stretch on the contig from its first step
// on R to its last, and all its steps
fn summary_row(path: &Path, piece: &Piece, walk: &Walk, lengths: &[u32], k: usize) -> Vec<u8> {
    let on_r = |t: &u32| *t != NONE;
    let first = piece.targets.iter().position(on_r).expect("a step on R");
    let last = piece.targets.iter().rposition(on_r).expect("a step on R");
    let bp = |steps: &[u32]| -> u64 {
        steps
            .iter()
            .map(|&h| u64::from(lengths[(h >> 1) as usize]))
            .sum()
    };
    let mut line = b"abridged\t".to_vec();
    line.extend_from_slice(piece.name);
    for n in [
        piece.frag,
        piece.offset + bp(&piece.handles[..first]),
        u64::from(piece.piece),
        piece.handles.len() as u64,
        bp(&piece.handles[first..=last]),
    ] {
        line.push(b'\t');
        line.extend_from_slice(n.to_string().as_bytes());
    }
    line.push(b'\t');
    push_copy(&mut line, walk.start, walk.start_copy);
    line.push(b'\t');
    let end_copy = (path.nearest(walk.end, walk.start_at) != Some(walk.end_at))
        .then(|| path.rank(walk.end_at));
    push_copy(&mut line, walk.end, end_copy);
    line.push(b'\t');
    line.extend_from_slice(k.to_string().as_bytes());
    line.push(b'\n');
    line
}

// The rows of encoded pieces: `references`' ref rows, then the nodes, route
// and walk rows
fn emit_rows<'g, S: Fn(usize) -> Option<&'g [u8]>>(
    path: &Path,
    references: &[Piece],
    enc: &Encoded,
    nodes: Nodes,
    sequence: Option<&S>,
    counts: &mut Counts,
    emit: &mut dyn FnMut(&[u8]) -> Result<(), String>,
) -> Result<(), String> {
    let Nodes { lengths, passes } = nodes;
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
        line.extend_from_slice(p.name);
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
        line.push(b'\t');
        let counts: Vec<i64> = p
            .handles
            .iter()
            .map(|&h| i64::from(passes((h >> 1) as usize)))
            .collect();
        if counts.iter().all(|&n| n == 1) {
            line.push(b'.');
        } else {
            push_list(&mut line, counts.into_iter());
        }
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
        push_list(
            &mut line,
            differences(interior.iter().map(|&h| i64::from(h >> 1)), &mut 0),
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
        push_copy(&mut line, walk.start, walk.start_copy);
        counts.copies += u64::from(walk.start_copy.is_some())
            + walk
                .choices
                .iter()
                .map(|c| u64::from(c.entry_copy.is_some()) + u64::from(c.exit_copy.is_some()))
                .sum::<u64>();
        line.push(b'\t');
        if walk.choices.is_empty() {
            line.push(b'.');
        }
        let mut previous = 0;
        let routes = differences(
            walk.choices.iter().map(|c| id[c.route] as i64),
            &mut previous,
        );
        for (k, (d, c)) in routes.zip(&walk.choices).enumerate() {
            if k > 0 {
                line.push(b',');
            }
            push_i64(&mut line, 2 * d + i64::from(c.flip));
            if let Some(k) = c.entry_copy {
                line.push(b':');
                push_i64(&mut line, i64::from(k));
            }
            if let Some(k) = c.exit_copy {
                line.push(b'@');
                push_i64(&mut line, i64::from(k));
            }
        }
        line.push(b'\n');
        emit(&line)?;
    }
    Ok(())
}
