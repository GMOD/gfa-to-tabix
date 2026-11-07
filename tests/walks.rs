// --walks over walks-two-refs.gfa, every row checked by hand. Five nodes of
// 6 bp make the reference GRCh38#0#chr: 1 2 3 4 5 at 0, 6, 12, 18 and 24.
// Q#0#chr takes 6 in place of 2. With --tile 10, nodes 1 and 2 lie in tile
// 0-10, 3 and 4 in 10-20, and 5 in 20-30; each tile's rows are one unit,
// whose extent is the stretch its ref rows and pieces cover. H#1#h inserts 7
// (3 bp) between 3 and 4, I#1#i inverts 2-3, D#1#d repeats 1-4, and U#1#u
// visits only 8 and 9. walks-two-refs-p.gfa says the same in P lines.
//
// A handle is 2 * id + 1 when reversed. In a ref row and a route row each
// handle is written as 2 * (id - previous id) + reverse; a walk row names its
// routes by 2 * (route id - previous route id) + flip; a handle on R or a
// route's exit takes `@k` where it lands on occurrence k of its node in R,
// and a route `:k` where the walk leaves R from occurrence k of its entry.
//
// Every file a test builds passes the release checks in `verify`.

use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::fs;
use std::io::{Read, Write};
use std::process::{Command, Output};
use std::sync::atomic::{AtomicUsize, Ordering};

use flate2::Compression;
use flate2::read::MultiGzDecoder;
use flate2::write::GzEncoder;

struct Built {
    output: Output,
    // by sample, out.<sample>.walks.gz decompressed
    files: BTreeMap<String, String>,
    // every sample's file, one after another
    walks: String,
}

impl Built {
    fn file(&self, sample: &str) -> &str {
        self.files.get(sample).map_or("", String::as_str)
    }
}

fn fixture(name: &str) -> String {
    format!("{}/tests/data/{name}", env!("CARGO_MANIFEST_DIR"))
}

fn build(fixture_name: &str, args: &[&str]) -> Built {
    static RUNS: AtomicUsize = AtomicUsize::new(0);
    let dir = std::env::temp_dir().join(format!(
        "gfa-to-tabix-walks-{}-{}",
        std::process::id(),
        RUNS.fetch_add(1, Ordering::Relaxed)
    ));
    fs::create_dir_all(&dir).unwrap();
    let input = if fixture_name == "-" || fixture_name.starts_with('/') {
        fixture_name.to_string()
    } else {
        fixture(fixture_name)
    };
    let output = Command::new(env!("CARGO_BIN_EXE_gfa-to-tabix"))
        .arg(input)
        .arg("-o")
        .arg(dir.join("out"))
        .args(["--walks", "--refs", "GRCh38,Q", "--tile", "10"])
        .args(args)
        .output()
        .unwrap();
    let tile_arg = ["--tile", "10"]
        .iter()
        .chain(args)
        .collect::<Vec<_>>()
        .windows(2)
        .rfind(|w| *w[0] == "--tile")
        .map(|w| w[1].parse().unwrap())
        .unwrap();
    let mut files = BTreeMap::new();
    for entry in fs::read_dir(&dir).unwrap().flatten() {
        let name = entry.file_name().into_string().unwrap();
        if name.ends_with(".walks.gz.idx") {
            continue;
        }
        let sample = name
            .strip_prefix("out.")
            .and_then(|n| n.strip_suffix(".walks.gz"))
            .unwrap_or_else(|| panic!("left behind: {name}"));
        let data = fs::read(entry.path()).unwrap();
        let directory = fs::read_to_string(dir.join(format!("{name}.idx")))
            .unwrap_or_else(|_| panic!("{name} has no directory"));
        verify(&data, &directory, tile_arg);
        files.insert(sample.to_string(), gunzip(&data));
    }
    let built = Built {
        walks: files.values().map(String::as_str).collect(),
        files,
        output,
    };
    fs::remove_dir_all(&dir).unwrap();
    built
}

fn gunzip(bytes: &[u8]) -> String {
    let mut text = String::new();
    MultiGzDecoder::new(bytes)
        .read_to_string(&mut text)
        .unwrap();
    text
}

// The pyramid blocks covering [lo, hi) widened to whole tiles, as (start,
// size)
fn cover(lo: u64, hi: u64, tile: u64) -> Vec<(u64, u64)> {
    let mut blocks = Vec::new();
    let mut at = lo / tile * tile;
    let end = hi.div_ceil(tile) * tile;
    while at < end {
        let size = [512, 64, 8, 1]
            .map(|n| n * tile)
            .into_iter()
            .find(|&s| at.is_multiple_of(s) && at + s <= end)
            .unwrap();
        blocks.push((at, size));
        at += size;
    }
    blocks
}

// The release checks of a walk file and its directory: the directory's first
// line is the header's `#walks` line with the data's length; the header, the
// units, the tables and the EOF block partition the file, each unit a run of
// gzip members starting with its `#unit` line; each table lists its
// sequence's units before it, in file order, as they are, each above 0
// bytes, and states `|S|`, where the sequence's last ref row ends; the
// directory names every table, sequences in byte order; every line starts
// with its unit's sequence; a departure block is named `.`, and no two units
// of a kind and sequence share any other name; a departure record lies in
// every block of its cover and no other, overlapping each; tile and detail
// lines lie within their unit's extent, which runs from the first base its
// ref rows' stretches and its pieces' spans cover to the last
fn verify(data: &[u8], directory: &str, tile: u64) {
    let lines: Vec<Vec<&str>> = directory.lines().map(|l| l.split('\t').collect()).collect();
    let walks = &lines[0];
    assert_eq!(walks[..2], ["#walks", "format:i:7"]);
    assert_eq!(
        walks.last().unwrap(),
        &format!("bytes:i:{}", data.len()).as_str()
    );
    let mut members = Vec::new();
    let mut at = 0;
    while at < data.len() {
        assert_eq!(data[at..at + 2], [0x1f, 0x8b], "a gzip member at {at}");
        let size = u16::from_le_bytes([data[at + 16], data[at + 17]]) as usize + 1;
        members.push((at, at + size));
        at += size;
    }
    let eof = members.pop().unwrap();
    assert_eq!(eof.1 - eof.0, 28);
    assert!(gunzip(&data[eof.0..eof.1]).is_empty());
    assert_eq!(lines[1][..2], ["#header", "0"]);
    let header_end: usize = lines[1][2].parse().unwrap();
    let header = gunzip(&data[..header_end]);
    assert_eq!(
        header.lines().next().unwrap(),
        walks[..walks.len() - 1].join("\t")
    );
    assert!(
        header
            .lines()
            .all(|l| l.starts_with('#') && !l.starts_with("#unit"))
    );
    let mut units: Vec<(usize, usize)> = Vec::new();
    for &(from, to) in members.iter().filter(|m| m.0 >= header_end) {
        if gunzip(&data[from..to]).starts_with("#unit\t") {
            units.push((from, to));
        } else {
            units.last_mut().expect("a member in a unit").1 = to;
        }
    }
    assert_eq!(units.first().map_or(eof.0, |u| u.0), header_end);
    assert_eq!(units.last().map_or(header_end, |u| u.1), eof.0);
    assert!(units.windows(2).all(|w| w[0].1 == w[1].0));
    let mut listed: BTreeMap<usize, String> = BTreeMap::new();
    let mut blocks: BTreeMap<String, Vec<(u64, u64)>> = BTreeMap::new();
    let mut names = BTreeSet::new();
    let sequences: Vec<&str> = lines[2..].iter().map(|c| c[0]).collect();
    assert!(
        sequences
            .windows(2)
            .all(|w| w[0].as_bytes() < w[1].as_bytes())
    );
    let mut before = header_end;
    let mut lengths: BTreeMap<&str, u64> = BTreeMap::new();
    for c in &lines[2..] {
        let (offset, length): (usize, usize) = (c[1].parse().unwrap(), c[2].parse().unwrap());
        let text = gunzip(&data[offset..offset + length]);
        let mut rows = text.lines();
        let head: Vec<&str> = rows.next().unwrap().split('\t').collect();
        assert_eq!(
            (head[1], head[2], head[4], head[5]),
            (c[0], "0", "table", ".")
        );
        lengths.insert(c[0], head[3].parse().unwrap());
        for row in rows {
            let e: Vec<&str> = row.split('\t').collect();
            assert_eq!((e[0], e[1]), ("#entry", c[0]), "{row}");
            let (at, length): (usize, usize) = (e[6].parse().unwrap(), e[7].parse().unwrap());
            assert!(length > 0, "{row}");
            assert_eq!(at, before, "{row}: not in file order or not every unit");
            before = at + length;
            listed.insert(at, e[1..6].join("\t") + "\t" + e[7]);
        }
        assert_eq!(offset, before, "{}: its table follows its units", c[0]);
        before = offset + length;
    }
    assert_eq!(before, eof.0);
    let mut ref_ends: BTreeMap<String, u64> = BTreeMap::new();
    for &(from, to) in &units {
        let text = gunzip(&data[from..to]);
        let mut rows = text.lines();
        let head: Vec<&str> = rows.next().unwrap().split('\t').collect();
        let (seq, kind) = (head[1], head[4]);
        let (lo, hi): (u64, u64) = (head[2].parse().unwrap(), head[3].parse().unwrap());
        if kind == "table" {
            continue;
        }
        assert_eq!(
            listed.get(&from),
            Some(&(head[1..6].join("\t") + "\t" + &(to - from).to_string())),
            "the unit at {from} is not listed as it is"
        );
        assert!(
            head[5] == "."
                || names.insert((seq.to_string(), kind.to_string(), head[5].to_string())),
            "two units named {head:?}"
        );
        let mut union: Option<(u64, u64)> = None;
        for row in rows {
            let c: Vec<&str> = row.split('\t').collect();
            assert_eq!(c[0], seq, "{row}");
            let (a, b): (u64, u64) = (c[1].parse().unwrap(), c[2].parse().unwrap());
            assert!(a < b, "{row}");
            let stretch = match c[3] {
                "departure" => {
                    assert_eq!((kind, head[5]), ("departures", "."));
                    blocks
                        .entry(row.to_string())
                        .or_default()
                        .push((lo, hi - lo));
                    None
                }
                "ref" => {
                    assert_eq!((a, b), (lo, hi), "{row}");
                    let start: u64 = c[6].parse().unwrap();
                    let bp: u64 = c[10].split(',').map(|n| n.parse::<u64>().unwrap()).sum();
                    let end = ref_ends.entry(seq.to_string()).or_default();
                    *end = (*end).max(start + bp);
                    Some((start, start + bp))
                }
                "walk" | "abridged" => Some((a, b)),
                _ => {
                    assert_eq!((a, b), (lo, hi), "{row}");
                    None
                }
            };
            assert!(
                if kind == "departures" {
                    a < hi && lo < b
                } else {
                    lo <= a && b <= hi
                },
                "{row}"
            );
            if let Some((a, b)) = stretch {
                union = Some(union.map_or((a, b), |(x, y)| (x.min(a), y.max(b))));
            }
        }
        if kind != "departures" {
            assert_eq!(union, Some((lo, hi)), "{head:?}");
        }
    }
    for (seq, length) in lengths {
        assert_eq!(ref_ends.get(seq).copied().unwrap_or(0), length, "{seq}");
    }
    assert_eq!(
        listed.len(),
        units.len() - (lines.len() - 2),
        "a listed unit was not found"
    );
    for (row, mut filed) in blocks {
        let c: Vec<&str> = row.split('\t').collect();
        filed.sort_unstable();
        assert_eq!(
            filed,
            cover(c[1].parse().unwrap(), c[2].parse().unwrap(), tile),
            "{row}"
        );
    }
}

// A walk file's units: each `#unit` line's columns and the lines after it
fn units(text: &str) -> Vec<(Vec<&str>, Vec<&str>)> {
    let mut units: Vec<(Vec<&str>, Vec<&str>)> = Vec::new();
    for line in text.lines() {
        match line.strip_prefix("#unit\t") {
            Some(head) => units.push((head.split('\t').collect(), Vec::new())),
            None => {
                if let Some(unit) = units.last_mut() {
                    unit.1.push(line);
                }
            }
        }
    }
    units
}

fn tsv(rows: &[&str]) -> String {
    rows.iter().map(|r| r.replace(' ', "\t") + "\n").collect()
}

fn joined<'a>(lines: impl Iterator<Item = &'a str>) -> String {
    lines.map(|line| line.to_string() + "\n").collect()
}

// A unit's `#unit` line and its lines
fn unit(text: &str, kind: &str, name: &str) -> String {
    units(text)
        .into_iter()
        .filter(|(head, _)| head[3] == kind && head[4] == name)
        .map(|(head, lines)| format!("#unit\t{}\n", head.join("\t")) + &joined(lines.into_iter()))
        .collect()
}

// The rows of tile units on sequence `anchor` of `kind` and name
fn rows_of(text: &str, anchor: &str, kind: &str, name: &str) -> String {
    joined(
        units(text)
            .into_iter()
            .filter(|(head, _)| head[0] == anchor && head[3] == "tile")
            .flat_map(|(_, lines)| lines)
            .filter(|line| {
                let cols: Vec<&str> = line.split('\t').collect();
                cols[3] == kind && cols[4] == name
            }),
    )
}

// The departure records, each once, in order
fn departures(text: &str) -> String {
    let records: BTreeSet<&str> = units(text)
        .into_iter()
        .filter(|(head, _)| head[3] == "departures")
        .flat_map(|(_, lines)| lines)
        .collect();
    joined(records.into_iter())
}

fn header(text: &str) -> String {
    joined(
        text.lines()
            .take_while(|line| line.starts_with('#') && !line.starts_with("#unit")),
    )
}

// Decoding, written from the format's description and independent of the
// encoder: every piece's steps, by (path, fragStart) and piece index.

fn deltas(field: &str, previous: &mut i64) -> Vec<u32> {
    if field == "." {
        return Vec::new();
    }
    field
        .split(',')
        .map(|tok| {
            let d: i64 = tok.parse().unwrap();
            let r = d & 1;
            *previous += (d - r) / 2;
            (2 * *previous + r) as u32
        })
        .collect()
}

type Route = (Option<u32>, Vec<u32>, Option<u32>);

fn flipped((e, interior, x): &Route) -> Route {
    (
        x.map(|h| h ^ 1),
        interior.iter().rev().map(|h| h ^ 1).collect(),
        e.map(|h| h ^ 1),
    )
}

// R's handles, and where each step starts and ends on its sequence
struct RefPath {
    handles: Vec<u32>,
    stretches: Vec<(u64, u64)>,
}

impl RefPath {
    // From the first base of the steps at `at` in R to the last
    fn span(&self, at: impl Iterator<Item = usize>) -> (u64, u64) {
        at.map(|i| self.stretches[i])
            .reduce(|(a, b), (c, d)| (a.min(c), b.max(d)))
            .unwrap()
    }

    fn occurrences(&self, h: u32) -> impl Iterator<Item = usize> + '_ {
        self.handles
            .iter()
            .enumerate()
            .filter(move |(_, r)| *r >> 1 == h >> 1)
            .map(|(i, _)| i)
    }

    // occurrence `k` of the node, or the first
    fn copy(&self, h: u32, k: Option<usize>) -> usize {
        self.occurrences(h).nth(k.unwrap_or(0)).unwrap()
    }

    fn nearest(&self, h: u32, i: usize) -> usize {
        let mut best = None;
        for j in self.occurrences(h) {
            if best.is_none_or(|b: usize| j.abs_diff(i) <= b.abs_diff(i)) {
                best = Some(j);
            }
        }
        best.unwrap()
    }

    fn step(&self, i: usize, h: u32) -> (usize, u32) {
        if self.handles[i] == h {
            (i + 1, self.handles[i + 1])
        } else {
            (i - 1, self.handles[i - 1] ^ 1)
        }
    }
}

// A token and the occurrence its `@k` names
fn with_copy(token: &str) -> (&str, Option<usize>) {
    match token.split_once('@') {
        Some((token, k)) => (token, Some(k.parse().unwrap())),
        None => (token, None),
    }
}

// A walk row's steps, each with its position in R, none for route interior
fn decode_walk(path: &RefPath, routes: &[Route], cols: &[&str]) -> Vec<(u32, Option<usize>)> {
    let count: usize = cols[8].parse().unwrap();
    let (start, start_copy) = with_copy(cols[9]);
    let start: u32 = start.parse().unwrap();
    let mut choices = Vec::new();
    let mut previous = 0i64;
    if cols[10] != "." {
        for tok in cols[10].split(',') {
            let (tok, exit_copy) = with_copy(tok);
            let mut parts = tok.split(':');
            let d: i64 = parts.next().unwrap().parse().unwrap();
            let flip = d & 1;
            previous += (d - flip) / 2;
            let route = &routes[previous as usize];
            let entry_copy: Option<usize> = parts.next().map(|k| k.parse().unwrap());
            choices.push((
                if flip == 1 {
                    flipped(route)
                } else {
                    route.clone()
                },
                entry_copy,
                exit_copy,
            ));
        }
    }
    let mut steps = Vec::new();
    let off_r = |interior: &[u32]| interior.iter().map(|&h| (h, None)).collect::<Vec<_>>();
    let mut rest = &choices[..];
    if let Some(((None, interior, _), _, _)) = choices.first() {
        steps.extend(off_r(interior));
        rest = &choices[1..];
    }
    let mut h = start;
    let mut i = path.copy(h, start_copy);
    steps.push((h, Some(i)));
    let step = |steps: &mut Vec<(u32, Option<usize>)>, h: &mut u32, i: &mut usize| {
        (*i, *h) = path.step(*i, *h);
        steps.push((*h, Some(*i)));
    };
    for ((entry, interior, exit), entry_copy, exit_copy) in rest {
        let entry = entry.expect("an open route after the first choice");
        match entry_copy {
            Some(k) => {
                let at = path.copy(entry, Some(*k));
                while i != at {
                    step(&mut steps, &mut h, &mut i);
                }
            }
            None => {
                while h != entry {
                    step(&mut steps, &mut h, &mut i);
                }
            }
        }
        assert_eq!(h, entry);
        steps.extend(off_r(interior));
        let Some(exit) = exit else {
            return steps;
        };
        h = *exit;
        i = match exit_copy {
            Some(k) => path.copy(h, Some(*k)),
            None => path.nearest(h, i),
        };
        steps.push((h, Some(i)));
    }
    while steps.len() < count {
        step(&mut steps, &mut h, &mut i);
    }
    steps
}

// A walk file read back: every path's steps, joining its pieces in order, by
// `path@fragStart`; and by sequence and path, the stretches of its contig each
// piece spans from its first step on R to its last, abridged ones as their
// rows state them, and each departure record's own bp.
struct Decoded {
    paths: BTreeMap<String, Vec<u32>>,
    stretches: BTreeMap<(String, String), Vec<(u64, u64)>>,
    // the nodes the ref rows hold
    reference: BTreeSet<u32>,
}

fn decode_file(text: &str) -> Decoded {
    let mut tiles: BTreeMap<(String, u64), Vec<Vec<&str>>> = BTreeMap::new();
    // by sequence, tile and record
    let mut details: BTreeMap<(String, u64, u64), Vec<Vec<&str>>> = BTreeMap::new();
    let mut records: BTreeSet<(String, Vec<&str>)> = BTreeSet::new();
    for (head, lines) in units(text) {
        let seq = head[0].to_string();
        let mut rows = lines.into_iter().map(|l| l.split('\t').collect::<Vec<_>>());
        match head[3] {
            "tile" => tiles
                .entry((seq, head[4].parse().unwrap()))
                .or_default()
                .extend(rows),
            "detail" => {
                let (cs, k) = head[4].split_once(':').unwrap();
                details
                    .entry((seq, cs.parse().unwrap(), k.parse().unwrap()))
                    .or_default()
                    .extend(rows);
            }
            "departures" => {
                records.extend(rows.by_ref().map(|c| (seq.clone(), c[3..].to_vec())));
            }
            _ => {}
        }
    }
    // node lengths from the `ref` and `nodes` rows
    let mut lengths: HashMap<u32, u64> = HashMap::new();
    let mut reference = BTreeSet::new();
    for cols in tiles.values().chain(details.values()).flatten() {
        let (ids, bps) = match cols[3] {
            "ref" => {
                let handles = deltas(cols[9], &mut 0);
                reference.extend(handles.iter().map(|h| h >> 1));
                (handles, cols[10])
            }
            "nodes" => {
                let mut id = 0u32;
                let ids = cols[4].split(',').map(|d| {
                    id = id.checked_add_signed(d.parse().unwrap()).unwrap();
                    2 * id
                });
                (ids.collect(), cols[5])
            }
            _ => continue,
        };
        for (h, bp) in ids.iter().zip(bps.split(',')) {
            lengths.insert(h >> 1, bp.parse().unwrap());
        }
    }
    let bp_of = |steps: &[(u32, Option<usize>)]| -> u64 {
        steps.iter().map(|(h, _)| lengths[&(h >> 1)]).sum()
    };
    // a piece's stretch on R: from where its first step on R starts on the
    // contig to where its last ends, and those steps' indices
    let on_r = |offset: u64, steps: &[(u32, Option<usize>)]| {
        let first = steps.iter().position(|s| s.1.is_some()).unwrap();
        let last = steps.iter().rposition(|s| s.1.is_some()).unwrap();
        let start = offset + bp_of(&steps[..first]);
        (start, start + bp_of(&steps[first..=last]), first, last)
    };
    let mut pieces: BTreeMap<String, BTreeMap<u64, Vec<u32>>> = BTreeMap::new();
    let mut stretches: BTreeMap<(String, String), Vec<(u64, u64)>> = BTreeMap::new();
    // every walk step a tile or detail unit holds, by path, as its W line's
    // start, its piece and its place there, its stretch of the contig, its
    // sequence and tile, and where it lies on R its stretch there and
    // whether it runs against R
    let mut placed: BTreeMap<String, Vec<Placed>> = BTreeMap::new();
    let mut decode_rows = |seq: &str, cs: u64, path: &RefPath, rows: &[Vec<&str>], detail: bool| {
        let mut previous = 0i64;
        let routes: Vec<Route> = rows
            .iter()
            .filter(|c| c[3] == "route")
            .map(|c| {
                let entry = deltas(c[4], &mut previous).first().copied();
                let interior = deltas(c[5], &mut previous);
                let exit = deltas(c[6], &mut previous).first().copied();
                (entry, interior, exit)
            })
            .collect();
        let mut decoded = Vec::new();
        for cols in rows {
            let steps = match cols[3] {
                "ref" => deltas(cols[9], &mut 0)
                    .into_iter()
                    .map(|h| (h, None))
                    .collect(),
                "walk" => decode_walk(path, &routes, cols),
                _ => continue,
            };
            if cols[3] == "walk" {
                assert_eq!(
                    path.span(steps.iter().filter_map(|s| s.1)),
                    (cols[1].parse().unwrap(), cols[2].parse().unwrap()),
                    "a walk row's span is its placed steps': {cols:?}"
                );
            }
            assert_eq!(steps.len(), cols[8].parse::<usize>().unwrap(), "{cols:?}");
            let offset: u64 = cols[6].parse().unwrap();
            if cols[3] == "walk" {
                let mut at = offset;
                let (frag, piece): (u64, u64) =
                    (cols[5].parse().unwrap(), cols[7].parse().unwrap());
                for (k, &(h, i)) in steps.iter().enumerate() {
                    let end = at + lengths[&(h >> 1)];
                    placed.entry(cols[4].to_string()).or_default().push(Placed {
                        order: (frag, piece, k),
                        contig: (at, end),
                        seq: seq.to_string(),
                        tile: cs,
                        on_r: i.map(|i| (path.stretches[i], path.handles[i] != h)),
                    });
                    at = end;
                }
            }
            if cols[3] == "walk" && !detail {
                let (start, end, _, _) = on_r(offset, &steps);
                stretches
                    .entry((seq.to_string(), cols[4].to_string()))
                    .or_default()
                    .push((start, end));
            }
            decoded.push((
                format!("{}@{}", cols[4], cols[5]),
                cols[7].parse::<u64>().unwrap(),
                offset,
                steps.clone(),
            ));
            pieces
                .entry(format!("{}@{}", cols[4], cols[5]))
                .or_default()
                .insert(
                    cols[7].parse().unwrap(),
                    steps.iter().map(|s| s.0).collect(),
                );
        }
        decoded
    };
    let mut abridged_stretches = Vec::new();
    for ((seq, cs), rows) in &tiles {
        let mut refs: Vec<&Vec<&str>> = rows.iter().filter(|c| c[3] == "ref").collect();
        refs.sort_by_key(|c| c[6].parse::<u64>().unwrap());
        let path = RefPath {
            handles: refs.iter().flat_map(|c| deltas(c[9], &mut 0)).collect(),
            stretches: refs
                .iter()
                .flat_map(|c| {
                    let mut at: u64 = c[6].parse().unwrap();
                    c[10].split(',').map(move |bp| {
                        let start = at;
                        at += bp.parse::<u64>().unwrap();
                        (start, at)
                    })
                })
                .collect(),
        };
        decode_rows(seq, *cs, &path, rows, false);
        let abridged: Vec<&Vec<&str>> = rows.iter().filter(|c| c[3] == "abridged").collect();
        let mut held: Vec<u64> = abridged.iter().map(|c| c[12].parse().unwrap()).collect();
        held.dedup();
        for k in held {
            let record = &details[&(seq.clone(), *cs, k)];
            assert!(record.iter().all(|c| c[3] != "ref" && c[3] != "abridged"));
            let decoded = decode_rows(seq, *cs, &path, record, true);
            let stands: Vec<&&Vec<&str>> = abridged
                .iter()
                .filter(|c| c[12].parse::<u64>().unwrap() == k)
                .collect();
            assert_eq!(
                stands.len(),
                decoded.len(),
                "one abridged row per piece of record {k}"
            );
            for ((name, piece, offset, steps), cols) in decoded.iter().zip(stands) {
                let (start, end, first, last) = on_r(*offset, steps);
                let (start_handle, start_copy) = with_copy(cols[10]);
                let (end_handle, end_copy) = with_copy(cols[11]);
                let (start_handle, end_handle) =
                    (start_handle.parse().unwrap(), end_handle.parse().unwrap());
                let start_at = path.copy(start_handle, start_copy);
                let end_at = match end_copy {
                    Some(k) => path.copy(end_handle, Some(k)),
                    None => path.nearest(end_handle, start_at),
                };
                assert_eq!(
                    path.span([start_at, end_at].into_iter()),
                    (cols[1].parse().unwrap(), cols[2].parse().unwrap()),
                    "an abridged row's span is its start's and end's: {cols:?}"
                );
                assert_eq!(
                    (
                        name.clone(),
                        piece.to_string(),
                        start.to_string(),
                        steps.len().to_string(),
                        (end - start).to_string(),
                        steps[first],
                        steps[last],
                    ),
                    (
                        format!("{}@{}", cols[4], cols[5]),
                        cols[7].to_string(),
                        cols[6].to_string(),
                        cols[8].to_string(),
                        cols[9].to_string(),
                        (start_handle, Some(start_at)),
                        (end_handle, Some(end_at)),
                    ),
                    "{cols:?}"
                );
                abridged_stretches.push(((seq.clone(), cols[4].to_string()), (start, end)));
            }
        }
    }
    for (key, stretch) in abridged_stretches {
        stretches.entry(key).or_default().push(stretch);
    }
    for steps in placed.values_mut() {
        steps.sort_by_key(|p| p.order);
    }
    for (seq, cols) in records {
        let (start, own): (u64, u64) = (cols[2].parse().unwrap(), cols[3].parse().unwrap());
        let holding = own_tiles(&placed[cols[1]], &seq, &cols);
        let named: Vec<u64> = if cols[11] == "." {
            Vec::new()
        } else {
            cols[11].split(',').map(|t| t.parse().unwrap()).collect()
        };
        assert_eq!(
            named, holding,
            "a record's ownTiles are the tiles of S holding the steps strictly between its leave and its rejoin, in the path's order: {cols:?}"
        );
        stretches
            .entry((seq, cols[1].to_string()))
            .or_default()
            .push((start, start + own));
    }
    let paths = pieces
        .into_iter()
        .map(|(path, pieces)| {
            assert!(pieces.keys().copied().eq(0..pieces.len() as u64), "{path}");
            (path, pieces.into_values().flatten().collect())
        })
        .collect();
    Decoded {
        paths,
        stretches,
        reference,
    }
}

// The handles of each W line, by `sample#hap#contig@start`.
fn gfa_paths(gfa: &str) -> HashMap<String, Vec<u32>> {
    gfa.lines()
        .filter(|l| l.starts_with("W\t"))
        .map(|line| {
            let cols: Vec<&str> = line.split('\t').collect();
            let mut handles = Vec::new();
            let walk = cols[6];
            let mut at = 0;
            while at < walk.len() {
                let reverse = u32::from(&walk[at..=at] == "<");
                let end = walk[at + 1..]
                    .find(['<', '>'])
                    .map_or(walk.len(), |p| at + 1 + p);
                handles.push(2 * walk[at + 1..end].parse::<u32>().unwrap() + reverse);
                at = end;
            }
            (
                format!("{}#{}#{}@{}", cols[1], cols[2], cols[3], cols[4]),
                handles,
            )
        })
        .collect()
}

// A decoded walk step: see `decode_file`
struct Placed {
    order: (u64, u64, usize),
    contig: (u64, u64),
    seq: String,
    tile: u64,
    on_r: Option<((u64, u64), bool)>,
}

// The tiles of S holding a record's own steps, the steps of its path strictly
// between its leave step and its rejoin step, in the path's order. The leave
// is a step on S ending at `hapStart` on its contig, at `leavePos` and
// `leaveStrand`; the rejoin is the path's next step on S, starting
// `ownBp` later, at `rejoinPos` and `rejoinStrand`.
fn own_tiles(steps: &[Placed], seq: &str, cols: &[&str]) -> Vec<u64> {
    let number = |k: usize| cols[k].parse::<u64>().unwrap();
    let (start, own, leave_pos, rejoin_pos) = (number(2), number(3), number(5), number(8));
    let on_s: Vec<usize> = (0..steps.len())
        .filter(|&k| steps[k].seq == seq && steps[k].on_r.is_some())
        .collect();
    let end = |k: usize, leave: bool, strand: &str| {
        let ((lo, hi), against) = steps[k].on_r.unwrap();
        let bp = if against == leave { lo } else { hi };
        (bp, if against { "-" } else { "+" })
            == (if leave { leave_pos } else { rejoin_pos }, strand)
    };
    let pair = on_s.windows(2).rev().find(|w| {
        steps[w[0]].contig.1 == start
            && end(w[0], true, cols[6])
            && steps[w[1]].contig.0 == start + own
            && end(w[1], false, cols[9])
    });
    let (leave, rejoin) = pair
        .map(|w| (w[0], w[1]))
        .unwrap_or_else(|| panic!("no leave and rejoin step for {cols:?}"));
    let mut tiles = Vec::new();
    for step in &steps[leave + 1..rejoin] {
        if step.seq == seq && !tiles.contains(&step.tile) {
            tiles.push(step.tile);
        }
    }
    tiles
}

// Each reference's file lists every W line with a step on a node of that
// reference and no other, every path rebuilds from its rows, and from its
// first step on a sequence to its last every base of it lies in one piece's
// stretch on R or one record's own bp, so a reader that nets an abridged
// piece over its stretch and takes the departures at its ends from their
// records counts each base once
fn assert_rebuilds(gfa: &str, built: &Built, samples: &[&str]) {
    let paths = gfa_paths(gfa);
    for sample in samples {
        let decoded = decode_file(built.file(sample));
        assert!(!decoded.paths.is_empty(), "{sample}");
        let on_reference: BTreeSet<&String> = paths
            .iter()
            .filter(|(_, handles)| {
                handles
                    .iter()
                    .any(|h| decoded.reference.contains(&(h >> 1)))
            })
            .map(|(path, _)| path)
            .collect();
        assert_eq!(
            decoded.paths.keys().collect::<BTreeSet<_>>(),
            on_reference,
            "{sample}: the lines with a step on a node of the reference"
        );
        for (path, steps) in &decoded.paths {
            assert_eq!(steps, &paths[path], "{sample}: {path}");
        }
        for ((seq, path), stretches) in &decoded.stretches {
            assert_tiles(stretches, &format!("{sample}: {seq} {path}"));
        }
    }
}

fn assert_tiles(stretches: &[(u64, u64)], what: &str) {
    let mut sorted = stretches.to_vec();
    sorted.sort_unstable();
    for pair in sorted.windows(2) {
        assert_eq!(pair[0].1, pair[1].0, "{what}: {sorted:?}");
    }
}

#[test]
fn every_path_rebuilds_from_its_rows() {
    for (gfa, refs, tile) in [
        ("walks-two-refs.gfa", "GRCh38,Q", "10"),
        ("walks-two-refs.gfa", "GRCh38,Q", "7"),
        ("walks-two-refs.gfa", "GRCh38,Q", "1000"),
        ("walks-repeat.gfa", "R", "10"),
        ("walks-repeat.gfa", "R", "1000"),
        ("walks-loop.gfa", "R", "10"),
        ("walks-loop.gfa", "R", "1000"),
        ("walks-records.gfa", "R", "10"),
        ("walks-contig-ends.gfa", "R", "10"),
        ("walks-skip.gfa", "R,Q", "10"),
    ] {
        let built = build(gfa, &["--refs", refs, "--tile", tile]);
        assert!(built.output.status.success(), "{gfa} {tile}");
        let samples: Vec<&str> = refs.split(',').collect();
        assert_rebuilds(&fs::read_to_string(fixture(gfa)).unwrap(), &built, &samples);
    }
}

// Past a byte budget of 1, a tile moves its paths to detail rows, costliest
// first, until its estimate of the bytes left runs out, which can leave the
// cheapest path in the tile
#[test]
fn every_path_rebuilds_from_its_detail_rows_when_abridged() {
    for (gfa, refs) in [
        ("walks-two-refs.gfa", "GRCh38,Q"),
        ("walks-repeat.gfa", "R"),
        ("walks-loop.gfa", "R"),
        ("walks-records.gfa", "R"),
        ("walks-contig-ends.gfa", "R"),
    ] {
        let built = build(gfa, &["--refs", refs, "--abridge-bytes", "1"]);
        assert!(built.output.status.success(), "{gfa}");
        for &sample in &refs.split(',').collect::<Vec<_>>() {
            let text = built.file(sample);
            assert!(
                text.lines()
                    .any(|l| l.split('\t').nth(3) == Some("abridged")),
                "{gfa}"
            );
        }
        let samples: Vec<&str> = refs.split(',').collect();
        assert_rebuilds(&fs::read_to_string(fixture(gfa)).unwrap(), &built, &samples);
    }
}

// Under --abridge-bytes n, every tile that keeps a walk row has rows, other
// than its abridged rows and from kind on, that deflate at level 6 in blocks
// of 65,280 bytes to at most n bytes
#[test]
fn a_tile_that_keeps_walk_rows_fits_its_budgets() {
    use flate2::write::DeflateEncoder;
    let deflated = |text: &str| -> usize {
        text.as_bytes()
            .chunks(65280)
            .map(|block| {
                let mut encoder = DeflateEncoder::new(Vec::new(), Compression::new(6));
                encoder.write_all(block).unwrap();
                encoder.finish().unwrap().len()
            })
            .sum()
    };
    for gfa in [
        "walks-repeat.gfa",
        "walks-loop.gfa",
        "walks-records.gfa",
        "walks-contig-ends.gfa",
    ] {
        for budget in [40, 80, 120, 160, 200, 240, 300] {
            let built = build(
                gfa,
                &[
                    "--refs",
                    "R",
                    "--tile",
                    "20",
                    "--abridge-bytes",
                    &budget.to_string(),
                ],
            );
            assert!(built.output.status.success(), "{gfa}");
            for (head, lines) in units(built.file("R")) {
                let rows: Vec<&str> = lines
                    .iter()
                    .filter(|l| l.split('\t').nth(3) != Some("abridged"))
                    .map(|l| l.splitn(4, '\t').nth(3).unwrap())
                    .collect();
                if head[3] == "tile" && rows.iter().any(|r| r.starts_with("walk\t")) {
                    let text: String = rows.iter().map(|r| format!("{r}\n")).collect();
                    assert!(deflated(&text) <= budget, "{gfa} {budget}: {head:?}");
                }
            }
        }
    }
}

// walks-abridge-bytes.gfa: 60 haplotypes with long contig names take R's
// one route-free piece in tile 0. Under a byte budget the tile moves the
// fewest paths whose leaving brings its rows within it: its kept rows
// deflate to at most the budget, and with the last moved path's walk row
// put back, in path order, to more. The writer moved 40 at 600 where 29
// fit, and 15 at 900 where 10 did, from an estimate it only ever added to
#[test]
fn a_tile_over_its_byte_budget_moves_the_fewest_paths_that_bring_it_within() {
    use flate2::write::DeflateEncoder;
    let deflated = |rows: &[&str]| -> usize {
        let text: String = rows.iter().map(|r| format!("{r}\n")).collect();
        text.as_bytes()
            .chunks(65280)
            .map(|block| {
                let mut encoder = DeflateEncoder::new(Vec::new(), Compression::new(6));
                encoder.write_all(block).unwrap();
                encoder.finish().unwrap().len()
            })
            .sum()
    };
    fn from_kind<'a>(line: &&'a str) -> &'a str {
        line.splitn(4, '\t').nth(3).unwrap()
    }
    for budget in [300, 600, 900] {
        let built = build(
            "walks-abridge-bytes.gfa",
            &[
                "--refs",
                "R",
                "--tile",
                "100",
                "--abridge-bytes",
                &budget.to_string(),
            ],
        );
        assert!(built.output.status.success());
        let units = units(built.file("R"));
        let tile = &units.iter().find(|(head, _)| head[3] == "tile").unwrap().1;
        let kept: Vec<&str> = tile
            .iter()
            .filter(|l| l.split('\t').nth(3) != Some("abridged"))
            .map(from_kind)
            .collect();
        let moved = tile.len() - kept.len();
        assert!(moved > 0, "{budget}");
        let last = &units
            .iter()
            .find(|(head, _)| head[3] == "detail" && head[4] == format!("0:{}", moved - 1))
            .unwrap()
            .1;
        let mut more = kept.clone();
        more.extend(last.iter().map(from_kind));
        let key = |r: &&str| -> (Vec<u8>, u64, u64) {
            let c: Vec<&str> = r.split('\t').collect();
            (
                c[1].as_bytes().to_vec(),
                c[2].parse().unwrap(),
                c[3].parse().unwrap(),
            )
        };
        more[1..].sort_by_key(key);
        assert!(deflated(&kept) <= budget, "{budget}: {moved} moved");
        assert!(
            deflated(&more) > budget,
            "{budget}: {moved} moved, one too many"
        );
    }
}

// D#1#d's pieces 0 and 2 lie in tile 0, with piece 1 in tile 10 between
// them, so tile 0 has a row for each, both naming the tile's second detail
// record, unit 0:1, and each row's hapOffset and bp give where its own piece
// lies on the contig: 0 to 12 and 24 to 36, not 0 to 24. Each row's span is
// its piece's on R, nodes 1 and 2, 0 to 12; the detail unit's extent is the
// union of its walk rows' spans
#[test]
fn an_abridged_row_stands_for_one_piece_and_names_its_detail_record() {
    let built = build("walks-two-refs.gfa", &["--abridge-bytes", "1"]);
    let r = built.file("GRCh38");
    assert_eq!(
        rows_of(r, "GRCh38#0#chr", "abridged", "D#1#d"),
        tsv(&[
            "GRCh38#0#chr 0 12 abridged D#1#d 0 0 0 2 12 2 4 1",
            "GRCh38#0#chr 0 12 abridged D#1#d 0 24 2 2 12 2 4 1",
            "GRCh38#0#chr 12 24 abridged D#1#d 0 12 1 2 12 6 8 1",
            "GRCh38#0#chr 12 24 abridged D#1#d 0 36 3 2 12 6 8 1",
            "GRCh38#0#chr 24 30 abridged D#1#d 0 48 4 1 6 10 10 0",
        ])
    );
    assert_eq!(
        unit(r, "detail", "0:1"),
        tsv(&[
            "#unit GRCh38#0#chr 0 12 detail 0:1",
            "GRCh38#0#chr 0 12 walk D#1#d 0 0 0 2 2 .",
            "GRCh38#0#chr 0 12 walk D#1#d 0 24 2 2 2 .",
        ])
    );
}

// R is 1-6, 6 bp each; L starts with 30 bp of its own, 11 12 13, before 3,
// and M ends with them after 3. Those steps lie at the contig's ends, where
// no record covers them, so each abridged row spans its piece from its
// first step on R to its last: L's piece 0 from 3's start at 30 for 12 bp,
// M's piece 1 over 3 alone, at 12 for 6. nsteps still counts the whole
// piece, 5 and 4 steps, which its detail record decodes.
#[test]
fn an_abridged_row_spans_its_piece_from_its_first_step_on_r_to_its_last() {
    let built = build(
        "walks-contig-ends.gfa",
        &["--refs", "R", "--abridge-bytes", "1"],
    );
    let r = built.file("R");
    assert_eq!(
        rows_of(r, "R#0#c", "abridged", "L#1#c") + &rows_of(r, "R#0#c", "abridged", "M#1#c"),
        tsv(&[
            "R#0#c 12 24 abridged L#1#c 0 30 0 5 12 6 8 0",
            "R#0#c 24 30 abridged L#1#c 0 42 1 1 6 10 10 0",
            "R#0#c 30 36 abridged L#1#c 0 48 2 1 6 12 12 0",
            "R#0#c 0 12 abridged M#1#c 0 0 0 2 12 2 4 0",
            "R#0#c 12 18 abridged M#1#c 0 12 1 4 6 6 6 1",
        ])
    );
    assert_eq!(departures(r), "");
    assert_eq!(
        unit(r, "detail", "10:0") + &unit(r, "detail", "10:1"),
        tsv(&[
            "#unit R#0#c 12 24 detail 10:0",
            "R#0#c 12 24 nodes 11,1,1 10,10,10",
            "R#0#c 12 24 route . 22,2,2 -20",
            "R#0#c 12 24 walk L#1#c 0 0 0 5 6 0",
            "#unit R#0#c 12 18 detail 10:1",
            "R#0#c 12 18 nodes 11,1,1 10,10,10",
            "R#0#c 12 18 route . 27,-1,-1 -15",
            "R#0#c 12 18 walk M#1#c 0 12 1 4 6 1",
        ])
    );
}

#[test]
fn each_reference_has_one_file_holding_only_its_rows() {
    let built = build("walks-two-refs.gfa", &[]);
    assert_eq!(built.files.keys().collect::<Vec<_>>(), ["GRCh38", "Q"]);
    for (sample, text) in &built.files {
        let anchor = format!("{sample}#0#chr");
        let rows: Vec<&str> = text.lines().filter(|l| !l.starts_with('#')).collect();
        assert!(!rows.is_empty(), "{sample}");
        assert!(
            rows.iter()
                .all(|row| row.starts_with(&format!("{anchor}\t"))
                    || row.starts_with(&format!("{anchor}~"))),
            "{sample}"
        );
    }
}

// walks-skip.gfa: R#0#chr and Q#0#chr walk 1 2 3 4 5, at 0, 10, 20, 60 and 70,
// node 3 being 40 bp. D#1#d goes from 2 straight to 5, leaving R where 2 ends
// at 20 and rejoining where 5 starts at 70, with no sequence of its own
// between; its ends' pieces are filed under tiles 10 and 70. B#1#b does the
// same on the reverse strand, leaving at 5's start and rejoining at 2's end,
// both steps against R. Each record's extent runs from its end nodes' first
// base to their last, 2's start at 10 to 5's end at 80. Each reference walks
// the other as itself, so it has no departure.
#[test]
fn a_path_that_jumps_over_the_reference_has_a_departure_record_over_the_stretch() {
    let built = build("walks-skip.gfa", &["--refs", "R,Q"]);
    for sample in ["R", "Q"] {
        let anchor = format!("{sample}#0#chr");
        assert_eq!(
            departures(built.file(sample)),
            tsv(&[
                &format!("{anchor} 10 80 departure B#1#b 10 0 0 70 - 1 20 - 1 ."),
                &format!("{anchor} 10 80 departure D#1#d 20 0 0 20 + 1 70 + 1 ."),
            ]),
            "{sample}"
        );
    }
}

// walks-two-refs.gfa at --tile 10. Q carries 6 in place of 2, 6 bp of its
// own between 1's end at 6 and 3's start at 12. I leaves 1 for 3 inverted,
// rejoining at 3's end at 18, then leaves 2 inverted at its start at 6 for 4
// at 18; between its <3 and <2 it follows R backwards, so there is no
// departure. D jumps back from 4's end at 24 to 1's start. H's insertion of 7
// lies inside its piece in tile 10, where the walk row shows it. With every
// path in one tile no departure lies between pieces, and there are none.
#[test]
fn a_departure_between_pieces_has_a_record_and_one_inside_a_piece_has_none() {
    let built = build("walks-two-refs.gfa", &[]);
    assert_eq!(
        departures(built.file("GRCh38")),
        tsv(&[
            "GRCh38#0#chr 0 18 departure I#1#i 6 0 0 6 + 1 18 - 1 .",
            "GRCh38#0#chr 0 18 departure Q#0#chr 6 6 0 6 + 1 12 + 1 0",
            "GRCh38#0#chr 0 24 departure D#1#d 24 0 0 24 + 1 0 + 1 .",
            "GRCh38#0#chr 6 24 departure I#1#i 18 0 0 6 - 1 18 + 1 .",
        ])
    );
    let whole = build("walks-two-refs.gfa", &["--tile", "1000"]);
    assert!(whole.output.status.success());
    assert_eq!(departures(&whole.walks), "");
}

// No line points at a departure block, so it is named `.`; a tile's start
// and a detail record's `cs:d`, which `ownTiles` and `abridged` rows point
// at, are unique within their kind and sequence. At --tile 1 the records of
// walks-two-refs.gfa cover blocks of 1 and 8 bp, several of each size and
// two at 16, and --abridge-bytes 1 moves pieces to several detail records
// per tile
#[test]
fn a_departure_block_is_named_dot_and_every_other_name_is_unique() {
    let built = build(
        "walks-two-refs.gfa",
        &["--tile", "1", "--abridge-bytes", "1"],
    );
    assert!(built.output.status.success());
    let heads: Vec<Vec<&str>> = units(&built.walks)
        .into_iter()
        .map(|(head, _)| head)
        .collect();
    let blocks: Vec<&Vec<&str>> = heads.iter().filter(|h| h[3] == "departures").collect();
    let sizes: BTreeMap<u64, usize> = blocks.iter().fold(BTreeMap::new(), |mut sizes, head| {
        let (lo, hi): (u64, u64) = (head[1].parse().unwrap(), head[2].parse().unwrap());
        *sizes.entry(hi - lo).or_default() += 1;
        sizes
    });
    assert!(sizes.values().all(|&n| n > 1), "{sizes:?}");
    assert_eq!(sizes.keys().collect::<Vec<_>>(), [&1, &8]);
    assert!(blocks.iter().all(|head| head[4] == "."), "{blocks:?}");
    let named: Vec<(&str, &str, &str)> = heads
        .iter()
        .filter(|h| h[4] != ".")
        .map(|h| (h[0], h[3], h[4]))
        .collect();
    let kinds: BTreeSet<&str> = named.iter().map(|n| n.1).collect();
    assert_eq!(kinds, BTreeSet::from(["detail", "tile"]));
    assert_eq!(named.iter().collect::<BTreeSet<_>>().len(), named.len());
}

// R has chr1 (1 2) and chr2 (3 4); H walks 1 2 3 4, then 5 of its own. On
// chr1 H leaves at 2's end and never comes back, and on chr2 it arrives from
// chr1 and goes on to 5: no step on either sequence lies on both sides of
// those stretches, so none is a departure, and the file has no record. Its
// pieces show where it goes: on chr2 a route from 4 onto 5, stored the way
// round whose handles sort first and taken flipped.
#[test]
fn a_contig_that_leaves_a_sequence_for_good_has_no_record() {
    let built = build_text(
        "one-ended",
        &[
            "S 1 AAAAAA",
            "S 2 AAAAAA",
            "S 3 AAAAAA",
            "S 4 AAAAAA",
            "S 5 AAAAAA",
            "W R 0 chr1 0 12 >1>2",
            "W R 0 chr2 0 12 >3>4",
            "W H 1 h 0 30 >1>2>3>4>5",
        ],
        &["--refs", "R"],
    );
    assert!(built.output.status.success());
    assert_eq!(departures(&built.walks), "");
    assert_eq!(
        rows_of(built.file("R"), "R#0#chr1", "walk", "H#1#h")
            + &rows_of(built.file("R"), "R#0#chr2", "route", ".")
            + &rows_of(built.file("R"), "R#0#chr2", "walk", "H#1#h"),
        tsv(&[
            "R#0#chr1 0 12 walk H#1#h 0 0 0 2 2 .",
            "R#0#chr2 0 12 route . 11 -1",
            "R#0#chr2 0 12 walk H#1#h 0 12 1 3 6 1",
        ])
    );
}

// R's chr has two lines, 0-12 and 20-32, so 12-20 is a hole, and a third line
// at 16 with no steps, which covers nothing. H steps from 2, ending at 12, to
// 3, starting at 20: adjacent once the hole is removed, so it has no record.
// G walks 8 bp of its own there.
#[test]
fn steps_either_side_of_a_hole_in_the_reference_are_adjacent() {
    let built = build_text(
        "hole",
        &[
            "S 1 AAAAAA",
            "S 2 AAAAAA",
            "S 3 AAAAAA",
            "S 4 AAAAAA",
            "S 5 AAAAAAAA",
            "W R 0 chr 0 12 >1>2",
            "W R 0 chr 16 16 ",
            "W R 0 chr 20 32 >3>4",
            "W H 1 h 0 24 >1>2>3>4",
            "W G 1 g 0 32 >1>2>5>3>4",
        ],
        &["--refs", "R"],
    );
    assert!(built.output.status.success());
    let walks = built.file("R");
    assert_eq!(
        header(walks)
            .lines()
            .filter(|l| l.starts_with("#hole"))
            .collect::<Vec<_>>(),
        ["#hole\tR#0#chr\t12\t20"]
    );
    assert_eq!(
        departures(walks),
        tsv(&["R#0#chr 6 26 departure G#1#g 12 8 0 12 + 1 20 + 1 0"])
    );
}

// R walks 1 2 3 2 3 4 with 10 bp nodes, all in one tile. H walks 3 4, which
// placement puts on the second 3, at 40, beside 4. The default copy is R's
// first, so the row names occurrence 1, and then follows R with no route.
#[test]
fn a_walk_row_names_the_copy_it_starts_on_where_it_is_not_the_first() {
    let built = build_text(
        "copy",
        &[
            "S 1 AAAAAAAAAA",
            "S 2 AAAAAAAAAA",
            "S 3 AAAAAAAAAA",
            "S 4 AAAAAAAAAA",
            "W R 0 chr 0 60 >1>2>3>2>3>4",
            "W H 1 h 0 20 >3>4",
        ],
        &["--refs", "R", "--tile", "1000"],
    );
    assert_eq!(
        rows_of(built.file("R"), "R#0#chr", "walk", "H#1#h"),
        tsv(&["R#0#chr 40 60 walk H#1#h 0 0 0 2 6@1 ."])
    );
}

// R walks 1 2 3 2 3 4 with 10 bp nodes, all in one tile. H carries 25 bp of
// its own on node 5 between 1 and 3, so placement predicts 3 at 35 and puts
// it on the second 3, at 40, though the occurrence nearest the route's entry
// is the first: the choice names occurrence 1. Abridged, the row's end names
// it too, since the 3 nearest its start is the first.
#[test]
fn a_route_exit_and_an_abridged_end_name_the_copy_where_it_is_not_the_nearest() {
    let lines = [
        "S 1 AAAAAAAAAA",
        "S 2 AAAAAAAAAA",
        "S 3 AAAAAAAAAA",
        "S 4 AAAAAAAAAA",
        "S 5 AAAAAAAAAAAAAAAAAAAAAAAAA",
        "W R 0 chr 0 60 >1>2>3>2>3>4",
        "W H 1 h 0 45 >1>5>3",
    ];
    let built = build_text("exit-copy", &lines, &["--refs", "R", "--tile", "1000"]);
    assert_eq!(
        rows_of(built.file("R"), "R#0#chr", "route", "2")
            + &rows_of(built.file("R"), "R#0#chr", "walk", "H#1#h"),
        tsv(&[
            "R#0#chr 0 60 route 2 8 -4",
            "R#0#chr 0 50 walk H#1#h 0 0 0 3 2 0@1",
        ])
    );
    let abridged = build_text(
        "exit-copy-abridged",
        &lines,
        &["--refs", "R", "--tile", "1000", "--abridge-bytes", "1"],
    );
    assert_eq!(
        rows_of(abridged.file("R"), "R#0#chr", "abridged", "H#1#h"),
        tsv(&["R#0#chr 0 50 abridged H#1#h 0 0 0 3 45 2 6@1 0"])
    );
    assert_eq!(
        unit(abridged.file("R"), "detail", "0:0"),
        tsv(&[
            "#unit R#0#chr 0 50 detail 0:0",
            "R#0#chr 0 50 nodes 5 25",
            "R#0#chr 0 50 route 2 8 -4",
            "R#0#chr 0 50 walk H#1#h 0 0 0 3 2 0@1",
        ])
    );
}

// R walks 2 then three copies of the 2 bp node 1, then 3; H walks one more 1,
// which placement puts on R's last, at 14, twice. Stepping along R from 2
// until a 1 would stop at R's first, so the route's token names the
// occurrence the walk leaves from, `:2`, the last; its exit lands on the
// occurrence nearest that, the same one, by default.
#[test]
fn a_walk_row_names_the_copy_it_leaves_r_from_where_stepping_would_stop_early() {
    let built = build_text(
        "counts",
        &[
            "S 1 AA",
            "S 2 AAAAAAAAAA",
            "S 3 AAAAAAAAAA",
            "W R 0 chr 0 26 >2>1>1>1>3",
            "W H 1 h 0 28 >2>1>1>1>1>3",
        ],
        &["--refs", "R", "--tile", "1000"],
    );
    assert_eq!(
        rows_of(built.file("R"), "R#0#chr", "route", "2")
            + &rows_of(built.file("R"), "R#0#chr", "walk", "H#1#h"),
        tsv(&[
            "R#0#chr 0 26 route 2 . 0",
            "R#0#chr 0 26 walk H#1#h 0 0 0 6 4 0:2",
        ])
    );
}

// U#1#u visits no reference node, so it has no rows and no line. Each walk
// file lists the other reference among its haplotypes, since its walk has
// rows there.
#[test]
fn a_walk_file_names_its_format_reference_and_each_haplotype_with_rows() {
    let built = build("walks-two-refs.gfa", &[]);
    for (sample, haplotypes) in [
        ("GRCh38", ["D#1", "H#1", "I#1", "Q#0"]),
        ("Q", ["D#1", "GRCh38#0", "H#1", "I#1"]),
    ] {
        let walks = "#walks format:i:7 tile:i:10 revisited:i:0 stay:i:311 abridge:i:1000000 abridgebytes:i:3000000";
        let reference = format!("#reference {sample}");
        let listed = haplotypes.map(|h| format!("#haplotype {h}"));
        let lines: Vec<&str> = [walks, &reference]
            .into_iter()
            .chain(listed.iter().map(String::as_str))
            .collect();
        assert_eq!(header(built.file(sample)), tsv(&lines));
    }
}

// R is 1 2 3 4, 6 bp each, so tile 0-10 holds 1 and 2 and tile 10-20 holds
// 3 and 4; 5, 6 and 7 are 8 bp of a path's own. Each path jumps back from
// 4's end at 24 to 1's start at 0, its own steps between. J's line walks 5
// after 4: own steps after the leave take the leave's tile, 10. H's first
// line ends with 4 and its next, from 30, starts with 5 before 1: steps
// leading a line take the tile of the first reference step after them, the
// rejoin's, 0, where a read at the leave would miss them. K's first line
// ends with 6 after 4 and its next starts with 7 before 1, so both
#[test]
fn a_record_names_the_tiles_holding_its_own_steps() {
    let built = build_text(
        "own-tiles",
        &[
            "S 1 AAAAAA",
            "S 2 AAAAAA",
            "S 3 AAAAAA",
            "S 4 AAAAAA",
            "S 5 CCCCCCCC",
            "S 6 GGGGGGGG",
            "S 7 TTTTTTTT",
            "W R 0 chr 0 24 >1>2>3>4",
            "W J 1 j 0 38 >1>2>3>4>5>1",
            "W H 1 h 0 24 >1>2>3>4",
            "W H 1 h 30 44 >5>1",
            "W K 1 k 0 32 >1>2>3>4>6",
            "W K 1 k 40 54 >7>1",
        ],
        &["--refs", "R"],
    );
    assert!(built.output.status.success());
    assert_eq!(
        departures(built.file("R")),
        tsv(&[
            "R#0#chr 0 24 departure H#1#h 24 14 6 24 + 1 0 + 1 0",
            "R#0#chr 0 24 departure J#1#j 24 8 0 24 + 1 0 + 1 10",
            "R#0#chr 0 24 departure K#1#k 24 24 8 24 + 1 0 + 1 10,0",
        ])
    );
    decode_file(built.file("R"));
}

// A tile's ref row lists its reference steps and their lengths, and its
// nodes row the ids and lengths of the nodes its routes visit off R. H's
// insertion of 7 between 3 and 4 is the tile's one route, and H's walk row
// names it after starting on 3. Q's 6 in place of 2 is a route off R that
// leaves R at 1 and does not return in tile 0-10; stored the way round whose
// handles sort first, it reads 6 reversed back onto 1 reversed, and Q's walk
// row takes it flipped. With --stay 0, D and I file each return to tile 0-10
// as a piece of its own.
#[test]
fn a_tile_holds_its_reference_its_routes_and_a_walk_row_per_piece() {
    let built = build("walks-two-refs.gfa", &["--stay", "0"]);
    let r = built.file("GRCh38");
    assert_eq!(
        unit(r, "tile", "0"),
        tsv(&[
            "#unit GRCh38#0#chr 0 12 tile 0",
            "GRCh38#0#chr 0 12 ref GRCh38#0#chr 0 0 0 2 2,2 6,6 .",
            "GRCh38#0#chr 0 12 nodes 6 6",
            "GRCh38#0#chr 0 12 route . 13 -9",
            "GRCh38#0#chr 0 12 walk D#1#d 0 0 0 2 2 .",
            "GRCh38#0#chr 0 12 walk D#1#d 0 24 2 2 2 .",
            "GRCh38#0#chr 0 12 walk H#1#h 100 100 0 2 2 .",
            "GRCh38#0#chr 0 6 walk I#1#i 0 0 0 1 2 .",
            "GRCh38#0#chr 6 12 walk I#1#i 0 12 2 1 5 .",
            "GRCh38#0#chr 0 6 walk Q#0#chr 0 0 0 2 2 1",
        ])
    );
    assert_eq!(
        rows_of(r, "GRCh38#0#chr", "route", "6") + &rows_of(r, "GRCh38#0#chr", "walk", "H#1#h"),
        tsv(&[
            "GRCh38#0#chr 12 24 route 6 8 -6",
            "GRCh38#0#chr 0 12 walk H#1#h 100 100 0 2 2 .",
            "GRCh38#0#chr 12 24 walk H#1#h 100 112 1 3 6 0",
            "GRCh38#0#chr 24 30 walk H#1#h 100 127 2 1 10 .",
        ])
    );
}

// walks-repeat.gfa: R#0#chr walks 1 2 3 2 3 4, a two-node repeat collapsed
// into one copy. Nodes 1-3 are 6 bp and node 4 is 15 bp, so R reaches them at
// 0, 6, 12, 18, 24 and 30 and ends at 45. H#1#h takes the same steps. Placed by
// first visit, the repeat's second pass would be filed under tile 0-10 and
// 10-20 again; on R's own path each step takes the tile of its own offset.
// H, following R, takes each pass of the repeat in turn and is filed as R is.
#[test]
fn a_reference_files_its_own_revisits_at_its_own_offset() {
    let built = build("walks-repeat.gfa", &["--refs", "R"]);
    assert!(built.output.status.success());
    let walks = built.file("R");
    assert!(
        header(walks).starts_with("#walks\tformat:i:7\ttile:i:10\trevisited:i:2\tstay:i:311\t")
    );
    assert_eq!(
        rows_of(walks, "R#0#chr", "ref", "R#0#chr"),
        tsv(&[
            "R#0#chr 0 12 ref R#0#chr 0 0 0 2 2,2 6,6 1,2",
            "R#0#chr 12 24 ref R#0#chr 0 12 1 2 6,-2 6,6 2,2",
            "R#0#chr 24 30 ref R#0#chr 0 24 2 1 6 6 2",
            "R#0#chr 30 45 ref R#0#chr 0 30 3 1 8 15 .",
        ])
    );
    assert_eq!(
        rows_of(walks, "R#0#chr", "walk", "H#1#h"),
        tsv(&[
            "R#0#chr 0 12 walk H#1#h 0 0 0 2 2 .",
            "R#0#chr 12 24 walk H#1#h 0 12 1 2 6 .",
            "R#0#chr 24 30 walk H#1#h 0 24 2 1 6 .",
            "R#0#chr 30 45 walk H#1#h 0 30 3 1 8 .",
        ])
    );
}

// walks-loop.gfa, in one tile: R walks 1 2 3 2 3 4. A takes the repeat three
// times. Following R from 1 until a 3 would stop a pass early, at R's first,
// so A's route token names the occurrence it leaves from, `:1`, the second.
// F inserts 5 inside the second copy and leaves R from the second 2 likewise.
// B jumps from the first 3 to 4, where stepping stops right.
#[test]
fn a_walk_the_default_rule_would_misread_names_the_copy_it_leaves_from() {
    let built = build("walks-loop.gfa", &["--refs", "R", "--tile", "1000"]);
    assert!(built.output.status.success());
    let walks = built.file("R");
    assert_eq!(
        rows_of(walks, "R#0#chr", "walk", "A#1#a") + &rows_of(walks, "R#0#chr", "walk", "F#1#f"),
        tsv(&[
            "R#0#chr 0 45 walk A#1#a 0 0 0 8 2 5:1",
            "R#0#chr 0 45 walk F#1#f 0 0 0 7 2 2:1",
        ])
    );
    assert_eq!(
        rows_of(walks, "R#0#chr", "walk", "B#1#b"),
        tsv(&["R#0#chr 0 45 walk B#1#b 0 0 0 4 2 6"])
    );
    let stderr = String::from_utf8_lossy(&built.output.stderr);
    assert!(stderr.contains("6 walk rows, 2 copies named"), "{stderr}");
}

#[test]
fn a_walk_back_into_a_tile_starts_a_new_piece_there() {
    let built = build("walks-two-refs.gfa", &["--stay", "0"]);
    assert_eq!(
        rows_of(&built.walks, "GRCh38#0#chr", "walk", "D#1#d"),
        tsv(&[
            "GRCh38#0#chr 0 12 walk D#1#d 0 0 0 2 2 .",
            "GRCh38#0#chr 0 12 walk D#1#d 0 24 2 2 2 .",
            "GRCh38#0#chr 12 24 walk D#1#d 0 12 1 2 6 .",
            "GRCh38#0#chr 12 24 walk D#1#d 0 36 3 2 6 .",
            "GRCh38#0#chr 24 30 walk D#1#d 0 48 4 1 10 .",
        ])
    );
}

// docs/walks-format.md's Example quotes GRCh38's file of this build: its
// directory, with offsets and lengths elided, then lines of its units, each
// with its columns aligned by spaces
#[test]
fn the_specs_example_quotes_the_tools_lines() {
    let built = build("walks-two-refs.gfa", &["--stay", "0"]);
    let spec = fs::read_to_string(format!(
        "{}/docs/walks-format.md",
        env!("CARGO_MANIFEST_DIR")
    ))
    .unwrap();
    let example = &spec[spec.find("\n## Example\n").unwrap()..];
    let blocks: Vec<&str> = example.split("```\n").skip(1).step_by(2).take(2).collect();
    let quoted = |block: &str| -> Vec<String> {
        block
            .lines()
            .map(|l| l.split_whitespace().collect::<Vec<_>>().join("\t"))
            .collect()
    };
    let directory = quoted(blocks[0]);
    assert_eq!(
        directory[1..],
        ["#header\t0\t…", "GRCh38#0#chr\t…\t…"],
        "{directory:?}"
    );
    assert!(directory[0].ends_with("\tbytes:i:…"));
    let lines: BTreeSet<&str> = built.file("GRCh38").lines().collect();
    assert!(lines.contains(directory[0].strip_suffix("\tbytes:i:…").unwrap()));
    let rows = quoted(blocks[1]);
    assert_eq!(rows.len(), 9);
    for row in &rows {
        assert!(lines.contains(row.as_str()), "{row}");
    }
}

// K takes walks-repeat.gfa's collapsed repeat three times. Placed nearest, its
// steps fall in tiles 0 0 10 10 20 10 20 30, at 0 6 12 18 24 18 24 30: the 3
// at 24 is a 6 bp stretch in tile 20-30 between two of tile 10-20's steps.
// --stay 12 keeps it in K's piece at 10-20 on that tile's 3, at 12, 12 bp
// from the 24 its previous step predicts, so the piece walks 3 2 3 2. --stay 6
// refuses that, but keeps the next stretch, the 2 at 18 between two steps of
// tile 20-30, as route interior, since tile 20-30's R has no 2; the piece
// there reads 3 <route through 2> 3 on R's one 3. --stay 5 keeps neither, so
// K takes six pieces and a record for its jump back from 3's end at 30 to 2's
// start at 18, both nodes R passes twice.
#[test]
fn a_short_stretch_over_a_revisited_node_stays_in_its_piece_on_a_pass_there() {
    let gfa = fs::read_to_string(fixture("walks-repeat.gfa")).unwrap()
        + "W\tK\t1\tk\t0\t57\t>1>2>3>2>3>2>3>4\n";
    let path = std::env::temp_dir().join(format!("walks-stay-{}.gfa", std::process::id()));
    fs::write(&path, gfa).unwrap();
    let built = |stay: &str| build(path.to_str().unwrap(), &["--refs", "R", "--stay", stay]);
    let (moved, interior, cut) = (built("12"), built("6"), built("5"));
    fs::remove_file(&path).unwrap();
    assert_eq!(
        rows_of(moved.file("R"), "R#0#chr", "walk", "K#1#k"),
        tsv(&[
            "R#0#chr 0 12 walk K#1#k 0 0 0 2 2 .",
            "R#0#chr 12 24 walk K#1#k 0 12 1 4 6 0",
            "R#0#chr 24 30 walk K#1#k 0 36 2 1 6 .",
            "R#0#chr 30 45 walk K#1#k 0 42 3 1 8 .",
        ])
    );
    assert_eq!(
        rows_of(interior.file("R"), "R#0#chr", "walk", "K#1#k"),
        tsv(&[
            "R#0#chr 0 12 walk K#1#k 0 0 0 2 2 .",
            "R#0#chr 12 24 walk K#1#k 0 12 1 2 6 .",
            "R#0#chr 24 30 walk K#1#k 0 24 2 3 6 0",
            "R#0#chr 30 45 walk K#1#k 0 42 3 1 8 .",
        ])
    );
    for built in [&moved, &interior] {
        assert_eq!(departures(&built.walks), "");
    }
    assert_eq!(
        rows_of(cut.file("R"), "R#0#chr", "walk", "K#1#k")
            .lines()
            .count(),
        6
    );
    assert_eq!(
        departures(cut.file("R")),
        tsv(&["R#0#chr 18 30 departure K#1#k 30 0 0 30 + 2 18 + 2 ."])
    );
}

// In walks-repeat.gfa R passes 2 and 3 twice and 1 and 4 once. X follows R
// to 4's end at 45 and jumps back to 2's second pass at 18: its leave is on a
// node R passes once and its rejoin on one R passes twice, which the record
// states end by end, and the tiles' ref rows state for every step of R
#[test]
fn a_record_states_how_many_times_the_reference_passes_each_end() {
    let gfa = fs::read_to_string(fixture("walks-repeat.gfa")).unwrap()
        + "W\tX\t1\tx\t0\t72\t>1>2>3>2>3>4>2>3>4\n";
    let path = std::env::temp_dir().join(format!("walks-passes-{}.gfa", std::process::id()));
    fs::write(&path, gfa).unwrap();
    let built = build(path.to_str().unwrap(), &["--refs", "R", "--stay", "0"]);
    fs::remove_file(&path).unwrap();
    assert_eq!(
        departures(built.file("R")),
        tsv(&["R#0#chr 18 45 departure X#1#x 45 0 0 45 + 1 18 + 2 ."])
    );
}

// R passes 2 once on chr and once on chrU, so twice: X's jump back from 2's
// end to 1's start leaves a node R passes twice, though chr holds it once
#[test]
fn a_pass_count_counts_every_sequence_of_the_reference() {
    let gfa = "S\t1\tACGTACGTAC\nS\t2\tACGTACGTAC\nS\t3\tACGTACGTAC\nS\t4\tACGTACGTAC\n\
               W\tR\t0\tchr\t0\t30\t>1>2>3\nW\tR\t0\tchrU\t0\t20\t>2>4\n\
               W\tX\t1\tx\t0\t30\t>1>2>1\n";
    let path = std::env::temp_dir().join(format!("walks-two-seqs-{}.gfa", std::process::id()));
    fs::write(&path, gfa).unwrap();
    let built = build(path.to_str().unwrap(), &["--refs", "R", "--stay", "0"]);
    fs::remove_file(&path).unwrap();
    assert!(built.file("R").contains("\trevisited:i:1\t"));
    assert_eq!(
        departures(built.file("R")),
        tsv(&["R#0#chr 0 20 departure X#1#x 20 0 0 20 + 2 0 + 1 ."])
    );
}

// R walks 1 2 3 4 3 5 on chr, passing 3 at 12 and 24, and 8 9 8 on chrU. B
// leaves 5 for a 3 and G leaves 4 for chrU's 8; R passes both nodes twice but
// neither in the piece's tile, so each stretch stays in the piece as route
// interior. C's stretch also visits 2, K's chrU's 9 and N's 4, which R passes
// once, so each starts pieces of its own. With R walking 1 2 3 4 6 7 3 5, F's
// stretch visits 6 and 7, and does the same. A node longer than a tile lies in
// the tile it starts in, whose extent runs past the tile's end to the node's.
#[test]
fn a_stay_refuses_a_stretch_over_a_node_the_reference_passes_once() {
    let nodes = "S\t1\tAAAAAA\nS\t2\tCCCCCC\nS\t3\tGGGGGG\nS\t4\tTTTTTT\nS\t6\tAAAAAA\n\
                 S\t7\tCCCCCC\nS\t8\tAAAAAA\nS\t9\tCCCCCC\n";
    let cases = [
        (
            "S\t5\tACGTACGTACGTACG\n\
             W\tR\t0\tchr\t0\t45\t>1>2>3>4>3>5\nW\tR\t0\tchrU\t0\t18\t>8>9>8\n\
             W\tB\t1\tb\t0\t36\t>5>3>5\nW\tC\t1\tc\t0\t42\t>5>2>3>5\n\
             W\tG\t1\tg\t0\t18\t>4>8>4\nW\tK\t1\tk\t0\t24\t>4>9>8>4\n\
             W\tN\t1\tn\t0\t24\t>1>4>3>2\n",
            vec![
                ("B#1#b", 1),
                ("C#1#c", 4),
                ("G#1#g", 1),
                ("K#1#k", 4),
                ("N#1#n", 4),
            ],
            "#unit R#0#chr 30 45 tile 30",
        ),
        (
            "S\t5\tACGTACGTACGTACG\n\
             W\tR\t0\tchr\t0\t57\t>1>2>3>4>6>7>3>5\nW\tF\t1\tf\t0\t30\t>4>6>7>3>4\n",
            vec![("F#1#f", 4)],
            "#unit R#0#chr 42 57 tile 40",
        ),
        (
            "S\t5\tACGTACGTACGTACGTACGT\n\
             W\tR\t0\tchr\t0\t62\t>1>2>3>4>6>7>3>5\nW\tF\t1\tf\t0\t30\t>4>6>7>3>4\n",
            vec![("F#1#f", 4)],
            "#unit R#0#chr 42 62 tile 40",
        ),
    ];
    for (k, (rest, expected, long)) in cases.into_iter().enumerate() {
        let path = std::env::temp_dir().join(format!("walks-reach-{}-{k}.gfa", std::process::id()));
        fs::write(&path, format!("H\tVN:Z:1.1\n{nodes}{rest}")).unwrap();
        let built = build(path.to_str().unwrap(), &["--refs", "R", "--stay", "30"]);
        fs::remove_file(&path).unwrap();
        assert!(built.output.status.success(), "case {k}");
        assert!(!built.file("R").contains("#long"));
        let tile = unit(built.file("R"), "tile", long.rsplit(' ').next().unwrap());
        assert_eq!(
            tile.lines().next(),
            Some(long.replace(' ', "\t").as_str()),
            "case {k}"
        );
        for (name, pieces) in expected {
            let rows = built
                .file("R")
                .lines()
                .filter(|line| line.split('\t').skip(3).take(2).eq(["walk", name]))
                .count();
            assert_eq!(rows, pieces, "case {k}: {name}");
        }
    }
}

// D spends 12 bp on tile 10-20's reference nodes before coming back to tile
// 0-10, but R and Q pass each node once, so no stay keeps that stretch in D's
// piece: every file of a reference that passes no node twice holds the rows
// --stay 0 writes.
#[test]
fn a_stay_leaves_a_reference_that_passes_each_node_once_alone() {
    for (gfa, refs) in [
        ("walks-two-refs.gfa", "GRCh38,Q"),
        ("walks-records.gfa", "R"),
    ] {
        for tile in ["7", "10", "1000"] {
            let none = build(gfa, &["--refs", refs, "--tile", tile, "--stay", "0"]);
            let stay = build(gfa, &["--refs", refs, "--tile", tile, "--stay", "1000"]);
            for sample in refs.split(',') {
                let rows = |built: &Built| {
                    let text = built.file(sample);
                    joined(
                        text[text.find("\n#reference").unwrap()..]
                            .lines()
                            .filter(|l| !l.starts_with("#entry")),
                    )
                };
                assert!(!rows(&none).is_empty());
                assert_eq!(rows(&none), rows(&stay), "{gfa} {sample} {tile}");
            }
        }
    }
}

#[test]
fn a_haplotype_with_two_contigs_is_listed_once() {
    let gfa = fs::read_to_string(fixture("walks-two-refs.gfa")).unwrap();
    let path = std::env::temp_dir().join(format!("walks-contigs-{}.gfa", std::process::id()));
    fs::write(
        &path,
        gfa + "W\tH\t1\th2\t0\t12\t>1>2\nW\tH\t2\th\t0\t6\t>1\n",
    )
    .unwrap();
    let built = build(path.to_str().unwrap(), &[]);
    fs::remove_file(&path).unwrap();
    assert!(built.output.status.success());
    assert!(header(built.file("GRCh38")).ends_with(&tsv(&[
        "#haplotype D#1",
        "#haplotype H#1",
        "#haplotype H#2",
        "#haplotype I#1",
        "#haplotype Q#0",
    ])));
}

#[test]
fn a_path_off_every_reference_is_counted_and_left_out() {
    let built = build("walks-two-refs.gfa", &[]);
    let stderr = String::from_utf8_lossy(&built.output.stderr);
    assert!(
        stderr.contains("1 paths visit no GRCh38 node and are left out"),
        "{stderr}"
    );
    assert!(!built.walks.contains("U#1#u"));
}

#[test]
fn p_lines_give_the_rows_w_lines_do() {
    let w = build("walks-two-refs.gfa", &[]);
    let p = build("walks-two-refs-p.gfa", &[]);
    assert!(p.output.status.success());
    assert_eq!(p.walks, w.walks);
}

#[test]
fn the_order_of_the_paths_changes_no_row() {
    for (name, refs) in [
        ("walks-two-refs.gfa", "GRCh38,Q"),
        ("walks-records.gfa", "R"),
    ] {
        let gfa = fs::read_to_string(fixture(name)).unwrap();
        let (paths, rest): (Vec<&str>, Vec<&str>) = gfa.lines().partition(|l| l.starts_with('W'));
        let reversed: Vec<&str> = paths.iter().rev().copied().collect();
        let rotated: Vec<&str> = paths[2..].iter().chain(&paths[..2]).copied().collect();
        let orders = [
            [rest.clone(), reversed.clone()].concat(),
            [rest.clone(), rotated].concat(),
            // paths before the S lines take a second read
            [reversed, rest].concat(),
        ];
        let plain = build(name, &["--refs", refs]);
        assert!(plain.output.status.success(), "{name}");
        for (i, lines) in orders.iter().enumerate() {
            let path = std::env::temp_dir().join(format!("{name}-{}-{i}", std::process::id()));
            fs::write(&path, lines.join("\n") + "\n").unwrap();
            let shuffled = build(path.to_str().unwrap(), &["--refs", refs]);
            fs::remove_file(&path).unwrap();
            assert!(shuffled.output.status.success(), "{name} order {i}");
            assert_eq!(shuffled.walks, plain.walks, "{name} order {i}");
        }
    }
}

#[test]
fn gzipped_input_gives_the_same_rows() {
    let gfa = fs::read(fixture("walks-two-refs.gfa")).unwrap();
    let path = std::env::temp_dir().join(format!("walks-two-refs-{}.gfa.gz", std::process::id()));
    let mut encoder = GzEncoder::new(fs::File::create(&path).unwrap(), Compression::default());
    encoder.write_all(&gfa).unwrap();
    encoder.finish().unwrap();
    let gzipped = build(path.to_str().unwrap(), &[]);
    fs::remove_file(&path).unwrap();
    let plain = build("walks-two-refs.gfa", &[]);
    assert!(gzipped.output.status.success());
    assert_eq!(gzipped.walks, plain.walks);
}

// A ref row's bases are its nodes' sequences in step order, as the S lines
// give them; a nodes row's are its nodes' in id order.
#[test]
fn sequences_adds_the_bases_of_ref_and_nodes_rows() {
    let built = build("walks-two-refs.gfa", &["--sequences"]);
    let r = built.file("GRCh38");
    assert!(r.contains(&tsv(&[
        "GRCh38#0#chr 0 12 ref GRCh38#0#chr 0 0 0 2 2,2 6,6 . SQ:Z:AAAAAACCCCCC"
    ])));
    assert!(r.contains(&tsv(&["GRCh38#0#chr 12 24 nodes 7 3 SQ:Z:GGG"])));
}

// R's chrE is a line with no steps: no tile, departure or detail unit, but
// the directory lists it, and its table holds only its `#unit` line
// A W line with no steps is skipped: chrE, the reference's only line of it,
// names no sequence, and H's three empty lines, two starting at 5 and one
// where H's line with steps starts, are neither refused nor seen. The table
// of chr states its 18 bp, though H's jump from 1 to 4 lies in the departure
// block 10-20
#[test]
fn a_w_line_with_no_steps_is_skipped() {
    let lines = [
        "S 1 AAAAAA",
        "S 2 AAAAAA",
        "S 4 AAAAAA",
        "W R 0 chr 0 18 >1>2>4",
        "W H 1 h 0 12 >1>4",
    ];
    let empty = [
        "W R 0 chrE 0 0 ",
        "W H 1 h 5 5 ",
        "W H 1 h 5 5 ",
        "W H 1 h 0 0 ",
    ];
    let without = build_text("steps", &lines, &["--refs", "R"]);
    let with = build_text(
        "empty",
        &[&lines[..], &empty[..]].concat(),
        &["--refs", "R"],
    );
    assert!(with.output.status.success());
    assert_eq!(with.files, without.files);
    let counted = |built: &Built| -> Vec<String> {
        String::from_utf8_lossy(&built.output.stderr)
            .lines()
            .map(|l| l.split_once("] ").map_or(l, |(_, rest)| rest).to_string())
            .filter(|l| l.contains("paths") && !l.contains("->"))
            .collect()
    };
    assert_eq!(counted(&with), counted(&without));
    let tables = unit(with.file("R"), "table", ".");
    let without_offsets = tables.lines().map(|l| {
        if l.starts_with("#entry") {
            l.rsplitn(3, '\t').last().unwrap()
        } else {
            l
        }
    });
    assert_eq!(
        joined(without_offsets),
        tsv(&[
            "#unit R#0#chr 0 18 table .",
            "#entry R#0#chr 0 12 tile 0",
            "#entry R#0#chr 0 10 departures .",
            "#entry R#0#chr 12 18 tile 10",
            "#entry R#0#chr 10 20 departures .",
        ])
    );
    let refused = build_text(
        "ends",
        &[&lines[..], &["W H 1 h 5 6 "][..]].concat(),
        &["--refs", "R"],
    );
    assert!(
        String::from_utf8_lossy(&refused.output.stderr)
            .contains("path H#1#h ends at 6, but its steps from 5 end at 5")
    );
}

// walks-two-refs.gfa plus X#1#x, which steps on 6, a node of Q and not of
// GRCh38: it is in Q's file and its header, and not in GRCh38's
#[test]
fn a_line_on_one_references_nodes_is_in_that_references_file_alone() {
    let gfa = fs::read_to_string(fixture("walks-two-refs.gfa")).unwrap() + "W\tX\t1\tx\t0\t6\t>6\n";
    let path = std::env::temp_dir().join(format!("walks-one-ref-{}.gfa", std::process::id()));
    fs::write(&path, &gfa).unwrap();
    let built = build(path.to_str().unwrap(), &[]);
    fs::remove_file(&path).unwrap();
    assert!(built.output.status.success());
    assert!(header(built.file("Q")).contains("#haplotype\tX#1\n"));
    assert_eq!(
        rows_of(built.file("Q"), "Q#0#chr", "walk", "X#1#x"),
        tsv(&["Q#0#chr 6 12 walk X#1#x 0 0 0 1 12 ."])
    );
    assert!(!built.file("GRCh38").contains("X#1"));
    assert_rebuilds(&gfa, &built, &["GRCh38", "Q"]);
}

// Built with no option but --refs, a file's header states the defaults
#[test]
fn the_defaults_are_65536_311_1000000_and_3000000() {
    let dir = std::env::temp_dir().join(format!("walks-defaults-{}", std::process::id()));
    fs::create_dir_all(&dir).unwrap();
    let output = Command::new(env!("CARGO_BIN_EXE_gfa-to-tabix"))
        .arg(fixture("walks-two-refs.gfa"))
        .arg("-o")
        .arg(dir.join("out"))
        .args(["--walks", "--refs", "GRCh38"])
        .output()
        .unwrap();
    let directory = fs::read_to_string(dir.join("out.GRCh38.walks.gz.idx")).unwrap();
    fs::remove_dir_all(&dir).unwrap();
    assert!(output.status.success());
    assert!(
        directory.starts_with(
            "#walks\tformat:i:7\ttile:i:65536\trevisited:i:0\tstay:i:311\tabridge:i:1000000\tabridgebytes:i:3000000\tbytes:i:"
        ),
        "{directory}"
    );
}

// Each --walks option takes at most 2^40. A tile of 2^55 bp made the
// pyramid's 512-tile block wrap to 0 bp, so the cover never advanced and
// filled memory; a step budget of 2^62 wrapped to 0 when counted in
// quarter steps, so every path was over it and abridged. Run in a 512 MB
// address space, so the old loop dies instead of filling the machine
#[test]
fn each_walks_option_takes_at_most_2_to_the_40() {
    for (option, over) in [
        ("--tile", "36028797018963968"),
        ("--abridge-steps", "4611686018427387904"),
        ("--stay", "1099511627777"),
        ("--abridge-bytes", "1099511627777"),
    ] {
        let dir = std::env::temp_dir().join(format!("walks-bound-{}", std::process::id()));
        fs::create_dir_all(&dir).unwrap();
        let output = Command::new("sh")
            .arg("-c")
            .arg("ulimit -v 524288 && exec \"$0\" \"$@\"")
            .arg(env!("CARGO_BIN_EXE_gfa-to-tabix"))
            .arg(fixture("walks-records.gfa"))
            .args(["--walks", "--refs", "R", option, over, "-o"])
            .arg(dir.join("out"))
            .output()
            .unwrap();
        fs::remove_dir_all(&dir).unwrap();
        let stderr = String::from_utf8_lossy(&output.stderr);
        assert_eq!(output.status.code(), Some(2), "{option}: {stderr}");
        assert!(stderr.contains("1099511627776"), "{option}: {stderr}");
    }
    for option in ["--tile", "--stay", "--abridge-steps", "--abridge-bytes"] {
        let built = build(
            "walks-records.gfa",
            &["--refs", "R", option, "1099511627776"],
        );
        assert!(built.output.status.success(), "{option}");
    }
}

// R walks 1 2 3 2 4 on chr, 10 bp nodes, passing 2 at 10 and 30, and 8 5 8
// on chrU, passing 8 at 0 and 20. H's 10 bp of its own after 1 predict 2 at
// 20, as near the pass at 10 as the one at 30: the lower offset wins, so H's
// route lands on R's first 2 and spans 0-20. G's 8 after 1 is predicted at
// 10 on chr, which has no 8, so it takes the node's first pass, chrU's at 0,
// and G's 2 after it is predicted on chrU, which has no 2, so it takes chr's
// first 2 at 10: the record leaves 1 at 10 and rejoins 2 at 10, a node R
// passes twice, with 8's 10 bp as its own, in no tile of chr
#[test]
fn a_step_takes_the_lower_pass_on_a_tie_and_the_first_pass_where_its_sequence_has_none() {
    let built = build_text(
        "tie",
        &[
            "S 1 AAAAAAAAAA",
            "S 2 AAAAAAAAAA",
            "S 3 AAAAAAAAAA",
            "S 4 AAAAAAAAAA",
            "S 5 AAAAAAAAAA",
            "S 6 CCCCCCCCCC",
            "S 8 GGGGGGGGGG",
            "W R 0 chr 0 50 >1>2>3>2>4",
            "W R 0 chrU 0 30 >8>5>8",
            "W H 1 h 0 30 >1>6>2",
            "W G 1 g 0 30 >1>8>2",
        ],
        &["--refs", "R", "--tile", "1000", "--stay", "0"],
    );
    assert!(built.output.status.success());
    let r = built.file("R");
    assert_eq!(
        rows_of(r, "R#0#chr", "route", "2") + &rows_of(r, "R#0#chr", "walk", "H#1#h"),
        tsv(&[
            "R#0#chr 0 50 route 2 10 -8",
            "R#0#chr 0 20 walk H#1#h 0 0 0 3 2 0",
        ])
    );
    assert_eq!(
        rows_of(r, "R#0#chrU", "walk", "G#1#g") + &rows_of(r, "R#0#chr", "walk", "G#1#g"),
        tsv(&[
            "R#0#chrU 0 10 walk G#1#g 0 10 1 1 16 .",
            "R#0#chr 0 10 walk G#1#g 0 0 0 1 2 .",
            "R#0#chr 10 20 walk G#1#g 0 20 2 1 4 .",
        ])
    );
    assert_eq!(
        departures(r),
        tsv(&["R#0#chr 0 20 departure G#1#g 10 10 0 10 + 1 10 + 2 ."])
    );
}

#[test]
fn sequences_refuses_a_segment_with_no_bases() {
    let built = build_text(
        "no-bases",
        &["S 1 * LN:i:6", "W R 0 chr 0 6 >1"],
        &["--refs", "R", "--sequences"],
    );
    assert_eq!(built.output.status.code(), Some(1));
    assert!(
        String::from_utf8_lossy(&built.output.stderr)
            .contains("segment 1 has no bases, so --sequences can't write them")
    );
    assert!(built.walks.is_empty());
}

#[test]
fn a_node_id_of_2_to_the_31_is_refused() {
    let built = build_text(
        "big-id",
        &["S 2147483648 AAAAAA", "W R 0 chr 0 6 >2147483648"],
        &["--refs", "R"],
    );
    assert_eq!(built.output.status.code(), Some(1));
    assert!(
        String::from_utf8_lossy(&built.output.stderr)
            .contains("--walks needs integer node ids below 2^31")
    );
    assert!(built.walks.is_empty());
}

// Memory follows the number of segments, not the largest id: a graph of
// three segments, one of them 2147483647, builds in a 512 MB address space,
// where arrays by id would need 66 GB. The ids come out as the GFA gives
// them, in a walk file the same as for ids 1, 2 and 3 but for the tokens
#[test]
fn a_node_id_near_2_to_the_31_costs_no_more_memory_than_a_small_one() {
    let dir = std::env::temp_dir().join(format!("walks-bigid-{}", std::process::id()));
    fs::create_dir_all(&dir).unwrap();
    let gfa = dir.join("bigid.gfa");
    fs::write(
        &gfa,
        tsv(&[
            "S 1 AAAA",
            "S 2147483647 CC",
            "S 3 GGG",
            "W R 0 chr 0 9 >1<2147483647>3",
            "W H 1 h 0 9 >1>2147483647>3",
        ]),
    )
    .unwrap();
    let output = Command::new("sh")
        .arg("-c")
        .arg("ulimit -v 524288 && exec \"$0\" \"$@\"")
        .arg(env!("CARGO_BIN_EXE_gfa-to-tabix"))
        .arg(&gfa)
        .args(["--walks", "--refs", "R", "--tile", "4", "-o"])
        .arg(dir.join("out"))
        .output()
        .unwrap();
    let walks = fs::read(dir.join("out.R.walks.gz")).map(|data| gunzip(&data));
    fs::remove_dir_all(&dir).unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let walks = walks.unwrap();
    assert_eq!(
        rows_of(&walks, "R#0#chr", "ref", "R#0#chr") + &rows_of(&walks, "R#0#chr", "walk", "H#1#h"),
        tsv(&[
            "R#0#chr 0 4 ref R#0#chr 0 0 0 1 2 4 .",
            "R#0#chr 4 9 ref R#0#chr 0 4 1 2 4294967295,-4294967288 2,3 .",
            "R#0#chr 0 4 walk H#1#h 0 0 0 1 2 .",
            "R#0#chr 4 9 walk H#1#h 0 4 1 2 4294967294 1",
        ])
    );
}

// A `#` in a W line's sample or haplotype would split its PanSN name
// differently from its columns
#[test]
fn a_hash_in_a_w_lines_sample_or_haplotype_is_refused() {
    for line in ["W H#x 1 h 0 6 >1", "W H 1#2 h 0 6 >1"] {
        let built = build_text(
            "hash-sample",
            &["S 1 AAAAAA", "W R 0 chr 0 6 >1", line],
            &["--refs", "R"],
        );
        assert_eq!(built.output.status.code(), Some(1), "{line}");
        assert!(
            String::from_utf8_lossy(&built.output.stderr).contains("holds a #"),
            "{line}"
        );
    }
}

// A path whose name starts with `#` would read as a header or `#unit` line
#[test]
fn a_path_name_starting_with_a_hash_is_refused() {
    let built = build_text(
        "hash",
        &["S 1 AAAAAA", "W R 0 chr 0 6 >1", "P #H 1+ *"],
        &["--refs", "R"],
    );
    assert_eq!(built.output.status.code(), Some(1));
    assert!(
        String::from_utf8_lossy(&built.output.stderr).contains("path #H starts with #"),
        "{}",
        String::from_utf8_lossy(&built.output.stderr)
    );
    assert!(built.walks.is_empty());
}

// The writer's sort ends a name at its first NUL byte, so one inside a name
// read every later field from the wrong place and panicked
#[test]
fn a_nul_byte_in_a_path_name_is_refused() {
    for line in ["W H\0X 1 c 0 6 >1", "P H\0X 1+ *"] {
        let built = build_text(
            "nul",
            &["S 1 AAAAAA", "W R 0 chr 0 6 >1", line],
            &["--refs", "R"],
        );
        let stderr = String::from_utf8_lossy(&built.output.stderr);
        assert_eq!(built.output.status.code(), Some(1), "{stderr}");
        assert!(stderr.contains("holds a NUL byte"), "{stderr}");
        assert!(built.walks.is_empty());
    }
}

// A directory in the data file's place fails the rename that puts the data
// file there, and the build leaves no file under a temporary name
#[test]
fn a_failed_write_leaves_no_temporary_file() {
    let dir = std::env::temp_dir().join(format!("walks-blocked-{}", std::process::id()));
    fs::create_dir_all(dir.join("out.GRCh38.walks.gz").join("x")).unwrap();
    let output = Command::new(env!("CARGO_BIN_EXE_gfa-to-tabix"))
        .arg(fixture("walks-two-refs.gfa"))
        .arg("-o")
        .arg(dir.join("out"))
        .args(["--walks", "--refs", "GRCh38"])
        .output()
        .unwrap();
    let left: Vec<String> = fs::read_dir(&dir)
        .unwrap()
        .flatten()
        .map(|e| e.file_name().into_string().unwrap())
        .collect();
    fs::remove_dir_all(&dir).unwrap();
    assert_eq!(output.status.code(), Some(1));
    assert_eq!(left, ["out.GRCh38.walks.gz"]);
}

#[test]
fn walks_reads_a_file_not_stdin() {
    let built = build("-", &[]);
    assert_eq!(built.output.status.code(), Some(1));
    assert!(String::from_utf8_lossy(&built.output.stderr).contains("needs a file"));
}

#[test]
fn an_unknown_reference_lists_the_samples() {
    let built = build("walks-two-refs.gfa", &["--refs", "GRCh38,X"]);
    assert_eq!(built.output.status.code(), Some(1));
    assert!(
        String::from_utf8_lossy(&built.output.stderr)
            .contains("--refs X matches no path's sample; have: GRCh38, Q, H, I, D, U")
    );
    assert!(built.walks.is_empty());
}

#[test]
fn cap_and_settle_are_gone() {
    for flag in ["--cap", "--settle"] {
        let built = build("walks-two-refs.gfa", &[flag, "5"]);
        assert_eq!(built.output.status.code(), Some(2), "{flag}");
        assert!(
            String::from_utf8_lossy(&built.output.stderr).contains("unexpected argument"),
            "{flag}"
        );
    }
}

// Format 7's word for the unit a reader fetches whole is tile; chunk was
// format 6's
#[test]
fn help_says_tile_not_chunk() {
    let output = Command::new(env!("CARGO_BIN_EXE_gfa-to-tabix"))
        .arg("--help")
        .output()
        .unwrap();
    let help = String::from_utf8_lossy(&output.stdout).to_lowercase();
    assert!(help.contains("--stay") && help.contains("tile"), "{help}");
    assert!(!help.contains("chunk"), "{help}");
}

// walks-records.gfa: R#0#chr is 1 2 3 4, 6 bp each, so tile 0-10 holds 1 and
// 2 and tile 10-20 holds 3 and 4. H#1#h has three W lines: 1 2 over 0-12, 5 6
// over 20-26, which visits no R node and has no rows, and 2 3 4 over 40-58,
// which starts in tile 0-10 and ends in 10-20. G#1#g has 1 2 over 0-12 and 4
// over 30-36. Each contig's departure from one W line to the next is recorded
// once: H's jumps back from 2's end at 12 to 2's start at 6, over 28 bp of its
// own, 2 steps on 5 and 6 and the 22 bp no line covers; G's jumps forward from
// 12 to 4's start at 18 over the 18 bp between its lines. The walk rows say
// nothing of the lines beside them.
#[test]
fn a_contig_departs_once_from_each_w_line_to_the_next_with_a_step_on_r() {
    let built = build("walks-records.gfa", &["--refs", "R"]);
    assert!(built.output.status.success());
    let walks = built.file("R");
    assert!(header(walks).starts_with("#walks\tformat:i:7\t"));
    assert_eq!(
        rows_of(walks, "R#0#chr", "walk", "H#1#h"),
        tsv(&[
            "R#0#chr 0 12 walk H#1#h 0 0 0 2 2 .",
            "R#0#chr 6 12 walk H#1#h 40 40 0 1 4 .",
            "R#0#chr 12 24 walk H#1#h 40 46 1 2 6 .",
        ])
    );
    assert_eq!(
        rows_of(walks, "R#0#chr", "walk", "G#1#g"),
        tsv(&[
            "R#0#chr 0 12 walk G#1#g 0 0 0 2 2 .",
            "R#0#chr 18 24 walk G#1#g 30 30 0 1 8 .",
        ])
    );
    assert_eq!(
        departures(walks),
        tsv(&[
            "R#0#chr 6 12 departure H#1#h 12 28 22 12 + 1 6 + 1 .",
            "R#0#chr 6 24 departure G#1#g 12 18 18 12 + 1 18 + 1 .",
        ])
    );
}

// A GFA of `lines`, written with tabs for spaces, built with `args`
fn build_text(name: &str, lines: &[&str], args: &[&str]) -> Built {
    let path = std::env::temp_dir().join(format!("walks-{name}-{}.gfa", std::process::id()));
    fs::write(&path, tsv(lines)).unwrap();
    let built = build(path.to_str().unwrap(), args);
    fs::remove_file(&path).unwrap();
    built
}

// walks-records.gfa with `lines` added at its end, or at its start with
// `first`, where they reach nodes before their S lines.
fn build_lines(name: &str, lines: &[&str], first: bool) -> Built {
    let gfa = fs::read_to_string(fixture("walks-records.gfa")).unwrap();
    let text = if first {
        tsv(lines) + &gfa
    } else {
        gfa + &tsv(lines)
    };
    let path = std::env::temp_dir().join(format!("walks-{name}-{}.gfa", std::process::id()));
    fs::write(&path, text).unwrap();
    let built = build(path.to_str().unwrap(), &["--refs", "R"]);
    fs::remove_file(&path).unwrap();
    built
}

// The first pass ends with a line per reference; the refusals come before it.
fn refused_in_first_pass(built: &Built) -> String {
    assert_eq!(built.output.status.code(), Some(1));
    assert!(built.walks.is_empty());
    let stderr = String::from_utf8_lossy(&built.output.stderr).into_owned();
    assert!(!stderr.contains("reference R:"), "{stderr}");
    stderr
}

#[test]
fn records_of_a_contig_that_overlap_or_share_a_start_are_refused() {
    for (name, line, error) in [
        (
            "overlap",
            "W G 1 g 10 22 >2>3",
            "path G#1#g: the line covering 0-12 overlaps the one covering 10-22",
        ),
        (
            "same-start",
            "W G 1 g 30 33 >5",
            "path G#1#g has two lines starting at 30",
        ),
    ] {
        for first in [false, true] {
            let stderr = refused_in_first_pass(&build_lines(name, &[line], first));
            assert!(stderr.contains(error), "{name}: {stderr}");
        }
    }
}

#[test]
fn a_w_line_whose_end_disagrees_with_its_steps_is_refused() {
    for (first, number) in [(false, 18), (true, 1)] {
        let stderr = refused_in_first_pass(&build_lines("end", &["W F 1 f 0 13 >1>2"], first));
        assert!(
            stderr.contains(&format!(
                "line {number}: path F#1#f ends at 13, but its steps from 0 end at 12"
            )),
            "{stderr}"
        );
    }
}

// The tool drops a segment of 0 bp as it reads the GFA: its steps leave every
// W and P line, a line left with no steps is skipped, and a reference
// sequence left with no bases has no units. So `lines` give the same files as
// `stripped`, the same graph with its 0 bp segments removed by hand.
fn assert_same_without_0_bp(name: &str, lines: &[&str], stripped: &[&str], args: &[&str]) {
    let with = build_text(&format!("{name}-0bp"), lines, args);
    let without = build_text(name, stripped, args);
    assert!(
        without.output.status.success(),
        "{}",
        String::from_utf8_lossy(&without.output.stderr)
    );
    assert!(
        with.output.status.success(),
        "{}",
        String::from_utf8_lossy(&with.output.stderr)
    );
    assert_eq!(with.files, without.files);
}

// Every step between H's first and third steps is 0 bp, so its two
// departures from 1 to 2 there had the same text, and the build aborted
#[test]
fn steps_of_0_bp_with_the_same_departure_text_twice_build() {
    assert_same_without_0_bp(
        "dup",
        &[
            "S 1 * LN:i:0",
            "S 2 * LN:i:0",
            "S 5 AAAAAAAAAAAAAAAAAAAA",
            "W R 0 chr 0 20 >1>5>2",
            "W H 1 c 0 0 >1>2>1>2",
        ],
        &[
            "S 5 AAAAAAAAAAAAAAAAAAAA",
            "W R 0 chr 0 20 >5",
            "W H 1 c 0 0 ",
        ],
        &["--refs", "R"],
    );
}

// R passed 2, of 0 bp, at 4 on both strands: H's `<2` took the `<2` pass in
// its departure records and the `>2` pass in its walk row
#[test]
fn a_node_of_0_bp_passed_twice_at_one_offset_leaves_the_lines() {
    assert_same_without_0_bp(
        "z2",
        &[
            "S 1 AAAA",
            "S 2 * LN:i:0",
            "S 3 CCCC",
            "S 4 GGGG",
            "S 5 TTT",
            "W R 0 chr1 0 12 >1>2<2>3>4",
            "W H 1 chr1 0 11 >4<5<2<1",
        ],
        &[
            "S 1 AAAA",
            "S 3 CCCC",
            "S 4 GGGG",
            "S 5 TTT",
            "W R 0 chr1 0 12 >1>3>4",
            "W H 1 chr1 0 11 >4<5<1",
        ],
        &["--refs", "R", "--tile", "4", "--stay", "0"],
    );
}

// R's line at 20 held only 2, of 0 bp: the file stated no hole 10-20, and
// H's step from 1 to 2 got a record
#[test]
fn a_reference_line_of_0_bp_after_the_last_is_no_line() {
    assert_same_without_0_bp(
        "hole-trailing",
        &[
            "S 1 AAAAAAAAAA",
            "S 2 * LN:i:0",
            "W R 0 chr 0 10 >1",
            "W R 0 chr 20 20 >2",
            "W H 1 h 0 10 >1>2",
        ],
        &[
            "S 1 AAAAAAAAAA",
            "W R 0 chr 0 10 >1",
            "W R 0 chr 20 20 ",
            "W H 1 h 0 10 >1",
        ],
        &["--refs", "R", "--tile", "4"],
    );
}

// R's line at 15 held only 2, of 0 bp, inside the hole 10-20: H's steps
// from 1 to 3 got two records, 10 to 15 and 15 to 20, across the hole
#[test]
fn a_reference_line_of_0_bp_inside_a_hole_is_no_line() {
    assert_same_without_0_bp(
        "hole-inside",
        &[
            "S 1 AAAAAAAAAA",
            "S 2 * LN:i:0",
            "S 3 CCCCC",
            "W R 0 chr 0 10 >1",
            "W R 0 chr 15 15 >2",
            "W R 0 chr 20 25 >3",
            "W H 1 h 0 15 >1>2>3",
        ],
        &[
            "S 1 AAAAAAAAAA",
            "S 3 CCCCC",
            "W R 0 chr 0 10 >1",
            "W R 0 chr 15 15 ",
            "W R 0 chr 20 25 >3",
            "W H 1 h 0 15 >1>3",
        ],
        &["--refs", "R", "--tile", "4"],
    );
}

// Tile 5 held 2, of 0 bp, at 5 and 3 at 7-9: its extent was 5-9
#[test]
fn a_reference_step_of_0_bp_widens_no_tile() {
    assert_same_without_0_bp(
        "zmix",
        &[
            "S 1 * LN:i:5",
            "S 2 * LN:i:0",
            "S 3 * LN:i:2",
            "S 4 * LN:i:5",
            "S 5 * LN:i:3",
            "W R 0 chr 0 5 >1>2",
            "W R 0 chr 7 9 >3",
            "W R 0 chr 12 17 >4",
            "W H 1 h 0 6 >5>2>5",
            "W H 2 h 0 15 >1>2>5>3>4",
        ],
        &[
            "S 1 * LN:i:5",
            "S 3 * LN:i:2",
            "S 4 * LN:i:5",
            "S 5 * LN:i:3",
            "W R 0 chr 0 5 >1",
            "W R 0 chr 7 9 >3",
            "W R 0 chr 12 17 >4",
            "W H 1 h 0 6 >5>5",
            "W H 2 h 0 15 >1>5>3>4",
        ],
        &["--refs", "R", "--tile", "5", "--stay", "0"],
    );
}

// Tile 5 held only 2 and 3, of 0 bp, at 5 and 7: its extent was 5-7
#[test]
fn reference_steps_of_0_bp_alone_make_no_tile() {
    assert_same_without_0_bp(
        "zgap",
        &[
            "S 1 * LN:i:5",
            "S 2 * LN:i:0",
            "S 3 * LN:i:0",
            "S 4 * LN:i:5",
            "S 5 * LN:i:3",
            "W R 0 chr 0 5 >1>2",
            "W R 0 chr 7 7 >3",
            "W R 0 chr 12 17 >4",
            "W H 1 h 0 13 >1>2>5>3>4",
            "W H 2 h 0 6 >5>3>5",
        ],
        &[
            "S 1 * LN:i:5",
            "S 4 * LN:i:5",
            "S 5 * LN:i:3",
            "W R 0 chr 0 5 >1",
            "W R 0 chr 7 7 ",
            "W R 0 chr 12 17 >4",
            "W H 1 h 0 13 >1>5>4",
            "W H 2 h 0 6 >5>5",
        ],
        &["--refs", "R", "--tile", "5", "--stay", "0"],
    );
}

// A line holding only 2, of 0 bp, inside another line of its contig was
// refused as an overlap
#[test]
fn a_line_of_0_bp_inside_another_is_no_overlap() {
    let segments = ["S 1 * LN:i:5", "S 2 * LN:i:0", "S 3 * LN:i:4"];
    for (name, lines, stripped) in [
        (
            "ov2",
            ["W R 0 chr 0 9 >1>3", "W H 1 h 0 9 >1>3", "W H 1 h 5 5 >2"],
            ["W R 0 chr 0 9 >1>3", "W H 1 h 0 9 >1>3", "W H 1 h 5 5 "],
        ),
        (
            "ov3",
            ["W R 0 chr 0 9 >1>3", "W H 1 h 0 9 >1>3", "W H 1 h 3 3 >2"],
            ["W R 0 chr 0 9 >1>3", "W H 1 h 0 9 >1>3", "W H 1 h 3 3 "],
        ),
        (
            "ov5",
            ["W R 0 chr 0 9 >1>3", "W R 0 chr 5 5 >2", "W H 1 h 0 9 >1>3"],
            ["W R 0 chr 0 9 >1>3", "W R 0 chr 5 5 ", "W H 1 h 0 9 >1>3"],
        ),
    ] {
        assert_same_without_0_bp(
            name,
            &[&segments[..], &lines[..]].concat(),
            &[&[segments[0], segments[2]][..], &stripped[..]].concat(),
            &["--refs", "R", "--tile", "5", "--stay", "0"],
        );
    }
}

// R's chr0 holds only 1 and 2, of 0 bp: it has no units and no table, and
// H's steps on them leave its line. Tile 10 of chr held only 91 and 92, of
// 0 bp, at chr's end, so its extent was the base before, 9-10, and J's step
// from 91 to chr3 and back to 92 had a record there
#[test]
fn a_sequence_of_0_bp_has_no_units_and_steps_of_0_bp_make_no_tile() {
    assert_same_without_0_bp(
        "zeroseq",
        &[
            "S 1 * LN:i:0",
            "S 2 * LN:i:0",
            "S 3 AAAAAA",
            "S 4 AAAAAAAAAA",
            "S 91 * LN:i:0",
            "S 92 * LN:i:0",
            "S 93 GGGGG",
            "W R 0 chr0 0 0 >1>2",
            "W R 0 chr2 0 6 >3",
            "W R 0 chr 0 10 >4>91>92",
            "W R 0 chr3 0 5 >93",
            "W H 1 h 0 6 >1>3>2",
            "W I 1 i 0 10 >4<92",
            "W J 1 j 0 15 >4>91>93<92",
            "W K 1 k 0 5 <92>93",
        ],
        &[
            "S 3 AAAAAA",
            "S 4 AAAAAAAAAA",
            "S 93 GGGGG",
            "W R 0 chr0 0 0 ",
            "W R 0 chr2 0 6 >3",
            "W R 0 chr 0 10 >4",
            "W R 0 chr3 0 5 >93",
            "W H 1 h 0 6 >3",
            "W I 1 i 0 10 >4",
            "W J 1 j 0 15 >4>93",
            "W K 1 k 0 5 >93",
        ],
        &["--refs", "R", "--stay", "0"],
    );
}

// H's two lines meet at 12, the first ending with 5, of 0 bp: the steps on
// 2 and 3 either side are adjacent, and no route shows 5
#[test]
fn a_step_on_a_node_of_0_bp_between_two_lines_is_no_departure() {
    assert_same_without_0_bp(
        "zero",
        &[
            "S 1 AAAAAA",
            "S 2 AAAAAA",
            "S 3 AAAAAA",
            "S 4 AAAAAA",
            "S 5 * LN:i:0",
            "W R 0 chr 0 24 >1>2>3>4",
            "W H 1 h 0 12 >1>2>5",
            "W H 1 h 12 24 >3>4",
        ],
        &[
            "S 1 AAAAAA",
            "S 2 AAAAAA",
            "S 3 AAAAAA",
            "S 4 AAAAAA",
            "W R 0 chr 0 24 >1>2>3>4",
            "W H 1 h 0 12 >1>2",
            "W H 1 h 12 24 >3>4",
        ],
        &["--refs", "R"],
    );
}
