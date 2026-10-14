// Format 2's rows for one chunk of a reference. The reference's pieces in
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
    // numbers. Handles follow as zigzag varint deltas.
    pub fn write(out: &mut Vec<u8>, piece: &PieceRef) {
        let PieceRef {
            reference,
            name,
            frag,
            offset,
            piece,
            tags,
            handles,
        } = *piece;
        out.push(u8::from(!reference));
        out.extend_from_slice(name);
        out.push(0);
        out.extend_from_slice(&frag.to_be_bytes());
        out.extend_from_slice(&offset.to_be_bytes());
        out.extend_from_slice(&piece.to_be_bytes());
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
}

// Writes the chunk's rows through `emit`, each without the anchor columns and
// with its newline. `sequence` gives a node's bases with --sequences.
pub fn write_chunk<'g, S: Fn(usize) -> Option<&'g [u8]>>(
    pieces: &[Piece],
    lengths: &[u32],
    sequence: Option<&S>,
    counts: &mut Counts,
    emit: &mut dyn FnMut(&[u8]) -> Result<(), String>,
) -> Result<(), String> {
    let mut references: Vec<&Piece> = pieces.iter().filter(|p| p.reference).collect();
    references.sort_by_key(|p| p.offset);
    let path = Path::new(
        references
            .iter()
            .flat_map(|p| p.handles.iter().copied())
            .collect(),
    );
    let mut routes = Routes::default();
    let mut walks = Vec::new();
    for piece in pieces.iter().filter(|p| !p.reference) {
        let Some(mut walk) = encode(&path, &piece.handles, &mut routes) else {
            return Err(format!(
                "{}: a piece with no step on the reference path in its chunk",
                String::from_utf8_lossy(&piece.name)
            ));
        };
        if decode(&path, &walk, &routes.list, false).as_deref() != Some(&piece.handles[..]) {
            walk.counted = true;
            if decode(&path, &walk, &routes.list, true).as_deref() != Some(&piece.handles[..]) {
                return Err(format!(
                    "{}: the walk row does not decode to its steps",
                    String::from_utf8_lossy(&piece.name)
                ));
            }
            counts.counted += 1;
        }
        walks.push((piece, walk));
    }

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
    for p in &references {
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
    for (p, walk) in &walks {
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
