// An allele inventory read out of the segment and link rows `gfa-to-tabix`
// writes, with no GFA: one row per allele the graph holds, anchored on the
// reference. Ports jbrowse-components' build_rgfa_alleles.sh.
//
// A link between two backbone (rank 0) nodes that leaves a gap is a deletion.
// A link from a backbone node to a rank > 0 one enters an allele; the walk goes
// on bidirected until it arrives on a backbone node, which is the exit. It
// tests the arrival, not a table of departures, because the file states only
// one of an L-line's two equivalent directions.

use std::collections::HashMap;
use std::fs::File;
use std::io::{BufRead, BufReader};

use flate2::read::MultiGzDecoder;

use crate::bed::Writer;

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

struct Row {
    chrom: String,
    start: u64,
    end: u64,
    line: String,
}

fn read_rows(path: &str) -> Result<impl Iterator<Item = Result<Vec<String>, String>>, String> {
    let file = File::open(path).map_err(|e| format!("{path}: {e}"))?;
    let path = path.to_string();
    Ok(BufReader::with_capacity(1 << 20, MultiGzDecoder::new(file))
        .lines()
        .filter(|line| !matches!(line, Ok(l) if l.starts_with('#') || l.is_empty()))
        .map(move |line| {
            line.map(|l| l.split('\t').map(str::to_string).collect())
                .map_err(|e| format!("{path}: {e}"))
        }))
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
fn read_segments(path: &str) -> Result<(Vec<Segment>, HashMap<String, u32>), String> {
    let mut segments: Vec<Segment> = Vec::new();
    let mut index: HashMap<String, u32> = HashMap::new();
    for row in read_rows(path)? {
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
    chrom: String,
    at: u64,
}

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

fn read_links(
    path: &str,
    segments: &[Segment],
    index: &HashMap<String, u32>,
) -> Result<Links, String> {
    let mut links = Links {
        successors: HashMap::new(),
        entries: Vec::new(),
        deletions: Vec::new(),
    };
    let mut seen: std::collections::HashSet<(String, String)> = std::collections::HashSet::new();
    for row in read_rows(path)? {
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
            let (lo, hi) = (source_at.min(target_at), source_at.max(target_at));
            // a mixed-orientation backbone pair is an inversion breakpoint
            if f[5] == f[9] && source.1 == target.1 && hi > lo {
                links.deletions.push(Deletion {
                    chrom: f[5].clone(),
                    start: lo,
                    end: hi,
                });
            }
        } else if a.rank == 0 && b.rank > 0 {
            links.entries.push(Entry {
                state: target,
                chrom: f[5].clone(),
                at: source_at,
            });
        }
    }
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

fn row(a: Allele) -> Row {
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
    Row {
        chrom,
        start,
        end,
        line,
    }
}

fn walk(links: &Links, segments: &[Segment], entry: &Entry) -> Option<Row> {
    let mut visited: std::collections::HashSet<State> = std::collections::HashSet::new();
    let mut current = entry.state;
    let mut path = String::new();
    let (mut alt_len, mut min_rank, mut donor) = (0u64, None::<i64>, "");
    let (mut nested, mut exit_at) = (false, None::<u64>);
    while visited.insert(current) {
        let segment = &segments[current.0 as usize];
        path.push(if current.1 { '>' } else { '<' });
        path.push_str(&segment.id);
        alt_len += segment.end - segment.start;
        if min_rank.is_none_or(|m| segment.rank < m) {
            min_rank = Some(segment.rank);
            donor = &segment.chrom;
        }
        let mut pick: Option<State> = None;
        let mut out = 0;
        for &next in links
            .successors
            .get(&current)
            .map_or(&[][..], Vec::as_slice)
        {
            out += 1;
            let next_segment = &segments[next.0 as usize];
            // arriving back on the backbone is the exit, whichever of the two
            // equivalent L-line directions the file stated it in
            if next_segment.rank == 0 {
                if exit_at.is_none() || next_segment.chrom == entry.chrom {
                    exit_at = Some(if next.1 {
                        next_segment.start
                    } else {
                        next_segment.end
                    });
                }
                continue;
            }
            // at a branch, stay on the contig the allele came in on, so a
            // nested bubble does not switch the walk onto another haplotype
            let held = pick.map(|p| &segments[p.0 as usize].chrom);
            if pick.is_none()
                || (next_segment.chrom == segment.chrom && held != Some(&segment.chrom))
            {
                pick = Some(next);
            }
        }
        if out > 1 {
            nested = true;
        }
        if exit_at.is_some() {
            break;
        }
        let Some(next) = pick else { break };
        current = next;
    }
    let exit_at = exit_at?;
    let (start, end) = (entry.at.min(exit_at), entry.at.max(exit_at));
    let ref_len = end - start;
    let delta = alt_len as i64 - ref_len as i64;
    let (class, label) = match delta {
        1.. => ("ins", format!("+{}", commify(delta))),
        0 => ("sub", format!("{} sub", commify(alt_len as i64))),
        _ => ("del", commify(delta)),
    };
    Some(row(Allele {
        chrom: &entry.chrom,
        start,
        end: if end > start { end } else { start + 1 },
        label,
        strand: if entry.state.1 { "+" } else { "-" },
        class,
        delta,
        alt_len,
        ref_len,
        rank: min_rank.unwrap_or(0).to_string(),
        first_seen_in: sample(donor),
        nested,
        segments: &path,
    }))
}

pub fn run(prefix: &str) -> Result<(), String> {
    let segs = format!("{prefix}.segs.bed.gz");
    let links_path = format!("{prefix}.links.bed.gz");
    for path in [&segs, &links_path] {
        if std::fs::metadata(path).map_or(true, |m| m.len() == 0) {
            return Err(format!("missing {path}: index the graph first"));
        }
    }
    let (segments, index) = read_segments(&segs)?;
    let links = read_links(&links_path, &segments, &index)?;

    let mut rows: Vec<Row> = Vec::new();
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
    let mut dangling = 0;
    for entry in &links.entries {
        match walk(&links, &segments, entry) {
            Some(r) => rows.push(r),
            None => dangling += 1,
        }
    }
    if dangling > 0 {
        eprintln!("note: {dangling} walk(s) reached no backbone link and were dropped");
    }
    rows.sort_unstable_by(|a, b| {
        (a.chrom.as_bytes(), a.start, a.line.as_bytes()).cmp(&(
            b.chrom.as_bytes(),
            b.start,
            b.line.as_bytes(),
        ))
    });

    let out = format!("{prefix}.alleles.bed.gz");
    let mut writer = Writer::create(&out)?;
    writer.header(HEADER.as_bytes())?;
    for r in &rows {
        writer.push(r.chrom.as_bytes(), r.start, r.end, r.line.as_bytes())?;
    }
    writer.finish()?;

    let count = |class: &str| {
        rows.iter()
            .filter(|r| r.line.split('\t').nth(9) == Some(class))
            .count()
    };
    let nested = rows
        .iter()
        .filter(|r| r.line.split('\t').nth(16) == Some("1"))
        .count();
    eprintln!(
        "{} alleles -> {out} (+ .tbi): {} ins, {} del, {} sub; {nested} nested",
        rows.len(),
        count("ins"),
        count("del"),
        count("sub"),
    );
    Ok(())
}
