use std::collections::HashSet;
use std::io::BufRead;

use crate::intern::Interner;

pub struct Placement {
    pub sequence: u32,
    pub start: u64,
    pub rank: i64,
}

pub struct Link {
    pub source: u32,
    pub source_reversed: bool,
    pub target: u32,
    pub target_reversed: bool,
}

impl Link {
    // The same for an L line and its reverse, `L 1 + 2 +` and `L 2 - 1 -`
    fn key(&self) -> (u32, bool, u32, bool) {
        let forward = (
            self.source,
            self.source_reversed,
            self.target,
            self.target_reversed,
        );
        let backward = (
            self.target,
            !self.target_reversed,
            self.source,
            !self.source_reversed,
        );
        forward.min(backward)
    }
}

pub fn strand(reversed: bool) -> u8 {
    if reversed { b'-' } else { b'+' }
}

// A node index and whether the path reads the node reversed, packed in one u32
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Step(u32);

impl Step {
    pub fn new(node: u32, reversed: bool) -> Step {
        Step(node << 1 | u32::from(reversed))
    }

    pub fn node(self) -> u32 {
        self.0 >> 1
    }

    pub fn reversed(self) -> bool {
        self.0 & 1 == 1
    }

    pub fn complement(self) -> Step {
        Step(self.0 ^ 1)
    }
}

pub struct Path {
    pub line: usize,
    pub written: Vec<u8>,
    pub name: Vec<u8>,
    pub start: u64,
    pub steps: Vec<Step>,
    pub walk: bool,
}

#[derive(Default)]
pub struct Graph {
    pub node_ids: Interner,
    pub lengths: Vec<Option<u64>>,
    pub declared: Vec<bool>,
    pub tagged: Vec<Option<Placement>>,
    pub sequences: Interner,
    pub links: Vec<Link>,
    pub paths: Vec<Path>,
    pub overlap: Option<String>,
    pub misnamed: Option<String>,
}

pub fn text(bytes: &[u8]) -> String {
    String::from_utf8_lossy(bytes).into_owned()
}

pub fn parse_u64(bytes: &[u8], what: &str) -> Result<u64, String> {
    if bytes.is_empty() || bytes.len() > 19 || !bytes.iter().all(u8::is_ascii_digit) {
        return Err(format!(
            "{what}: {} is not a non-negative integer",
            text(bytes)
        ));
    }
    Ok(bytes.iter().fold(0, |n, &b| n * 10 + u64::from(b - b'0')))
}

pub fn is_blunt(overlap: &[u8]) -> bool {
    matches!(overlap, b"" | b"*" | b"0M")
}

pub fn blunt_error(what: &str) -> String {
    format!(
        "{what}. Coordinates come from summing node lengths along a path, \
         which is only right when consecutive nodes abut. Blunt the graph \
         first (e.g. `vg mod -X` or `odgi build`)."
    )
}

pub fn w_coordinate(bytes: &[u8], what: &str) -> Result<u64, String> {
    if bytes == b"*" {
        Err(format!(
            "{what} is *, which GFA allows but which states no offset on the contig, \
             so the line can't be placed; write the line's start and end"
        ))
    } else {
        parse_u64(bytes, what)
    }
}

struct Suffix {
    at: usize,
    start: u64,
    end: Option<u64>,
}

// `start` or `start-end` after the last `open` of `name`
fn suffix(name: &[u8], open: u8) -> Option<Suffix> {
    let number = |digits: &[u8]| parse_u64(digits, "").ok();
    let at = name.iter().rposition(|&b| b == open)?;
    let mut ends = name[at + 1..].splitn(2, |&b| b == b'-');
    let start = ends.next().and_then(number)?;
    match ends.next() {
        None => Some(Suffix {
            at,
            start,
            end: None,
        }),
        Some(end) => number(end).map(|end| Suffix {
            at,
            start,
            end: Some(end),
        }),
    }
}

// A P line's path and where the line starts on it, read from the right of
// its name once the bp of its steps are known: odgi's `:start-end` where the
// steps span it, beneath it vg's `[start]` or `[start-end]`, beneath that the
// digits of a fourth `#` field. The starts add up (docs/walks-format.md, ADR
// 0014).
pub fn read_path_name(name: &[u8], bp: u64) -> Result<(&[u8], u64), String> {
    let spans = |range: &Suffix| range.end.and_then(|end| end.checked_sub(range.start)) == Some(bp);
    let colon = suffix(name, b':').filter(|cut| bp > 0 && spans(cut));
    let uncut = colon.as_ref().map_or(name, |cut| &name[..cut.at]);
    let bracket = uncut
        .strip_suffix(b"]")
        .and_then(|inner| suffix(inner, b'['));
    let whole = bracket.as_ref().map_or(uncut, |piece| &uncut[..piece.at]);
    let fourth = (whole.iter().filter(|&&b| b == b'#').count() == 3)
        .then(|| suffix(whole, b'#'))
        .flatten()
        .filter(|field| field.end.is_none());
    let path = fourth.as_ref().map_or(whole, |field| &whole[..field.at]);
    let start = [&colon, &bracket, &fourth]
        .iter()
        .try_fold(0u64, |sum, layer| {
            sum.checked_add(layer.as_ref().map_or(0, |suffix| suffix.start))
        });
    let stated_end = bracket
        .as_ref()
        .filter(|piece| colon.is_none() && !spans(piece))
        .and_then(|piece| piece.end.map(|end| (piece.start, end)));
    match (stated_end, start) {
        (Some((start, end)), _) => Err(format!(
            "path {}: the [start-end] in its name ends at {end}, but its steps from {start} end at {}",
            text(name),
            start.saturating_add(bp)
        )),
        _ if name.is_empty() => Err("a P line has an empty name".into()),
        _ if path.is_empty() => Err(format!(
            "path {}: its name is only a start, with no name before it",
            text(name)
        )),
        (_, None) => Err(format!(
            "path {}: the starts in its name add up past 2^64",
            text(name)
        )),
        (_, Some(start)) => Ok((path, start)),
    }
}

// Why two lines of one path can't both stand, the stretch `first` covers
// starting no later than `second`'s: they share a start or overlap
pub fn collision(path: &[u8], first: (u64, u64), second: (u64, u64)) -> Option<String> {
    let path = text(path);
    if first.0 == second.0 {
        Some(format!("path {path} has two lines starting at {}", first.0))
    } else if second.0 < first.1 {
        Some(format!(
            "path {path}: the line covering {}-{} overlaps the one covering {}-{}. \
             Where vg wrote the lines from a VCF-phased GBWT, the fourth field of a P \
             line's name and a W line's start column number phase blocks, which this \
             tool can't tell from starts",
            first.0, first.1, second.0, second.1
        ))
    } else {
        None
    }
}

pub fn sample(path: &[u8]) -> &[u8] {
    path.split(|&b| b == b'#').next().unwrap_or(path)
}

// What a path is listed under: `sample#haplotype` where its name has three
// fields or more, its sample where it has fewer
pub fn haplotype(path: &[u8]) -> &[u8] {
    let mut hashes = memchr::memchr_iter(b'#', path);
    match (hashes.next(), hashes.next()) {
        (Some(_), Some(second)) => &path[..second],
        _ => sample(path),
    }
}

impl Graph {
    pub fn read(input: impl BufRead) -> Result<Graph, String> {
        let mut graph = Graph::default();
        for (number, line) in input.split(b'\n').enumerate() {
            let mut line = line.map_err(|e| e.to_string())?;
            if line.last() == Some(&b'\r') {
                line.pop();
            }
            let cols: Vec<&[u8]> = line.split(|&b| b == b'\t').collect();
            match cols[0] {
                b"S" => graph.segment(&cols),
                b"L" => graph.link(&cols),
                b"P" => graph.p_line(&cols, number + 1),
                b"W" => graph.w_line(&cols, number + 1),
                _ => Ok(()),
            }
            .map_err(|e| format!("line {}: {e}", number + 1))?;
        }
        let mut seen = HashSet::with_capacity(graph.links.len());
        graph.links.retain(|link| seen.insert(link.key()));
        graph.name_paths();
        Ok(graph)
    }

    // Reads each P line's name, its steps' lengths now known. A line on a
    // segment with no length keeps its name: no placement gets past it
    fn name_paths(&mut self) {
        let Graph {
            paths,
            lengths,
            misnamed,
            ..
        } = self;
        for path in paths.iter_mut().filter(|path| !path.walk) {
            let bp: Option<u64> = path
                .steps
                .iter()
                .map(|step| lengths[step.node() as usize])
                .sum();
            match bp.map(|bp| read_path_name(&path.written, bp)) {
                Some(Ok((name, start))) => (path.name, path.start) = (name.to_vec(), start),
                Some(Err(e)) => {
                    misnamed.get_or_insert(format!("line {}: {e}", path.line));
                }
                None => {}
            }
        }
    }

    fn node(&mut self, id: &[u8]) -> u32 {
        let index = self.node_ids.id(id);
        if index as usize == self.lengths.len() {
            self.lengths.push(None);
            self.declared.push(false);
            self.tagged.push(None);
        }
        index
    }

    fn segment(&mut self, cols: &[&[u8]]) -> Result<(), String> {
        if cols.len() < 3 {
            return Err(format!(
                "S line with too few fields: {}",
                text(cols[1..].concat().as_slice())
            ));
        }
        let node = self.node(cols[1]) as usize;
        let (mut name, mut offset, mut rank, mut ln) = (None, None, None, None);
        for tag in &cols[3..] {
            match tag.get(..5) {
                Some(b"SN:Z:") => name = Some(&tag[5..]),
                Some(b"SO:i:") => offset = Some(parse_u64(&tag[5..], "SO tag")?),
                Some(b"SR:i:") => {
                    let parsed = std::str::from_utf8(&tag[5..])
                        .ok()
                        .and_then(|s| s.parse::<i64>().ok());
                    rank =
                        Some(parsed.ok_or_else(|| {
                            format!("SR tag: {} is not an integer", text(&tag[5..]))
                        })?);
                }
                Some(b"LN:i:") => ln = Some(parse_u64(&tag[5..], "LN tag")?),
                _ => {}
            }
        }
        self.declared[node] = true;
        self.lengths[node] = if cols[2] == b"*" {
            ln
        } else {
            Some(cols[2].len() as u64)
        };
        if let Some(name) = name {
            let sequence = self.sequences.id(name);
            self.tagged[node] = Some(Placement {
                sequence,
                start: offset.unwrap_or(0),
                rank: rank.unwrap_or(-1),
            });
        }
        Ok(())
    }

    fn link(&mut self, cols: &[&[u8]]) -> Result<(), String> {
        if cols.len() < 5 {
            return Err("L line with too few fields".into());
        }
        if self.overlap.is_none() && cols.len() > 5 && !is_blunt(cols[5]) {
            self.overlap = Some(format!(
                "link {}->{} has a non-blunt overlap ({})",
                text(cols[1]),
                text(cols[3]),
                text(cols[5])
            ));
        }
        let reversed = |strand: &[u8]| match strand {
            b"+" => Ok(false),
            b"-" => Ok(true),
            _ => Err(format!(
                "link {}->{}: strand {} is not + or -",
                text(cols[1]),
                text(cols[3]),
                text(strand)
            )),
        };
        let (source_reversed, target_reversed) = (reversed(cols[2])?, reversed(cols[4])?);
        let source = self.node(cols[1]);
        let target = self.node(cols[3]);
        self.links.push(Link {
            source,
            source_reversed,
            target,
            target_reversed,
        });
        Ok(())
    }

    fn p_line(&mut self, cols: &[&[u8]], line: usize) -> Result<(), String> {
        if cols.len() < 3 {
            return Err("P line with too few fields".into());
        }
        if self.overlap.is_none()
            && cols.len() > 3
            && let Some(bad) = cols[3].split(|&b| b == b',').find(|o| !is_blunt(o))
        {
            self.overlap = Some(format!(
                "path {} has a non-blunt overlap ({})",
                text(cols[1]),
                text(bad)
            ));
        }
        let mut steps = Vec::new();
        for step in cols[2].split(|&b| b == b',').filter(|s| !s.is_empty()) {
            let (id, reversed) = match step.split_last() {
                Some((b'+', id)) if !id.is_empty() => (id, false),
                Some((b'-', id)) if !id.is_empty() => (id, true),
                _ => {
                    return Err(format!(
                        "path {}: step {} is not a segment id and + or -",
                        text(cols[1]),
                        text(step)
                    ));
                }
            };
            steps.push(Step::new(self.node(id), reversed));
        }
        self.paths.push(Path {
            line,
            written: cols[1].to_vec(),
            name: cols[1].to_vec(),
            start: 0,
            steps,
            walk: false,
        });
        Ok(())
    }

    fn w_line(&mut self, cols: &[&[u8]], line: usize) -> Result<(), String> {
        if cols.len() < 7 {
            return Err("W line with too few fields".into());
        }
        let walk = cols[6];
        if !matches!(walk.first(), Some(b'<' | b'>')) {
            return Err(format!(
                "W line walk {} does not start with > or <",
                text(walk)
            ));
        }
        let name = [cols[1], cols[2], cols[3]].join(&b'#');
        let start = w_coordinate(cols[4], "W line start")?;
        let mut steps = Vec::new();
        let mut rest = walk;
        while let Some((&strand, tail)) = rest.split_first() {
            let end = memchr::memchr2(b'<', b'>', tail).unwrap_or(tail.len());
            if end > 0 {
                steps.push(Step::new(self.node(&tail[..end]), strand == b'<'));
            }
            rest = &tail[end..];
        }
        self.paths.push(Path {
            line,
            written: name.clone(),
            name,
            start,
            steps,
            walk: true,
        });
        Ok(())
    }

    // A graph is rGFA when every S line has an SN tag.
    pub fn is_rgfa(&self) -> bool {
        self.declared
            .iter()
            .zip(&self.tagged)
            .all(|(&declared, tagged)| !declared || tagged.is_some())
    }

    pub fn has_tags(&self) -> bool {
        self.tagged.iter().any(Option::is_some)
    }

    pub fn segment_count(&self) -> usize {
        self.declared.iter().filter(|&&d| d).count()
    }

    pub fn content_hash(&self) -> GraphHash {
        let mut hash = GraphHash::default();
        for ((id, length), _) in self
            .node_ids
            .iter()
            .zip(&self.lengths)
            .zip(&self.declared)
            .filter(|(_, declared)| **declared)
        {
            hash.add(id, *length);
        }
        hash
    }
}

// The graph:Z: of a node and link index and of a walk file: FNV-1a of each
// S line's id and length, summed, so the order of the S lines doesn't change
// it
#[derive(Default, Clone, Copy, PartialEq, Debug)]
pub struct GraphHash(u64);

impl GraphHash {
    pub fn add(&mut self, id: &[u8], length: Option<u64>) {
        let segment = id
            .iter()
            .chain(&[0xff])
            .chain(&length.unwrap_or(u64::MAX).to_le_bytes())
            .fold(0xcbf29ce484222325u64, |h, &b| {
                (h ^ b as u64).wrapping_mul(0x100000001b3)
            });
        self.0 = self.0.wrapping_add(segment);
    }
}

impl std::fmt::Display for GraphHash {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(f, "{:016x}", self.0)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn steps(path: &Path) -> Vec<(u32, bool)> {
        path.steps
            .iter()
            .map(|s| (s.node(), s.reversed()))
            .collect()
    }

    #[test]
    fn a_link_stated_twice_either_way_round_is_kept_once_as_first_written() {
        let gfa = "L\t1\t+\t2\t+\t0M\nL\t2\t-\t1\t-\t0M\nL\t1\t+\t2\t+\t*\n\
                   L\t2\t+\t1\t+\t0M\nL\t3\t+\t3\t-\t0M\nL\t3\t+\t3\t-\t0M\n";
        let graph = Graph::read(gfa.as_bytes()).unwrap();
        let links: Vec<(u32, bool, u32, bool)> = graph
            .links
            .iter()
            .map(|l| (l.source, l.source_reversed, l.target, l.target_reversed))
            .collect();
        assert_eq!(
            links,
            [
                (0, false, 1, false),
                (1, false, 0, false),
                (2, false, 2, true)
            ]
        );
    }

    #[test]
    fn path_and_walk_steps_keep_their_orientation() {
        let graph =
            Graph::read("P\tp\ta+,bb-,c+\t*\nW\ts\t1\tchr\t0\t9\t>c<bb<a\n".as_bytes()).unwrap();
        assert_eq!(
            graph.node_ids[..],
            [b"a".to_vec(), b"bb".to_vec(), b"c".to_vec()]
        );
        assert_eq!(steps(&graph.paths[0]), [(0, false), (1, true), (2, false)]);
        assert_eq!(steps(&graph.paths[1]), [(2, false), (1, true), (0, true)]);
    }

    #[test]
    fn a_step_needs_a_strand() {
        for steps in ["a+,b", "a+,b?", "a+,+"] {
            let text = format!("S\ta\tA\nS\tb\tC\nP\tp\t{steps}\t*\n");
            let error = Graph::read(text.as_bytes()).err().unwrap();
            assert!(error.contains("is not a segment id and + or -"), "{error}");
        }
    }

    #[test]
    fn a_link_strand_is_plus_or_minus() {
        let error = Graph::read("L\ta\t+\tb\tx\t0M\n".as_bytes()).err().unwrap();
        assert!(error.contains("strand x is not + or -"), "{error}");
    }

    const NAMES: &str = include_str!("../docs/walks-container/dialect/p-names.tsv");

    fn refusal(error: &str) -> &'static str {
        if error.contains("the [start-end] in its name ends at") {
            "end"
        } else if error.contains("its name is only a start") || error.contains("an empty name") {
            "empty"
        } else {
            "other"
        }
    }

    #[test]
    fn a_p_line_name_reads_as_the_shared_table_says() {
        let rows: Vec<Vec<&str>> = NAMES
            .lines()
            .skip(1)
            .map(|row| row.split('\t').collect())
            .collect();
        assert!(rows.len() > 60);
        for row in rows {
            let (name, bp) = (row[0].as_bytes(), row[1].parse().unwrap());
            let read = match read_path_name(name, bp) {
                Ok((path, start)) => [text(path), start.to_string(), text(haplotype(path))],
                Err(e) => ["refused".into(), refusal(&e).into(), ".".into()],
            };
            assert_eq!(read[..], row[2..], "{} of {bp} bp", row[0]);
        }
    }

    #[test]
    fn the_specs_table_of_p_line_names_reads_as_it_says() {
        let rows: Vec<Vec<&str>> = include_str!("../docs/walks-format.md")
            .lines()
            .skip_while(|line| !line.starts_with("| P line name |"))
            .skip(2)
            .take_while(|line| line.starts_with('|'))
            .map(|line| {
                line.trim_matches('|')
                    .split('|')
                    .map(|cell| cell.trim().trim_matches('`'))
                    .collect()
            })
            .collect();
        assert_eq!(rows.len(), 11);
        for row in rows {
            let said = match read_path_name(row[0].as_bytes(), row[1].parse().unwrap()) {
                Ok((path, start)) => [text(path), start.to_string()],
                Err(_) => ["refused".into(), String::new()],
            };
            assert_eq!(said[..], row[2..4], "{}", row[0]);
        }
    }

    #[test]
    fn a_p_line_is_named_whether_its_segments_come_before_or_after_it() {
        let segments = "S\ta\tACGTAC\n";
        let paths = "P\tG#0#chr1[100-106]\ta+\t*\nP\tG#1#chr1#100\ta+\t*\n\
                     P\tG#2#chr1:100-106\ta+\t*\nP\tG#3#chr1:101-106\ta+\t*\n";
        for gfa in [format!("{segments}{paths}"), format!("{paths}{segments}")] {
            let graph = Graph::read(gfa.as_bytes()).unwrap();
            let read: Vec<(String, u64)> = graph
                .paths
                .iter()
                .map(|p| (text(&p.name), p.start))
                .collect();
            let expected = [
                ("G#0#chr1", 100),
                ("G#1#chr1", 100),
                ("G#2#chr1", 100),
                ("G#3#chr1:101-106", 0),
            ]
            .map(|(name, start)| (name.to_string(), start));
            assert_eq!(read, expected);
            assert_eq!(graph.misnamed, None);
        }
    }

    #[test]
    fn the_first_misnamed_p_line_is_kept_for_the_placement_to_refuse() {
        let gfa = "S\ta\tACGTAC\nP\tok\ta+\t*\nP\tG#0#chr1[100-900]\ta+\t*\nP\t[5]\ta+\t*\n";
        let graph = Graph::read(gfa.as_bytes()).unwrap();
        assert_eq!(
            graph.misnamed.as_deref(),
            Some(
                "line 3: path G#0#chr1[100-900]: the [start-end] in its name ends at 900, \
                 but its steps from 100 end at 106"
            )
        );
    }

    #[test]
    fn starts_that_add_up_past_2_to_the_64_are_refused() {
        let error = read_path_name(b"H#1#c#9999999999999999999[9999999999999999999]", 6)
            .err()
            .unwrap();
        assert!(error.contains("add up past 2^64"), "{error}");
    }

    #[test]
    fn a_w_line_start_of_star_is_refused_as_stating_no_offset() {
        let error = Graph::read("S\t1\tA\nW\tH\t1\tc\t*\t*\t>1\n".as_bytes())
            .err()
            .unwrap();
        assert!(
            error.contains("W line start is *, which GFA allows but which states no offset"),
            "{error}"
        );
    }
}
