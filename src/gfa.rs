use std::collections::HashMap;
use std::io::BufRead;

pub struct Placement {
    pub sequence: u32,
    pub start: u64,
    pub rank: i64,
}

pub struct Link {
    pub source: u32,
    pub source_strand: Vec<u8>,
    pub target: u32,
    pub target_strand: Vec<u8>,
}

pub struct Path {
    pub name: Vec<u8>,
    pub start: u64,
    pub steps: Vec<u32>,
}

#[derive(Default)]
pub struct Graph {
    node_index: HashMap<Vec<u8>, u32>,
    pub node_ids: Vec<Vec<u8>>,
    pub lengths: Vec<Option<u64>>,
    pub declared: Vec<bool>,
    pub tagged: Vec<Option<Placement>>,
    sequence_index: HashMap<Vec<u8>, u32>,
    pub sequences: Vec<Vec<u8>>,
    pub links: Vec<Link>,
    pub paths: Vec<Path>,
    pub overlap: Option<String>,
}

fn text(bytes: &[u8]) -> String {
    String::from_utf8_lossy(bytes).into_owned()
}

fn parse_u64(bytes: &[u8], what: &str) -> Result<u64, String> {
    std::str::from_utf8(bytes)
        .ok()
        .and_then(|s| s.parse().ok())
        .ok_or_else(|| format!("{what}: {} is not a non-negative integer", text(bytes)))
}

fn is_blunt(overlap: &[u8]) -> bool {
    matches!(overlap, b"" | b"*" | b"0M")
}

// `odgi extract` names a path `K12#1#chr:1004500-1004961`; the suffix is the
// only record of where the extracted piece starts.
fn split_range_suffix(name: &[u8]) -> (&[u8], u64) {
    if let Some(colon) = name.iter().rposition(|&b| b == b':') {
        let tail = &name[colon + 1..];
        if let Some(dash) = tail.iter().position(|&b| b == b'-') {
            let (start, end) = (&tail[..dash], &tail[dash + 1..]);
            let digits = |s: &[u8]| !s.is_empty() && s.iter().all(u8::is_ascii_digit);
            if digits(start)
                && digits(end)
                && let Ok(start) = parse_u64(start, "path range")
            {
                return (&name[..colon], start);
            }
        }
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
        if let Some(&index) = self.node_index.get(id) {
            return index;
        }
        let index = self.node_ids.len() as u32;
        self.node_index.insert(id.to_vec(), index);
        self.node_ids.push(id.to_vec());
        self.lengths.push(None);
        self.declared.push(false);
        self.tagged.push(None);
        index
    }

    fn sequence(&mut self, name: &[u8]) -> u32 {
        if let Some(&index) = self.sequence_index.get(name) {
            return index;
        }
        let index = self.sequences.len() as u32;
        self.sequence_index.insert(name.to_vec(), index);
        self.sequences.push(name.to_vec());
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
                    rank = std::str::from_utf8(&tag[5..])
                        .ok()
                        .and_then(|s| s.parse::<i64>().ok())
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
            let sequence = self.sequence(name);
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
        let source = self.node(cols[1]);
        let target = self.node(cols[3]);
        self.links.push(Link {
            source,
            source_strand: cols[2].to_vec(),
            target,
            target_strand: cols[4].to_vec(),
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
        let (name, start) = split_range_suffix(cols[1]);
        let name = name.to_vec();
        let mut steps = Vec::new();
        for step in cols[2].split(|&b| b == b',') {
            if !step.is_empty() {
                steps.push(self.node(&step[..step.len() - 1]));
            }
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
        for id in walk.split(|&b| b == b'<' || b == b'>') {
            if !id.is_empty() {
                steps.push(self.node(id));
            }
        }
        self.paths.push(Path { name, start, steps });
        Ok(())
    }

    // A graph is rGFA when every S line carries an SN tag.
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
