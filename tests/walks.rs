// --walks over walks-two-refs.gfa, every row checked by hand. Five nodes of
// 6 bp make the reference R#0#chr: 1 2 3 4 5 at 0, 6, 12, 18 and 24. Q#0#chr
// takes 6 in place of 2. With --chunk 10, nodes 1 and 2 lie in chunk 0-10, 3
// and 4 in 10-20, and 5 in 20-30; each chunk's rows are filed under its first
// base. H#1#h inserts 7 (3 bp) between 3 and 4,
// I#1#i inverts 2-3, D#1#d repeats 1-4, and U#1#u visits only 8 and 9.
// walks-two-refs-p.gfa says the same in P lines.
//
// A handle is 2 * id + 1 when reversed. In a ref row and a route row each
// handle is written as 2 * (id - previous id) + reverse; a walk row names its
// routes by 2 * (route id - previous route id) + flip, and a handle on R or a
// route's exit takes `@k` where it lands on occurrence k of its node in R.

use std::collections::{BTreeMap, HashMap};
use std::fs;
use std::io::{Read, Write};
use std::process::{Command, Output};
use std::sync::atomic::{AtomicUsize, Ordering};

use flate2::Compression;
use flate2::read::MultiGzDecoder;
use flate2::write::GzEncoder;

struct Built {
    output: Output,
    // by sample, from out.<sample>.walks.bed.gz
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
        .args(["--walks", "--refs", "R,Q", "--chunk", "10"])
        .args(args)
        .output()
        .unwrap();
    let mut files = BTreeMap::new();
    for entry in fs::read_dir(&dir).unwrap().flatten() {
        let name = entry.file_name().into_string().unwrap();
        if name.ends_with(".bed.gz.tbi") {
            continue;
        }
        let sample = name
            .strip_prefix("out.")
            .and_then(|n| n.strip_suffix(".walks.bed.gz"))
            .unwrap_or_else(|| panic!("left behind: {name}"));
        assert!(
            dir.join(format!("{name}.tbi")).exists(),
            "{name} has no index"
        );
        let mut text = String::new();
        MultiGzDecoder::new(fs::File::open(entry.path()).unwrap())
            .read_to_string(&mut text)
            .unwrap();
        files.insert(sample.to_string(), text);
    }
    let built = Built {
        walks: files.values().map(String::as_str).collect(),
        files,
        output,
    };
    fs::remove_dir_all(&dir).unwrap();
    built
}

fn tsv(rows: &[&str]) -> String {
    rows.iter().map(|r| r.replace(' ', "\t") + "\n").collect()
}

fn under(text: &str, anchor: &str) -> String {
    text.lines()
        .filter(|line| line.starts_with(&format!("{anchor}\t")))
        .map(|line| line.to_string() + "\n")
        .collect()
}

fn rows_of(text: &str, anchor: &str, kind: &str, name: &str) -> String {
    text.lines()
        .filter(|line| {
            let cols: Vec<&str> = line.split('\t').collect();
            cols.len() > 4 && cols[0] == anchor && cols[3] == kind && cols[4] == name
        })
        .map(|line| line.to_string() + "\n")
        .collect()
}

fn header(text: &str) -> String {
    text.lines()
        .take_while(|line| line.starts_with('#'))
        .map(|line| line.to_string() + "\n")
        .collect()
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

struct RefPath {
    handles: Vec<u32>,
}

impl RefPath {
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

fn decode_walk(path: &RefPath, routes: &[Route], cols: &[&str]) -> Vec<u32> {
    let (start, start_copy) = with_copy(cols[9]);
    let start: u32 = start.parse().unwrap();
    let mut end_parts = cols[10].split(':');
    let end = (i64::from(start) + end_parts.next().unwrap().parse::<i64>().unwrap()) as u32;
    let tail: Option<usize> = end_parts.next().map(|n| n.parse().unwrap());
    let counted = tail.is_some();
    let mut choices = Vec::new();
    let mut previous = 0i64;
    if cols[11] != "." {
        for tok in cols[11].split(',') {
            let (tok, exit_copy) = with_copy(tok);
            let mut parts = tok.split(':');
            let d: i64 = parts.next().unwrap().parse().unwrap();
            let flip = d & 1;
            previous += (d - flip) / 2;
            let route = &routes[previous as usize];
            let count: Option<usize> = parts.next().map(|n| n.parse().unwrap());
            choices.push((
                if flip == 1 {
                    flipped(route)
                } else {
                    route.clone()
                },
                count,
                exit_copy,
            ));
        }
    }
    let mut steps = Vec::new();
    let mut rest = &choices[..];
    if let Some(((None, interior, _), _, _)) = choices.first() {
        steps.extend_from_slice(interior);
        rest = &choices[1..];
    }
    let mut h = start;
    let mut i = path.copy(h, start_copy);
    steps.push(h);
    let follow =
        |steps: &mut Vec<u32>, h: &mut u32, i: &mut usize, target: u32, count: Option<usize>| {
            let mut taken = 0;
            while if counted {
                taken < count.unwrap()
            } else {
                *h != target
            } {
                (*i, *h) = path.step(*i, *h);
                steps.push(*h);
                taken += 1;
            }
        };
    for ((entry, interior, exit), count, exit_copy) in rest {
        let entry = entry.expect("an open route after the first choice");
        follow(&mut steps, &mut h, &mut i, entry, *count);
        assert_eq!(h, entry);
        steps.extend_from_slice(interior);
        let Some(exit) = exit else {
            return steps;
        };
        h = *exit;
        i = match exit_copy {
            Some(k) => path.copy(h, Some(*k)),
            None => path.nearest(h, i),
        };
        steps.push(h);
    }
    follow(&mut steps, &mut h, &mut i, end, tail);
    assert_eq!(h, end);
    steps
}

// Every path's steps rebuilt from a walk file, joining its pieces in order.
fn decode_file(text: &str) -> BTreeMap<String, Vec<u32>> {
    let mut chunks: BTreeMap<(String, u64), Vec<Vec<&str>>> = BTreeMap::new();
    // by sequence, chunk and record
    let mut details: BTreeMap<(String, u64, u64), Vec<Vec<&str>>> = BTreeMap::new();
    for line in text.lines().filter(|l| !l.starts_with('#')) {
        let cols: Vec<&str> = line.split('\t').collect();
        match cols[0].split_once('~') {
            Some((_, "departure")) => {}
            Some((seq, cs)) => details
                .entry((
                    seq.to_string(),
                    cs.parse().unwrap(),
                    cols[1].parse::<u64>().unwrap() / 16384,
                ))
                .or_default()
                .push(cols),
            None => chunks
                .entry((cols[0].to_string(), cols[1].parse().unwrap()))
                .or_default()
                .push(cols),
        }
    }
    let mut pieces: BTreeMap<String, BTreeMap<u64, Vec<u32>>> = BTreeMap::new();
    let mut decode_rows = |path: &RefPath, rows: &[Vec<&str>]| {
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
                "ref" => deltas(cols[9], &mut 0),
                "walk" => decode_walk(path, &routes, cols),
                _ => continue,
            };
            assert_eq!(steps.len(), cols[8].parse::<usize>().unwrap(), "{cols:?}");
            decoded.push((
                format!("{}@{}", cols[4], cols[5]),
                cols[7].parse::<i64>().unwrap(),
                steps.len(),
            ));
            pieces
                .entry(format!("{}@{}", cols[4], cols[5]))
                .or_default()
                .insert(cols[7].parse().unwrap(), steps);
        }
        decoded
    };
    for ((seq, cs), rows) in &chunks {
        let mut refs: Vec<&Vec<&str>> = rows.iter().filter(|c| c[3] == "ref").collect();
        refs.sort_by_key(|c| c[6].parse::<u64>().unwrap());
        let path = RefPath {
            handles: refs.iter().flat_map(|c| deltas(c[9], &mut 0)).collect(),
        };
        decode_rows(&path, rows);
        for cols in rows.iter().filter(|c| c[3] == "abridged") {
            let record = &details[&(seq.clone(), *cs, cols[12].parse().unwrap())];
            assert!(record.iter().all(|c| c[3] != "ref" && c[3] != "abridged"));
            let decoded = decode_rows(&path, record);
            let name = format!("{}@{}", cols[4], cols[5]);
            assert!(decoded.iter().all(|(n, _, _)| *n == name), "{cols:?}");
            let mut previous = 0;
            let listed: Vec<i64> = cols[7]
                .split(',')
                .map(|d| {
                    previous += d.parse::<i64>().unwrap();
                    previous
                })
                .collect();
            let mut held: Vec<i64> = decoded.iter().map(|(_, piece, _)| *piece).collect();
            held.sort_unstable();
            assert_eq!(held, listed, "{cols:?}");
            let steps: usize = decoded.iter().map(|(_, _, n)| n).sum();
            assert_eq!(steps.to_string(), cols[8], "{cols:?}");
        }
    }
    pieces
        .into_iter()
        .map(|(path, pieces)| {
            assert!(pieces.keys().copied().eq(0..pieces.len() as u64), "{path}");
            (path, pieces.into_values().flatten().collect())
        })
        .collect()
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

fn assert_rebuilds(gfa: &str, built: &Built, samples: &[&str]) {
    let paths = gfa_paths(gfa);
    for sample in samples {
        let decoded = decode_file(built.file(sample));
        assert!(!decoded.is_empty(), "{sample}");
        for (path, steps) in &decoded {
            assert_eq!(steps, &paths[path], "{sample}: {path}");
        }
    }
}

#[test]
fn every_path_rebuilds_from_its_rows() {
    for (gfa, refs, chunk) in [
        ("walks-two-refs.gfa", "R,Q", "10"),
        ("walks-two-refs.gfa", "R,Q", "7"),
        ("walks-two-refs.gfa", "R,Q", "1000"),
        ("walks-repeat.gfa", "R", "10"),
        ("walks-repeat.gfa", "R", "1000"),
        ("walks-loop.gfa", "R", "10"),
        ("walks-loop.gfa", "R", "1000"),
        ("walks-records.gfa", "R", "10"),
        ("walks-skip.gfa", "R,Q", "10"),
    ] {
        let built = build(gfa, &["--refs", refs, "--chunk", chunk]);
        assert!(built.output.status.success(), "{gfa} {chunk}");
        let samples: Vec<&str> = refs.split(',').collect();
        assert_rebuilds(&fs::read_to_string(fixture(gfa)).unwrap(), &built, &samples);
    }
}

// Past a byte budget of 1, a chunk moves its paths to detail rows, costliest
// first, until its estimate of the bytes left runs out, which can leave the
// cheapest path in the chunk
#[test]
fn every_path_rebuilds_from_its_detail_rows_when_abridged() {
    for (gfa, refs) in [
        ("walks-two-refs.gfa", "R,Q"),
        ("walks-repeat.gfa", "R"),
        ("walks-loop.gfa", "R"),
        ("walks-records.gfa", "R"),
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

// D#1#d's pieces 0 and 2 lie in chunk 0, with piece 1 in chunk 10, so its
// row there lists both, and names the chunk's second detail record
#[test]
fn an_abridged_row_lists_its_pieces_and_names_its_detail_record() {
    let built = build("walks-two-refs.gfa", &["--abridge-bytes", "1"]);
    let r = built.file("R");
    assert_eq!(
        rows_of(r, "R#0#chr", "abridged", "D#1#d"),
        tsv(&[
            "R#0#chr 0 1 abridged D#1#d 0 0 0,2 4 24 2 4 1",
            "R#0#chr 10 11 abridged D#1#d 0 12 1,2 4 24 6 8 1",
            "R#0#chr 20 21 abridged D#1#d 0 48 4 1 6 10 10 0",
        ])
    );
    assert_eq!(
        under(r, "R#0#chr~0")
            .lines()
            .filter(|l| l.contains("\tD#1#d\t"))
            .map(|l| l.to_string() + "\n")
            .collect::<String>(),
        tsv(&[
            "R#0#chr~0 16384 16385 walk D#1#d 0 0 0 2 2 2 .",
            "R#0#chr~0 16384 16385 walk D#1#d 0 24 2 2 2 2 .",
        ])
    );
}

#[test]
fn each_reference_has_one_file_holding_only_its_rows() {
    let built = build("walks-two-refs.gfa", &[]);
    assert_eq!(built.files.keys().collect::<Vec<_>>(), ["Q", "R"]);
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
// between; its ends' pieces are filed under chunks 10 and 70. B#1#b does the
// same on the reverse strand, leaving at 5's start and rejoining at 2's end,
// both steps against R. Each record is filed over the bases from 2's last to
// 5's first, 19-71, which one Tabix bin of 128 kb holds. Each reference walks
// the other as itself, so it has no departure.
#[test]
fn a_path_that_jumps_over_the_reference_has_a_departure_record_over_the_stretch() {
    let built = build("walks-skip.gfa", &[]);
    for sample in ["R", "Q"] {
        let anchor = format!("{sample}#0#chr~departure");
        assert_eq!(
            under(built.file(sample), &anchor),
            tsv(&[
                &format!("{anchor} 19 71 departure B#1#b 10 0 0 70 - 20 -"),
                &format!("{anchor} 19 71 departure D#1#d 20 0 0 20 + 70 +"),
            ]),
            "{sample}"
        );
    }
}

// walks-two-refs.gfa at --chunk 10. Q carries 6 in place of 2, 6 bp of its
// own between 1's end at 6 and 3's start at 12. I leaves 1 for 3 inverted,
// rejoining at 3's end at 18, then leaves 2 inverted at its start at 6 for 4
// at 18; between its <3 and <2 it follows R backwards, so there is no
// departure. D jumps back from 4's end at 24 to 1's start. H's insertion of 7
// lies inside its piece in chunk 10, where the walk row shows it. With every
// path in one chunk no departure lies between pieces, and there are none.
#[test]
fn a_departure_between_pieces_has_a_record_and_one_inside_a_piece_has_none() {
    let built = build("walks-two-refs.gfa", &[]);
    assert_eq!(
        under(built.file("R"), "R#0#chr~departure"),
        tsv(&[
            "R#0#chr~departure 0 24 departure D#1#d 24 0 0 24 + 0 +",
            "R#0#chr~departure 5 13 departure Q#0#chr 6 6 0 6 + 12 +",
            "R#0#chr~departure 5 18 departure I#1#i 6 0 0 6 + 18 -",
            "R#0#chr~departure 6 19 departure I#1#i 18 0 0 6 - 18 +",
        ])
    );
    let whole = build("walks-two-refs.gfa", &["--chunk", "1000"]);
    assert!(whole.output.status.success());
    assert!(!whole.walks.contains("~departure"));
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
    assert!(!built.walks.contains("~departure"));
    assert_eq!(
        rows_of(built.file("R"), "R#0#chr1", "walk", "H#1#h")
            + &rows_of(built.file("R"), "R#0#chr2", "route", ".")
            + &rows_of(built.file("R"), "R#0#chr2", "walk", "H#1#h"),
        tsv(&[
            "R#0#chr1 0 1 walk H#1#h 0 0 0 2 2 2 .",
            "R#0#chr2 0 1 route . 11 -1",
            "R#0#chr2 0 1 walk H#1#h 0 12 1 3 6 2 1",
        ])
    );
}

// H's first line ends with node 5, of 0 bp, and its second line starts where
// the first ends. 2's end and 3's start are the same base and the step on 5
// carries no sequence, so the two steps are adjacent and the contig has no
// record there; the first piece's route from 2 onto 5, taken flipped, shows
// the step.
#[test]
fn a_step_on_a_node_of_0_bp_between_two_lines_is_no_departure() {
    let built = build_text(
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
        &["--refs", "R"],
    );
    assert!(built.output.status.success());
    assert!(!built.walks.contains("~departure"));
    assert_eq!(
        rows_of(built.file("R"), "R#0#chr", "route", ".")
            + &rows_of(built.file("R"), "R#0#chr", "walk", "H#1#h"),
        tsv(&[
            "R#0#chr 0 1 route . 11 -5",
            "R#0#chr 0 1 walk H#1#h 0 0 0 3 2 2 1",
            "R#0#chr 10 11 walk H#1#h 12 12 0 2 6 2 .",
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
        under(walks, "R#0#chr~departure"),
        tsv(&["R#0#chr~departure 11 21 departure G#1#g 12 8 0 12 + 20 +"])
    );
}

// R walks 1 2 3 2 3 4 with 10 bp nodes, all in one chunk. H walks 3 4, which
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
        &["--refs", "R", "--chunk", "1000"],
    );
    assert_eq!(
        rows_of(built.file("R"), "R#0#chr", "walk", "H#1#h"),
        tsv(&["R#0#chr 0 1 walk H#1#h 0 0 0 2 6@1 2 ."])
    );
}

// R walks 1 2 3 2 3 4 with 10 bp nodes, all in one chunk. H carries 25 bp of
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
    let built = build_text("exit-copy", &lines, &["--refs", "R", "--chunk", "1000"]);
    assert_eq!(
        rows_of(built.file("R"), "R#0#chr", "route", "2")
            + &rows_of(built.file("R"), "R#0#chr", "walk", "H#1#h"),
        tsv(&[
            "R#0#chr 0 1 route 2 8 -4",
            "R#0#chr 0 1 walk H#1#h 0 0 0 3 2 4 0@1",
        ])
    );
    let abridged = build_text(
        "exit-copy-abridged",
        &lines,
        &["--refs", "R", "--chunk", "1000", "--abridge-bytes", "1"],
    );
    assert_eq!(
        rows_of(abridged.file("R"), "R#0#chr", "abridged", "H#1#h"),
        tsv(&["R#0#chr 0 1 abridged H#1#h 0 0 0 3 45 2 6@1 0"])
    );
    assert_eq!(
        rows_of(abridged.file("R"), "R#0#chr~0", "walk", "H#1#h"),
        tsv(&["R#0#chr~0 0 1 walk H#1#h 0 0 0 3 2 4 0@1"])
    );
}

// R walks 2 then three copies of the 2 bp node 1, then 3; H walks one more 1,
// which placement puts on R's last, at 14, twice. Its handles alone would
// decode without step counts, putting the extra 1 at R's first, so the row
// gives counts: 3 steps along R to the last 1, a route back onto it, then one
// step to 3.
#[test]
fn a_walk_row_gives_step_counts_where_its_copies_would_decode_wrongly() {
    let built = build_text(
        "counts",
        &[
            "S 1 AA",
            "S 2 AAAAAAAAAA",
            "S 3 AAAAAAAAAA",
            "W R 0 chr 0 26 >2>1>1>1>3",
            "W H 1 h 0 28 >2>1>1>1>1>3",
        ],
        &["--refs", "R", "--chunk", "1000"],
    );
    assert_eq!(
        rows_of(built.file("R"), "R#0#chr", "route", "2")
            + &rows_of(built.file("R"), "R#0#chr", "walk", "H#1#h"),
        tsv(&[
            "R#0#chr 0 1 route 2 . 0",
            "R#0#chr 0 1 walk H#1#h 0 0 0 6 4 2:1 0:3",
        ])
    );
}

// U#1#u visits no reference node, so it has no rows and no line. Each walk
// file lists the other reference among its haplotypes, since its walk has
// rows there.
#[test]
fn a_walk_file_names_its_format_reference_and_each_haplotype_with_rows() {
    let built = build("walks-two-refs.gfa", &[]);
    for (sample, other) in [("R", "Q"), ("Q", "R")] {
        assert_eq!(
            header(built.file(sample)),
            tsv(&[
                "#walks format:i:6 chunk:i:10 maxnode:i:6 stay:i:311 abridge:i:1000000 abridgebytes:i:3000000",
                &format!("#reference {sample}"),
                "#haplotype D#1",
                "#haplotype H#1",
                "#haplotype I#1",
                &format!("#haplotype {other}#0"),
            ])
        );
    }
}

// A chunk's ref row lists its reference steps and their lengths, and its
// nodes row the ids and lengths of the nodes its routes visit off R. H's
// insertion of 7 between 3 and 4 is the chunk's one route, and H's walk row
// names it after starting on 3. Q's 6 in place of 2 is a route off R that
// leaves R at 1 and does not return in chunk 0-10; stored the way round whose
// handles sort first, it reads 6 reversed back onto 1 reversed, and Q's walk
// row takes it flipped. With --stay 0, D and I file each return to chunk 0-10
// as a piece of its own.
#[test]
fn a_chunk_holds_its_reference_its_routes_and_a_walk_row_per_piece() {
    let built = build("walks-two-refs.gfa", &["--stay", "0"]);
    let r = built.file("R");
    assert_eq!(
        under(r, "R#0#chr\t0"),
        tsv(&[
            "R#0#chr 0 1 ref R#0#chr 0 0 0 2 2,2 6,6",
            "R#0#chr 0 1 nodes 6 6",
            "R#0#chr 0 1 route . 13 -9",
            "R#0#chr 0 1 walk D#1#d 0 0 0 2 2 2 .",
            "R#0#chr 0 1 walk D#1#d 0 24 2 2 2 2 .",
            "R#0#chr 0 1 walk H#1#h 100 100 0 2 2 2 .",
            "R#0#chr 0 1 walk I#1#i 0 0 0 1 2 0 .",
            "R#0#chr 0 1 walk I#1#i 0 12 2 1 5 0 .",
            "R#0#chr 0 1 walk Q#0#chr 0 0 0 2 2 0 1",
        ])
    );
    assert_eq!(
        rows_of(r, "R#0#chr", "route", "6") + &rows_of(r, "R#0#chr", "walk", "H#1#h"),
        tsv(&[
            "R#0#chr 10 11 route 6 8 -6",
            "R#0#chr 0 1 walk H#1#h 100 100 0 2 2 2 .",
            "R#0#chr 10 11 walk H#1#h 100 112 1 3 6 2 0",
            "R#0#chr 20 21 walk H#1#h 100 127 2 1 10 0 .",
        ])
    );
}

// walks-repeat.gfa: R#0#chr walks 1 2 3 2 3 4, a two-node repeat collapsed
// into one copy. Nodes 1-3 are 6 bp and node 4 is 15 bp, so R reaches them at
// 0, 6, 12, 18, 24 and 30 and ends at 45. H#1#h takes the same steps. Placed by
// first visit, the repeat's second pass would be filed under chunk 0-10 and
// 10-20 again; on R's own path each step takes the chunk of its own offset.
// H, following R, takes each pass of the repeat in turn and is filed as R is.
#[test]
fn a_reference_files_its_own_revisits_at_its_own_offset() {
    let built = build("walks-repeat.gfa", &["--refs", "R"]);
    assert!(built.output.status.success());
    let walks = built.file("R");
    assert!(
        header(walks).starts_with("#walks\tformat:i:6\tchunk:i:10\tmaxnode:i:15\tstay:i:311\t")
    );
    assert_eq!(
        rows_of(walks, "R#0#chr", "ref", "R#0#chr"),
        tsv(&[
            "R#0#chr 0 1 ref R#0#chr 0 0 0 2 2,2 6,6",
            "R#0#chr 10 11 ref R#0#chr 0 12 1 2 6,-2 6,6",
            "R#0#chr 20 21 ref R#0#chr 0 24 2 1 6 6",
            "R#0#chr 30 31 ref R#0#chr 0 30 3 1 8 15",
        ])
    );
    assert_eq!(
        rows_of(walks, "R#0#chr", "walk", "H#1#h"),
        tsv(&[
            "R#0#chr 0 1 walk H#1#h 0 0 0 2 2 2 .",
            "R#0#chr 10 11 walk H#1#h 0 12 1 2 6 -2 .",
            "R#0#chr 20 21 walk H#1#h 0 24 2 1 6 0 .",
            "R#0#chr 30 31 walk H#1#h 0 30 3 1 8 0 .",
        ])
    );
}

// walks-loop.gfa, in one chunk: R walks 1 2 3 2 3 4. A takes the repeat three
// times. Following R from 1 until the first 3 would stop a pass early, so A's
// row gives each stretch along R as a step count after a colon, and the tail
// after the last route likewise. F inserts 5 inside the second copy.
#[test]
fn a_walk_the_default_rule_would_misread_states_its_step_counts() {
    let built = build("walks-loop.gfa", &["--refs", "R", "--chunk", "1000"]);
    assert!(built.output.status.success());
    let walks = built.file("R");
    assert_eq!(
        rows_of(walks, "R#0#chr", "walk", "A#1#a") + &rows_of(walks, "R#0#chr", "walk", "F#1#f"),
        tsv(&[
            "R#0#chr 0 1 walk A#1#a 0 0 0 8 2 6:2 5:4",
            "R#0#chr 0 1 walk F#1#f 0 0 0 7 2 6:1 2:3",
        ])
    );
    assert_eq!(
        rows_of(walks, "R#0#chr", "walk", "B#1#b"),
        tsv(&["R#0#chr 0 1 walk B#1#b 0 0 0 4 2 6 6"])
    );
    let stderr = String::from_utf8_lossy(&built.output.stderr);
    assert!(
        stderr.contains("6 walk rows, 2 with step counts"),
        "{stderr}"
    );
}

#[test]
fn a_walk_back_into_a_chunk_starts_a_new_piece_there() {
    let built = build("walks-two-refs.gfa", &["--stay", "0"]);
    assert_eq!(
        rows_of(&built.walks, "R#0#chr", "walk", "D#1#d"),
        tsv(&[
            "R#0#chr 0 1 walk D#1#d 0 0 0 2 2 2 .",
            "R#0#chr 0 1 walk D#1#d 0 24 2 2 2 2 .",
            "R#0#chr 10 11 walk D#1#d 0 12 1 2 6 2 .",
            "R#0#chr 10 11 walk D#1#d 0 36 3 2 6 2 .",
            "R#0#chr 20 21 walk D#1#d 0 48 4 1 10 0 .",
        ])
    );
}

// K takes walks-repeat.gfa's collapsed repeat three times. Placed nearest, its
// steps fall in chunks 0 0 10 10 20 10 20 30, at 0 6 12 18 24 18 24 30: the 3
// at 24 is a 6 bp stretch in chunk 20-30 between two of chunk 10-20's steps.
// --stay 12 keeps it in K's piece at 10-20 on that chunk's 3, at 12, 12 bp
// from the 24 its previous step predicts, so the piece walks 3 2 3 2. --stay 6
// refuses that, but keeps the next stretch, the 2 at 18 between two steps of
// chunk 20-30, as route interior, since chunk 20-30's R has no 2; the piece
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
            "R#0#chr 0 1 walk K#1#k 0 0 0 2 2 2 .",
            "R#0#chr 10 11 walk K#1#k 0 12 1 4 6 -2 0",
            "R#0#chr 20 21 walk K#1#k 0 36 2 1 6 0 .",
            "R#0#chr 30 31 walk K#1#k 0 42 3 1 8 0 .",
        ])
    );
    assert_eq!(
        rows_of(interior.file("R"), "R#0#chr", "walk", "K#1#k"),
        tsv(&[
            "R#0#chr 0 1 walk K#1#k 0 0 0 2 2 2 .",
            "R#0#chr 10 11 walk K#1#k 0 12 1 2 6 -2 .",
            "R#0#chr 20 21 walk K#1#k 0 24 2 3 6 0 0",
            "R#0#chr 30 31 walk K#1#k 0 42 3 1 8 0 .",
        ])
    );
    for built in [&moved, &interior] {
        assert!(!built.walks.contains("~departure"));
    }
    assert_eq!(
        rows_of(cut.file("R"), "R#0#chr", "walk", "K#1#k")
            .lines()
            .count(),
        6
    );
    assert_eq!(
        under(cut.file("R"), "R#0#chr~departure"),
        tsv(&["R#0#chr~departure 18 30 departure K#1#k 30 0 0 30 + 18 +"])
    );
}

// R walks 1 2 3 4 3 5 on chr, passing 3 at 12 and 24, and 8 9 8 on chrU. B
// leaves 5 for a 3 and G leaves 4 for chrU's 8; R passes both nodes twice but
// neither in the piece's chunk, so each stretch stays in the piece as route
// interior. C's stretch also visits 2, K's chrU's 9 and N's 4, which R passes
// once, so each starts pieces of its own. With R walking 1 2 3 4 6 7 3 5, F's
// stretch visits 6 and 7, and does the same. A node longer than a chunk gets
// its `#long` line either way.
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
            vec!["#long\tR#0#chr\t30\t45"],
        ),
        (
            "S\t5\tACGTACGTACGTACG\n\
             W\tR\t0\tchr\t0\t57\t>1>2>3>4>6>7>3>5\nW\tF\t1\tf\t0\t30\t>4>6>7>3>4\n",
            vec![("F#1#f", 4)],
            vec!["#long\tR#0#chr\t42\t57"],
        ),
        (
            "S\t5\tACGTACGTACGTACGTACGT\n\
             W\tR\t0\tchr\t0\t62\t>1>2>3>4>6>7>3>5\nW\tF\t1\tf\t0\t30\t>4>6>7>3>4\n",
            vec![("F#1#f", 4)],
            vec!["#long\tR#0#chr\t42\t62"],
        ),
    ];
    for (k, (rest, expected, long)) in cases.into_iter().enumerate() {
        let path = std::env::temp_dir().join(format!("walks-reach-{}-{k}.gfa", std::process::id()));
        fs::write(&path, format!("H\tVN:Z:1.1\n{nodes}{rest}")).unwrap();
        let built = build(path.to_str().unwrap(), &["--refs", "R", "--stay", "30"]);
        fs::remove_file(&path).unwrap();
        assert!(built.output.status.success(), "case {k}");
        let header: Vec<&str> = built
            .file("R")
            .lines()
            .filter(|l| l.starts_with("#long"))
            .collect();
        assert_eq!(header, long, "case {k}");
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

// D spends 12 bp on chunk 10-20's reference nodes before coming back to chunk
// 0-10, but R and Q pass each node once, so no stay keeps that stretch in D's
// piece: every file of a reference that passes no node twice holds the rows
// --stay 0 writes.
#[test]
fn a_stay_leaves_a_reference_that_passes_each_node_once_alone() {
    for (gfa, refs) in [("walks-two-refs.gfa", "R,Q"), ("walks-records.gfa", "R")] {
        for chunk in ["7", "10", "1000"] {
            let none = build(gfa, &["--refs", refs, "--chunk", chunk, "--stay", "0"]);
            let stay = build(gfa, &["--refs", refs, "--chunk", chunk, "--stay", "1000"]);
            for sample in refs.split(',') {
                let rows = |built: &Built| {
                    let text = built.file(sample);
                    text[text.find("\n#reference").unwrap()..].to_string()
                };
                assert!(!rows(&none).is_empty());
                assert_eq!(rows(&none), rows(&stay), "{gfa} {sample} {chunk}");
            }
        }
    }
}

// An insertion of 40 bp off both references leaves maxnode at 6, the longest
// reference node, since a window reads back only as far as a reference node
// can start before it.
#[test]
fn maxnode_counts_the_reference_nodes() {
    let gfa = fs::read_to_string(fixture("walks-two-refs.gfa")).unwrap();
    let path = std::env::temp_dir().join(format!("walks-maxnode-{}.gfa", std::process::id()));
    fs::write(
        &path,
        gfa + &format!(
            "S\t10\t{}\nL\t1\t+\t10\t+\t0M\nL\t10\t+\t2\t+\t0M\nW\tJ\t1\tj\t0\t70\t>1>10>2>3>4>5\n",
            "A".repeat(40)
        ),
    )
    .unwrap();
    let built = build(path.to_str().unwrap(), &[]);
    fs::remove_file(&path).unwrap();
    assert!(built.output.status.success());
    assert!(header(built.file("R")).starts_with("#walks\tformat:i:6\tchunk:i:10\tmaxnode:i:6\t"));
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
    assert!(header(built.file("R")).ends_with(&tsv(&[
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
        stderr.contains("1 paths visit no R node and are left out"),
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
    for (name, refs) in [("walks-two-refs.gfa", "R,Q"), ("walks-records.gfa", "R")] {
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
    let r = built.file("R");
    assert!(r.contains(&tsv(&[
        "R#0#chr 0 1 ref R#0#chr 0 0 0 2 2,2 6,6 SQ:Z:AAAAAACCCCCC"
    ])));
    assert!(r.contains(&tsv(&["R#0#chr 10 11 nodes 7 3 SQ:Z:GGG"])));
}

#[test]
fn walks_reads_a_file_not_stdin() {
    let built = build("-", &[]);
    assert_eq!(built.output.status.code(), Some(1));
    assert!(String::from_utf8_lossy(&built.output.stderr).contains("needs a file"));
}

#[test]
fn an_unknown_reference_lists_the_samples() {
    let built = build("walks-two-refs.gfa", &["--refs", "R,X"]);
    assert_eq!(built.output.status.code(), Some(1));
    assert!(
        String::from_utf8_lossy(&built.output.stderr)
            .contains("--refs X matches no path's sample; have: R, Q, H, I, D, U")
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

// walks-records.gfa: R#0#chr is 1 2 3 4, 6 bp each, so chunk 0-10 holds 1 and
// 2 and chunk 10-20 holds 3 and 4. H#1#h has three W lines: 1 2 over 0-12, 5 6
// over 20-26, which visits no R node and has no rows, and 2 3 4 over 40-58,
// which starts in chunk 0-10 and ends in 10-20. G#1#g has 1 2 over 0-12 and 4
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
    assert!(header(walks).starts_with("#walks\tformat:i:6\t"));
    assert_eq!(
        rows_of(walks, "R#0#chr", "walk", "H#1#h"),
        tsv(&[
            "R#0#chr 0 1 walk H#1#h 0 0 0 2 2 2 .",
            "R#0#chr 0 1 walk H#1#h 40 40 0 1 4 0 .",
            "R#0#chr 10 11 walk H#1#h 40 46 1 2 6 2 .",
        ])
    );
    assert_eq!(
        rows_of(walks, "R#0#chr", "walk", "G#1#g"),
        tsv(&[
            "R#0#chr 0 1 walk G#1#g 0 0 0 2 2 2 .",
            "R#0#chr 10 11 walk G#1#g 30 30 0 1 8 0 .",
        ])
    );
    assert_eq!(
        under(walks, "R#0#chr~departure"),
        tsv(&[
            "R#0#chr~departure 6 12 departure H#1#h 12 28 22 12 + 6 +",
            "R#0#chr~departure 11 19 departure G#1#g 12 18 18 12 + 18 +",
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
