// A walk file of format 7 (ADR 0010): a header unit, then per reference
// sequence its units and a table listing them, then a BGZF EOF block; and a
// directory beside it naming the header and each table. A unit is a whole run
// of BGZF blocks that starts with its `#unit` line. Both files are written
// under temporary names and renamed, the data file first.

use std::fs::{self, File};

use flate2::Compression;

use crate::parallel_bgzf;

// zlib-rs's first level on deflate_slow, zlib's lazy matching, where 3 to 6 use
// deflate_medium: on MC chr22 and pggb chrY 2.6% and 5.0% smaller than level
// 6 in the same time (docs/walks-container/writer/)
const LEVEL: u32 = 7;

// A unit by the blocks it spans, [from, to)
struct Entry {
    lo: u64,
    hi: u64,
    kind: &'static str,
    name: String,
    from: u64,
    to: u64,
}

// A file under its temporary name, removed unless `rename` moves it into place
struct Temp(String);

impl Temp {
    fn new(path: &str) -> Temp {
        Temp(format!("{path}.tmp-{}", std::process::id()))
    }

    fn rename(mut self, path: &str) -> std::io::Result<()> {
        fs::rename(&self.0, path)?;
        self.0.clear();
        Ok(())
    }
}

impl Drop for Temp {
    fn drop(&mut self) {
        if !self.0.is_empty() {
            let _ = fs::remove_file(&self.0);
        }
    }
}

pub struct UnitFile {
    path: String,
    temp: Temp,
    sink: parallel_bgzf::Writer,
    walks: Vec<u8>,
    directory: Vec<u8>,
    // the units of the sequence being written
    entries: Vec<Entry>,
    open: Option<Entry>,
    units: u64,
    // the block the next unit or table must start at, so they partition the
    // file
    next: u64,
}

impl UnitFile {
    // `header` is the header unit's text, its `#walks` line first
    pub fn create(path: &str, header: &[u8], threads: usize) -> Result<UnitFile, String> {
        let temp = Temp::new(path);
        let file = File::create(&temp.0).map_err(|e| format!("{path}: {e}"))?;
        let sink = parallel_bgzf::Writer::new(file, Compression::new(LEVEL), threads);
        UnitFile::start(path, temp, sink, header)
    }

    fn start(
        path: &str,
        temp: Temp,
        sink: parallel_bgzf::Writer,
        header: &[u8],
    ) -> Result<UnitFile, String> {
        let mut out = UnitFile {
            path: path.to_string(),
            temp,
            sink,
            walks: header
                .split(|&b| b == b'\n')
                .next()
                .unwrap_or_default()
                .to_vec(),
            directory: Vec::new(),
            entries: Vec::new(),
            open: None,
            units: 0,
            next: 0,
        };
        out.write(header)?;
        out.cut()?;
        out.next = out.block();
        out.resolve_all()?;
        let length = out.start_of(out.block())?;
        out.directory = format!("#header\t0\t{length}\n").into_bytes();
        Ok(out)
    }

    fn failed(&self, e: std::io::Error) -> String {
        format!("{}: {e}", self.path)
    }

    fn holds(&self, kept: bool, guarantee: &str) -> Result<(), String> {
        if kept {
            Ok(())
        } else {
            Err(format!(
                "{}: the writer broke its guarantee that {guarantee}",
                self.path
            ))
        }
    }

    // The block a unit or table starts at, which must be where the last one
    // ended
    fn starting(&self) -> Result<u64, String> {
        let from = self.block();
        self.holds(from == self.next, "the units partition the file")?;
        Ok(from)
    }

    fn block(&self) -> u64 {
        self.sink.position().0
    }

    fn cut(&mut self) -> Result<(), String> {
        self.sink.cut().map(drop).map_err(|e| self.failed(e))
    }

    fn resolve_all(&mut self) -> Result<(), String> {
        self.sink.flush_all().map_err(|e| self.failed(e))
    }

    fn start_of(&self, block: u64) -> Result<u64, String> {
        self.sink
            .block_start(block)
            .ok_or_else(|| format!("{}: block {block} is not written", self.path))
    }

    pub fn write(&mut self, text: &[u8]) -> Result<(), String> {
        self.sink.write(text).map(drop).map_err(|e| self.failed(e))
    }

    // Starts a unit, writing its `#unit` line; its lines follow through `write`
    pub fn begin(
        &mut self,
        seq: &[u8],
        (lo, hi): (u64, u64),
        kind: &'static str,
        name: &str,
    ) -> Result<(), String> {
        let line = unit_line(seq, lo, hi, kind, name);
        let from = self.starting()?;
        self.write(&line)?;
        self.open = Some(Entry {
            lo,
            hi,
            kind,
            name: name.to_string(),
            from,
            to: from,
        });
        Ok(())
    }

    pub fn end(&mut self) -> Result<(), String> {
        self.cut()?;
        let mut entry = self.open.take().expect("a unit is open");
        entry.to = self.block();
        self.next = entry.to;
        self.entries.push(entry);
        self.units += 1;
        Ok(())
    }

    // Ends sequence `seq`, of `length` bp: writes its table, which lists its
    // units in file order, and names the table in the directory. Fails
    // where a listed unit is empty or does not start where the one before
    // it ends, or where two units of a kind share a name other than `.`.
    pub fn table(&mut self, seq: &[u8], length: u64) -> Result<(), String> {
        self.resolve_all()?;
        let mut names: Vec<(&str, &str)> = self
            .entries
            .iter()
            .filter(|e| e.name != ".")
            .map(|e| (e.kind, e.name.as_str()))
            .collect();
        names.sort_unstable();
        self.holds(
            names.windows(2).all(|w| w[0] != w[1]),
            "no two units of a kind and sequence share a name other than .",
        )?;
        let mut text = unit_line(seq, 0, length, "table", ".");
        let mut at = self.entries.first().map(|e| e.from);
        for e in &self.entries {
            let (from, to) = (self.start_of(e.from)?, self.start_of(e.to)?);
            self.holds(
                at == Some(e.from) && to > from,
                "a table lists its units in file order, each above 0 bytes",
            )?;
            at = Some(e.to);
            text.extend_from_slice(b"#entry\t");
            text.extend_from_slice(seq);
            text.extend_from_slice(
                format!(
                    "\t{}\t{}\t{}\t{}\t{from}\t{}\n",
                    e.lo,
                    e.hi,
                    e.kind,
                    e.name,
                    to - from
                )
                .as_bytes(),
            );
        }
        self.entries.clear();
        let from = self.starting()?;
        self.write(&text)?;
        self.cut()?;
        self.next = self.block();
        self.resolve_all()?;
        let (start, end) = (self.start_of(from)?, self.start_of(self.block())?);
        self.directory.extend_from_slice(seq);
        self.directory
            .extend_from_slice(format!("\t{start}\t{}\n", end - start).as_bytes());
        self.sink.forget_before(self.block());
        Ok(())
    }

    // Writes the EOF block and renames the data file, then writes the
    // directory, its first line the header's `#walks` line and the data
    // file's length, and renames it. Returns how many units the file holds
    // besides the header and the tables.
    pub fn finish(self) -> Result<u64, String> {
        self.holds(
            self.block() == self.next && self.open.is_none(),
            "the EOF block follows the last table",
        )?;
        let UnitFile {
            path,
            temp,
            sink,
            walks,
            directory,
            units,
            ..
        } = self;
        let io = |e: std::io::Error| format!("{path}: {e}");
        sink.finish().map_err(io)?;
        let bytes = fs::metadata(&temp.0).map_err(io)?.len();
        temp.rename(&path).map_err(io)?;
        let index = format!("{path}.idx");
        let index_temp = Temp::new(&index);
        let mut text = walks;
        text.extend_from_slice(format!("\tbytes:i:{bytes}\n").as_bytes());
        text.extend_from_slice(&directory);
        let io = |e: std::io::Error| format!("{index}: {e}");
        fs::write(&index_temp.0, text).map_err(io)?;
        index_temp.rename(&index).map_err(io)?;
        Ok(units)
    }
}

fn unit_line(seq: &[u8], lo: u64, hi: u64, kind: &str, name: &str) -> Vec<u8> {
    let mut line = b"#unit\t".to_vec();
    line.extend_from_slice(seq);
    line.extend_from_slice(format!("\t{lo}\t{hi}\t{kind}\t{name}\n").as_bytes());
    line
}

#[cfg(test)]
mod tests {
    use super::*;
    use flate2::read::MultiGzDecoder;
    use std::io::Read;

    // Writes a file whose offsets count from `base`, as if `base` bytes of
    // units came first, with units of incompressible text big enough to span
    // blocks; each table entry and directory line, less `base`, must give the
    // unit's place in the file as written
    fn units_read_back_at(base: u64) {
        let dir = std::env::temp_dir().join(format!("units-{}-{base}", std::process::id()));
        fs::create_dir_all(&dir).unwrap();
        let path = dir.join("f.walks.gz").to_str().unwrap().to_string();
        let temp = Temp::new(&path);
        let sink =
            parallel_bgzf::Writer::new(File::create(&temp.0).unwrap(), Compression::new(LEVEL), 2)
                .starting_at(base);
        let mut out = UnitFile::start(&path, temp, sink, b"#walks\tformat:i:7\n").unwrap();
        let mut noise = 1u64;
        for k in 0..4u64 {
            out.begin(b"s", (k, k + 1), "tile", &k.to_string()).unwrap();
            let text: String = (0..150_000)
                .map(|_| {
                    noise = noise
                        .wrapping_mul(6364136223846793005)
                        .wrapping_add(1442695040888963407);
                    char::from(b'a' + (noise >> 59) as u8)
                })
                .collect();
            out.write(text.as_bytes()).unwrap();
            out.write(b"\n").unwrap();
            out.end().unwrap();
        }
        out.table(b"s", 4).unwrap();
        out.finish().unwrap();
        let data = fs::read(&path).unwrap();
        let directory = fs::read_to_string(format!("{path}.idx")).unwrap();
        fs::remove_dir_all(&dir).unwrap();
        let unit = |offset: u64, length: u64| {
            let from = (offset - base) as usize;
            let mut text = String::new();
            MultiGzDecoder::new(&data[from..from + length as usize])
                .read_to_string(&mut text)
                .unwrap();
            text
        };
        let line: Vec<u64> = directory
            .lines()
            .nth(2)
            .unwrap()
            .split('\t')
            .skip(1)
            .map(|n| n.parse().unwrap())
            .collect();
        let table = unit(line[0], line[1]);
        let entries: Vec<Vec<&str>> = table
            .lines()
            .skip(1)
            .map(|l| l.split('\t').collect())
            .collect();
        assert_eq!(entries.len(), 4);
        for (k, e) in entries.iter().enumerate() {
            let (offset, length): (u64, u64) = (e[6].parse().unwrap(), e[7].parse().unwrap());
            assert!(offset > base);
            assert!(
                unit(offset, length).starts_with(&format!("#unit\ts\t{k}\t{}\ttile\t{k}\n", k + 1))
            );
        }
        assert!(directory.starts_with(&format!("#walks\tformat:i:7\tbytes:i:{}\n", data.len())));
    }

    #[test]
    fn offsets_past_2_to_the_31_and_32_round_trip() {
        for base in [(1 << 31) - 70_000, (1 << 32) - 70_000, 1 << 40] {
            units_read_back_at(base);
        }
    }
}
