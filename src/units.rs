// A walk file of format 7 (ADR 0010): a header unit, then per reference
// sequence its units and a table listing them, then a BGZF EOF block; and a
// directory beside it naming the header and each table. A unit is a whole run
// of BGZF blocks that starts with its `#unit` line. Both files are written
// under temporary names and renamed, the data file first.

use std::fs::{self, File};

use flate2::Compression;

use crate::parallel_bgzf;

// A unit by the blocks it spans, [from, to)
struct Entry {
    lo: u64,
    hi: u64,
    kind: &'static str,
    name: String,
    from: u64,
    to: u64,
}

pub struct UnitFile {
    path: String,
    temp: String,
    sink: parallel_bgzf::Writer,
    walks: Vec<u8>,
    directory: Vec<u8>,
    // the units of the sequence being written
    entries: Vec<Entry>,
    open: Option<Entry>,
    units: u64,
}

fn temp_name(path: &str) -> String {
    format!("{path}.tmp-{}", std::process::id())
}

impl UnitFile {
    // `header` is the header unit's text, its `#walks` line first
    pub fn create(path: &str, header: &[u8], threads: usize) -> Result<UnitFile, String> {
        let temp = temp_name(path);
        let file = File::create(&temp).map_err(|e| format!("{path}: {e}"))?;
        let mut out = UnitFile {
            path: path.to_string(),
            temp,
            sink: parallel_bgzf::Writer::new(file, Compression::new(6), threads),
            walks: header
                .split(|&b| b == b'\n')
                .next()
                .unwrap_or_default()
                .to_vec(),
            directory: Vec::new(),
            entries: Vec::new(),
            open: None,
            units: 0,
        };
        out.write(header)?;
        out.cut()?;
        out.resolve_all()?;
        let length = out.start_of(out.block())?;
        out.directory = format!("#header\t0\t{length}\n").into_bytes();
        Ok(out)
    }

    fn io(&self) -> impl Fn(std::io::Error) -> String + '_ {
        |e| format!("{}: {e}", self.path)
    }

    fn block(&self) -> u64 {
        self.sink.position().0
    }

    fn cut(&mut self) -> Result<(), String> {
        self.sink.cut().map_err(|e| format!("{}: {e}", self.path))?;
        Ok(())
    }

    fn resolve_all(&mut self) -> Result<(), String> {
        self.sink
            .flush_all()
            .map_err(|e| format!("{}: {e}", self.path))
    }

    fn start_of(&self, block: u64) -> Result<u64, String> {
        self.sink
            .block_start(block)
            .ok_or_else(|| format!("{}: block {block} is not written", self.path))
    }

    pub fn write(&mut self, text: &[u8]) -> Result<(), String> {
        self.sink.write(text).map_err(self.io())?;
        Ok(())
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
        let from = self.block();
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
        self.entries.push(entry);
        self.units += 1;
        Ok(())
    }

    // Ends sequence `seq`: writes its table, which lists its units in file
    // order, and names the table in the directory
    pub fn table(&mut self, seq: &[u8]) -> Result<(), String> {
        self.resolve_all()?;
        let hi = self.entries.iter().map(|e| e.hi).max().unwrap_or(0);
        let mut text = unit_line(seq, 0, hi, "table", ".");
        for e in &self.entries {
            let (from, to) = (self.start_of(e.from)?, self.start_of(e.to)?);
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
        let from = self.block();
        self.write(&text)?;
        self.cut()?;
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
        let bytes = fs::metadata(&temp).map_err(io)?.len();
        fs::rename(&temp, &path).map_err(io)?;
        let index = format!("{path}.idx");
        let index_temp = temp_name(&index);
        let mut text = walks;
        text.extend_from_slice(format!("\tbytes:i:{bytes}\n").as_bytes());
        text.extend_from_slice(&directory);
        let io = |e: std::io::Error| format!("{index}: {e}");
        fs::write(&index_temp, text).map_err(io)?;
        fs::rename(&index_temp, &index).map_err(io)?;
        Ok(units)
    }
}

fn unit_line(seq: &[u8], lo: u64, hi: u64, kind: &str, name: &str) -> Vec<u8> {
    let mut line = b"#unit\t".to_vec();
    line.extend_from_slice(seq);
    line.extend_from_slice(format!("\t{lo}\t{hi}\t{kind}\t{name}\n").as_bytes());
    line
}
