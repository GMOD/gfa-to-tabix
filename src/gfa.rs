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
    pub name: Vec<u8>,
    pub start: u64,
    pub steps: Vec<Step>,
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

// A P line's name and where its piece starts. `vg convert` writes a path piece
// as `sample#hap#contig[start-end]` or, for a haplotype,
// `sample#hap#contig#start`; `odgi extract` writes `name:start-end`.
pub fn split_path_name(name: &[u8]) -> (&[u8], u64) {
    let number = |s: &[u8]| parse_u64(s, "").ok();
    if let Some(inner) = name.strip_suffix(b"]")
        && let Some(open) = inner.iter().rposition(|&b| b == b'[')
        && let Some(start) = inner[open + 1..]
            .split(|&b| b == b'-')
            .next()
            .and_then(number)
    {
        return (&name[..open], start);
    }
    if name.iter().filter(|&&b| b == b'#').count() == 3
        && let Some(hash) = name.iter().rposition(|&b| b == b'#')
        && let Some(start) = number(&name[hash + 1..])
    {
        return (&name[..hash], start);
    }
    if let Some(colon) = name.iter().rposition(|&b| b == b':')
        && let [start, end] = name[colon + 1..].split(|&b| b == b'-').collect::<Vec<_>>()[..]
        && number(end).is_some()
        && let Some(start) = number(start)
    {
        return (&name[..colon], start);
    }
    (name, 0)
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
                b"P" => graph.p_line(&cols),
                b"W" => graph.w_line(&cols),
                _ => Ok(()),
            }
            .map_err(|e| format!("line {}: {e}", number + 1))?;
        }
        Ok(graph)
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

    fn p_line(&mut self, cols: &[&[u8]]) -> Result<(), String> {
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
        let (name, start) = split_path_name(cols[1]);
        let name = name.to_vec();
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
        self.paths.push(Path { name, start, steps });
        Ok(())
    }

    fn w_line(&mut self, cols: &[&[u8]]) -> Result<(), String> {
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
        let start = parse_u64(cols[4], "W line start")?;
        let mut steps = Vec::new();
        let mut rest = walk;
        while let Some((&strand, tail)) = rest.split_first() {
            let end = memchr::memchr2(b'<', b'>', tail).unwrap_or(tail.len());
            if end > 0 {
                steps.push(Step::new(self.node(&tail[..end]), strand == b'<'));
            }
            rest = &tail[end..];
        }
        self.paths.push(Path { name, start, steps });
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

    #[test]
    fn a_path_piece_name_gives_its_start() {
        let names = [
            "G#0#chr1[100-106]",
            "G#0#chr1[100]",
            "G#1#chr1#100",
            "G#0#chr1:100-106",
        ];
        let text: String = names.iter().map(|n| format!("P\t{n}\ta+\t*\n")).collect();
        let graph = Graph::read(text.as_bytes()).unwrap();
        let read: Vec<(&[u8], u64)> = graph
            .paths
            .iter()
            .map(|p| (p.name.as_slice(), p.start))
            .collect();
        assert_eq!(
            read,
            [
                (b"G#0#chr1".as_slice(), 100),
                (b"G#0#chr1", 100),
                (b"G#1#chr1", 100),
                (b"G#0#chr1", 100),
            ]
        );
    }
}
