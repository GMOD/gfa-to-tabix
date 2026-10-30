// An allele inventory read out of the segment and link rows `gfa-to-tabix`
// writes, with no GFA: one row per allele the graph holds, anchored on the
// reference.
//
// A link from a backbone (rank 0) node forward to a later one is a deletion.
// Each link between a backbone node and a rank > 0 one starts a walk off the
// backbone, whichever of the L line's two equivalent directions the file
// states. The walk stops at the first node with a link back onto the backbone
// of the sequence it left, and each such link is an allele. Successors go in
// segment order and rows are keyed on the route in a canonical direction, so
// neither the L lines' order nor their direction changes the output.

use std::collections::{HashMap, HashSet};
use std::fs::File;
use std::io::{BufRead, BufReader};

use flate2::read::MultiGzDecoder;

use crate::bed::{self, Line};

const HEADER: &str = "#chrom\tstart\tend\tname\tscore\tstrand\tthickStart\tthickEnd\titemRgb\tclass\tdelta\taltLen\trefLen\tCIGAR\tdiscoveryRank\tfirstSeenIn\tnested\tsegments\n";

struct Segment {
    id: String,
    chrom: String,
    start: u64,
    end: u64,
    rank: i64,
}

// (segment index, traversed forward)
type State = (u32, bool);

fn fields(
    lines: impl Iterator<Item = Result<String, String>>,
) -> impl Iterator<Item = Result<Vec<String>, String>> {
    lines
        .filter(|line| !matches!(line, Ok(l) if l.starts_with('#') || l.is_empty()))
        .map(|line| line.map(|l| l.split('\t').map(str::to_string).collect()))
}

fn read_lines(path: &str) -> Result<impl Iterator<Item = Result<String, String>>, String> {
    let file = File::open(path).map_err(|e| format!("{path}: {e}"))?;
    let path = path.to_string();
    Ok(BufReader::with_capacity(1 << 20, MultiGzDecoder::new(file))
        .lines()
        .map(move |line| line.map_err(|e| format!("{path}: {e}"))))
}

fn number<T: std::str::FromStr>(path: &str, field: &str, what: &str) -> Result<T, String> {
    field
        .parse()
        .map_err(|_| format!("{path}: {what} {field:?} is not a number"))
}

// Segment rows are `chrom start end id rank`. The anchored layout files a node
// under the interval its bubble hangs from and orders its links differently,
// which changes which route a walk takes at a branch, so only the contig layout
// is read.
fn read_segments(
    path: &str,
    lines: impl Iterator<Item = Result<String, String>>,
) -> Result<(Vec<Segment>, HashMap<String, u32>), String> {
    let mut segments: Vec<Segment> = Vec::new();
    let mut index: HashMap<String, u32> = HashMap::new();
    for row in fields(lines) {
        let f = row?;
        if f.len() < 5 {
            return Err(format!(
                "{path}: a segment row has {} columns, not 5",
                f.len()
            ));
        }
        if f.len() >= 8 && !f[5].is_empty() && f[6].parse::<u64>().is_ok() {
            return Err(format!(
                "{path} is in the anchored layout: index the graph again with --layout contig"
            ));
        }
        let segment = Segment {
            id: f[3].clone(),
            chrom: f[0].clone(),
            start: number(path, &f[1], "start")?,
            end: number(path, &f[2], "end")?,
            rank: number(path, &f[4], "rank")?,
        };
        if !index.contains_key(&segment.id) {
            index.insert(segment.id.clone(), segments.len() as u32);
            segments.push(segment);
        }
    }
    Ok((segments, index))
}

pub(crate) fn commify(n: i64) -> String {
    let digits = n.unsigned_abs().to_string();
    let mut out = String::new();
    for (i, c) in digits.chars().enumerate() {
        if i > 0 && (digits.len() - i).is_multiple_of(3) {
            out.push(',');
        }
        out.push(c);
    }
    if n < 0 { format!("-{out}") } else { out }
}

fn cigar(alt: u64, reference: u64) -> String {
    use std::cmp::Ordering::*;
    match alt.cmp(&reference) {
        Greater if reference > 0 => format!("{reference}M{}I", alt - reference),
        Greater => format!("{alt}I"),
        Less if alt > 0 => format!("{alt}M{}D", reference - alt),
        Less => format!("{reference}D"),
        Equal => format!("{reference}M"),
    }
}

// `GRCh38#0#chr1` -> `chr1`, so the rows sit on the reference assembly's own
// refNames.
fn ref_name(name: &str) -> &str {
    let mut parts = name.splitn(3, '#');
    match (parts.next(), parts.next(), parts.next()) {
        (Some(a), Some(b), Some(rest)) if !a.is_empty() && !b.is_empty() => rest,
        _ => name,
    }
}

fn sample(name: &str) -> &str {
    let mut parts = name.split('#');
    match (parts.next(), parts.next(), parts.next(), parts.next()) {
        (Some(sample), Some(_), Some(_), None) => sample,
        _ => name,
    }
}

struct Entry {
    state: State,
    // the backbone state the walk leaves, and where it leaves it
    side: State,
    chrom: String,
    at: u64,
}

#[derive(PartialEq, Eq, PartialOrd, Ord)]
struct Deletion {
    chrom: String,
    start: u64,
    end: u64,
}

struct Links {
    successors: HashMap<State, Vec<State>>,
    entries: Vec<Entry>,
    deletions: Vec<Deletion>,
}

// (backbone side left, route, backbone side reached)
type Key = (State, Vec<State>, State);

fn read_links(
    path: &str,
    lines: impl Iterator<Item = Result<String, String>>,
    segments: &[Segment],
    index: &HashMap<String, u32>,
) -> Result<Links, String> {
    let mut links = Links {
        successors: HashMap::new(),
        entries: Vec::new(),
        deletions: Vec::new(),
    };
    let mut seen: HashSet<(String, String)> = HashSet::new();
    for row in fields(lines) {
        let f = row?;
        if f.len() < 13 {
            return Err(format!(
                "{path}: a link row has {} columns, not 13",
                f.len()
            ));
        }
        let split = |oriented: &str| -> Option<State> {
            let (id, strand) = oriented.split_at(oriented.len().checked_sub(1)?);
            Some((*index.get(id)?, strand == "+"))
        };
        let (Some(source), Some(target)) = (split(&f[3]), split(&f[4])) else {
            continue;
        };
        // every L-line is written under both of its endpoints
        if !seen.insert((f[3].clone(), f[4].clone())) {
            continue;
        }
        links.successors.entry(source).or_default().push(target);
        links
            .successors
            .entry((target.0, !target.1))
            .or_default()
            .push((source.0, !source.1));
        let coordinate = |field: &String| number::<u64>(path, field, "coordinate");
        let source_at = if source.1 {
            coordinate(&f[7])?
        } else {
            coordinate(&f[6])?
        };
        let target_at = if target.1 {
            coordinate(&f[10])?
        } else {
            coordinate(&f[11])?
        };
        let (a, b) = (&segments[source.0 as usize], &segments[target.0 as usize]);
        if a.rank == 0 && b.rank == 0 {
            // a mixed-orientation backbone pair is an inversion breakpoint,
            // and a link back to an earlier node a duplication
            let (from, to) = if source.1 {
                (source_at, target_at)
            } else {
                (target_at, source_at)
            };
            if f[5] == f[9] && source.1 == target.1 && from < to {
                links.deletions.push(Deletion {
                    chrom: f[5].clone(),
                    start: from,
                    end: to,
                });
            }
        } else if a.rank == 0 && b.rank > 0 {
            links.entries.push(Entry {
                state: target,
                side: source,
                chrom: f[5].clone(),
                at: source_at,
            });
        } else if a.rank > 0 && b.rank == 0 {
            links.entries.push(Entry {
                state: (source.0, !source.1),
                side: (target.0, !target.1),
                chrom: f[9].clone(),
                at: target_at,
            });
        }
    }
    // segment order, not file order, picks the route at a branch, and a GFA
    // may state a link in both directions
    for next in links.successors.values_mut() {
        next.sort_unstable();
        next.dedup();
    }
    links
        .entries
        .sort_by(|a, b| (&a.chrom, a.at, a.side, a.state).cmp(&(&b.chrom, b.at, b.side, b.state)));
    links
        .entries
        .dedup_by(|a, b| (a.side, a.state) == (b.side, b.state));
    links.deletions.sort();
    links.deletions.dedup();
    Ok(links)
}

struct Allele<'a> {
    chrom: &'a str,
    start: u64,
    end: u64,
    label: String,
    strand: &'a str,
    class: &'a str,
    delta: i64,
    alt_len: u64,
    ref_len: u64,
    rank: String,
    first_seen_in: &'a str,
    nested: bool,
    segments: &'a str,
}

fn row(a: Allele) -> Line {
    let rgb = match a.class {
        "ins" => "192,0,192",
        "sub" => "0,154,138",
        _ => "128,128,128",
    };
    let chrom = ref_name(a.chrom).to_string();
    let (start, end) = (a.start, a.end);
    let line = format!(
        "{chrom}\t{start}\t{end}\t{}\t0\t{}\t{start}\t{end}\t{rgb}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n",
        a.label,
        a.strand,
        a.class,
        a.delta,
        a.alt_len,
        a.ref_len,
        cigar(a.alt_len, a.ref_len),
        a.rank,
        a.first_seen_in,
        u8::from(a.nested),
        a.segments,
    );
    Line {
        chrom: chrom.into_bytes(),
        start,
        end,
        text: line.into_bytes(),
    }
}

// Each allele's key and row; None when the walk never reaches the backbone of
// the sequence it left. A walk's next step depends only on its state and that
// sequence, so `dead` holds the states from which a walk on it reaches none.
fn walk<'a>(
    links: &Links,
    segments: &[Segment],
    entry: &'a Entry,
    dead: &mut HashSet<(State, &'a str)>,
) -> Option<Vec<(Key, Line)>> {
    let mut visited: HashSet<State> = HashSet::new();
    let mut states = Vec::new();
    let mut current = entry.state;
    let mut nested = false;
    let mut exits = Vec::new();
    while visited.insert(current) {
        if dead.contains(&(current, entry.chrom.as_str())) {
            break;
        }
        states.push(current);
        let segment = &segments[current.0 as usize];
        let next = links
            .successors
            .get(&current)
            .map_or(&[][..], Vec::as_slice);
        nested |= next.len() > 1;
        // at a branch, stay on the contig the allele came in on, so a nested
        // bubble leaves the walk on the same haplotype
        let mut pick: Option<State> = None;
        for &state in next {
            let next_segment = &segments[state.0 as usize];
            if next_segment.rank == 0 {
                if next_segment.chrom == entry.chrom {
                    exits.push(state);
                }
            } else if pick.is_none_or(|p| {
                segments[p.0 as usize].chrom != segment.chrom && next_segment.chrom == segment.chrom
            }) {
                pick = Some(state);
            }
        }
        if !exits.is_empty() {
            break;
        }
        let Some(next) = pick else { break };
        current = next;
    }
    if exits.is_empty() {
        dead.extend(states.iter().map(|&s| (s, entry.chrom.as_str())));
        return None;
    }
    let alt_len: u64 = states
        .iter()
        .map(|s| segments[s.0 as usize].end - segments[s.0 as usize].start)
        .sum();
    let reversed: Vec<State> = states.iter().rev().map(|&(id, fwd)| (id, !fwd)).collect();
    let forward = entry.side.1;
    let mut rows = Vec::new();
    for exit in exits {
        let to = &segments[exit.0 as usize];
        let exit_at = if exit.1 { to.start } else { to.end };
        // an exit behind the entry repeats the reference between them, a
        // duplication the inventory leaves out
        if exit.1 == forward
            && (if forward {
                exit_at < entry.at
            } else {
                exit_at > entry.at
            })
        {
            continue;
        }
        let key: Key = (entry.side, states.clone(), exit);
        let back: Key = (
            (exit.0, !exit.1),
            reversed.clone(),
            (entry.side.0, !entry.side.1),
        );
        let key = key.min(back);
        let mut path = String::new();
        let (mut min_rank, mut donor) = (None::<i64>, "");
        for &(id, fwd) in &key.1 {
            let segment = &segments[id as usize];
            path.push(if fwd { '>' } else { '<' });
            path.push_str(&segment.id);
            if min_rank.is_none_or(|m| segment.rank < m) {
                min_rank = Some(segment.rank);
                donor = &segment.chrom;
            }
        }
        let (start, end) = (entry.at.min(exit_at), entry.at.max(exit_at));
        let ref_len = end - start;
        let delta = alt_len as i64 - ref_len as i64;
        let (class, label) = match delta {
            1.. => ("ins", format!("+{}", commify(delta))),
            0 => ("sub", format!("{} sub", commify(alt_len as i64))),
            _ => ("del", commify(delta)),
        };
        let line = row(Allele {
            chrom: &entry.chrom,
            start,
            end: if end > start { end } else { start + 1 },
            label,
            strand: if key.1[0].1 { "+" } else { "-" },
            class,
            delta,
            alt_len,
            ref_len,
            rank: min_rank.unwrap_or(0).to_string(),
            first_seen_in: sample(donor),
            nested,
            segments: &path,
        });
        rows.push((key, line));
    }
    Some(rows)
}

// Format 2's rows split into format 1's node and link rows, each without its
// kind column
pub fn split_graph(
    path: &str,
    lines: impl Iterator<Item = Result<String, String>>,
) -> Result<(Vec<String>, Vec<String>), String> {
    let (mut nodes, mut links) = (Vec::new(), Vec::new());
    for line in lines {
        let line = line?;
        if line.starts_with('#') {
            if line.contains("\tlayout:Z:anchored") {
                return Err(format!(
                    "{path} is in the anchored layout: index the graph again with --layout contig"
                ));
            }
            continue;
        }
        let mut columns: Vec<&str> = line.split('\t').collect();
        if columns.len() < 4 {
            return Err(format!("{path}: a row has {} columns", columns.len()));
        }
        let kind = columns.remove(3);
        match kind {
            "N" => nodes.push(columns.join("\t")),
            "L" => links.push(columns.join("\t")),
            _ => return Err(format!("{path}: row kind {kind:?} is neither N nor L")),
        }
    }
    Ok((nodes, links))
}

pub fn run(prefix: &str) -> Result<(), String> {
    let graph = format!("{prefix}.graph.bed.gz");
    if std::fs::metadata(&graph).is_ok_and(|m| m.len() > 0) {
        let (nodes, links) = split_graph(&graph, read_lines(&graph)?)?;
        return from_rows(
            &graph,
            nodes.into_iter(),
            links.into_iter(),
            &format!("{prefix}.alleles.bed.gz"),
        );
    }
    let segs = format!("{prefix}.segs.bed.gz");
    let links_path = format!("{prefix}.links.bed.gz");
    for path in [&segs, &links_path] {
        if std::fs::metadata(path).map_or(true, |m| m.len() == 0) {
            return Err(format!(
                "missing {prefix}.graph.bed.gz and {path}: index the graph first"
            ));
        }
    }
    let (segments, index) = read_segments(&segs, read_lines(&segs)?)?;
    let links = read_links(&links_path, read_lines(&links_path)?, &segments, &index)?;
    write(&segments, &links, &format!("{prefix}.alleles.bed.gz"))
}

pub fn from_rows(
    name: &str,
    segs: impl Iterator<Item = String>,
    links: impl Iterator<Item = String>,
    out: &str,
) -> Result<(), String> {
    let (segments, index) = read_segments(name, segs.map(Ok))?;
    let links = read_links(name, links.map(Ok), &segments, &index)?;
    write(&segments, &links, out)
}

fn write(segments: &[Segment], links: &Links, out: &str) -> Result<(), String> {
    let mut rows: Vec<Line> = Vec::new();
    for d in &links.deletions {
        let ref_len = d.end - d.start;
        rows.push(row(Allele {
            chrom: &d.chrom,
            start: d.start,
            end: d.end,
            label: commify(-(ref_len as i64)),
            strand: ".",
            class: "del",
            delta: -(ref_len as i64),
            alt_len: 0,
            ref_len,
            rank: ".".into(),
            first_seen_in: ".",
            nested: false,
            segments: ".",
        }));
    }
    let mut written: HashSet<Key> = HashSet::new();
    let mut dead = HashSet::new();
    let mut dangling = 0;
    for entry in &links.entries {
        let Some(found) = walk(links, segments, entry, &mut dead) else {
            dangling += 1;
            continue;
        };
        for (key, line) in found {
            if written.insert(key) {
                rows.push(line);
            }
        }
    }
    if dangling > 0 {
        eprintln!("note: {dangling} walk(s) reached no backbone link and were dropped");
    }
    let index = bed::write_lines(out, HEADER.as_bytes(), &mut rows)?;

    fn column(line: &Line, n: usize) -> Option<&[u8]> {
        line.text.split(|&b| b == b'\t').nth(n)
    }
    let count = |class: &str| {
        rows.iter()
            .filter(|r| column(r, 9) == Some(class.as_bytes()))
            .count()
    };
    let nested = rows.iter().filter(|r| column(r, 16) == Some(b"1")).count();
    eprintln!(
        "{} alleles -> {out} (+ .{index}): {} ins, {} del, {} sub; {nested} nested",
        rows.len(),
        count("ins"),
        count("del"),
        count("sub"),
    );
    Ok(())
}
