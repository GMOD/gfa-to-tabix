// An external sort for rows keyed by an integer, with the row's text as the
// tiebreak. Rows collect in memory until a budget fills, then a background
// thread sorts them and writes a compressed run file; `merge` streams the runs
// back in order.

use std::cmp::{Ordering, Reverse};
use std::collections::BinaryHeap;
use std::fs::{self, File};
use std::io::{self, BufReader, BufWriter, Read, Write};
use std::mem;
use std::path::{Path, PathBuf};
use std::thread::{self, JoinHandle};

use flate2::Compression;
use flate2::read::DeflateDecoder;
use flate2::write::DeflateEncoder;

#[derive(Default)]
struct Batch {
    text: Vec<u8>,
    // (key, offset into text, length)
    rows: Vec<(u32, u32, u32)>,
}

pub struct Sorter {
    dir: PathBuf,
    name: &'static str,
    dedup: bool,
    budget: usize,
    batch: Batch,
    runs: Vec<PathBuf>,
    spilling: Option<JoinHandle<Result<(), String>>>,
}

fn io_error(path: &Path) -> impl Fn(io::Error) -> String + '_ {
    move |e| format!("{}: {e}", path.display())
}

fn write_run(path: &Path, batch: Batch, dedup: bool) -> Result<(), String> {
    let Batch { text, mut rows } = batch;
    let row_text = |&(_, offset, length): &(u32, u32, u32)| {
        &text[offset as usize..offset as usize + length as usize]
    };
    rows.sort_unstable_by(|a, b| a.0.cmp(&b.0).then_with(|| row_text(a).cmp(row_text(b))));
    if dedup {
        rows.dedup_by(|a, b| a.0 == b.0 && row_text(a) == row_text(b));
    }
    let fail = io_error(path);
    let file = File::create(path).map_err(&fail)?;
    let mut out = BufWriter::with_capacity(1 << 20, DeflateEncoder::new(file, Compression::fast()));
    for row in &rows {
        out.write_all(&row.0.to_le_bytes()).map_err(&fail)?;
        out.write_all(&row.2.to_le_bytes()).map_err(&fail)?;
        out.write_all(row_text(row)).map_err(&fail)?;
    }
    out.into_inner()
        .map_err(|e| fail(e.into_error()))?
        .finish()
        .map(drop)
        .map_err(&fail)
}

struct Run {
    reader: BufReader<DeflateDecoder<BufReader<File>>>,
}

impl Run {
    // Reads the next row into `text`; false at the end of the run.
    fn next(&mut self, key: &mut u32, text: &mut Vec<u8>) -> io::Result<bool> {
        let mut word = [0u8; 4];
        match self.reader.read_exact(&mut word) {
            Ok(()) => {}
            Err(e) if e.kind() == io::ErrorKind::UnexpectedEof => return Ok(false),
            Err(e) => return Err(e),
        }
        *key = u32::from_le_bytes(word);
        self.reader.read_exact(&mut word)?;
        text.resize(u32::from_le_bytes(word) as usize, 0);
        self.reader.read_exact(text)?;
        Ok(true)
    }
}

struct Head {
    key: u32,
    text: Vec<u8>,
    run: usize,
}

impl PartialEq for Head {
    fn eq(&self, other: &Self) -> bool {
        self.cmp(other) == Ordering::Equal
    }
}

impl Eq for Head {}

impl PartialOrd for Head {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for Head {
    fn cmp(&self, other: &Self) -> Ordering {
        (self.key, &self.text, self.run).cmp(&(other.key, &other.text, other.run))
    }
}

impl Sorter {
    // Run files go in `dir` as `name.0`, `name.1`, ... With `dedup`, rows
    // equal in key and text come out once.
    pub fn new(dir: &Path, name: &'static str, dedup: bool, budget: usize) -> Sorter {
        Sorter {
            dir: dir.to_path_buf(),
            name,
            dedup,
            budget: budget.min(u32::MAX as usize),
            batch: Batch::default(),
            runs: Vec::new(),
            spilling: None,
        }
    }

    // `fill` appends the row's text.
    pub fn push(&mut self, key: u32, fill: impl FnOnce(&mut Vec<u8>)) -> Result<(), String> {
        let offset = self.batch.text.len();
        fill(&mut self.batch.text);
        let length = self.batch.text.len() - offset;
        self.batch.rows.push((key, offset as u32, length as u32));
        if self.batch.text.len() + 12 * self.batch.rows.len() >= self.budget {
            self.spill()?;
        }
        Ok(())
    }

    fn wait(&mut self) -> Result<(), String> {
        match self.spilling.take() {
            Some(handle) => handle
                .join()
                .map_err(|_| format!("sorting {} rows panicked", self.name))?,
            None => Ok(()),
        }
    }

    fn spill(&mut self) -> Result<(), String> {
        self.wait()?;
        if self.batch.rows.is_empty() {
            return Ok(());
        }
        let batch = mem::take(&mut self.batch);
        let path = self.dir.join(format!("{}.{}", self.name, self.runs.len()));
        self.runs.push(path.clone());
        let dedup = self.dedup;
        self.spilling = Some(thread::spawn(move || write_run(&path, batch, dedup)));
        Ok(())
    }

    // Streams every row in (key, text) order to `emit`, then deletes the runs.
    // Returns the number of rows emitted.
    pub fn merge(
        mut self,
        mut emit: impl FnMut(u32, &[u8]) -> Result<(), String>,
    ) -> Result<u64, String> {
        self.spill()?;
        self.wait()?;
        let mut runs = Vec::with_capacity(self.runs.len());
        let mut heap = BinaryHeap::with_capacity(self.runs.len());
        for (index, path) in self.runs.iter().enumerate() {
            let file = File::open(path).map_err(io_error(path))?;
            let mut run = Run {
                reader: BufReader::with_capacity(
                    1 << 16,
                    DeflateDecoder::new(BufReader::with_capacity(1 << 16, file)),
                ),
            };
            let mut head = Head {
                key: 0,
                text: Vec::new(),
                run: index,
            };
            if run
                .next(&mut head.key, &mut head.text)
                .map_err(io_error(path))?
            {
                heap.push(Reverse(head));
            }
            runs.push(run);
        }
        let mut emitted = 0;
        let mut last: Option<(u32, Vec<u8>)> = None;
        while let Some(Reverse(mut head)) = heap.pop() {
            let repeat = self.dedup
                && last
                    .as_ref()
                    .is_some_and(|(key, text)| *key == head.key && *text == head.text);
            if !repeat {
                emit(head.key, &head.text)?;
                emitted += 1;
                if self.dedup {
                    let (key, text) = last.get_or_insert_with(|| (0, Vec::new()));
                    *key = head.key;
                    text.clone_from(&head.text);
                }
            }
            let path = &self.runs[head.run];
            if runs[head.run]
                .next(&mut head.key, &mut head.text)
                .map_err(io_error(path))?
            {
                heap.push(Reverse(head));
            }
        }
        for path in &self.runs {
            fs::remove_file(path).map_err(io_error(path))?;
        }
        Ok(emitted)
    }
}

impl Drop for Sorter {
    fn drop(&mut self) {
        let _ = self.wait();
        for path in &self.runs {
            let _ = fs::remove_file(path);
        }
    }
}
