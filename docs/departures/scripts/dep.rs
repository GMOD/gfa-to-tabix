// dep: independent enumeration of every place a path does not follow the
// reference R, straight from a GFA. Usage: dep <gfa> <refsample> <out-prefix>
use std::collections::HashMap;
use std::fs::File;
use std::io::{BufRead, BufReader, BufWriter, Write};

const NONE: u32 = u32::MAX;
const CHUNK: u32 = 16;

struct Path {
    name: String,
    start: u64,
    steps: Vec<(u32, bool)>,
}

fn parse_steps(field: &[u8], w: bool) -> Vec<(u32, bool)> {
    let mut out = Vec::new();
    let mut id: u64 = 0;
    let mut rev = false;
    let mut have = false;
    for &c in field {
        match c {
            b'0'..=b'9' => {
                id = id * 10 + u64::from(c - b'0');
                have = true;
            }
            b'>' | b'<' if w => {
                if have {
                    out.push((id as u32, rev));
                }
                id = 0;
                have = false;
                rev = c == b'<';
            }
            b'+' | b'-' if !w => {
                out.push((id as u32, c == b'-'));
                id = 0;
                have = false;
            }
            _ => {}
        }
    }
    if w && have {
        out.push((id as u32, rev));
    }
    out
}

fn read_path(line: &[u8]) -> Option<Path> {
    let f: Vec<&[u8]> = line.split(|&c| c == b'\t').collect();
    if f[0] == b"W" {
        let name = format!(
            "{}#{}#{}",
            String::from_utf8_lossy(f[1]),
            String::from_utf8_lossy(f[2]),
            String::from_utf8_lossy(f[3])
        );
        let start: u64 = std::str::from_utf8(f[4]).ok()?.parse().unwrap_or(0);
        Some(Path { name, start, steps: parse_steps(f[6], true) })
    } else if f[0] == b"P" {
        Some(Path { name: String::from_utf8_lossy(f[1]).to_string(), start: 0, steps: parse_steps(f[2], false) })
    } else {
        None
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let (gfa, refsample, out) = (&args[1], &args[2], &args[3]);
    let prefix = format!("{refsample}#");
    let mut lengths: Vec<u32> = Vec::new();
    let mut refs: Vec<Path> = Vec::new();
    let mut reader = BufReader::with_capacity(1 << 24, File::open(gfa).unwrap());
    let mut line = Vec::new();
    while reader.read_until(b'\n', &mut line).unwrap() > 0 {
        if line.last() == Some(&b'\n') {
            line.pop();
        }
        if line.starts_with(b"S\t") {
            let mut it = line.split(|&c| c == b'\t');
            it.next();
            let id: usize = std::str::from_utf8(it.next().unwrap()).unwrap().parse().unwrap();
            let len = it.next().unwrap().len() as u32;
            if lengths.len() <= id {
                lengths.resize(id + 1, 0);
            }
            lengths[id] = len;
        } else if line.starts_with(b"W\t") || line.starts_with(b"P\t") {
            let is_ref = if line[0] == b'W' {
                line[2..].starts_with(refsample.as_bytes()) && line[2 + refsample.len()] == b'\t'
            } else {
                line[2..].starts_with(prefix.as_bytes())
            };
            if is_ref {
                refs.push(read_path(&line).unwrap());
            }
        }
        line.clear();
    }
    let n = lengths.len();
    let mut seq_of = vec![NONE; n];
    let mut pos = vec![0u32; n];
    let mut rank = vec![0u32; n];
    let mut rrev = vec![false; n];
    let mut npass = vec![0u16; n];
    for (s, p) in refs.iter().enumerate() {
        let mut off: u64 = 0;
        for (k, &(id, rev)) in p.steps.iter().enumerate() {
            let i = id as usize;
            if npass[i] == 0 {
                seq_of[i] = s as u32;
                pos[i] = off as u32;
                rank[i] = k as u32;
                rrev[i] = rev;
            }
            npass[i] = npass[i].saturating_add(1);
            off += u64::from(lengths[i]);
        }
        eprintln!("ref {} {} steps {} bp", p.name, p.steps.len(), off);
    }
    let mut dep = BufWriter::new(File::create(format!("{out}.dep.tsv")).unwrap());
    let mut pres = BufWriter::new(File::create(format!("{out}.presence.tsv")).unwrap());
    let mut counts: HashMap<String, u64> = HashMap::new();
    let mut reader = BufReader::with_capacity(1 << 24, File::open(gfa).unwrap());
    let ref_names: Vec<&String> = refs.iter().map(|p| &p.name).collect();
    while reader.read_until(b'\n', &mut line).unwrap() > 0 {
        if line.last() == Some(&b'\n') {
            line.pop();
        }
        if line.starts_with(b"W\t") || line.starts_with(b"P\t") {
            let p = read_path(&line).unwrap();
            line.clear();
            if ref_names.contains(&&p.name) {
                continue;
            }
            let mut before = Vec::with_capacity(p.steps.len() + 1);
            let mut off = 0u64;
            for &(id, _) in &p.steps {
                before.push(off);
                off += u64::from(lengths[id as usize]);
            }
            before.push(off);
            let on: Vec<usize> = (0..p.steps.len()).filter(|&k| seq_of[p.steps[k].0 as usize] != NONE).collect();
            if on.is_empty() {
                *counts.entry("unplaced_paths".into()).or_default() += 1;
                continue;
            }
            let mut chunks: Vec<(u32, u32)> = on.iter().map(|&k| { let i = p.steps[k].0 as usize; (seq_of[i], pos[i] >> CHUNK) }).collect();
            chunks.sort_unstable();
            chunks.dedup();
            let (a0, z0) = (on[0], *on.last().unwrap());
            let lead = before[a0];
            let tail = off - before[z0 + 1];
            write!(pres, "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}", p.name, p.start, off, lead, tail, a0, p.steps.len() - z0 - 1, on.len()).unwrap();
            let mut first = true;
            for (s, c) in &chunks {
                write!(pres, "{}{}:{}", if first { '\t' } else { ',' }, s, c).unwrap();
                first = false;
            }
            writeln!(pres).unwrap();
            for t in 0..on.len() - 1 {
                let (a, b) = (on[t], on[t + 1]);
                let (ia, ib) = (p.steps[a].0 as usize, p.steps[b].0 as usize);
                let inva = p.steps[a].1 != rrev[ia];
                let invb = p.steps[b].1 != rrev[ib];
                let own = (b - a - 1) as u64;
                let own_bp = before[b] - before[a + 1];
                let multi = npass[ia] > 1 || npass[ib] > 1;
                let same = seq_of[ia] == seq_of[ib];
                let follows = !multi && same && own == 0 && ((!inva && !invb && rank[ib] == rank[ia] + 1) || (inva && invb && rank[ib] + 1 == rank[ia]));
                if follows {
                    continue;
                }
                let (pa, ea) = (pos[ia], pos[ia] + lengths[ia]);
                let (pb, eb) = (pos[ib], pos[ib] + lengths[ib]);
                let (rs, re, order) = if ea <= pb { (ea, pb, '+') } else if eb <= pa { (eb, pa, '-') } else { (pa.min(pb), pa.min(pb), 'o') };
                let l = re - rs;
                let (ca, cb) = (pa >> CHUNK, pb >> CHUNK);
                let kind = if !same {
                    "xseq"
                } else if multi {
                    "multi"
                } else if order == 'o' {
                    "overlap"
                } else if l == 0 && inva == invb && ((order == '+') == !inva) {
                    if own > 0 { "ins" } else { "adj?" }
                } else if l == 0 {
                    "flip0"
                } else {
                    "jump"
                };
                let between = !same || ca != cb;
                let ob = match own_bp { 0 => "0", 1..=49 => "1-49", 50..=999 => "50-999", 1000..=9999 => "1k-10k", 10000..=99999 => "10k-100k", _ => ">=100k" };
                let lb = match l { 0 => "0", 1..=49 => "1-49", 50..=999 => "50-999", 1000..=65535 => "1k-64k", 65536..=2097151 => "64k-2M", _ => ">=2M" };
                *counts.entry(format!("{kind}\tbetween={between}\town={ob}\tL={lb}")).or_default() += 1;
                if own_bp >= 1000 || (!multi && (between || l >= 1000 || kind != "jump" && kind != "ins")) {
                    writeln!(dep, "{}\t{}\t{}\t{}:{}\t{}:{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}", p.name, p.start, kind, seq_of[ia], ca, seq_of[ib], cb, rs, re, order, l, own_bp, own, p.start + before[a + 1], u8::from(inva), u8::from(invb), u8::from(multi)).unwrap();
                }
            }
        }
        line.clear();
    }
    let mut c: Vec<_> = counts.into_iter().collect();
    c.sort();
    let mut f = File::create(format!("{out}.counts.tsv")).unwrap();
    for (k, v) in c {
        writeln!(f, "{k}\t{v}").unwrap();
    }
}
